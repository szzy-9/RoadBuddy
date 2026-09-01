from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RadarDataStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class CrashClusterSummary(BaseModel):
    id: int
    crash_count: int = Field(ge=0)
    eligible_driver_age_crashes: int = Field(ge=0)
    young_driver_crashes: int = Field(ge=0)
    young_driver_pct: float | None = Field(default=None, ge=0, le=100)
    young_driver_pct_displayable: bool
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)


class CrashClusterDetail(CrashClusterSummary):
    first_year: int | None = None
    last_year: int | None = None


class RadarClustersResponse(BaseModel):
    clusters: list[CrashClusterSummary]
    data_status: RadarDataStatus
    last_updated: datetime | None


class RadarStatusResponse(BaseModel):
    crash_data: RadarDataStatus
    last_updated: datetime | None
    source: str | None = None
    licence: str | None = None

