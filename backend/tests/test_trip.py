import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api import trip as trip_api
from app.config import Settings
from app.schemas.trip import DataAvailability, TripCheckRequest
from app.services.geocoding import Coordinates
from app.services.routing import RouteResult
from app.services.trip_analysis import RouteUnavailable, _analyse_production_trip

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
        raise trip_analysis.WeatherUnavailable

    monkeypatch.setattr(trip_analysis, "geocode_address", fake_geocode)
    monkeypatch.setattr(trip_analysis, "calculate_route", fake_route)
    monkeypatch.setattr(trip_analysis, "get_weather_at", fail_weather)
    monkeypatch.setattr(trip_analysis, "get_route_hotspots", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(trip_analysis, "route_has_high_speed_zone", lambda *_args: False)
    monkeypatch.setattr(trip_analysis, "is_after_dark", lambda *_args: False)

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
    monkeypatch.setattr(trip_analysis, "get_route_hotspots", fail_optional_data)
    monkeypatch.setattr(trip_analysis, "route_has_high_speed_zone", fail_optional_data)
    monkeypatch.setattr(trip_analysis, "is_after_dark", lambda *_args: False)

    request = TripCheckRequest.model_validate(VALID_REQUEST)
    settings = Settings(use_mock_data=False, ors_api_key="test-only")
    result = asyncio.run(_analyse_production_trip(request, settings, Mock()))

    assert result.route.distance_km == 12.5
    assert result.hotspots == []
    assert result.data_status.weather == DataAvailability.AVAILABLE
    assert result.data_status.crash_data == DataAvailability.UNAVAILABLE
    assert result.data_status.speed_zones == DataAvailability.UNAVAILABLE
    assert result.factors == []
