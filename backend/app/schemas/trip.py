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


class RouteSummary(BaseModel):
    origin: str
    destination: str
    distance_km: float = Field(ge=0)
    duration_minutes: int = Field(ge=0)


class RiskFactor(BaseModel):
    type: Literal["rain", "after_dark", "high_speed_zone", "significant_crash_history"]
    label: str


class TripHotspot(BaseModel):
    cluster_id: int
    name: str | None
    crash_count: int = Field(ge=0)
    dominant_type: str | None
    wet_count: int = Field(ge=0)
    dark_count: int = Field(ge=0)
    longitude: float
    latitude: float


class AlternativeDeparture(BaseModel):
    departure_time: datetime
    concern_level: ConcernLevel
    factor_count: int = Field(ge=0)


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
    data_status: TripDataStatus
    rule_version: str
