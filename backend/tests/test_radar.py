import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.services.crash_query import (
    BoundingBox,
    CrashDataUnavailable,
    get_clusters_in_bbox,
)


def test_radar_bbox_returns_only_visible_clusters(client: TestClient) -> None:
    response = client.get("/api/radar/clusters?bbox=144.70,-37.90,144.80,-37.82")

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
    response = client.get("/api/radar/clusters", params={"bbox": bbox})

    assert response.status_code == 422


def test_cluster_detail(client: TestClient) -> None:
    response = client.get("/api/radar/clusters/101")

    assert response.status_code == 200
    assert response.json()["wet_count"] == 9
    assert response.json()["dark_count"] == 7


def test_spatial_query_boundary_converts_database_failure() -> None:
    class BrokenSession:
        def execute(self, _statement):
            raise SQLAlchemyError("database unavailable")

    with pytest.raises(CrashDataUnavailable):
        get_clusters_in_bbox(
            BrokenSession(),  # type: ignore[arg-type]
            BoundingBox(144.0, -38.0, 145.0, -37.0),
            use_mock_data=False,
        )

