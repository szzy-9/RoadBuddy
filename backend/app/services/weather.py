from dataclasses import dataclass
from datetime import datetime

import httpx

from app.config import Settings


class WeatherUnavailable(Exception):
    pass


@dataclass(frozen=True)
class WeatherConditions:
    rain: bool
    precipitation_mm: float


async def get_weather_at(
    latitude: float,
    longitude: float,
    journey_time: datetime,
    settings: Settings,
    client: httpx.AsyncClient,
) -> WeatherConditions:
    try:
        response = await client.get(
            f"{settings.open_meteo_base_url.rstrip('/')}/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "precipitation,rain",
                "timezone": "auto",
                "start_date": journey_time.date().isoformat(),
                "end_date": journey_time.date().isoformat(),
            },
        )
        response.raise_for_status()
        hourly = response.json()["hourly"]
        times = [datetime.fromisoformat(value) for value in hourly["time"]]
        target = journey_time.replace(tzinfo=None)
        index = min(range(len(times)), key=lambda item: abs(times[item] - target))
        precipitation = float(hourly["precipitation"][index] or 0)
        rain = float(hourly["rain"][index] or 0)
        total = max(precipitation, rain)
        return WeatherConditions(rain=total >= 0.1, precipitation_mm=total)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise WeatherUnavailable from exc

