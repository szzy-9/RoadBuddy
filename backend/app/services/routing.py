from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings
from app.services.geocoding import Coordinates


class RoutingUnavailable(Exception):
    pass


@dataclass(frozen=True)
class RouteResult:
    distance_km: float
    duration_minutes: int
    geometry: dict[str, Any]


async def calculate_route(
    origin: Coordinates,
    destination: Coordinates,
    settings: Settings,
    client: httpx.AsyncClient,
) -> RouteResult:
    if not settings.ors_api_key:
        raise RoutingUnavailable("ORS_API_KEY is not configured")

    try:
        response = await client.post(
            "https://api.openrouteservice.org/v2/directions/driving-car/geojson",
            headers={
                "Authorization": settings.ors_api_key,
                "Accept": "application/geo+json",
                "Content-Type": "application/json",
            },
            json={
                "coordinates": [
                    [origin.longitude, origin.latitude],
                    [destination.longitude, destination.latitude],
                ],
                "instructions": False,
            },
        )
        response.raise_for_status()
        feature = response.json()["features"][0]
        summary = feature["properties"]["summary"]
        geometry = feature["geometry"]
        if geometry.get("type") != "LineString":
            raise ValueError("OpenRouteService did not return a LineString")
        return RouteResult(
            distance_km=round(float(summary["distance"]) / 1000, 1),
            duration_minutes=max(round(float(summary["duration"]) / 60), 1),
            geometry=geometry,
        )
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise RoutingUnavailable from exc

