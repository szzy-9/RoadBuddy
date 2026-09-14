import json
from typing import NamedTuple

from sqlalchemy import Select, and_, func, or_, select, text, true
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.models import Crash, CrashCluster200m, DatasetSnapshot, SourceMetadata
from app.schemas.indicator import IndicatorExplanation
from app.schemas.radar import CrashClusterDetail, CrashClusterSummary, RadarStatusResponse
from app.schemas.trip import RouteRiskSegment, TripHotspot
from app.services.indicator_explanations import RADAR_CLUSTER_LIMITATION
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


def _titlecase(value: str) -> str:
    """Make an uppercase stored value readable.

    Crash road names and DCA descriptions are stored in capitals, e.g.
    "PRINCES HIGHWAY" and "REAR END(VEHICLES IN SAME LANE)". Only the casing
    changes, so the text still reflects what the dataset recorded.

    Args:
        value: The stored value.

    Returns:
        The same text in sentence case.
    """
    # Source values pack a bracket against the preceding word, e.g.
    # "REAR END(VEHICLES IN SAME LANE)", which reads badly mid-sentence.
    cleaned = " ".join(value.replace("(", " (").split())
    return cleaned[:1].upper() + cleaned[1:].lower()


def _cluster_membership(grid_x, grid_y) -> tuple:
    """Use the original 200 m rounding rule for both statistics and display."""
    projected = func.ST_Transform(Crash.geom, CLUSTER_GRID_SRID)
    return (
        Crash.geom.is_not(None),
        func.round(func.ST_X(projected) / CLUSTER_GRID_METRES) * CLUSTER_GRID_METRES == grid_x,
        func.round(func.ST_Y(projected) / CLUSTER_GRID_METRES) * CLUSTER_GRID_METRES == grid_y,
    )


def _cluster_projection() -> Select[tuple]:
    """Keep cluster identity/statistics, displaying its nearest valid member crash.

    A correlated lateral join selects one representative per cluster inside the
    same SQL statement. Spatial filters still use the stored cluster geometry.
    """
    centre = func.ST_SetSRID(
        func.ST_MakePoint(CrashCluster200m.grid_x, CrashCluster200m.grid_y),
        CLUSTER_GRID_SRID,
    )
    member = (
        select(Crash.geom.label("geom"))
        .where(
            *_cluster_membership(CrashCluster200m.grid_x, CrashCluster200m.grid_y),
            func.ST_IsValid(Crash.geom),
            ~func.ST_IsEmpty(Crash.geom),
            # A generous cell envelope uses the existing geom index to narrow
            # candidates; the rounding predicates above decide membership.
            func.ST_Intersects(
                Crash.geom,
                func.ST_Transform(func.ST_Expand(centre, CLUSTER_GRID_METRES), 4326),
            ),
        )
        .order_by(
            func.ST_Distance(func.ST_Transform(Crash.geom, CLUSTER_GRID_SRID), centre),
            Crash.accident_no,
        )
        .limit(1)
        .correlate(CrashCluster200m)
        .lateral("representative_crash")
    )
    display_geom = func.coalesce(member.c.geom, CrashCluster200m.geom)
    return select(
        CrashCluster200m.cluster_id.label("id"),
        CrashCluster200m.total_crashes.label("crash_count"),
        CrashCluster200m.eligible_driver_age_crashes,
        CrashCluster200m.young_driver_crashes,
        CrashCluster200m.young_driver_pct,
        CrashCluster200m.young_driver_pct_displayable,
        func.ST_X(display_geom).label("longitude"),
        func.ST_Y(display_geom).label("latitude"),
    ).select_from(CrashCluster200m).outerjoin(member, true())


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
            road_name=cluster.get("name"),
            dominant_crash_type=cluster.get("dominant_type"),
            wet_crashes=cluster.get("wet_count"),
            dark_crashes=cluster.get("dark_count"),
            explanation=IndicatorExplanation(
                source="RoadBuddy development sample",
                trigger=f"{crash_count} recorded injury crashes are grouped in this crash cluster.",
                limitation=RADAR_CLUSTER_LIMITATION,
            ),
        )

    try:


        row = session.execute(
            _cluster_projection()
            .add_columns(CrashCluster200m.grid_x, CrashCluster200m.grid_y)
            .where(CrashCluster200m.cluster_id == cluster_id)
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
    
    # The cluster table stores no road name or condition breakdown, so these are
    # read from the crashes that snap to the cluster's own grid point. The
    # crash's stored vicgrid_x/y are a different projection to grid_x/grid_y, so
    # the geometry is transformed rather than compared against those columns.
    in_cluster = _cluster_membership(row.grid_x, row.grid_y)

    try:
        conditions = session.execute(
            select(
                func.count().filter(Crash.has_wet_surface.is_(True)),
                func.count().filter(Crash.has_known_surface.is_(True)),
                func.count().filter(Crash.light_condition.like("Dark%")),
                func.count().filter(
                    Crash.light_condition.is_not(None),
                    Crash.light_condition != "Unk.",
                ),
            ).where(*in_cluster)
        ).one()

        # Name and type are stored apart ("PRINCES" + "HIGHWAY"), and the same
        # name recurs under different types, so both are grouped together.
        road = session.execute(
            select(Crash.road_name, Crash.road_type)
            .where(*in_cluster, Crash.road_name.is_not(None))
            .group_by(Crash.road_name, Crash.road_type)
            .order_by(func.count().desc())
            .limit(1)
        ).one_or_none()

        dominant_type = None
        if row.crash_count >= MIN_CRASHES_FOR_DOMINANT_TYPE:
            dominant_type = session.execute(
                select(Crash.dca_code_description)
                .where(*in_cluster, Crash.dca_code_description.is_not(None))
                .group_by(Crash.dca_code_description)
                .order_by(func.count().desc())
                .limit(1)
            ).scalar_one_or_none()
    except SQLAlchemyError as exc:
        raise CrashDataUnavailable from exc

    # A count is reported only where the condition was actually recorded: with
    # nothing known, a zero would read as "never happened here in the wet".
    wet_crashes = int(conditions[0]) if conditions[1] else None
    dark_crashes = int(conditions[2]) if conditions[3] else None
    road_name = (
        " ".join(word.capitalize() for word in " ".join(p for p in road if p).split())
        if road
        else None
    )
    dominant_type = _titlecase(dominant_type) if dominant_type else None

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
        road_name=road_name,
        dominant_crash_type=dominant_type,
        wet_crashes=wet_crashes,
        dark_crashes=dark_crashes,
        explanation=IndicatorExplanation(
            source="Victorian Road Crash Data",
            trigger=f"{row.crash_count} recorded injury crashes are grouped in this crash cluster.",
            limitation=RADAR_CLUSTER_LIMITATION,
        ),
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


# Spacing of the clustering grid, in metres, and the projection its coordinates
# are expressed in. Cluster rows store the grid point each crash was snapped to,
# so membership is "rounds to this same point" rather than "falls in this box".
# Verified against RDS: grid_x/grid_y equal ST_Transform(geom, 32755) exactly,
# and the rounding below reproduces total_crashes for every cluster checked.
CLUSTER_GRID_METRES = 200
CLUSTER_GRID_SRID = 32755

# Below this, "most were X" would rest on one or two records, so the dominant
# crash type is withheld rather than shown.
MIN_CRASHES_FOR_DOMINANT_TYPE = 5


# Radius searched around the origin and destination, in metres. Wide enough to
# cover the streets around an address, not the roads between two suburbs.
ENDPOINT_SEARCH_RADIUS_METRES = 1000
ROUTE_CORRIDOR_METRES = 150


def _near_geometry(geom, route, radius):
    """Metre-based distance plus a bounding envelope for the existing geom index."""
    corridor = func.ST_Buffer(func.Geography(route), radius)
    return and_(
        geom.op("&&")(func.ST_Envelope(func.Geometry(corridor))),
        func.ST_DWithin(func.Geography(geom), func.Geography(route), radius),
    )


def get_endpoint_hotspots(
    session: Session,
    origin_longitude: float,
    origin_latitude: float,
    destination_longitude: float,
    destination_latitude: float,
    use_mock_data: bool,
    *,
    route_geojson: str | None = None,
) -> list[TripHotspot]:
    """Find the largest clusters near the route, or endpoints for legacy callers.

    Production trips supply the ORS polyline, searching a 150 m corridor along
    it. Cluster grid geometry determines proximity; markers use member crashes.

    Args:
        session: Database session.
        origin_longitude: Origin longitude in decimal degrees.
        origin_latitude: Origin latitude in decimal degrees.
        destination_longitude: Destination longitude in decimal degrees.
        destination_latitude: Destination latitude in decimal degrees.
        use_mock_data: When true, return the deterministic sample instead.
        route_geojson: Existing driving LineString; omit for endpoint-only search.

    Returns:
        Up to eight hotspots within the route corridor (or endpoint radii),
        ordered by crash count, highest first.

    Raises:
        CrashDataUnavailable: When the crash tables cannot be queried.
    """
    if use_mock_data:
        from app.services.mock_data import mock_trip_hotspots

        return mock_trip_hotspots()

    try:
        endpoints = [
            func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
            for longitude, latitude in (
                (origin_longitude, origin_latitude),
                (destination_longitude, destination_latitude),
            )
        ]
        # Geography gives the radius an explicit metre unit while stored
        # geometries remain SRID 4326.
        near_endpoint = or_(
            *[
                func.ST_DWithin(
                    func.Geography(CrashCluster200m.geom),
                    func.Geography(endpoint),
                    ENDPOINT_SEARCH_RADIUS_METRES,
                )
                for endpoint in endpoints
            ]
        )
        proximity = (
            _near_geometry(
                CrashCluster200m.geom,
                func.ST_SetSRID(func.ST_GeomFromGeoJSON(route_geojson), 4326),
                ROUTE_CORRIDOR_METRES,
            )
            if route_geojson is not None else near_endpoint
        )
        rows = session.execute(
            _cluster_projection()
            .where(proximity)
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


def get_route_segment_crash_counts(
    session: Session,
    segments: list[RouteRiskSegment],
) -> dict[int, int | None]:
    """Count recorded crashes within 150 m of every section in one PostGIS query.

    Each crash is counted once per section; adjoining corridors may overlap.
    An empty spatial dataset is unavailable, while zero near a section in a
    populated dataset is a real zero. No speed or weather inference is made.
    """
    if not segments:
        return {}
    payload = json.dumps([
        {"index": segment.index, "geometry": segment.geometry.model_dump()}
        for segment in segments
    ])
    try:
        rows = session.execute(text("""
            WITH sections AS (
                SELECT item.index,
                    ST_SetSRID(ST_GeomFromGeoJSON(item.geometry::text), 4326) AS geom
                FROM jsonb_to_recordset(CAST(:segments AS jsonb))
                    AS item(index integer, geometry jsonb)
            ), availability AS (
                SELECT EXISTS (
                    SELECT 1 FROM crash
                    WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom) AND ST_IsValid(geom)
                ) AS available
            )
            SELECT sections.index,
                CASE WHEN (SELECT available FROM availability)
                    THEN count(crash.accident_no) ELSE NULL END AS nearby_crash_count
            FROM sections
            LEFT JOIN crash ON
                crash.geom && ST_Envelope(ST_Buffer(sections.geom::geography, :radius)::geometry)
                AND ST_DWithin(crash.geom::geography, sections.geom::geography, :radius)
            GROUP BY sections.index
            ORDER BY sections.index
        """), {"segments": payload, "radius": ROUTE_CORRIDOR_METRES}).all()
    except SQLAlchemyError as exc:
        raise CrashDataUnavailable from exc
    return {row.index: row.nearby_crash_count for row in rows}


def route_has_high_speed_zone(
    session: Session,
    route_geojson: str,
) -> bool:
    # Speed-zone reference data has not been loaded into the new schema yet.
    # Treat it as unavailable rather than guessing or inferring a speed limit.
    raise CrashDataUnavailable

