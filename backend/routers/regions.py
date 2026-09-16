from fastapi import APIRouter, Query

from models import RegionChildren, RegionDetail
from services import RegionService

from .opengin import read_service

router = APIRouter()
region_service = RegionService(read_service=read_service)


@router.get("/v1/regions/root", response_model=RegionDetail)
async def get_root_region():
    return await region_service.get_root()


@router.get(
    "/v1/regions/{region_id}/children",
    response_model=RegionChildren,
    response_model_exclude_none=True,
)
async def get_region_children(
    region_id: str,
    relation: str = Query(...),
    include_geojson: bool = Query(default=False),
):
    return await region_service.get_children(region_id, relation, include_geojson)


@router.get("/v1/regions/{region_id}", response_model=RegionDetail)
async def get_region(region_id: str):
    return await region_service.get_region(region_id)
