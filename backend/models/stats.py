from typing import Any

from pydantic import BaseModel, Field

from .opengin import Kind


class DatasetSummary(BaseModel):
    """A DataCategory hub linked to a region via AS_CATEGORY."""

    id: str
    name: str
    kind: Kind


class DatasetTable(DatasetSummary):
    """One hub's filtered tabular attribute for a region."""

    attribute: str
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)


class RegionStats(BaseModel):
    """All dataset tables available for one region."""

    region_id: str
    datasets: list[DatasetTable] = Field(default_factory=list)
