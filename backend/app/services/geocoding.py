import math
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings

MAPBOX_GEOCODE_BASE_URL = "https://api.mapbox.com/search/geocode/v6"
MAX_GEOCODING_RESULTS = 5

# Mapbox ranks by relevance within the box but does not clip to it, so results
# from neighbouring states still come back and are dropped by _is_victorian.
VICTORIA_BOUNDS = "140.95,-39.25,150.05,-33.95"
GEOCODE_TYPES = "place,locality,postcode,address,neighborhood,street"


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
    context = properties.get("context")
    if not isinstance(context, dict):
        return False
    region = context.get("region")
    if not isinstance(region, dict):
        return False

    region_code = region.get("region_code")
    region_name = region.get("name")
    return (
        isinstance(region_code, str)
        and region_code.upper() == "VIC"
        or isinstance(region_name, str)
        and region_name.casefold() == "victoria"
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

    label = properties.get("full_address") or properties.get("name")
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


def _geocoding_params(text: str, settings: Settings) -> dict[str, str | int]:
    if not settings.mapbox_token:
        raise GeocodingUnavailable("MAPBOX_TOKEN is not configured")
    return {
        "q": text,
        "access_token": settings.mapbox_token,
        "bbox": VICTORIA_BOUNDS,
        "country": "AU",
        "types": GEOCODE_TYPES,
        "limit": MAX_GEOCODING_RESULTS,
    }


async def _forward_geocode(
    text: str,
    settings: Settings,
    client: httpx.AsyncClient,
) -> list[GeocodingSuggestion]:
    try:
        response = await client.get(
            f"{MAPBOX_GEOCODE_BASE_URL}/forward",
            params=_geocoding_params(text, settings),
        )
        response.raise_for_status()
        return _victorian_suggestions(response.json())
    except (httpx.HTTPError, TypeError, ValueError) as exc:
        raise GeocodingUnavailable from exc


async def autocomplete_address(
    query: str,
    settings: Settings,
    client: httpx.AsyncClient,
) -> list[GeocodingSuggestion]:
    normalized_query = query.strip()
    if len(normalized_query) < 3:
        return []
    return await _forward_geocode(normalized_query, settings, client)


async def geocode_address(
    address: str,
    settings: Settings,
    client: httpx.AsyncClient,
) -> Coordinates:
    suggestions = await _forward_geocode(address.strip(), settings, client)
    if not suggestions:
        raise GeocodingUnavailable("No Victorian location matched the address")

    result = suggestions[0]
    return Coordinates(
        longitude=result.longitude,
        latitude=result.latitude,
        label=result.label,
    )
