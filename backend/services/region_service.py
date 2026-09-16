import asyncio
import json
from pathlib import Path

from exception import BadRequestError, NotFoundError
from models import Entity, Kind, Relation
from models.regions import (
    NavigationOption,
    RegionChildItem,
    RegionChildren,
    RegionDetail,
)
from scripts.seed_utils import HIERARCHY_FILE, SEED_DIR, HierarchyNode, load_hierarchy
from services.read_service import ReadService
from utils.util_functions import Util

HYDRATE_CONCURRENCY = 10  # max parallel OpenGIN searches when filling a children dropdown
COUNTRY_KIND = Kind(major="region", minor="country")


def relation_label(relation: str) -> str:
    """Turn a YAML relation slug into a panel label (province → Province)."""
    return Util.format_attribute_name(relation)


def extract_geojson(metadata) -> dict | None:
    """Find the geojson entry in an OpenGIN metadata payload.

    Live OpenGIN returns {"geojson": "<protobuf StringValue JSON>"}. Seed-style
    payloads may already be a FeatureCollection dict or [{key, value}].
    """
    if metadata is None:
        return None

    if isinstance(metadata, dict):
        if metadata.get("key") == "geojson":
            return _as_feature_collection(metadata.get("value"))
        if "geojson" in metadata:
            return _as_feature_collection(metadata.get("geojson"))
        for nested_key in ("body", "metadata", "items", "data"):
            if nested_key in metadata:
                found = extract_geojson(metadata[nested_key])
                if found is not None:
                    return found
        return None

    if isinstance(metadata, list):
        for entry in metadata:
            found = extract_geojson(entry)
            if found is not None:
                return found

    return None


def _as_feature_collection(value) -> dict | None:
    """Decode protobuf if needed, then return a FeatureCollection dict."""
    value = _decode_geojson_value(value)
    if not isinstance(value, dict):
        return None
    if value.get("type") == "Feature":
        return {"type": "FeatureCollection", "features": [value]}
    return value


def _decode_geojson_value(value):
    """Turn an OpenGIN geojson metadata value into a GeoJSON dict.

    Live reads wrap the FeatureCollection JSON in google.protobuf.StringValue
    ({typeUrl, value: hex}). Decode that with Util.decode_protobuf_attribute_name,
    then json.loads. Already-decoded dicts pass through.
    """
    if isinstance(value, dict):
        if value.get("type") in ("FeatureCollection", "Feature"):
            return value
        if _is_protobuf_envelope(value):
            decoded = Util.decode_protobuf_attribute_name(json.dumps(value))
            return _parse_json_object(decoded)
        return value
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if _is_protobuf_envelope_text(stripped):
        decoded = Util.decode_protobuf_attribute_name(stripped)
        parsed = _parse_json_object(decoded)
        if parsed is not None:
            return parsed
    return _parse_json_object(stripped)


def _is_protobuf_envelope(value: dict) -> bool:
    return "value" in value and bool(value.get("typeUrl") or value.get("type_url"))


def _is_protobuf_envelope_text(value: str) -> bool:
    return value.startswith("{") and ("typeUrl" in value or "type_url" in value)


def _parse_json_object(raw: str | None):
    if not raw or raw == "Unknown":
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def geojson_has_geometry(geojson) -> bool:
    """True if the FeatureCollection has at least one feature with geometry."""
    if not isinstance(geojson, dict):
        return False
    features = geojson.get("features") or []
    return any(isinstance(feature, dict) and feature.get("geometry") for feature in features)


class RegionService:
    """Compose OpenGIN reads with hierarchy.yaml for the region map UI.

    YAML answers "what child types can sit under this kind".
    The graph answers "which child entities actually exist".
    """

    def __init__(
        self,
        read_service: ReadService | None = None,
        hierarchy_path: Path | None = None,
    ):
        """Load hierarchy.yaml once and index nodes by kind.minor."""
        self._read = read_service or ReadService()
        path = hierarchy_path or (SEED_DIR / HIERARCHY_FILE) # for now get hierarchy from yaml
        self._tree = load_hierarchy(path)
        self._by_minor: dict[str, HierarchyNode] = {}
        self._index(self._tree)

    def _index(self, node: HierarchyNode) -> None:
        """Recursively fill _by_minor: kind.minor → the full YAML node.

        The value is the node (with .children), not just the minor string, so
        navigations_for can look up a kind and read its child types in O(1).
        """
        if node.minor:
            self._by_minor[node.minor] = node
        for child in node.children:
            self._index(child)

    def navigations_for(self, minor: str) -> list[NavigationOption]:
        """Return the child types YAML allows under this kind (schema, not graph).

        Country → [province]; province → [administrative_district, electoral_district].
        A leaf kind (GND) returns [].
        """
        node = self._by_minor.get(minor)
        if node is None:
            return []
        return [
            NavigationOption(
                relation=child.relation,
                label=relation_label(child.relation),
                minor=child.minor,
            )
            for child in node.children
            if child.relation
        ]

    async def get_root(self) -> RegionDetail:
        """Find the country entity (Sri Lanka / LK) and hydrate it like get_region."""
        matches = await self._read.get_entities(Entity(kind=COUNTRY_KIND))
        if not matches:
            raise NotFoundError("Root country region not found")
        return await self._hydrate(matches[0])

    async def get_region(self, region_id: str) -> RegionDetail:
        """Load one region by id: name, kind, geojson, and next navigation types."""
        entity = await self._get_entity_by_id(region_id)
        if entity is None:
            raise NotFoundError(f"Region {region_id} not found")
        return await self._hydrate(entity)

    async def get_children(
        self,
        region_id: str,
        relation: str,
        include_geojson: bool = False,
    ) -> RegionChildren:
        """List children of one relation for a dropdown (names only by default).

        1. Fetch outgoing relation rows (relatedEntityId only).
        2. Search each id for name/kind, at most HYDRATE_CONCURRENCY at a time.
        3. If include_geojson, also pull metadata for sibling map outlines.
        """
        relation_name = (relation or "").strip()
        if not relation_name:
            raise BadRequestError("relation is required")

        rows = await self._read.fetch_relations(
            region_id,
            Relation(name=relation_name, direction="OUTGOING"),
        )
        child_ids = [row.relatedEntityId for row in rows if row.relatedEntityId]
        semaphore = asyncio.Semaphore(HYDRATE_CONCURRENCY)

        async def hydrate_one(entity_id: str) -> RegionChildItem | None:
            async with semaphore:
                return await self._hydrate_child(entity_id, include_geojson)

        items = await asyncio.gather(*(hydrate_one(entity_id) for entity_id in child_ids))
        return RegionChildren(
            relation=relation_name,
            items=[item for item in items if item is not None],
        )

    async def _hydrate(self, entity: Entity) -> RegionDetail:
        """Attach geojson (from OpenGIN metadata) and YAML navigations to an entity."""
        return RegionDetail(
            id=entity.id,
            name=entity.name,
            kind=entity.kind,
            geojson=await self._geojson_for(entity.id),
            navigations=self.navigations_for(entity.kind.minor),
        )

    async def _hydrate_child(
        self, entity_id: str, include_geojson: bool
    ) -> RegionChildItem | None:
        """Resolve one related id to a dropdown row; skip ids OpenGIN cannot find.

        GeoJSON is fetched only when include_geojson is true (sibling outlines).
        """
        entity = await self._get_entity_by_id(entity_id)
        if entity is None:
            return None
        geojson = None
        has_geometry = None
        if include_geojson:
            geojson = await self._geojson_for(entity_id)
            has_geometry = geojson_has_geometry(geojson)
        return RegionChildItem(
            id=entity.id,
            name=entity.name,
            kind=entity.kind,
            hasGeometry=has_geometry,
            geojson=geojson,
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

    async def _geojson_for(self, entity_id: str):
        """GET entity metadata and pull the geojson key; None if the entity has no geometry."""
        try:
            metadata = await self._read.get_entity_metadata(entity_id)
        except NotFoundError:
            return None
        return extract_geojson(metadata)
