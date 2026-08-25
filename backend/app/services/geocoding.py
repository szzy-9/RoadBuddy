import math
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings

ORS_GEOCODE_BASE_URL = "https://api.openrouteservice.org/geocode"
MAX_GEOCODING_RESULTS = 5

VICTORIA_BOUNDS = {
    "boundary.country": "AU",
    "boundary.rect.min_lon": 140.95,
    "boundary.rect.min_lat": -39.25,
    "boundary.rect.max_lon": 150.05,
    "boundary.rect.max_lat": -33.95,
}


class GeocodingUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Coordinates:
    longitude: float
    latitude: float
    label: str


@dataclass(frozen=True)
class GeocodingSuggestion:
    label: str
    longitude: float
    latitude: float


def _is_victorian(properties: dict[str, Any]) -> bool:
    region = properties.get("region")
    region_abbreviation = properties.get("region_a")
    return (
        isinstance(region, str)
        and region.casefold() == "victoria"
        or isinstance(region_abbreviation, str)
        and region_abbreviation.upper() == "VIC"
    )


def _parse_victorian_feature(feature: object) -> GeocodingSuggestion | None:
    if not isinstance(feature, dict):
        return None

    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    if not _is_victorian(properties):
        return None

    label = properties.get("label")
    coordinates = geometry.get("coordinates")
    if not isinstance(label, str) or not label.strip():
        return None
    if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
        return None

    try:
        longitude = float(coordinates[0])
        latitude = float(coordinates[1])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(longitude) or not math.isfinite(latitude):
        return None

    return GeocodingSuggestion(
        label=label.strip(),
        longitude=longitude,
        latitude=latitude,
    )


def _victorian_suggestions(payload: object) -> list[GeocodingSuggestion]:
    if not isinstance(payload, dict):
        return []
    features = payload.get("features")
    if not isinstance(features, list):
        return []

    suggestions: list[GeocodingSuggestion] = []
    seen: set[tuple[str, float, float]] = set()
    for feature in features:
        suggestion = _parse_victorian_feature(feature)
        if suggestion is None:
            continue
        identity = (
            suggestion.label.casefold(),
            suggestion.longitude,
            suggestion.latitude,
        )
        if identity in seen:
            continue
        seen.add(identity)
        suggestions.append(suggestion)
        if len(suggestions) == MAX_GEOCODING_RESULTS:
            break
    return suggestions


def _geocoding_params(text: str) -> dict[str, str | int | float]:
    return {
        "text": text,
        "size": MAX_GEOCODING_RESULTS,
        **VICTORIA_BOUNDS,
    }


def _authorization_headers(settings: Settings) -> dict[str, str]:
    if not settings.ors_api_key:
        raise GeocodingUnavailable("ORS_API_KEY is not configured")
    return {"Authorization": settings.ors_api_key}


async def autocomplete_address(
    query: str,
    settings: Settings,
    client: httpx.AsyncClient,
) -> list[GeocodingSuggestion]:
    normalized_query = query.strip()
    if len(normalized_query) < 3:
        return []

    try:
        response = await client.get(
            f"{ORS_GEOCODE_BASE_URL}/autocomplete",
            params=_geocoding_params(normalized_query),
            headers=_authorization_headers(settings),
        )
        response.raise_for_status()
        return _victorian_suggestions(response.json())
    except (httpx.HTTPError, TypeError, ValueError) as exc:
        raise GeocodingUnavailable from exc


async def geocode_address(
    address: str,
    settings: Settings,
    client: httpx.AsyncClient,
) -> Coordinates:
    try:
        response = await client.get(
            f"{ORS_GEOCODE_BASE_URL}/search",
            params=_geocoding_params(address.strip()),
            headers=_authorization_headers(settings),
        )
        response.raise_for_status()
        suggestions = _victorian_suggestions(response.json())
    except (httpx.HTTPError, TypeError, ValueError) as exc:
        raise GeocodingUnavailable from exc

    if not suggestions:
        raise GeocodingUnavailable("No Victorian location matched the address")
    result = suggestions[0]
    return Coordinates(
        longitude=result.longitude,
        latitude=result.latitude,
        label=result.label,
    )
