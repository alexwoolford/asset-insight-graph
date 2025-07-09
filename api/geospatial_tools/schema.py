from typing import List

from pydantic import BaseModel, Field


class get_assets_in_state(BaseModel):
    """Retrieve assets located in the specified U.S. state."""

    state: str = Field(..., description="Full state name, e.g. California")


class get_assets_in_region(BaseModel):
    """Retrieve assets located in a U.S. region such as west or northeast."""

    region: str = Field(..., description="Region name")


class get_assets_within_distance(BaseModel):
    """Retrieve assets within a distance of another asset or city."""

    distance: int = Field(..., description="Numeric distance value")
    unit: str = Field(..., description="km or miles")
    reference: str = Field(..., description="Reference asset or city")


class get_portfolio_distribution(BaseModel):
    """Return asset counts by platform and region."""


class get_assets_by_type(BaseModel):
    """Retrieve assets of the given building type."""

    building_type: str = Field(..., description="commercial, residential, etc")


class get_total_assets(BaseModel):
    """Return the total number of assets."""


def get_tool_schemas() -> List[type[BaseModel]]:
    return [
        get_assets_in_state,
        get_assets_in_region,
        get_assets_within_distance,
        get_portfolio_distribution,
        get_assets_by_type,
        get_total_assets,
    ]
