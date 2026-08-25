import asyncio
import json
from datetime import timedelta

import httpx
from sqlalchemy.orm import Session

from app.config import Settings
from app.schemas.trip import (
    AlternativeDeparture,
    DataAvailability,
    RouteSummary,
    TripCheckRequest,
    TripCheckResponse,
    TripDataStatus,
)
from app.services.crash_query import (
    CrashDataUnavailable,
    get_route_hotspots,
    route_has_high_speed_zone,
)
from app.services.daylight import is_after_dark
from app.services.geocoding import GeocodingUnavailable, geocode_address
from app.services.mock_data import (
    mock_after_dark,
    mock_geocode,
    mock_rain_at,
    mock_route_metrics,
    mock_trip_hotspots,
)
from app.services.risk_engine import RULE_VERSION, ConditionFlags, calculate_concern
from app.services.routing import RoutingUnavailable, calculate_route
from app.services.weather import WeatherConditions, get_weather_at


class RouteUnavailable(Exception):
    pass


async def analyse_trip(
    request: TripCheckRequest,
    settings: Settings,
    _session: Session,
) -> TripCheckResponse:
    if not settings.use_mock_data:
        return await _analyse_production_trip(request, settings, _session)

    return _analyse_mock_trip(request)


def _analyse_mock_trip(request: TripCheckRequest) -> TripCheckResponse:

    origin_coordinates = mock_geocode(request.origin)
    destination_coordinates = mock_geocode(request.destination)
    distance_km, duration_minutes = mock_route_metrics(
        origin_coordinates,
        destination_coordinates,
    )

    selected_flags = ConditionFlags(
        rain=mock_rain_at(request.departure_time),
        after_dark=mock_after_dark(request.departure_time),
        high_speed_zone=True,
        significant_crash_history=True,
    )
    concern_level, factors = calculate_concern(selected_flags)

    later_time = request.departure_time + timedelta(minutes=30)
    later_flags = ConditionFlags(
        rain=mock_rain_at(later_time),
        after_dark=mock_after_dark(later_time),
        high_speed_zone=selected_flags.high_speed_zone,
        significant_crash_history=selected_flags.significant_crash_history,
    )
    later_level, later_factors = calculate_concern(later_flags)
    alternative = None
    if len(later_factors) < len(factors):
        alternative = AlternativeDeparture(
            departure_time=later_time,
            concern_level=later_level,
            factor_count=len(later_factors),
        )

    return TripCheckResponse(
        route=RouteSummary(
            origin=request.origin,
            destination=request.destination,
            distance_km=distance_km,
            duration_minutes=duration_minutes,
        ),
        concern_level=concern_level,
        factors=factors,
        hotspots=mock_trip_hotspots(),
        alternative_departure=alternative,
        data_status=TripDataStatus(
            weather=DataAvailability.AVAILABLE,
            crash_data=DataAvailability.AVAILABLE,
            speed_zones=DataAvailability.AVAILABLE,
        ),
        rule_version=RULE_VERSION,
    )


async def _analyse_production_trip(
    request: TripCheckRequest,
    settings: Settings,
    session: Session,
) -> TripCheckResponse:
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            origin_coordinates, destination_coordinates = await asyncio.gather(
                geocode_address(request.origin, settings, client),
                geocode_address(request.destination, settings, client),
            )
            route = await calculate_route(
                origin_coordinates,
                destination_coordinates,
                settings,
                client,
            )
        except (GeocodingUnavailable, RoutingUnavailable) as exc:
            raise RouteUnavailable from exc

        route_geojson = json.dumps(route.geometry, separators=(",", ":"))
        try:
            hotspots = get_route_hotspots(session, route_geojson, use_mock_data=False)
            crash_status = DataAvailability.AVAILABLE
        except CrashDataUnavailable:
            hotspots = []
            crash_status = DataAvailability.UNAVAILABLE

        try:
            high_speed_zone = route_has_high_speed_zone(session, route_geojson)
            speed_status = DataAvailability.AVAILABLE
        except CrashDataUnavailable:
            high_speed_zone = False
            speed_status = DataAvailability.UNAVAILABLE

        midpoint_latitude = (origin_coordinates.latitude + destination_coordinates.latitude) / 2
        midpoint_longitude = (origin_coordinates.longitude + destination_coordinates.longitude) / 2
        journey_midpoint = request.departure_time + timedelta(minutes=route.duration_minutes / 2)
        later_departure = request.departure_time + timedelta(minutes=30)
        later_midpoint = later_departure + timedelta(minutes=route.duration_minutes / 2)

        weather_results = await asyncio.gather(
            get_weather_at(
                midpoint_latitude,
                midpoint_longitude,
                journey_midpoint,
                settings,
                client,
            ),
            get_weather_at(
                midpoint_latitude,
                midpoint_longitude,
                later_midpoint,
                settings,
                client,
            ),
            return_exceptions=True,
        )

    weather_available = all(isinstance(item, WeatherConditions) for item in weather_results)
    selected_rain = (
        weather_results[0].rain
        if isinstance(weather_results[0], WeatherConditions)
        else False
    )
    later_rain = (
        weather_results[1].rain
        if isinstance(weather_results[1], WeatherConditions)
        else False
    )

    static_flags = {
        "high_speed_zone": high_speed_zone,
        "significant_crash_history": any(hotspot.crash_count >= 5 for hotspot in hotspots),
    }
    selected_flags = ConditionFlags(
        rain=selected_rain,
        after_dark=is_after_dark(midpoint_latitude, midpoint_longitude, journey_midpoint),
        **static_flags,
    )
    concern_level, factors = calculate_concern(selected_flags)

    later_flags = ConditionFlags(
        rain=later_rain,
        after_dark=is_after_dark(midpoint_latitude, midpoint_longitude, later_midpoint),
        **static_flags,
    )
    later_level, later_factors = calculate_concern(later_flags)
    alternative = None
    if len(later_factors) < len(factors):
        alternative = AlternativeDeparture(
            departure_time=later_departure,
            concern_level=later_level,
            factor_count=len(later_factors),
        )

    return TripCheckResponse(
        route=RouteSummary(
            origin=request.origin,
            destination=request.destination,
            distance_km=route.distance_km,
            duration_minutes=route.duration_minutes,
        ),
        concern_level=concern_level,
        factors=factors,
        hotspots=hotspots,
        alternative_departure=alternative,
        data_status=TripDataStatus(
            weather=(
                DataAvailability.AVAILABLE
                if weather_available
                else DataAvailability.UNAVAILABLE
            ),
            crash_data=crash_status,
            speed_zones=speed_status,
        ),
        rule_version=RULE_VERSION,
    )
