import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.connection import get_db
from app.schemas.radar import (
    CrashClusterDetail,
    RadarClustersResponse,
    RadarDataStatus,
    RadarStatusResponse,
)
from app.services.crash_query import (
    BoundingBox,
    ClusterNotFound,
    CrashDataUnavailable,
    get_cluster_detail,
    get_clusters_in_bbox,
    get_crash_dataset_status,
)

router = APIRouter(prefix="/radar", tags=["radar"])


def parse_bbox(bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat")) -> BoundingBox:
    try:
        parts = [float(value.strip()) for value in bbox.split(",")]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="bbox must contain four numbers") from exc

    if len(parts) != 4 or not all(math.isfinite(value) for value in parts):
        raise HTTPException(status_code=422, detail="bbox must contain four finite numbers")

    min_lon, min_lat, max_lon, max_lat = parts
    if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
        raise HTTPException(status_code=422, detail="bbox coordinates or ordering are invalid")
    return BoundingBox(min_lon, min_lat, max_lon, max_lat)


@router.get("/clusters", response_model=RadarClustersResponse)
def clusters(
    bbox: Annotated[BoundingBox, Depends(parse_bbox)],
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[Session, Depends(get_db)],
) -> RadarClustersResponse:
    try:
        results = get_clusters_in_bbox(session, bbox, settings.use_mock_data)
        status = get_crash_dataset_status(session, settings.use_mock_data)
    except CrashDataUnavailable:
        return RadarClustersResponse(
            clusters=[],
            data_status=RadarDataStatus.UNAVAILABLE,
            last_updated=None,
        )
    return RadarClustersResponse(
        clusters=results,
        data_status=RadarDataStatus.AVAILABLE,
        last_updated=status.last_updated,
    )


@router.get("/clusters/{cluster_id}", response_model=CrashClusterDetail)
def cluster_detail(
    cluster_id: int,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[Session, Depends(get_db)],
) -> CrashClusterDetail:
    try:
        return get_cluster_detail(session, cluster_id, settings.use_mock_data)
    except ClusterNotFound as exc:
        raise HTTPException(status_code=404, detail="Crash cluster not found") from exc
    except CrashDataUnavailable as exc:
        raise HTTPException(status_code=503, detail="Crash data is currently unavailable") from exc


@router.get("/status", response_model=RadarStatusResponse)
def radar_status(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[Session, Depends(get_db)],
) -> RadarStatusResponse:
    try:
        return get_crash_dataset_status(session, settings.use_mock_data)
    except CrashDataUnavailable:
        return RadarStatusResponse(crash_data="unavailable", last_updated=None)
