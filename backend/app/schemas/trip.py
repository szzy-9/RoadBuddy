from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

Address = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class ConcernLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGHER = "higher"


class DataAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class TripCheckRequest(BaseModel):
    origin: Address
    destination: Address
    departure_time: datetime

    @field_validator("departure_time")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("departure_time must include a timezone offset")
        return value


class LocationSuggestion(BaseModel):
    label: str
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)


class LocationSuggestionsResponse(BaseModel):
    suggestions: list[LocationSuggestion]


class GeoPoint(BaseModel):
    """A geographic coordinate pair resolved from a free-text address."""

    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)


class RouteSummary(BaseModel):
    """Origin, destination and headline metrics for a checked route."""

    origin: str
    destination: str
    origin_point: GeoPoint
    destination_point: GeoPoint
    distance_km: float = Field(ge=0)
    duration_minutes: int = Field(ge=0)


class RiskFactor(BaseModel):
    type: Literal["rain", "after_dark", "high_speed_zone", "significant_crash_history"]
    label: str


class TripHotspot(BaseModel):
    cluster_id: int
    crash_count: int = Field(ge=0)
    eligible_driver_age_crashes: int = Field(ge=0)
    young_driver_crashes: int = Field(ge=0)
    young_driver_pct: float | None = Field(default=None, ge=0, le=100)
    young_driver_pct_displayable: bool
    longitude: float
    latitude: float


class AlternativeDeparture(BaseModel):
    departure_time: datetime
    concern_level: ConcernLevel
    factor_count: int = Field(ge=0)


class DepartureComparisonOption(BaseModel):
    """One departure option, with a short reason for its concern level."""

    departure_time: datetime
    arrival_time: datetime
    concern_level: ConcernLevel
    factor_count: int = Field(ge=0)
    factors: list["RiskFactor"] = Field(default_factory=list)
    reason: str | None = None


class DepartureComparison(BaseModel):
    selected: DepartureComparisonOption
    thirty_minutes_later: DepartureComparisonOption
    difference_summary: str | None = None


class TripDataStatus(BaseModel):
    weather: DataAvailability
    crash_data: DataAvailability
    speed_zones: DataAvailability


class TripCheckResponse(BaseModel):
    route: RouteSummary
    concern_level: ConcernLevel
    factors: list[RiskFactor]
    hotspots: list[TripHotspot]
    alternative_departure: AlternativeDeparture | None
    departure_comparison: DepartureComparison
    data_status: TripDataStatus
    rule_version: str

