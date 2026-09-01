from typing import NamedTuple

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.models import Crash, CrashCluster200m, DatasetSnapshot, SourceMetadata
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
        CrashCluster200m.cluster_id.label("id"),
        CrashCluster200m.total_crashes.label("crash_count"),
        CrashCluster200m.eligible_driver_age_crashes,
        CrashCluster200m.young_driver_crashes,
        CrashCluster200m.young_driver_pct,
        CrashCluster200m.young_driver_pct_displayable,
        func.ST_X(CrashCluster200m.geom).label("longitude"),
        func.ST_Y(CrashCluster200m.geom).label("latitude"),
    )


def get_clusters_in_bbox(
    session: Session,
    bbox: BoundingBox,
    use_mock_data: bool,
    zoom: float,
) -> list[CrashClusterSummary]:
    if use_mock_data:
        return [
            CrashClusterSummary(
                id=cluster["id"],
                crash_count=cluster["crash_count"],
                eligible_driver_age_crashes=cluster["crash_count"],
                young_driver_crashes=max(1, round(cluster["crash_count"] * 0.35)),
                young_driver_pct=(
                    round(
                        100
                        * max(1, round(cluster["crash_count"] * 0.35))
                        / cluster["crash_count"],
                        2,
                    )
                    if cluster["crash_count"] >= 10
                    else None
                ),
                young_driver_pct_displayable=cluster["crash_count"] >= 10,
                longitude=cluster["longitude"],
                latitude=cluster["latitude"],
            )
            for cluster in MOCK_CLUSTERS
            if bbox.min_lon <= cluster["longitude"] <= bbox.max_lon
            and bbox.min_lat <= cluster["latitude"] <= bbox.max_lat
        ]
    if zoom < 8:
        min_crashes = 50
    elif zoom < 10:
        min_crashes = 30
    elif zoom < 12:
        min_crashes = 10
    else:
        min_crashes = 5

    try:
        viewport = func.ST_MakeEnvelope(*bbox, 4326)
        rows = session.execute(
            _cluster_projection()
            .where(func.ST_Intersects(CrashCluster200m.geom, viewport),
            CrashCluster200m.total_crashes >= min_crashes,
        )
            .order_by(CrashCluster200m.total_crashes.desc())
            .limit(500)
        ).all()
    except SQLAlchemyError as exc:
        raise CrashDataUnavailable from exc

    return [
        CrashClusterSummary(
            id=row.id,
            crash_count=row.crash_count,
            eligible_driver_age_crashes=row.eligible_driver_age_crashes,
            young_driver_crashes=row.young_driver_crashes,
            young_driver_pct=(
                float(row.young_driver_pct)
                if row.young_driver_pct is not None
                else None
            ),
            young_driver_pct_displayable=row.young_driver_pct_displayable,
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

        crash_count = cluster["crash_count"]
        young_driver_crashes = max(1, round(crash_count * 0.35))

        return CrashClusterDetail(
            id=cluster["id"],
            crash_count=crash_count,
            eligible_driver_age_crashes=crash_count,
            young_driver_crashes=young_driver_crashes,
            young_driver_pct=(
                round(100 * young_driver_crashes / crash_count, 2)
                if crash_count >= 10
                else None
            ),
            young_driver_pct_displayable=crash_count >= 10,
            longitude=cluster["longitude"],
            latitude=cluster["latitude"],
            first_year=cluster["first_year"],
            last_year=cluster["last_year"],
        )

    try:


        row = session.execute(
            _cluster_projection().where(CrashCluster200m.cluster_id == cluster_id)
        ).one_or_none()
    except SQLAlchemyError as exc:
        raise CrashDataUnavailable from exc
    if row is None:
        raise ClusterNotFound

    try:
        year_bounds = session.execute(
            select(
                func.min(func.extract("year", Crash.accident_date)),
                func.max(func.extract("year", Crash.accident_date)),
            )
        ).one()
    except SQLAlchemyError as exc:
        raise CrashDataUnavailable from exc
    last_year = int(year_bounds[1]) if year_bounds[1] is not None else None
    first_year = int(year_bounds[0]) if year_bounds[0] is not None else None
    
    return CrashClusterDetail(
        id=row.id,
        crash_count=row.crash_count,
        eligible_driver_age_crashes=row.eligible_driver_age_crashes,
        young_driver_crashes=row.young_driver_crashes,
        young_driver_pct=(
            float(row.young_driver_pct)
            if row.young_driver_pct is not None
            else None
        ),
        young_driver_pct_displayable=row.young_driver_pct_displayable,
        longitude=row.longitude,
        latitude=row.latitude,
        first_year=first_year,
        last_year=last_year,
    )


def get_crash_dataset_status(
    session: Session,
    use_mock_data: bool,
) -> RadarStatusResponse:
    if use_mock_data:
        return RadarStatusResponse(
            crash_data="available",
            last_updated=MOCK_DATASET_UPDATED,
            source="Deterministic development-only sample",
            licence="Development use only",
        )

    try:
        row = session.execute(
            select(
                DatasetSnapshot.source_updated_at,
                DatasetSnapshot.retrieved_at,
                SourceMetadata.source_name,
                SourceMetadata.licence,
            )
            .join(
                SourceMetadata,
                SourceMetadata.source_id == DatasetSnapshot.source_id,
            )
            .where(DatasetSnapshot.validation_status == "validated")
            .order_by(
                DatasetSnapshot.activated_at.desc().nullslast(),
                DatasetSnapshot.retrieved_at.desc(),
            )
            .limit(1)
        ).one_or_none()
    except SQLAlchemyError as exc:
        raise CrashDataUnavailable from exc

    if row is None:
        return RadarStatusResponse(
            crash_data="unavailable",
            last_updated=None,
        )

    return RadarStatusResponse(
        crash_data="available",
        last_updated=row.source_updated_at or row.retrieved_at,
        source=row.source_name,
        licence=row.licence,
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
                    func.Geography(CrashCluster200m.geom),
                    func.Geography(route),
                    500,
                )
            )
            .order_by(CrashCluster200m.total_crashes.desc())
            .limit(8)
        ).all()
    except SQLAlchemyError as exc:
        raise CrashDataUnavailable from exc

    return [
        TripHotspot(
            cluster_id=row.id,
            crash_count=row.crash_count,
            eligible_driver_age_crashes=row.eligible_driver_age_crashes,
            young_driver_crashes=row.young_driver_crashes,
            young_driver_pct=(
                float(row.young_driver_pct)
                if row.young_driver_pct is not None
                else None
            ),
            young_driver_pct_displayable=row.young_driver_pct_displayable,
            longitude=row.longitude,
            latitude=row.latitude,
        )
        for row in rows
    ]


def route_has_high_speed_zone(
    session: Session,
    route_geojson: str,
) -> bool:
    # Speed-zone reference data has not been loaded into the new schema yet.
    # Treat it as unavailable rather than guessing or inferring a speed limit.
    raise CrashDataUnavailable

