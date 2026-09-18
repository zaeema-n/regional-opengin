import csv
import io
from dataclasses import dataclass
from pathlib import Path

import yaml

from models import AddRelation, EntityCreate, Kind
from scripts.seed_utils import SEED_DIR, build_entity, child_relation
from utils import Util

STATS_FILE = "stats.yaml"


@dataclass
class StatsDataset:
    """One TSV → one hub (or another year of the same hub)."""

    file: str
    id: str
    name: str
    attribute: str
    date: str


@dataclass
class StatsConfig:
    """Shared hub kind/relation plus the datasets list from stats.yaml."""

    kind: Kind
    relation: str
    datasets: list[StatsDataset]


def load_stats_config(path: Path | None = None) -> StatsConfig:
    """Load stats.yaml (shared kind/relation, then each dataset entry)."""
    config_path = path or (SEED_DIR / STATS_FILE)
    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    kind_raw = data.get("kind") or {}
    datasets = [
        StatsDataset(
            file=str(item.get("file") or ""),
            id=str(item.get("id") or ""),
            name=str(item.get("name") or ""),
            attribute=str(item.get("attribute") or ""),
            date=str(item.get("date") or ""),
        )
        for item in (data.get("datasets") or [])
    ]
    return StatsConfig(
        kind=Kind(
            major=str(kind_raw.get("major") or ""),
            minor=str(kind_raw.get("minor") or ""),
        ),
        relation=str(data.get("relation") or ""),
        datasets=datasets,
    )


def _normalize_tsv_text(raw: str) -> str:
    """Collapse TSV line endings (including \\r\\r\\n) to \\n.

    These files use \\r\\r\\n. Leaving that unnormalized makes csv emit a
    blank row between every real row.
    """
    return raw.replace("\r\r\n", "\n").replace("\r\n", "\n").replace("\r", "\n")


def _cell_value(column: str, raw: str):
    """Keep entity_id as text; coerce other numeric TSV cells to float."""
    text = (raw or "").strip()
    if column == "entity_id":
        return text
    if text == "":
        return ""
    try:
        return float(text)
    except ValueError:
        return text


def read_stats_tsv(path: Path) -> tuple[list[str], list[list]]:
    """Parse a stats TSV into columns and rows (no date column yet).

    Reads bytes so Python does not turn \\r\\r\\n into blank lines first.
    Empty lines are skipped. Numeric measure cells become floats.
    """
    text = _normalize_tsv_text(path.read_bytes().decode("utf-8"))
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    try:
        header = next(reader)
    except StopIteration:
        return [], []
    columns = [name.strip() for name in header]
    if not columns or "entity_id" not in columns:
        raise ValueError(f"{path} is missing an entity_id column")

    rows: list[list] = []
    for raw_row in reader:
        if not raw_row or all(not (cell or "").strip() for cell in raw_row):
            continue
        if len(raw_row) != len(columns):
            raise ValueError(
                f"{path} row has {len(raw_row)} values, expected {len(columns)}: "
                f"{raw_row!r}"
            )
        rows.append(
            [_cell_value(column, cell) for column, cell in zip(columns, raw_row)]
        )
    return columns, rows


def row_entity_id(columns: list[str], row: list) -> str:
    """Return the entity_id cell for one TSV row."""
    return str(row[columns.index("entity_id")]).strip()


def skip_entity_id(value: object) -> bool:
    """True when entity_id is empty or the TSV sentinel 'None'."""
    text = str(value or "").strip()
    return text == "" or text == "None"


def inject_date_columns(columns: list[str]) -> list[str]:
    """Insert 'date' immediately after entity_id. Year stays off the hub id/name."""
    index = columns.index("entity_id") + 1
    if index < len(columns) and columns[index] == "date":
        return list(columns)
    return [*columns[:index], "date", *columns[index:]]


def inject_row_date(columns: list[str], row: list, date: str) -> list:
    """Copy one TSV row and inject the dataset date after entity_id."""
    index = columns.index("entity_id") + 1
    return [*row[:index], date, *row[index:]]


def table_from_kept_rows(
    columns: list[str], rows: list[list], date: str
) -> dict:
    """Build the hub attribute table: date on each kept row, not on the edge."""
    return {
        "columns": inject_date_columns(columns),
        "rows": [inject_row_date(columns, row, date) for row in rows],
    }


# PostgreSQL bind limit is 65535. OpenGIN inserts one values[] table per query
# and binds extra params beyond the cells, so stay well under the cap.
PG_SAFE_BIND_PARAMS = 50000


def table_batch_size(n_columns: int) -> int:
    """Max rows per OpenGIN tabular insert for this column count."""
    return max(1, PG_SAFE_BIND_PARAMS // max(n_columns, 1))


def chunk_table(columns: list[str], rows: list[list]) -> list[dict]:
    """Split a table into pieces that fit in one PostgreSQL INSERT."""
    batch_size = table_batch_size(len(columns))
    if not rows:
        return [{"columns": list(columns), "rows": []}]
    return [
        {
            "columns": list(columns),
            "rows": [list(row) for row in rows[i : i + batch_size]],
        }
        for i in range(0, len(rows), batch_size)
    ]


def attribute_start_time(date: str) -> str:
    """Turn yaml date (YYYY-MM-DD) into an OpenGIN startTime timestamp."""
    text = (date or "").strip()
    if not text:
        return ""
    if "T" in text:
        return text if text.endswith("Z") else f"{text}Z"
    return f"{text}T00:00:00Z"


def tabular_attribute(key: str, table: dict, date: str) -> dict:
    """OpenGIN write envelope: key + value.values[{startTime, endTime, value}].

    Large tables are split across values[] so each insert stays under
    PostgreSQL's 65535-parameter limit.
    """
    start = attribute_start_time(date)
    chunks = chunk_table(list(table.get("columns") or []), list(table.get("rows") or []))
    return {
        "key": key,
        "value": {
            "values": [
                {"startTime": start, "endTime": "", "value": chunk}
                for chunk in chunks
            ]
        },
    }


def build_hub_entity(
    dataset: StatsDataset,
    kind: Kind,
    columns: list[str],
    rows: list[list],
) -> EntityCreate:
    """Hub EntityCreate with the tabular attribute and no relationships.

    `columns` / `rows` are the kept table (date already injected). The hub
    does not carry AS_CATEGORY edges; those go on each region.
    """
    table = {"columns": list(columns), "rows": [list(row) for row in rows]}
    if rows and not Util.validate_and_sanitize_tabular_dataset(table):
        raise ValueError(f"Invalid tabular dataset for hub {dataset.id}")
    entity = build_entity({"id": dataset.id, "name": dataset.name}, kind)
    entity.attributes = [tabular_attribute(dataset.attribute, table, dataset.date)]
    return entity


def hub_update_payload(hub: EntityCreate) -> EntityCreate:
    """Hub PUT: id and attributes only. Kind is immutable and must not be sent."""
    return EntityCreate(id=hub.id, attributes=hub.attributes)


def as_category_relation(
    region_id: str, hub_id: str, relation: str
) -> AddRelation:
    """Outgoing region → hub edge via child_relation (epoch startTime)."""
    return child_relation(relation, hub_id, region_id)


def region_edge_payload(
    region_id: str, hub_id: str, relation: str
) -> EntityCreate:
    """Relationship-only PUT: region id plus one AS_CATEGORY edge to the hub.

    Unset EntityCreate fields are omitted on dump so kind is not sent.
    """
    return EntityCreate(
        id=region_id,
        relationships=[as_category_relation(region_id, hub_id, relation)],
    )
