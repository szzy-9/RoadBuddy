from typing import NamedTuple

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.models import CrashCluster, CrashRecord, DatasetMetadata, SpeedZone
from app.schemas.radar import CrashClusterDetail, CrashClusterSummary, RadarStatusResponse
from app.schemas.trip import TripHotspot
from app.services.mock_data import MOCK_CLUSTERS, MOCK_DATASET_UPDATED


class BoundingBox(NamedTuple):
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float


class CrashDataUnavailable(Exception):
    pass


class ClusterNotFound(Exception):
    pass


def _cluster_projection() -> Select[tuple]:
    return select(
        CrashCluster.id,
        CrashCluster.name,
        CrashCluster.crash_count,
        CrashCluster.dominant_type,
        CrashCluster.wet_count,
        CrashCluster.dark_count,
        func.ST_X(CrashCluster.geometry).label("longitude"),
        func.ST_Y(CrashCluster.geometry).label("latitude"),
    )


def get_clusters_in_bbox(
    session: Session,
    bbox: BoundingBox,
    use_mock_data: bool,
) -> list[CrashClusterSummary]:
    if use_mock_data:
        return [
            CrashClusterSummary(
                id=cluster["id"],
                name=cluster["name"],
                crash_count=cluster["crash_count"],
                dominant_type=cluster["dominant_type"],
                longitude=cluster["longitude"],
                latitude=cluster["latitude"],
            )
            for cluster in MOCK_CLUSTERS
            if bbox.min_lon <= cluster["longitude"] <= bbox.max_lon
            and bbox.min_lat <= cluster["latitude"] <= bbox.max_lat
        ]

    try:
        viewport = func.ST_MakeEnvelope(*bbox, 4326)
        rows = session.execute(
            _cluster_projection()
            .where(func.ST_Intersects(CrashCluster.geometry, viewport))
            .order_by(CrashCluster.crash_count.desc())
            .limit(500)
        ).all()
    except SQLAlchemyError as exc:
        raise CrashDataUnavailable from exc

    return [
        CrashClusterSummary(
            id=row.id,
            name=row.name,
            crash_count=row.crash_count,
            dominant_type=row.dominant_type,
            longitude=row.longitude,
            latitude=row.latitude,
        )
        for row in rows
    ]


def get_cluster_detail(
    session: Session,
    cluster_id: int,
    use_mock_data: bool,
) -> CrashClusterDetail:
    if use_mock_data:
        cluster = next((item for item in MOCK_CLUSTERS if item["id"] == cluster_id), None)
        if cluster is None:
            raise ClusterNotFound
        return CrashClusterDetail(**cluster)

    try:
        row = session.execute(
            _cluster_projection().where(CrashCluster.id == cluster_id)
        ).one_or_none()
    except SQLAlchemyError as exc:
        raise CrashDataUnavailable from exc
    if row is None:
        raise ClusterNotFound

    try:
        year_bounds = session.execute(
            select(
                func.min(func.extract("year", CrashRecord.crash_date)),
                func.max(func.extract("year", CrashRecord.crash_date)),
            )
        ).one()
    except SQLAlchemyError as exc:
        raise CrashDataUnavailable from exc
    last_year = int(year_bounds[1]) if year_bounds[1] is not None else None
    first_year = last_year - 5 if last_year is not None else None
    return CrashClusterDetail(
        id=row.id,
        name=row.name,
        crash_count=row.crash_count,
        dominant_type=row.dominant_type,
        wet_count=row.wet_count,
        dark_count=row.dark_count,
        longitude=row.longitude,
        latitude=row.latitude,
        first_year=first_year,
        last_year=last_year,
    )


def get_crash_dataset_status(session: Session, use_mock_data: bool) -> RadarStatusResponse:
    if use_mock_data:
        return RadarStatusResponse(
            crash_data="available",
            last_updated=MOCK_DATASET_UPDATED,
            source="Deterministic development-only sample",
            licence="Development use only",
        )

    try:
        metadata = session.scalar(
            select(DatasetMetadata).where(DatasetMetadata.dataset_name == "crash_records")
        )
    except SQLAlchemyError as exc:
        raise CrashDataUnavailable from exc
    if metadata is None:
        return RadarStatusResponse(crash_data="unavailable", last_updated=None)
    return RadarStatusResponse(
        crash_data="available",
        last_updated=metadata.last_updated,
        source=metadata.source,
        licence=metadata.licence,
    )


def get_route_hotspots(
    session: Session,
    route_geojson: str,
    use_mock_data: bool,
) -> list[TripHotspot]:
    if use_mock_data:
        from app.services.mock_data import mock_trip_hotspots

        return mock_trip_hotspots()

    try:
        route = func.ST_SetSRID(func.ST_GeomFromGeoJSON(route_geojson), 4326)
        # Geography gives the corridor an explicit metre unit while stored
        # geometries remain SRID 4326.
        rows = session.execute(
            _cluster_projection()
            .where(
                func.ST_DWithin(
                    func.Geography(CrashCluster.geometry),
                    func.Geography(route),
                    500,
                )
            )
            .order_by(CrashCluster.crash_count.desc())
            .limit(8)
        ).all()
    except SQLAlchemyError as exc:
        raise CrashDataUnavailable from exc

    return [
        TripHotspot(
            cluster_id=row.id,
            name=row.name,
            crash_count=row.crash_count,
            dominant_type=row.dominant_type,
            wet_count=row.wet_count,
            dark_count=row.dark_count,
            longitude=row.longitude,
            latitude=row.latitude,
        )
        for row in rows
    ]


def route_has_high_speed_zone(session: Session, route_geojson: str) -> bool:
    try:
        route = func.ST_SetSRID(func.ST_GeomFromGeoJSON(route_geojson), 4326)
        return session.scalar(
            select(func.count(SpeedZone.id) > 0).where(
                SpeedZone.speed_limit >= 80,
                func.ST_DWithin(
                    func.Geography(SpeedZone.geometry),
                    func.Geography(route),
                    40,
                ),
            )
        ) or False
    except SQLAlchemyError as exc:
        raise CrashDataUnavailable from exc
