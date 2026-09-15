from fastapi import APIRouter, Body, Query

from models import AttributeFilterRecords, Entity, EntityCreate, Relation
from services import IngestionService, ReadService

router = APIRouter()
read_service = ReadService()
ingestion_service = IngestionService()


@router.post("/v1/entities/search")
async def search_entities(entity: Entity):
    return await read_service.get_entities(entity)


@router.post("/v1/entities/{entity_id}/relations")
async def fetch_relations(entity_id: str, relation: Relation):
    return await read_service.fetch_relations(entity_id, relation)


@router.get("/v1/entities/{entity_id}/metadata")
async def get_entity_metadata(entity_id: str):
    return await read_service.get_entity_metadata(entity_id)


@router.post("/v1/entities/{entity_id}/attributes/{attribute_name}")
async def get_entity_attribute(
    entity_id: str,
    attribute_name: str,
    startTime: str | None = None,
    endTime: str | None = None,
    fields: list[str] | None = Query(default=None),
    filters: AttributeFilterRecords | None = Body(default=None),
):
    return await read_service.get_entity_attribute(
        entityId=entity_id,
        attributeName=attribute_name,
        startTime=startTime,
        endTime=endTime,
        fields=fields,
        filters=filters,
    )


@router.post("/entities")
async def create_entity(entity: EntityCreate):
    return await ingestion_service.create_entity(entity)


@router.put("/entities/{entity_id}")
async def update_entity(entity_id: str, entity: EntityCreate):
    return await ingestion_service.update_entity(entity_id, entity)
