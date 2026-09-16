import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from models import AddRelation, AddRelationValue, EntityCreate, Kind, NameValue

ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "data" / "seed"
HIERARCHY_FILE = "hierarchy.yaml"


@dataclass
class HierarchyNode:
    """One level in hierarchy.yaml (kinds and edges, not instance rows).

    parent_column / relation live on the child: they tell the parent how to
    attach this node (e.g. province.csv country_id, edge name "province").
    geojson is a path relative to data/seed/; missing or empty means no
    geometry metadata for that level.
    """

    major: str
    minor: str
    file: str
    parent_column: str | None = None
    relation: str | None = None
    geojson: str | None = None
    children: list["HierarchyNode"] = field(default_factory=list)


@dataclass
class SeedItem:
    """One entity ready to POST to OpenGIN.

    update_on_conflict is True for parents (PUT if the entity already exists)
    and False for leaves (skip on 400).
    """

    entity: EntityCreate
    update_on_conflict: bool


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a seed CSV into a list of row dicts keyed by header name.

    Returns e.g. [{"id": "LK", "name": "Sri Lanka"}].
    """
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def parse_node(raw: dict, inherited_major: str = "") -> HierarchyNode:
    """Turn one YAML mapping into a HierarchyNode, recursing into children.

    major is taken from this mapping, or inherited_major if omitted (so
    children inherit region from the root).

    Returns the node for this mapping, with children already parsed.
    """
    major = str(raw.get("major") or inherited_major)
    return HierarchyNode(
        major=major,
        minor=str(raw.get("minor") or ""),
        file=str(raw.get("file") or ""),
        parent_column=raw.get("parent_column") or None,
        relation=raw.get("relation") or None,
        geojson=raw.get("geojson") or None,
        children=[parse_node(child, major) for child in (raw.get("children") or [])],
    )


def load_hierarchy(path: Path) -> HierarchyNode:
    """Load hierarchy.yaml and return the root HierarchyNode (full tree)."""
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return parse_node(data)


def load_rows_for_tree(
    node: HierarchyNode, seed_dir: Path
) -> dict[str, list[dict[str, str]]]:
    """Walk the YAML tree and read each node's CSV if the file exists.

    Returns a dict keyed by file name, e.g.
    {"country.csv": [{"id": "LK", ...}], "province.csv": [...]}.
    Missing files are omitted (that YAML node is skipped later).
    """
    rows_by_file: dict[str, list[dict[str, str]]] = {}

    def walk(current: HierarchyNode) -> None:
        path = seed_dir / current.file
        if current.file and path.exists() and current.file not in rows_by_file:
            rows_by_file[current.file] = read_csv(path)
        for child in current.children:
            walk(child)

    walk(node)
    return rows_by_file


def _entity_name(value: str) -> NameValue:
    """Wrap a display name in the OpenGIN NameValue shape."""
    return NameValue(startTime="", endTime="", value=value)


def child_relation(
    name: str, related_entity_id: str, parent_entity_id: str
) -> AddRelation:
    """Build one parent→child edge, e.g. name="province", related_entity_id="LK-1".

    key is the unique relationship id (not the relation name) so multiple
    outgoing edges of the same type survive one OpenGIN update.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    relation_id = f"{parent_entity_id}-{name}-{related_entity_id}"
    return AddRelation(
        key=relation_id,
        value=AddRelationValue(
            relatedEntityId=related_entity_id,
            startTime=now,
            endTime="",
            id=relation_id,
            name=name,
        ),
    )


def build_entity(
    row: dict[str, str],
    kind: Kind,
    relationships: list[AddRelation] | None = None,
) -> EntityCreate:
    """Build an OpenGIN create payload from one CSV row (id + name) and a kind."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return EntityCreate(
        id=row["id"],
        kind=kind,
        created=now,
        terminated="",
        name=_entity_name(row["name"]),
        metadata=[],
        attributes=[],
        relationships=relationships or [],
    )


def collect_payloads(
    node: HierarchyNode, rows_by_file: dict[str, list[dict[str, str]]]
) -> list[SeedItem]:
    """Build SeedItems for this node and everything under it, children first.

    Recurses into loaded children, then appends this node's own CSV rows.
    Parents get relationships to matching child rows (parent_column == this id).

    Returns a flat list in insert order. Example country → province → dsd:
    [all DSDs, all provinces, then the country]. Leaves have
    update_on_conflict=False; nodes with loaded children have True.
    """
    items: list[SeedItem] = []
    # Only children whose CSV was actually loaded.
    loaded_children = [
        child for child in node.children if child.file in rows_by_file
    ]
    # Descend first: items becomes all descendants, deepest first.
    for child in loaded_children:
        items.extend(collect_payloads(child, rows_by_file))

    rows = rows_by_file.get(node.file)
    if rows is None:
        return items

    kind = Kind(major=node.major, minor=node.minor)
    is_parent = bool(loaded_children)
    for row in rows:
        relationships: list[AddRelation] = []
        for child in loaded_children:
            if not child.parent_column or not child.relation:
                continue
            for child_row in rows_by_file[child.file]:
                if child_row.get(child.parent_column) == row["id"]:
                    relationships.append(
                        child_relation(
                            child.relation, child_row["id"], row["id"]
                        )
                    )
        items.append(
            SeedItem(
                entity=build_entity(row, kind, relationships),
                update_on_conflict=is_parent,
            )
        )
    return items


def load_seed_payloads(seed_dir: Path = SEED_DIR) -> list[SeedItem]:
    """Load YAML + CSVs and return every SeedItem in OpenGIN insert order."""
    root = load_hierarchy(seed_dir / HIERARCHY_FILE)
    rows_by_file = load_rows_for_tree(root, seed_dir)
    return collect_payloads(root, rows_by_file)
