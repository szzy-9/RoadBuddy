import math
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings

MAPBOX_GEOCODE_BASE_URL = "https://api.mapbox.com/search/geocode/v6"
MAPBOX_SEARCH_BOX_BASE_URL = "https://api.mapbox.com/search/searchbox/v1"
MAX_GEOCODING_RESULTS = 5
# About 1km at Victorian latitudes; wide enough to collapse the same suburb
# returned by both endpoints, tight enough to keep adjacent suburbs apart.
DUPLICATE_PLACE_DEGREES = 0.01

# Mapbox ranks by relevance within the box but does not clip to it, so results
# from neighbouring states still come back and are dropped by _is_victorian.
VICTORIA_BOUNDS = "140.95,-39.25,150.05,-33.95"
# MELBOURNE_PROXIMITY = "144.9631,-37.8136"
GEOCODE_TYPES = "place,locality,postcode,address,neighborhood,street"

# The geocoding endpoint above indexes addresses, suburbs and postcodes but no
# points of interest, so a business name ("Ikea Springvale") matches nothing and
# Mapbox falls back to fuzzy street names anywhere in the country. Search Box
# carries the POI index, so autocomplete asks it first and keeps geocoding as
# the fallback for the plain addresses it is better at.
SEARCH_BOX_TYPES = "poi,place,locality,postcode,address,neighborhood,street"
# Only the feature kinds that can stand in for "the suburb the user meant".
LOCALITY_TYPES = "place,locality,postcode"


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


# Victorian postcodes occupy 3000-3999 and no other state uses that range, so a
# postcode identifies the state on its own.
VICTORIA_POSTCODE_RANGE = (3000, 3999)


def _postcode_is_victorian(context: dict[str, Any]) -> bool:
    """Fall back to the postcode when a feature carries no region.

    Search Box omits `context.region` on every point of interest, so a POI would
    otherwise be discarded no matter where it sits.
    """
    postcode = context.get("postcode")
    if not isinstance(postcode, dict):
        return False
    name = postcode.get("name")
    if not isinstance(name, str) or not name.strip().isdigit():
        return False

    low, high = VICTORIA_POSTCODE_RANGE
    return low <= int(name.strip()) <= high


def _is_victorian(properties: dict[str, Any]) -> bool:
    context = properties.get("context")
    if not isinstance(context, dict):
        return False
    region = context.get("region")
    if not isinstance(region, dict):
        return _postcode_is_victorian(context)

    region_code = region.get("region_code")
    region_name = region.get("name")
    if (
        isinstance(region_code, str)
        and region_code.upper() == "VIC"
        or isinstance(region_name, str)
        and region_name.casefold() == "victoria"
    ):
        return True
    # A region that names another state is authoritative; only an unusable one
    # falls through to the postcode.
    if isinstance(region_code, str) or isinstance(region_name, str):
        return False
    return _postcode_is_victorian(context)


def _joined(*parts: object) -> str | None:
    """Join the non-empty string parts into one comma-separated label."""
    kept = [part.strip() for part in parts if isinstance(part, str) and part.strip()]
    return ", ".join(kept) if kept else None


def _feature_label(properties: dict[str, Any]) -> str | None:
    """Build the line shown in the dropdown.

    Search Box splits a label across fields where geocoding returns one
    `full_address`: a point of interest holds its business name in `name` and
    only the street in `full_address`, while a suburb or postcode has no
    `full_address` at all and keeps its state in `place_formatted`. Without
    rejoining them, results read as a bare "Princes Hwy, Melbourne 3171" or an
    unusable "Springvale" with no state.
    """
    name = properties.get("name")
    address = properties.get("full_address")
    if isinstance(address, str) and address.strip():
        if properties.get("feature_type") == "poi":
            return _joined(name, address)
        return address.strip()
    return _joined(name, properties.get("place_formatted"))


def _parse_victorian_feature(feature: object) -> GeocodingSuggestion | None:
    if not isinstance(feature, dict):
        return None

    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    if not _is_victorian(properties):
        return None

    label = _feature_label(properties)
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
        # "proximity": MELBOURNE_PROXIMITY,
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


def _search_box_params(
    text: str,
    settings: Settings,
    proximity: str | None = None,
) -> dict[str, str | int]:
    if not settings.mapbox_token:
        raise GeocodingUnavailable("MAPBOX_TOKEN is not configured")
    params: dict[str, str | int] = {
        "q": text,
        "access_token": settings.mapbox_token,
        "bbox": VICTORIA_BOUNDS,
        "country": "AU",
        "types": SEARCH_BOX_TYPES,
        "limit": MAX_GEOCODING_RESULTS,
    }
    if proximity:
        params["proximity"] = proximity
    return params


async def _search_box_forward(
    text: str,
    settings: Settings,
    client: httpx.AsyncClient,
    proximity: str | None = None,
) -> list[GeocodingSuggestion]:
    try:
        response = await client.get(
            f"{MAPBOX_SEARCH_BOX_BASE_URL}/forward",
            params=_search_box_params(text, settings, proximity),
        )
        response.raise_for_status()
        return _victorian_suggestions(response.json())
    except (httpx.HTTPError, TypeError, ValueError) as exc:
        raise GeocodingUnavailable from exc


async def _locality_match(
    text: str,
    settings: Settings,
    client: httpx.AsyncClient,
) -> GeocodingSuggestion | None:
    """Resolve text to the Victorian suburb or postcode it names, if any."""
    try:
        response = await client.get(
            f"{MAPBOX_GEOCODE_BASE_URL}/forward",
            params={
                "q": text,
                "access_token": settings.mapbox_token,
                "bbox": VICTORIA_BOUNDS,
                "country": "AU",
                "types": LOCALITY_TYPES,
                "limit": 1,
            },
        )
        response.raise_for_status()
        matches = _victorian_suggestions(response.json())
    except (httpx.HTTPError, TypeError, ValueError):
        return None
    return matches[0] if matches else None


def _names_the_whole_place(text: str, match: GeocodingSuggestion) -> bool:
    """Whether `text` is the place's name rather than a phrase containing it.

    Mapbox answers a locality lookup with its best partial match, so "Ikea
    Springvale" comes back as "Springvale". Only treat the text as a place when
    the matched name accounts for all of it, or the search would split a
    two-word suburb like "Glen Iris" into a business and a suburb.
    """
    return _leading_name(match.label) == text.strip().casefold()


async def _branch_near_locality(
    query: str,
    settings: Settings,
    client: httpx.AsyncClient,
) -> list[GeocodingSuggestion]:
    """Find "<business> <suburb>" by searching the business near the suburb.

    Mapbox ranks a point of interest whose own name contains the suburb above
    the branch that actually sits there, so "Ikea Springvale" returns a van
    hire pod named after the store rather than the store. Splitting the suburb
    off and passing it as a proximity bias instead puts the real branch first.
    """
    words = query.split()
    if len(words) < 2:
        return []

    # The query may already name a place ("Glen Iris"), in which case splitting
    # it invents a business out of half a suburb and searches somewhere
    # unrelated.
    whole = await _locality_match(query, settings, client)
    if whole is not None and _names_the_whole_place(query, whole):
        return []

    # Suburbs run to two words ("Springvale South", "Wantirna South"), so try
    # the longer tail first and keep at least one word as the business name.
    for tail_length in (2, 1):
        if tail_length >= len(words):
            continue
        head = " ".join(words[:-tail_length])
        tail = " ".join(words[-tail_length:])
        match = await _locality_match(tail, settings, client)
        if match is None or not _names_the_whole_place(tail, match):
            continue
        proximity = f"{match.longitude},{match.latitude}"
        return await _search_box_forward(head, settings, client, proximity)
    return []


def _leading_name(label: str) -> str:
    """The part of a label before the first comma, folded for comparison."""
    return label.split(",", 1)[0].strip().casefold()


def _is_duplicate_place(
    suggestion: GeocodingSuggestion,
    existing: GeocodingSuggestion,
) -> bool:
    """Whether two results name the same place.

    The two endpoints return a suburb at slightly different points, so the same
    place arrives twice with coordinates that differ by a few hundred metres and
    labels that differ in wording. Matching the leading name within a small
    radius catches that without merging genuinely distinct neighbours.
    """
    if _leading_name(suggestion.label) != _leading_name(existing.label):
        return False
    return (
        abs(suggestion.longitude - existing.longitude) <= DUPLICATE_PLACE_DEGREES
        and abs(suggestion.latitude - existing.latitude) <= DUPLICATE_PLACE_DEGREES
    )


def _merge_suggestions(
    *groups: list[GeocodingSuggestion],
) -> list[GeocodingSuggestion]:
    """Combine result sets in order, dropping repeats of the same place."""
    merged: list[GeocodingSuggestion] = []
    for group in groups:
        for suggestion in group:
            if any(_is_duplicate_place(suggestion, kept) for kept in merged):
                continue
            merged.append(suggestion)
            if len(merged) == MAX_GEOCODING_RESULTS:
                return merged
    return merged


async def autocomplete_address(
    query: str,
    settings: Settings,
    client: httpx.AsyncClient,
) -> list[GeocodingSuggestion]:
    normalized_query = query.strip()
    if len(normalized_query) < 3:
        return []

    # A POI lookup is the only way to match a business name, but it is the
    # weaker of the two for plain addresses, so both run and the POI hits lead.
    try:
        poi_results = await _search_box_forward(normalized_query, settings, client)
    except GeocodingUnavailable:
        # Search Box being down must not take address search down with it; the
        # geocoding call below still answers everything except POIs.
        poi_results = []

    # "<business> <suburb>" needs the suburb split off to rank the real branch
    # first, so it leads when it finds anything.
    try:
        branch_results = await _branch_near_locality(normalized_query, settings, client)
    except GeocodingUnavailable:
        branch_results = []

    if len(branch_results) >= MAX_GEOCODING_RESULTS:
        return branch_results

    try:
        address_results = await _forward_geocode(normalized_query, settings, client)
    except GeocodingUnavailable:
        merged = _merge_suggestions(branch_results, poi_results)
        if merged:
            return merged
        raise

    return _merge_suggestions(branch_results, poi_results, address_results)


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
