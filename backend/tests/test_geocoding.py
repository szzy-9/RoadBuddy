import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import trip as trip_api
from app.config import Settings
from app.services.geocoding import (
    GeocodingUnavailable,
    autocomplete_address,
    geocode_address,
)


def _feature(
    label: str,
    longitude: float,
    latitude: float,
    *,
    region: str | None = None,
    region_abbreviation: str | None = None,
) -> dict:
    properties = {"label": label}
    if region is not None:
        properties["region"] = region
    if region_abbreviation is not None:
        properties["region_a"] = region_abbreviation
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
    }


def _settings() -> Settings:
    return Settings(ors_api_key="test-only", use_mock_data=False)


def test_autocomplete_short_query_returns_empty_without_request() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("ORS must not be called for a short query")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            assert await autocomplete_address("Ta", _settings(), client) == []

    asyncio.run(run())


def test_autocomplete_accepts_victoria_and_filters_other_states() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.heigit.org"
        assert request.url.path == "/pelias/v1/autocomplete"
        assert request.headers["Authorization"] == "test-only"
        assert request.url.params["boundary.country"] == "AU"
        assert request.url.params["size"] == "5"
        return httpx.Response(
            200,
            json={
                "features": [
                    _feature(
                        "Tarneit VIC 3029, Australia",
                        144.657,
                        -37.8233,
                        region="Victoria",
                    ),
                    _feature(
                        "Albury NSW 2640, Australia",
                        146.91,
                        -36.08,
                        region="New South Wales",
                        region_abbreviation="NSW",
                    ),
                    _feature(
                        "Docklands VIC 3008, Australia",
                        144.9465,
                        -37.815,
                        region_abbreviation="VIC",
                    ),
                    {"properties": {}, "geometry": {}},
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await autocomplete_address("Tar", _settings(), client)

    results = asyncio.run(run())

    assert [result.label for result in results] == [
        "Tarneit VIC 3029, Australia",
        "Docklands VIC 3008, Australia",
    ]


def test_autocomplete_ors_failure_is_safe() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "upstream detail"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(GeocodingUnavailable):
                await autocomplete_address("Tarneit", _settings(), client)

    asyncio.run(run())


def test_forward_geocoding_uses_ors_and_returns_victoria_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.heigit.org"
        assert request.url.path == "/pelias/v1/search"
        assert request.headers["Authorization"] == "test-only"
        assert request.url.params["boundary.rect.min_lon"] == "140.95"
        return httpx.Response(
            200,
            json={
                "features": [
                    _feature(
                        "Docklands VIC 3008, Australia",
                        144.9465,
                        -37.815,
                        region="Victoria",
                    )
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await geocode_address("Docklands VIC 3008", _settings(), client)

    result = asyncio.run(run())

    assert result.label == "Docklands VIC 3008, Australia"
    assert result.longitude == 144.9465
    assert result.latitude == -37.815


def test_locations_endpoint_returns_empty_for_short_query(client: TestClient) -> None:
    response = client.get("/api/trip/locations", params={"q": "Ta"})

    assert response.status_code == 200
    assert response.json() == {"suggestions": []}


def test_locations_endpoint_hides_ors_failure(client: TestClient, monkeypatch) -> None:
    async def fail_search(*_args, **_kwargs):
        raise GeocodingUnavailable

    monkeypatch.setattr(trip_api, "autocomplete_address", fail_search)
    response = client.get("/api/trip/locations", params={"q": "Tarneit"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Location search is temporarily unavailable. Please try again."
    }
