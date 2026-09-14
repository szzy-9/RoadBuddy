import asyncio
import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text

from app.api import trip as trip_api
from app.config import Settings
from app.schemas.trip import DataAvailability, TripCheckRequest
from app.services.geocoding import Coordinates
from app.services.routing import RouteResult
from app.services.trip_analysis import RouteUnavailable, _analyse_production_trip
from app.services.weather import WeatherConditions, WeatherUnavailable

VALID_REQUEST = {
    "origin": "Tarneit VIC 3029",
    "destination": "Docklands VIC 3008",
    "departure_time": "2026-08-25T22:40:00+10:00",
}


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_trip_check_returns_deterministic_mock_result(client: TestClient) -> None:
    response = client.post("/api/trip/check", json=VALID_REQUEST)

    assert response.status_code == 200
    payload = response.json()
    assert payload["concern_level"] == "higher"
    assert payload["rule_version"] == "prototype-v0.1"
    assert payload["route"]["origin"] == VALID_REQUEST["origin"]
    assert payload["hotspots"]

    comparison = payload["departure_comparison"]
    selected_departure = datetime.fromisoformat(VALID_REQUEST["departure_time"])
    duration = timedelta(minutes=payload["route"]["duration_minutes"])
    assert datetime.fromisoformat(comparison["selected"]["departure_time"]) == selected_departure
    assert datetime.fromisoformat(comparison["selected"]["arrival_time"]) == (
        selected_departure + duration
    )
    assert comparison["selected"]["concern_level"] == payload["concern_level"]
    assert comparison["selected"]["factor_count"] == len(payload["factors"])

    later_departure = selected_departure + timedelta(minutes=30)
    assert datetime.fromisoformat(
        comparison["thirty_minutes_later"]["departure_time"]
    ) == later_departure
    assert datetime.fromisoformat(comparison["thirty_minutes_later"]["arrival_time"]) == (
        later_departure + duration
    )
    assert comparison["thirty_minutes_later"]["factor_count"] == 4
    assert comparison["difference_summary"] == "Rain is forecast for the later option."
    assert payload["alternative_departure"] is None
    for factors in (
        payload["factors"], comparison["selected"]["factors"],
        comparison["thirty_minutes_later"]["factors"],
    ):
        for factor in factors:
            assert factor["explanation"]["source"] == "RoadBuddy development sample"
            assert factor["explanation"]["trigger"]


def test_trip_factor_explanation_is_optional_and_structured() -> None:
    from app.schemas.trip import RiskFactor

    legacy = RiskFactor(type="rain", label="Rain")
    assert legacy.explanation is None
    explanation = {"source": "Open-Meteo", "trigger": "0.35 mm precipitation is forecast."}
    factor = RiskFactor(type="rain", label="Rain", explanation=explanation)
    assert factor.model_dump()["explanation"] == explanation


def test_production_trip_explanations_use_each_departures_actual_data(monkeypatch) -> None:
    from app.schemas.trip import TripHotspot
    from app.services import trip_analysis

    monkeypatch.setattr(trip_analysis, "geocode_address", AsyncMock(return_value=Coordinates(
        longitude=144.9, latitude=-37.8, label="Test location",
    )))
    monkeypatch.setattr(trip_analysis, "calculate_route", AsyncMock(return_value=RouteResult(
        1.2, 20, {"type": "LineString", "coordinates": [[144.9, -37.8], [144.91, -37.8]]},
    )))
    weather = AsyncMock(side_effect=[
        WeatherConditions(rain=True, precipitation_mm=0.35),
        WeatherConditions(rain=True, precipitation_mm=1.75),
    ])
    monkeypatch.setattr(trip_analysis, "get_weather_at", weather)
    monkeypatch.setattr(trip_analysis, "is_after_dark", lambda *_: True)
    monkeypatch.setattr(trip_analysis, "route_has_high_speed_zone", lambda *_: True)
    hotspots = [TripHotspot(
        cluster_id=index, crash_count=count, eligible_driver_age_crashes=count,
        young_driver_crashes=1, young_driver_pct_displayable=False,
        longitude=144.9, latitude=-37.8,
    ) for index, count in enumerate([5, 4, 12])]
    monkeypatch.setattr(trip_analysis, "get_endpoint_hotspots", lambda *_, **__: hotspots)
    monkeypatch.setattr(trip_analysis, "get_route_segment_crash_counts",
                        lambda _session, segments: {segment.index: 0 for segment in segments})
    request = TripCheckRequest.model_validate({
        **VALID_REQUEST, "departure_time": "2026-08-25T21:17:00+10:00",
    })
    result = asyncio.run(_analyse_production_trip(request, Settings(use_mock_data=False), Mock()))
    selected = {factor.type: factor.model_dump()["explanation"] for factor in result.factors}
    later = {factor.type: factor.model_dump()["explanation"]
             for factor in result.departure_comparison.thirty_minutes_later.factors}
    assert result.factors == result.departure_comparison.selected.factors
    for factors, precipitation, midpoint in [(selected, "0.35", "21:27"),
                                              (later, "1.75", "21:57")]:
        assert factors["rain"] == {
            "source": "Open-Meteo",
            "trigger": f"{precipitation} mm precipitation is forecast around the route midpoint.",
        }
        assert factors["after_dark"] == {
            "source": "Astral daylight calculation",
            "trigger": f"The journey midpoint at {midpoint} is after dark at the route midpoint.",
        }
        assert factors["high_speed_zone"] == {
            "source": "Vicmap Speed Zones",
            "trigger": "The route intersects a recorded high-speed zone.",
        }
        assert factors["significant_crash_history"] == {
            "source": "Victorian Road Crash Data",
            "trigger": "2 nearby crash clusters have at least 5 recorded injury crashes.",
        }


def test_trip_check_returns_route_coordinates(client: TestClient) -> None:
    response = client.post("/api/trip/check", json=VALID_REQUEST)

    assert response.status_code == 200
    route = response.json()["route"]
    for key in ("origin_point", "destination_point"):
        point = route[key]
        assert -180 <= point["longitude"] <= 180
        assert -90 <= point["latitude"] <= 90

    assert route["geometry"]["type"] == "LineString"
    assert route["segments"]
    assert route["segments"][0]["geometry"]["coordinates"][0] == (
        route["geometry"]["coordinates"][0]
    )
    assert route["segments"][-1]["geometry"]["coordinates"][-1] == (
        route["geometry"]["coordinates"][-1]
    )
    previous_end = None
    for index, segment in enumerate(route["segments"]):
        assert segment["index"] == index
        assert segment["geometry"]["type"] == "LineString"
        coordinates = segment["geometry"]["coordinates"]
        assert len(coordinates) >= 2
        for point in coordinates:
            assert len(point) == 2
            assert -180 <= point[0] <= 180
            assert -90 <= point[1] <= 90
        if previous_end is not None:
            assert coordinates[0] == previous_end
        previous_end = coordinates[-1]
    again = client.post("/api/trip/check", json=VALID_REQUEST).json()["route"]
    assert again == route


def test_hotspots_query_uses_real_route_geometry(monkeypatch) -> None:
    from app.services import trip_analysis

    resolved = {
        VALID_REQUEST["origin"]: (144.6570, -37.8233),
        VALID_REQUEST["destination"]: (144.9465, -37.8150),
    }
    received: dict[str, object] = {}

    async def fake_geocode(address, _settings, _client):
        longitude, latitude = resolved[address]
        return Coordinates(longitude=longitude, latitude=latitude, label=address)

    async def fake_route(_origin, _destination, _settings, _client):
        return RouteResult(
            distance_km=25.3,
            duration_minutes=28,
            geometry={"type": "LineString", "coordinates": [[144.66, -37.82], [144.95, -37.82]]},
        )

    async def fake_weather(*_args, **_kwargs):
        return WeatherConditions(rain=False, precipitation_mm=0.0)

    def capture_hotspots(_session, *coordinates, **kwargs):
        received["geometry"] = kwargs["route_geojson"]
        return []

    monkeypatch.setattr(trip_analysis, "geocode_address", fake_geocode)
    monkeypatch.setattr(trip_analysis, "calculate_route", fake_route)
    monkeypatch.setattr(trip_analysis, "get_weather_at", fake_weather)
    monkeypatch.setattr(trip_analysis, "get_endpoint_hotspots", capture_hotspots)
    monkeypatch.setattr(trip_analysis, "route_has_high_speed_zone", lambda *_args: False)
    monkeypatch.setattr(trip_analysis, "is_after_dark", lambda *_args: False)
    def fake_counts(_session, segments):
        counts = (0, 4, 5, 9, 10, 19, 20, 49, 50, None)
        return {
            segment.index: counts[segment.index % len(counts)]
            for segment in reversed(segments)
        }

    monkeypatch.setattr(trip_analysis, "get_route_segment_crash_counts", fake_counts)

    request = TripCheckRequest.model_validate(VALID_REQUEST)
    settings = Settings(use_mock_data=False, ors_api_key="test-only")
    result = asyncio.run(_analyse_production_trip(request, settings, Mock()))

    assert json.loads(received["geometry"]) == {
        "type": "LineString", "coordinates": [[144.66, -37.82], [144.95, -37.82]],
    }
    assert result.route.geometry.model_dump(mode="json") == json.loads(received["geometry"])
    assert [segment.nearby_crash_count for segment in result.route.segments[:10]] == (
        [0, 4, 5, 9, 10, 19, 20, 49, 50, None]
    )
    assert result.data_status.crash_data == DataAvailability.UNAVAILABLE


def test_trip_comparison_summarises_rain_easing(client: TestClient) -> None:
    response = client.post(
        "/api/trip/check",
        json={**VALID_REQUEST, "departure_time": "2026-08-25T22:10:00+10:00"},
    )

    assert response.status_code == 200
    payload = response.json()
    comparison = payload["departure_comparison"]
    assert comparison["selected"]["factor_count"] == 4
    assert comparison["thirty_minutes_later"]["factor_count"] == 3
    assert comparison["difference_summary"] == "Rain is forecast to ease."
    assert payload["alternative_departure"]["departure_time"] == (
        comparison["thirty_minutes_later"]["departure_time"]
    )


def test_trip_request_validation(client: TestClient) -> None:
    empty_origin = client.post(
        "/api/trip/check",
        json={**VALID_REQUEST, "origin": "   "},
    )
    invalid_time = client.post(
        "/api/trip/check",
        json={**VALID_REQUEST, "departure_time": "not-a-date"},
    )
    missing_timezone = client.post(
        "/api/trip/check",
        json={**VALID_REQUEST, "departure_time": "2026-08-25T22:40:00"},
    )

    assert empty_origin.status_code == 422
    assert invalid_time.status_code == 422
    assert missing_timezone.status_code == 422


def test_route_failure_returns_safe_message(client: TestClient, monkeypatch) -> None:
    async def fail_route(*_args, **_kwargs):
        raise RouteUnavailable

    monkeypatch.setattr(trip_api, "analyse_trip", fail_route)
    response = client.post("/api/trip/check", json=VALID_REQUEST)

    assert response.status_code == 502
    assert response.json() == {
        "detail": "We could not calculate this route. Please check the locations and try again."
    }


def test_weather_failure_keeps_route_and_marks_weather_unavailable(monkeypatch) -> None:
    from app.services import trip_analysis

    async def fake_geocode(address, _settings, _client):
        return Coordinates(longitude=144.9, latitude=-37.8, label=address)

    async def fake_route(_origin, _destination, _settings, _client):
        return RouteResult(
            distance_km=12.5,
            duration_minutes=20,
            geometry={"type": "LineString", "coordinates": [[144.9, -37.8], [145.0, -37.9]]},
        )

    async def fail_weather(*_args, **_kwargs):
        raise WeatherUnavailable

    monkeypatch.setattr(trip_analysis, "geocode_address", fake_geocode)
    monkeypatch.setattr(trip_analysis, "calculate_route", fake_route)
    monkeypatch.setattr(trip_analysis, "get_weather_at", fail_weather)
    monkeypatch.setattr(trip_analysis, "get_endpoint_hotspots", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(trip_analysis, "route_has_high_speed_zone", lambda *_args: False)
    monkeypatch.setattr(trip_analysis, "is_after_dark", lambda *_args: False)
    monkeypatch.setattr(trip_analysis, "get_route_segment_crash_counts", lambda *_: {})

    request = TripCheckRequest.model_validate(VALID_REQUEST)
    settings = Settings(
        use_mock_data=False,
        ors_api_key="test-only",
    )
    result = asyncio.run(_analyse_production_trip(request, settings, Mock()))

    assert result.route.distance_km == 12.5
    assert result.data_status.weather == DataAvailability.UNAVAILABLE
    assert result.factors == []
    assert result.departure_comparison.selected.departure_time == request.departure_time
    assert result.departure_comparison.selected.arrival_time == (
        request.departure_time + timedelta(minutes=20)
    )
    assert result.departure_comparison.thirty_minutes_later.departure_time == (
        request.departure_time + timedelta(minutes=30)
    )
    assert result.departure_comparison.thirty_minutes_later.arrival_time == (
        request.departure_time + timedelta(minutes=50)
    )
    assert result.departure_comparison.selected.factor_count == 0
    assert result.departure_comparison.thirty_minutes_later.factor_count == 0
    assert result.departure_comparison.difference_summary is None


def test_optional_database_failures_keep_trip_result_available(monkeypatch) -> None:
    from app.services import trip_analysis

    async def fake_geocode(address, _settings, _client):
        return Coordinates(longitude=144.9, latitude=-37.8, label=address)

    async def fake_route(_origin, _destination, _settings, _client):
        return RouteResult(
            distance_km=12.5,
            duration_minutes=20,
            geometry={
                "type": "LineString",
                "coordinates": [[144.9, -37.8], [145.0, -37.9]],
            },
        )

    async def fake_weather(*_args, **_kwargs):
        return trip_analysis.WeatherConditions(rain=False, precipitation_mm=0)

    def fail_optional_data(*_args, **_kwargs):
        raise trip_analysis.CrashDataUnavailable

    monkeypatch.setattr(trip_analysis, "geocode_address", fake_geocode)
    monkeypatch.setattr(trip_analysis, "calculate_route", fake_route)
    monkeypatch.setattr(trip_analysis, "get_weather_at", fake_weather)
    monkeypatch.setattr(trip_analysis, "get_endpoint_hotspots", fail_optional_data)
    monkeypatch.setattr(trip_analysis, "route_has_high_speed_zone", fail_optional_data)
    monkeypatch.setattr(trip_analysis, "is_after_dark", lambda *_args: False)
    monkeypatch.setattr(trip_analysis, "get_route_segment_crash_counts", fail_optional_data)

    request = TripCheckRequest.model_validate(VALID_REQUEST)
    settings = Settings(use_mock_data=False, ors_api_key="test-only")
    result = asyncio.run(_analyse_production_trip(request, settings, Mock()))

    assert result.route.distance_km == 12.5
    assert result.hotspots == []
    assert result.data_status.weather == DataAvailability.AVAILABLE
    assert result.data_status.crash_data == DataAvailability.UNAVAILABLE
    assert result.data_status.speed_zones == DataAvailability.UNAVAILABLE
    assert result.factors == []
    assert result.route.geometry.type == "LineString"
    assert result.route.segments
    assert all(segment.nearby_crash_count is None for segment in result.route.segments)


def test_route_sections_keep_bends_and_shared_boundaries() -> None:
    from app.schemas.trip import GeoLineString
    from app.services.route_segments import distance_metres, split_route

    points = [(144.9, -37.8), (144.91, -37.8), (144.91, -37.81), (144.92, -37.81)]
    segments = split_route(GeoLineString(type="LineString", coordinates=points))
    assert len(segments) > 3
    assert segments[0].geometry.coordinates[0] == points[0]
    assert segments[-1].geometry.coordinates[-1] == points[-1]
    flattened = []
    for index, segment in enumerate(segments):
        assert segment.index == index
        coords = segment.geometry.coordinates
        if index:
            assert coords[0] == segments[index - 1].geometry.coordinates[-1]
        flattened.extend(coords if not index else coords[1:])
        length = sum(distance_metres(a, b) for a, b in zip(coords, coords[1:], strict=False))
        if index < len(segments) - 1:
            assert 400 <= length <= 500
        else:
            assert 0 < length <= 500
    # Every original bend survives, in its original order.
    assert [p for p in flattened if p in points] == points


def test_route_segment_counts_match_sections_in_one_spatial_query(postgis_session) -> None:
    from app.schemas.trip import GeoLineString, RouteRiskSegment
    from app.services.crash_query import get_route_segment_crash_counts

    session = postgis_session
    segments = [RouteRiskSegment(
        index=index, nearby_crash_count=None,
        geometry=GeoLineString(type="LineString", coordinates=[
            (144.0 + index * .02, -37.8), (144.005 + index * .02, -37.8),
        ]),
    ) for index in range(10)]
    expected = [0, 4, 5, 9, 10, 19, 20, 49, 50, 51]
    for index, count in enumerate(expected):
        session.execute(text("""
            INSERT INTO crash (accident_no, geom)
            SELECT :prefix || n, ST_SetSRID(ST_MakePoint(:lon, -37.799), 4326)
            FROM generate_series(1, :count) n
        """), {"prefix": f"{index}-", "lon": 144.002 + index * .02, "count": count})
    # This crash is over 150 m away, and a missing geometry must not be counted.
    session.execute(text("""
        INSERT INTO crash (accident_no, geom) VALUES
        ('outside', ST_SetSRID(ST_MakePoint(144.002, -37.798), 4326)), ('missing', NULL)
    """))
    queries = []
    connection = session.connection()

    def record(_conn, _cursor, statement, _params, _context, _many):
        queries.append(statement)

    event.listen(connection, "before_cursor_execute", record)
    try:
        counts = get_route_segment_crash_counts(session, list(reversed(segments)))
    finally:
        event.remove(connection, "before_cursor_execute", record)
    assert len(queries) == 1
    assert counts == dict(enumerate(expected))


def test_mock_same_suburb_route_has_visible_geometry(client: TestClient) -> None:
    result = client.post("/api/trip/check", json={
        **VALID_REQUEST,
        "origin": "1 Collins St Melbourne", "destination": "200 Collins St Melbourne",
    })
    assert result.status_code == 200
    route = result.json()["route"]
    assert len({tuple(point) for point in route["geometry"]["coordinates"]}) >= 2
    assert any(len(set(map(tuple, segment["geometry"]["coordinates"]))) >= 2
               for segment in route["segments"])


@pytest.mark.parametrize("coordinates", [[], [[144, -37]], [[181, -37], [144, -37]],
                                           [[144, -37, 1], [144, -37, 2]]])
def test_invalid_provider_geometry_is_a_route_failure(monkeypatch, coordinates) -> None:
    from app.services import trip_analysis

    async def fake_geocode(address, *_):
        return Coordinates(longitude=144.9, latitude=-37.8, label=address)

    async def fake_route(*_):
        return RouteResult(1, 1, {"type": "LineString", "coordinates": coordinates})

    monkeypatch.setattr(trip_analysis, "geocode_address", fake_geocode)
    monkeypatch.setattr(trip_analysis, "calculate_route", fake_route)
    with pytest.raises(RouteUnavailable):
        asyncio.run(_analyse_production_trip(
            TripCheckRequest.model_validate(VALID_REQUEST), Settings(use_mock_data=False), Mock(),
        ))


def test_empty_spatial_dataset_is_unavailable(postgis_session) -> None:
    from app.schemas.trip import GeoLineString
    from app.services.crash_query import get_route_segment_crash_counts
    from app.services.route_segments import split_route

    segments = split_route(GeoLineString(
        type="LineString", coordinates=[(144.9, -37.8), (144.91, -37.8)],
    ))
    assert get_route_segment_crash_counts(postgis_session, segments) == {0: None, 1: None}


def test_segment_query_preserves_nulls_and_maps_rows_by_index() -> None:
    from sqlalchemy.exc import SQLAlchemyError

    from app.schemas.trip import GeoLineString
    from app.services.crash_query import CrashDataUnavailable, get_route_segment_crash_counts
    from app.services.route_segments import split_route

    segments = split_route(GeoLineString(
        type="LineString", coordinates=[(144.9, -37.8), (144.91, -37.8)],
    ))
    session = Mock()
    session.execute.return_value.all.return_value = [
        SimpleNamespace(index=1, nearby_crash_count=None),
        SimpleNamespace(index=0, nearby_crash_count=0),
    ]
    assert get_route_segment_crash_counts(session, segments) == {0: 0, 1: None}
    assert session.execute.call_count == 1
    statement, params = session.execute.call_args.args
    assert params["radius"] == 150
    assert [item["index"] for item in json.loads(params["segments"])] == [0, 1]
    assert "ST_DWithin" in str(statement)
    session.execute.side_effect = SQLAlchemyError("unavailable")
    with pytest.raises(CrashDataUnavailable):
        get_route_segment_crash_counts(session, segments)


def test_resolved_coordinates_are_used_instead_of_regeocoding(monkeypatch) -> None:
    """A point the user already picked must not be looked up a second time.

    Re-geocoding a chosen label is lossy: "Chadstone Shopping Centre, Melbourne
    3145" has no point of interest index behind it, so it parses as street
    number 3145 on a road called Melbourne and lands in Wodonga.
    """
    from app.services import trip_analysis

    def fail_geocode(address, *_args, **_kwargs):
        raise AssertionError(f"re-geocoded an already resolved address: {address!r}")

    monkeypatch.setattr(trip_analysis, "geocode_address", fail_geocode)

    routed: list[Coordinates] = []

    async def fake_route(origin, destination, _settings, _client):
        routed.extend([origin, destination])
        return RouteResult(
            distance_km=15.0,
            duration_minutes=20,
            geometry={
                "type": "LineString",
                "coordinates": [[145.0825, -37.8877], [145.1439, -37.9265]],
            },
        )

    monkeypatch.setattr(trip_analysis, "calculate_route", fake_route)
    monkeypatch.setattr(
        trip_analysis,
        "get_endpoint_hotspots",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        trip_analysis,
        "get_route_segment_crash_counts",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        trip_analysis,
        "route_has_high_speed_zone",
        lambda *_args, **_kwargs: False,
    )

    async def fake_weather(*_args, **_kwargs):
        return WeatherConditions(rain=False, precipitation_mm=0.0)

    monkeypatch.setattr(trip_analysis, "get_weather_at", fake_weather)
    monkeypatch.setattr(trip_analysis, "is_after_dark", lambda *_args: False)

    request = TripCheckRequest.model_validate(
        {
            "origin": "Chadstone Shopping Centre, Melbourne 3145, Australia",
            "destination": "IKEA, 917 Princes Hwy, Melbourne 3171, Australia",
            "departure_time": "2026-08-25T22:40:00+10:00",
            "origin_point": {"longitude": 145.0825, "latitude": -37.8877},
            "destination_point": {"longitude": 145.1439, "latitude": -37.9265},
        }
    )

    response = asyncio.run(
        _analyse_production_trip(request, Settings(mapbox_token="t"), Mock())
    )

    assert [(c.longitude, c.latitude) for c in routed] == [
        (145.0825, -37.8877),
        (145.1439, -37.9265),
    ]
    assert response.route.origin_point.longitude == 145.0825
    assert response.route.destination_point.latitude == -37.9265
    # The label the user saw is what the result should echo back.
    assert response.route.origin == "Chadstone Shopping Centre, Melbourne 3145, Australia"


def test_typed_address_without_a_point_is_still_geocoded(monkeypatch) -> None:
    """Free text the user never picked from the list still needs a lookup."""
    from app.services import trip_analysis

    looked_up: list[str] = []

    async def fake_geocode(address, *_args, **_kwargs):
        looked_up.append(address)
        return Coordinates(longitude=144.657, latitude=-37.8233, label=address)

    monkeypatch.setattr(trip_analysis, "geocode_address", fake_geocode)

    async def fake_route(_origin, _destination, _settings, _client):
        return RouteResult(
            distance_km=15.0,
            duration_minutes=20,
            geometry={
                "type": "LineString",
                "coordinates": [[144.66, -37.82], [144.95, -37.82]],
            },
        )

    monkeypatch.setattr(trip_analysis, "calculate_route", fake_route)
    monkeypatch.setattr(
        trip_analysis, "get_endpoint_hotspots", lambda *_a, **_k: []
    )
    monkeypatch.setattr(
        trip_analysis, "get_route_segment_crash_counts", lambda *_a, **_k: {}
    )
    monkeypatch.setattr(
        trip_analysis, "route_has_high_speed_zone", lambda *_a, **_k: False
    )

    async def fake_weather(*_args, **_kwargs):
        return WeatherConditions(rain=False, precipitation_mm=0.0)

    monkeypatch.setattr(trip_analysis, "get_weather_at", fake_weather)
    monkeypatch.setattr(trip_analysis, "is_after_dark", lambda *_args: False)

    request = TripCheckRequest.model_validate(VALID_REQUEST)

    asyncio.run(_analyse_production_trip(request, Settings(mapbox_token="t"), Mock()))

    assert looked_up == [VALID_REQUEST["origin"], VALID_REQUEST["destination"]]
