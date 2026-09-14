import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError

from app.services.crash_query import (
    BoundingBox,
    CrashDataUnavailable,
    get_cluster_detail,
    get_clusters_in_bbox,
    get_endpoint_hotspots,
)


def test_radar_bbox_returns_only_visible_clusters(client: TestClient) -> None:
    response = client.get("/api/radar/clusters?bbox=144.70,-37.90,144.80,-37.82&zoom=12")

    assert response.status_code == 200
    clusters = response.json()["clusters"]
    assert [cluster["id"] for cluster in clusters] == [101]


@pytest.mark.parametrize(
    "bbox",
    [
        "bad",
        "144,-38,145",
        "145,-38,144,-37",
        "144,-100,145,-37",
        "nan,-38,145,-37",
    ],
)
def test_radar_bbox_validation(client: TestClient, bbox: str) -> None:
    response = client.get("/api/radar/clusters", params={"bbox": bbox, "zoom": 12})

    assert response.status_code == 422


def test_cluster_detail(client: TestClient) -> None:
    response = client.get("/api/radar/clusters/101")

    assert response.status_code == 200
    detail = response.json()
    assert detail["crash_count"] == 12
    assert detail["young_driver_crashes"] == 4
    assert detail["young_driver_pct"] == 33.33
    assert detail["young_driver_pct_displayable"] is True
    assert detail["explanation"] == {
        "source": "RoadBuddy development sample",
        "trigger": "12 recorded injury crashes are grouped in this crash cluster.",
    }


def test_radar_explanation_is_optional_for_older_details(client: TestClient) -> None:
    from app.schemas.radar import CrashClusterDetail

    detail = client.get("/api/radar/clusters/101").json()
    detail.pop("explanation", None)
    assert CrashClusterDetail.model_validate(detail).explanation is None


def test_real_cluster_explanation_uses_actual_crash_count() -> None:
    row = SimpleNamespace(
        id=9, crash_count=7, eligible_driver_age_crashes=7, young_driver_crashes=1,
        young_driver_pct=None, young_driver_pct_displayable=False,
        longitude=144.9, latitude=-37.8, grid_x=320000, grid_y=5810000,
    )
    session = Mock()
    session.execute.side_effect = [
        Mock(one_or_none=Mock(return_value=row)),
        Mock(one=Mock(return_value=(2020, 2024))),
        Mock(one=Mock(return_value=(2, 7, 3, 7))),
        Mock(one_or_none=Mock(return_value=("PRINCES", "HIGHWAY"))),
        Mock(scalar_one_or_none=Mock(return_value="REAR END")),
    ]
    detail = get_cluster_detail(session, 9, use_mock_data=False)
    assert detail.model_dump()["explanation"] == {
        "source": "Victorian Road Crash Data",
        "trigger": "7 recorded injury crashes are grouped in this crash cluster.",
    }
    assert detail.crash_count == 7
    assert detail.wet_crashes == 2
    assert detail.dark_crashes == 3


def test_radar_data_failure_returns_unavailable_without_clusters(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(*_args, **_kwargs):
        raise CrashDataUnavailable

    monkeypatch.setattr("app.api.radar.get_clusters_in_bbox", unavailable)

    response = client.get("/api/radar/clusters?bbox=144.70,-37.90,144.80,-37.82&zoom=12")

    assert response.status_code == 200
    assert response.json() == {
        "clusters": [],
        "data_status": "unavailable",
        "last_updated": None,
    }


def test_spatial_query_boundary_converts_database_failure() -> None:
    class BrokenSession:
        def execute(self, _statement):
            raise SQLAlchemyError("database unavailable")

    with pytest.raises(CrashDataUnavailable):
        get_clusters_in_bbox(
            BrokenSession(),  # type: ignore[arg-type]
            BoundingBox(144.0, -38.0, 145.0, -37.0),
            use_mock_data=False,
            zoom=12,
        )


@pytest.mark.parametrize("member_available", [True, False])
def test_cluster_display_uses_nearest_member_without_changing_statistics(
    postgis_session, member_available,
) -> None:
    session = postgis_session
    session.execute(text("""
        INSERT INTO crash_cluster_200m VALUES
        (123, 320000, 5810000, 12, 10, 4, 40, true,
         ST_Transform(ST_SetSRID(ST_MakePoint(320000, 5810000), 32755), 4326))
    """))
    session.execute(text("""
        INSERT INTO crash VALUES
        ('missing', '2020-01-01', NULL, NULL, NULL, NULL, NULL, NULL, NULL)
    """))
    if member_available:
        session.execute(text("""
            INSERT INTO crash (accident_no, accident_date, geom)
            SELECT id, '2021-01-01',
                ST_Transform(ST_SetSRID(ST_MakePoint(x, y), 32755), 4326)
            FROM (VALUES
                ('farther', 320090, 5810090),
                ('nearest', 320010, 5810020),
                ('tied-later', 320010, 5810020),
                ('different-cell', 320110, 5810000)
            ) AS points(id, x, y)
        """))
    expected = session.execute(text("""
        SELECT ST_X(geom), ST_Y(geom) FROM crash WHERE accident_no = 'nearest'
    """)).one_or_none()
    centre = session.execute(text("""
        SELECT ST_X(geom), ST_Y(geom) FROM crash_cluster_200m
    """)).one()
    statements = []

    def record(_conn, _cursor, statement, _params, _context, _many):
        statements.append(statement)

    connection = session.connection()
    event.listen(connection, "before_cursor_execute", record)
    try:
        clusters = get_clusters_in_bbox(
            session, BoundingBox(140, -40, 150, -33), False, 12,
        )
    finally:
        event.remove(connection, "before_cursor_execute", record)
    assert len(statements) == 1
    assert len(clusters) == 1
    detail = get_cluster_detail(session, 123, False)
    hotspots = get_endpoint_hotspots(session, *centre, *centre, False)
    for result in [clusters[0], detail, hotspots[0]]:
        assert getattr(result, "id", getattr(result, "cluster_id", None)) == 123
        assert result.crash_count == 12
        assert result.eligible_driver_age_crashes == 10
        assert result.young_driver_crashes == 4
        assert result.young_driver_pct == 40
        assert result.young_driver_pct_displayable is True
        assert (result.longitude, result.latitude) == pytest.approx(expected or centre)
    if member_available:
        assert tuple(expected) != tuple(centre)
        # The grid centre remains the viewport filter even if the display point
        # is outside a very tight viewport around that centre.
        tight_bbox = BoundingBox(centre[0] - .000001, centre[1] - .000001,
                                 centre[0] + .000001, centre[1] + .000001)
        assert [cluster.id for cluster in get_clusters_in_bbox(
            session, tight_bbox, False, 12,
        )] == [123]

    session.execute(text("""
        INSERT INTO crash_cluster_200m VALUES
        (456, 322000, 5810000, 99, 90, 20, 22.22, true,
         ST_Transform(ST_SetSRID(ST_MakePoint(322000, 5810000), 32755), 4326))
    """))
    # The supplied route passes through cluster 123, far from either geocoded
    # endpoint. The larger off-route cluster must be excluded.
    route_hotspots = get_endpoint_hotspots(
        session, 140, -35, 149, -39, False,
        route_geojson=json.dumps({"type": "LineString", "coordinates": [
            [centre[0] - .005, centre[1]], [centre[0] + .005, centre[1]],
        ]}),
    )
    assert [hotspot.cluster_id for hotspot in route_hotspots] == [123]
    assert (route_hotspots[0].longitude, route_hotspots[0].latitude) == (
        pytest.approx(expected or centre)
    )
