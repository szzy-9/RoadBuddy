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
    region_name: str | None = None,
    region_code: str | None = None,
) -> dict:
    region: dict[str, str] = {}
    if region_name is not None:
        region["name"] = region_name
    if region_code is not None:
        region["region_code"] = region_code
    return {
        "type": "Feature",
        "properties": {"full_address": label, "context": {"region": region}},
        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
    }


def _settings() -> Settings:
    return Settings(mapbox_token="test-only", use_mock_data=False)


def test_autocomplete_short_query_returns_empty_without_request() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("Mapbox must not be called for a short query")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            assert await autocomplete_address("Ta", _settings(), client) == []

    asyncio.run(run())


def test_autocomplete_accepts_victoria_and_filters_other_states() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.mapbox.com"
        assert request.url.path == "/search/geocode/v6/forward"
        assert request.url.params["access_token"] == "test-only"
        assert request.url.params["country"] == "AU"
        assert request.url.params["limit"] == "5"
        return httpx.Response(
            200,
            json={
                "features": [
                    _feature(
                        "Tarneit, Victoria, Australia",
                        144.657,
                        -37.8233,
                        region_name="Victoria",
                    ),
                    _feature(
                        "Albury, New South Wales, Australia",
                        146.91,
                        -36.08,
                        region_name="New South Wales",
                        region_code="NSW",
                    ),
                    _feature(
                        "Docklands, Victoria, Australia",
                        144.9465,
                        -37.815,
                        region_code="VIC",
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
        "Tarneit, Victoria, Australia",
        "Docklands, Victoria, Australia",
    ]


def test_autocomplete_upstream_failure_is_safe() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "upstream detail"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(GeocodingUnavailable):
                await autocomplete_address("Tarneit", _settings(), client)

    asyncio.run(run())


def test_autocomplete_without_token_is_unavailable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("Mapbox must not be called without a token")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(GeocodingUnavailable):
                await autocomplete_address(
                    "Tarneit",
                    Settings(mapbox_token=None, use_mock_data=False),
                    client,
                )

    asyncio.run(run())


def test_forward_geocoding_uses_mapbox_and_returns_victoria_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.mapbox.com"
        assert request.url.path == "/search/geocode/v6/forward"
        assert request.url.params["bbox"] == "140.95,-39.25,150.05,-33.95"
        return httpx.Response(
            200,
            json={
                "features": [
                    _feature(
                        "Docklands, Victoria, Australia",
                        144.9465,
                        -37.815,
                        region_name="Victoria",
                    )
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await geocode_address("Docklands VIC 3008", _settings(), client)

    result = asyncio.run(run())

    assert result.label == "Docklands, Victoria, Australia"
    assert result.longitude == 144.9465
    assert result.latitude == -37.815


def test_forward_geocoding_without_victorian_match_is_unavailable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "features": [
                    _feature(
                        "Albury, New South Wales, Australia",
                        146.91,
                        -36.08,
                        region_code="NSW",
                    )
                ]
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(GeocodingUnavailable):
                await geocode_address("Albury", _settings(), client)

    asyncio.run(run())


def test_locations_endpoint_returns_empty_for_short_query(client: TestClient) -> None:
    response = client.get("/api/trip/locations", params={"q": "Ta"})

    assert response.status_code == 200
    assert response.json() == {"suggestions": []}


def test_locations_endpoint_hides_upstream_failure(client: TestClient, monkeypatch) -> None:
    async def fail_search(*_args, **_kwargs):
        raise GeocodingUnavailable

    monkeypatch.setattr(trip_api, "autocomplete_address", fail_search)
    response = client.get("/api/trip/locations", params={"q": "Tarneit"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Location search is temporarily unavailable. Please try again."
    }
