from typing import Any

from pydantic import BaseModel, Field

from .opengin import Kind


class NavigationOption(BaseModel):
    """A child relation the UI can offer under the current region."""

    relation: str
    label: str
    minor: str


class RegionDetail(BaseModel):
    """Hydrated region for the focused map + next panel row."""

    id: str
    name: str
    kind: Kind
    geojson: Any | None = None
    navigations: list[NavigationOption] = Field(default_factory=list)


class RegionChildItem(BaseModel):
    """One child in a dropdown. geojson is only present when requested."""

    id: str
    name: str
    kind: Kind
    hasGeometry: bool | None = None
    geojson: Any | None = None


class RegionChildren(BaseModel):
    """Children of one relation under a parent region."""

    relation: str
    items: list[RegionChildItem] = Field(default_factory=list)
