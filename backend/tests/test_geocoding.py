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
        assert request.url.params["access_token"] == "test-only"
        assert request.url.params["country"] == "AU"
        assert request.url.params["limit"] == "5"
        if request.url.path == "/search/searchbox/v1/forward":
            return httpx.Response(200, json={"features": []})
        assert request.url.path == "/search/geocode/v6/forward"
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


def _searchbox_feature(
    label: str,
    longitude: float,
    latitude: float,
    *,
    region_code: str | None = None,
    feature_type: str = "poi",
) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "full_address": label,
            "feature_type": feature_type,
            "context": {"region": {"region_code": region_code}},
        },
        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
    }


def test_autocomplete_finds_points_of_interest_via_search_box() -> None:
    """A business name only exists in the POI index, not in v6 /forward."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/search/searchbox/v1/forward":
            return httpx.Response(
                200,
                json={
                    "features": [
                        _searchbox_feature(
                            "IKEA Springvale, 3171 Victoria, Australia",
                            145.1527,
                            -37.9493,
                            region_code="VIC",
                        )
                    ]
                },
            )
        # Real Mapbox geocoding finds only non-Victorian streets for this query.
        return httpx.Response(
            200,
            json={
                "features": [
                    _feature(
                        "Springvale Road, Nangus New South Wales 2722, Australia",
                        148.06,
                        -35.09,
                        region_code="NSW",
                    )
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await autocomplete_address("Ikea Springvale", _settings(), client)

    results = asyncio.run(run())

    assert [result.label for result in results] == [
        "IKEA Springvale, 3171 Victoria, Australia"
    ]
    assert "/search/searchbox/v1/forward" in calls


def test_autocomplete_falls_back_to_v6_when_search_box_has_no_victorian_match() -> None:
    """Search Box returning nothing usable must not lose the v6 address result."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/search/searchbox/v1/forward":
            return httpx.Response(
                200,
                json={
                    "features": [
                        _searchbox_feature(
                            "Springvale Road, Nangus New South Wales 2722, Australia",
                            148.06,
                            -35.09,
                            region_code="NSW",
                        )
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "features": [
                    _feature(
                        "1452 High Street, Glen Iris Victoria 3146, Australia",
                        145.06,
                        -37.86,
                        region_code="VIC",
                    )
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await autocomplete_address("1452 High Street", _settings(), client)

    results = asyncio.run(run())

    assert [result.label for result in results] == [
        "1452 High Street, Glen Iris Victoria 3146, Australia"
    ]
    assert "/search/geocode/v6/forward" in calls


def test_autocomplete_survives_search_box_failure() -> None:
    """A broken POI lookup must degrade to v6, not take the whole search down."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/searchbox/v1/forward":
            return httpx.Response(500, json={"error": "boom"})
        return httpx.Response(
            200,
            json={
                "features": [
                    _feature(
                        "Springvale, Victoria, Australia",
                        145.158,
                        -37.946,
                        region_code="VIC",
                    )
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await autocomplete_address("Springvale", _settings(), client)

    results = asyncio.run(run())

    assert [result.label for result in results] == ["Springvale, Victoria, Australia"]


def test_autocomplete_merges_poi_and_address_results_without_duplicates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/searchbox/v1/forward":
            return httpx.Response(
                200,
                json={
                    "features": [
                        _searchbox_feature(
                            "Springvale, Victoria, Australia",
                            145.158,
                            -37.946,
                            region_code="VIC",
                        )
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "features": [
                    _feature(
                        "Springvale, Victoria, Australia",
                        145.158,
                        -37.946,
                        region_code="VIC",
                    ),
                    _feature(
                        "Springvale South, Victoria, Australia",
                        145.148,
                        -37.971,
                        region_code="VIC",
                    ),
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await autocomplete_address("Springvale", _settings(), client)

    results = asyncio.run(run())

    assert [result.label for result in results] == [
        "Springvale, Victoria, Australia",
        "Springvale South, Victoria, Australia",
    ]


def test_geocode_address_still_uses_v6_only() -> None:
    """Resolving a submitted trip is an address lookup; POIs must not be called."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search/geocode/v6/forward"
        return httpx.Response(
            200,
            json={
                "features": [
                    _feature(
                        "Docklands, Victoria, Australia",
                        144.9465,
                        -37.815,
                        region_code="VIC",
                    )
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await geocode_address("Docklands VIC 3008", _settings(), client)

    assert asyncio.run(run()).label == "Docklands, Victoria, Australia"


def _poi_feature(name: str, address: str, postcode: str) -> dict:
    """A Search Box POI: no region, business name only in `name`."""
    return {
        "type": "Feature",
        "properties": {
            "name": name,
            "full_address": address,
            "feature_type": "poi",
            "context": {
                "country": {"country_code": "AU"},
                "postcode": {"name": postcode},
            },
        },
        "geometry": {"type": "Point", "coordinates": [145.1432, -37.9258]},
    }


def test_poi_without_region_is_kept_when_postcode_is_victorian() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/searchbox/v1/forward":
            return httpx.Response(
                200,
                json={
                    "features": [
                        _poi_feature(
                            "IKEA Springvale",
                            "Princes Hwy, Melbourne 3171, Australia",
                            "3171",
                        )
                    ]
                },
            )
        return httpx.Response(200, json={"features": []})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await autocomplete_address("Ikea Springvale", _settings(), client)

    results = asyncio.run(run())

    assert [result.label for result in results] == [
        "IKEA Springvale, Princes Hwy, Melbourne 3171, Australia"
    ]


def test_poi_without_region_is_dropped_when_postcode_is_interstate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/searchbox/v1/forward":
            return httpx.Response(
                200,
                json={
                    "features": [
                        _poi_feature(
                            "Sydney Opera House",
                            "Bennelong Point, Sydney 2000, Australia",
                            "2000",
                        )
                    ]
                },
            )
        return httpx.Response(200, json={"features": []})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await autocomplete_address("Opera House", _settings(), client)

    assert asyncio.run(run()) == []


def test_named_region_still_wins_over_postcode() -> None:
    """A feature that names another state is rejected even with a 3xxx postcode."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/searchbox/v1/forward":
            return httpx.Response(200, json={"features": []})
        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "full_address": "Somewhere, New South Wales, Australia",
                            "context": {
                                "region": {"region_code": "NSW"},
                                "postcode": {"name": "3171"},
                            },
                        },
                        "geometry": {"type": "Point", "coordinates": [148.0, -35.0]},
                    }
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await autocomplete_address("Somewhere", _settings(), client)

    assert asyncio.run(run()) == []


def test_same_suburb_from_both_endpoints_is_listed_once() -> None:
    """The endpoints place a suburb a few hundred metres apart; show one entry."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/searchbox/v1/forward":
            return httpx.Response(
                200,
                json={
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {
                                "name": "Springvale",
                                "feature_type": "locality",
                                "place_formatted": "Melbourne 3171, Australia",
                                "context": {"postcode": {"name": "3171"}},
                            },
                            "geometry": {
                                "type": "Point",
                                "coordinates": [145.1531, -37.9490],
                            },
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "features": [
                    _feature(
                        "Springvale, Victoria, Australia",
                        145.1582,
                        -37.9460,
                        region_code="VIC",
                    ),
                    _feature(
                        "Springvale South, Victoria, Australia",
                        145.1486,
                        -37.9710,
                        region_code="VIC",
                    ),
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await autocomplete_address("Springvale", _settings(), client)

    labels = [result.label for result in asyncio.run(run())]

    assert labels == [
        "Springvale, Melbourne 3171, Australia",
        "Springvale South, Victoria, Australia",
    ]


def test_brand_in_a_suburb_finds_the_branch_not_a_name_match() -> None:
    """"Ikea Springvale" must find the store, not a car-rental pod named after it.

    Mapbox ranks a POI whose *name* contains the suburb above the branch that
    actually sits there, so the suburb is resolved separately and used to bias
    a search for the remaining words.
    """
    seen: list[tuple[str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        query = params["q"]
        seen.append((query, params.get("proximity")))

        if request.url.path == "/search/geocode/v6/forward":
            if query == "Springvale":
                return httpx.Response(
                    200,
                    json={
                        "features": [
                            _feature(
                                "Springvale, Victoria, Australia",
                                145.15823,
                                -37.946014,
                                region_code="VIC",
                            )
                        ]
                    },
                )
            return httpx.Response(200, json={"features": []})

        # Only the proximity-biased lookup for the brand alone finds the store.
        if query == "Ikea" and params.get("proximity"):
            return httpx.Response(
                200,
                json={
                    "features": [
                        _poi_feature(
                            "IKEA",
                            "917 Princes Hwy, Melbourne 3171, Australia",
                            "3171",
                        )
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "features": [
                    _poi_feature(
                        "GoGet Van Hire Ikea Springvale",
                        "Princes Hwy, Melbourne 3171, Australia",
                        "3171",
                    )
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await autocomplete_address("Ikea Springvale", _settings(), client)

    labels = [result.label for result in asyncio.run(run())]

    assert labels[0] == "IKEA, 917 Princes Hwy, Melbourne 3171, Australia"
    assert ("Ikea", "145.15823,-37.946014") in seen


def test_two_word_suburb_is_not_split_into_a_business_search() -> None:
    """"Glen Iris" is one suburb, not a "Glen" business in an "Iris" suburb."""
    def handler(request: httpx.Request) -> httpx.Response:
        query = request.url.params["q"]
        if request.url.path == "/search/geocode/v6/forward":
            # Mapbox answers a partial query with its best match, so "Iris"
            # also comes back as Glen Iris; only the exact name may count.
            if query in {"Glen Iris", "Iris"}:
                return httpx.Response(
                    200,
                    json={
                        "features": [
                            _feature(
                                "Glen Iris, Victoria, Australia",
                                145.0634,
                                -37.8561,
                                region_code="VIC",
                            )
                        ]
                    },
                )
            return httpx.Response(200, json={"features": []})

        # Searching the leftover word would surface unrelated landmarks.
        assert request.url.params.get("proximity") is None, (
            "a whole-suburb query must not be split into a proximity search"
        )
        return httpx.Response(200, json={"features": []})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await autocomplete_address("Glen Iris", _settings(), client)

    assert [r.label for r in asyncio.run(run())] == ["Glen Iris, Victoria, Australia"]


def test_business_query_is_split_even_though_suburb_alone_matches() -> None:
    """"Ikea Springvale" partially matches Springvale; that must not block it."""
    proximity_searches: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        query = request.url.params["q"]
        if request.url.path == "/search/geocode/v6/forward":
            # Both the full phrase and the bare suburb resolve to Springvale.
            if "springvale" in query.casefold():
                return httpx.Response(
                    200,
                    json={
                        "features": [
                            _feature(
                                "Springvale, Victoria, Australia",
                                145.15823,
                                -37.946014,
                                region_code="VIC",
                            )
                        ]
                    },
                )
            return httpx.Response(200, json={"features": []})

        if request.url.params.get("proximity"):
            proximity_searches.append(query)
            return httpx.Response(
                200,
                json={
                    "features": [
                        _poi_feature(
                            "IKEA",
                            "917 Princes Hwy, Melbourne 3171, Australia",
                            "3171",
                        )
                    ]
                },
            )
        return httpx.Response(200, json={"features": []})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await autocomplete_address("Ikea Springvale", _settings(), client)

    labels = [result.label for result in asyncio.run(run())]

    assert labels[0] == "IKEA, 917 Princes Hwy, Melbourne 3171, Australia"
    assert proximity_searches == ["Ikea"]
