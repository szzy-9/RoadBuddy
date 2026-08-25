from dataclasses import dataclass

import httpx

from app.config import Settings


class GeocodingUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Coordinates:
    longitude: float
    latitude: float
    label: str


async def geocode_address(
    address: str,
    settings: Settings,
    client: httpx.AsyncClient,
) -> Coordinates:
    if not settings.pelias_base_url:
        raise GeocodingUnavailable("PELIAS_BASE_URL is not configured")

    params: dict[str, str | int] = {"text": address, "size": 1}
    if settings.pelias_api_key:
        params["api_key"] = settings.pelias_api_key

    try:
        response = await client.get(
            f"{settings.pelias_base_url.rstrip('/')}/v1/search",
            params=params,
        )
        response.raise_for_status()
        payload = response.json()
        feature = payload["features"][0]
        longitude, latitude = feature["geometry"]["coordinates"][:2]
        label = feature.get("properties", {}).get("label", address)
        return Coordinates(
            longitude=float(longitude),
            latitude=float(latitude),
            label=str(label),
        )
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise GeocodingUnavailable from exc

