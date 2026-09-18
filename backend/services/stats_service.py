import asyncio
import json
from pathlib import Path

from exception import BadRequestError, NotFoundError
from models import AttributeFilterRecord, AttributeFilterRecords, Entity, Relation
from models.stats import DatasetTable, RegionStats
from scripts.seed_stats_utils import load_stats_config
from services.read_service import ReadService
from utils.util_functions import Util

HYDRATE_CONCURRENCY = 10  # max parallel OpenGIN searches / attribute reads


def normalize_attribute_table(payload) -> tuple[list[str], list[list]]:
    """Flatten an OpenGIN attribute read into (columns, rows).

    Live reads return {start, end, value} where value is a JSON string of a
    google.protobuf.Struct envelope (typeUrl + hex). Util decodes that to the
    inner table JSON. Multiple records (chunks) are concatenated.
    Bare tables, values[] envelopes, and StringValue wrapping still work.
    """
    tables = list(_iter_tables(payload))
    if not tables:
        return [], []
    columns = tables[0][0]
    rows: list[list] = []
    for _, chunk_rows in tables:
        rows.extend(chunk_rows)
    return columns, rows


def _iter_tables(payload):
    """Yield (columns, rows) tables found in an attribute payload."""
    payload = _maybe_parse_json(payload)
    if Util.is_protobuf_envelope(payload):
        decoded = Util.decode_protobuf_attribute_name(payload)
        if decoded and decoded != "Unknown":
            yield from _iter_tables(decoded)
        return
    if isinstance(payload, dict):
        if "columns" in payload:
            yield (
                [str(column) for column in (payload.get("columns") or [])],
                list(payload.get("rows") or []),
            )
            return
        for key in ("values", "value", "body", "data", "attribute"):
            if key in payload:
                yield from _iter_tables(payload[key])
        return
    if isinstance(payload, list):
        for item in payload:
            yield from _iter_tables(item)


def _maybe_parse_json(payload):
    if not isinstance(payload, str):
        return payload
    stripped = payload.strip()
    if not stripped or not stripped.startswith(("{", "[")):
        return payload
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return payload


class StatsService:
    """Compose OpenGIN reads with stats.yaml for the region data panel.

    YAML answers which relation links regions to hubs, which kind those hubs
    have, and which tabular attribute to read on each hub id.
    The graph answers which hubs are actually attached to a region.
    """

    def __init__(
        self,
        read_service: ReadService | None = None,
        stats_path: Path | None = None,
    ):
        """Load stats.yaml once and index hub id → attribute name."""
        self._read = read_service or ReadService()
        self._config = load_stats_config(stats_path)
        self._attribute_by_hub_id = {
            dataset.id: dataset.attribute
            for dataset in self._config.datasets
            if dataset.id and dataset.attribute
        }

    async def get_region_stats(self, region_id: str) -> RegionStats:
        """Discover DataCategory hubs on a region and load each table.

        1. Outgoing AS_CATEGORY (name from yaml) → related hub ids.
        2. Search each id; keep hubs whose kind matches yaml.
        3. Map hub id → attribute from yaml; skip hubs with no mapping.
        4. Filtered attribute reads in parallel. A failed or unreadable
           table becomes columns/rows [] so one hub cannot fail the panel.
        """
        stripped = (region_id or "").strip()
        if not stripped:
            raise BadRequestError("region_id is required")

        hubs = await self._available_hubs(stripped)
        pending = [
            (hub, self._attribute_by_hub_id[hub.id])
            for hub in hubs
            if hub.id in self._attribute_by_hub_id
        ]
        if not pending:
            return RegionStats(region_id=stripped, datasets=[])

        semaphore = asyncio.Semaphore(HYDRATE_CONCURRENCY)

        async def load_one(hub: Entity, attribute: str) -> DatasetTable:
            async with semaphore:
                return await self._read_table(hub, attribute, stripped)

        datasets = await asyncio.gather(
            *(load_one(hub, attribute) for hub, attribute in pending)
        )
        return RegionStats(region_id=stripped, datasets=list(datasets))

    async def _available_hubs(self, region_id: str) -> list[Entity]:
        """Outgoing category relations, hydrated and filtered to yaml kind."""
        rows = await self._read.fetch_relations(
            region_id,
            Relation(name=self._config.relation, direction="OUTGOING"),
        )
        hub_ids = [row.relatedEntityId for row in rows if row.relatedEntityId]
        if not hub_ids:
            return []

        semaphore = asyncio.Semaphore(HYDRATE_CONCURRENCY)

        async def hydrate_one(entity_id: str) -> Entity | None:
            async with semaphore:
                return await self._get_entity_by_id(entity_id)

        entities = await asyncio.gather(
            *(hydrate_one(entity_id) for entity_id in hub_ids)
        )
        return [
            entity
            for entity in entities
            if entity is not None and self._is_stats_hub(entity)
        ]

    def _is_stats_hub(self, entity: Entity) -> bool:
        expected = self._config.kind
        return (
            entity.kind.major == expected.major
            and entity.kind.minor == expected.minor
        )

    async def _get_entity_by_id(self, entity_id: str) -> Entity | None:
        """Search OpenGIN by id; return None if missing rather than failing the list."""
        stripped = (entity_id or "").strip()
        if not stripped:
            return None
        try:
            matches = await self._read.get_entities(Entity(id=stripped))
        except NotFoundError:
            return None
        for match in matches:
            if match.id == stripped:
                return match
        return None

    async def _read_table(
        self, hub: Entity, attribute: str, region_id: str
    ) -> DatasetTable:
        """Filtered attribute read for one hub; empty table on failure."""
        try:
            payload = await self._read.get_entity_attribute(
                entityId=hub.id,
                attributeName=attribute,
                filters=AttributeFilterRecords(
                    records=[
                        AttributeFilterRecord(
                            field_name="entity_id",
                            operator="eq",
                            value=region_id,
                        )
                    ]
                ),
            )
            columns, rows = normalize_attribute_table(payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            columns, rows = [], []
        return DatasetTable(
            id=hub.id,
            name=hub.name,
            kind=hub.kind,
            attribute=attribute,
            columns=columns,
            rows=rows,
        )
