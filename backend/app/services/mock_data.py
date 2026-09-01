import hashlib
import math
from datetime import datetime

from app.schemas.trip import TripHotspot

MOCK_DATASET_UPDATED = datetime.fromisoformat("2024-12-31T00:00:00+11:00")

MOCK_CLUSTERS = [
    {
        "id": 101,
        "name": "Princes Fwy / Forsyth Rd",
        "crash_count": 12,
        "dominant_type": "Rear-end crashes",
        "wet_count": 9,
        "dark_count": 7,
        "longitude": 144.7417,
        "latitude": -37.8637,
        "first_year": 2019,
        "last_year": 2024,
    },
    {
        "id": 102,
        "name": "Western Ring Rd / Ballarat Rd",
        "crash_count": 9,
        "dominant_type": "Side-impact crashes",
        "wet_count": 4,
        "dark_count": 6,
        "longitude": 144.8248,
        "latitude": -37.7808,
        "first_year": 2020,
        "last_year": 2024,
    },
    {
        "id": 103,
        "name": "Footscray Rd / Dock Link Rd",
        "crash_count": 7,
        "dominant_type": "Lane-change crashes",
        "wet_count": 3,
        "dark_count": 4,
        "longitude": 144.9192,
        "latitude": -37.8109,
        "first_year": 2019,
        "last_year": 2024,
    },
    {
        "id": 104,
        "name": "Hoddle St / Victoria Pde",
        "crash_count": 15,
        "dominant_type": "Rear-end crashes",
        "wet_count": 6,
        "dark_count": 5,
        "longitude": 144.9912,
        "latitude": -37.8093,
        "first_year": 2019,
        "last_year": 2024,
    },
]

KNOWN_LOCATIONS = {
    "tarneit": (144.6570, -37.8233),
    "docklands": (144.9465, -37.8150),
    "melbourne": (144.9631, -37.8136),
    "geelong": (144.3617, -38.1499),
}


def mock_geocode(address: str) -> tuple[float, float]:
    lowered = address.lower()
    for name, coordinates in KNOWN_LOCATIONS.items():
        if name in lowered:
            return coordinates

    digest = hashlib.sha256(lowered.encode("utf-8")).digest()
    longitude = 144.75 + (int.from_bytes(digest[:2], "big") / 65535) * 0.35
    latitude = -37.92 + (int.from_bytes(digest[2:4], "big") / 65535) * 0.25
    return longitude, latitude


def mock_route_metrics(start: tuple[float, float], end: tuple[float, float]) -> tuple[float, int]:
    lon1, lat1 = start
    lon2, lat2 = end
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    direct_km = radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = round(max(direct_km * 1.24, 1.2), 1)
    duration_minutes = max(round(distance_km / 68 * 60), 4)
    return distance_km, duration_minutes


def mock_rain_at(departure_time: datetime) -> bool:
    # Repeatable half-hour window for exercising alternative-departure behaviour.
    return departure_time.minute < 30


def mock_after_dark(departure_time: datetime) -> bool:
    return departure_time.hour < 6 or departure_time.hour >= 19


def mock_trip_hotspots() -> list[TripHotspot]:
    return [
        TripHotspot(
            cluster_id=cluster["id"],
            crash_count=cluster["crash_count"],
            eligible_driver_age_crashes=cluster["crash_count"],
            young_driver_crashes=max(1, round(cluster["crash_count"] * 0.35)),
            young_driver_pct=(
                round(
                    100
                    * max(1, round(cluster["crash_count"] * 0.35))
                    / cluster["crash_count"],
                    2,
                )
                if cluster["crash_count"] >= 10
                else None
            ),
            young_driver_pct_displayable=cluster["crash_count"] >= 10,
            longitude=cluster["longitude"],
            latitude=cluster["latitude"],
        )
        for cluster in MOCK_CLUSTERS[:2]
    ]

