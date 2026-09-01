import asyncio
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import perf_counter

import httpx
from sqlalchemy.orm import Session

from app.config import Settings
from app.schemas.trip import (
    AlternativeDeparture,
    ConcernLevel,
    DataAvailability,
    DepartureComparison,
    DepartureComparisonOption,
    GeoPoint,
    RiskFactor,
    RouteSummary,
    TripCheckRequest,
    TripCheckResponse,
    TripDataStatus,
)
from app.services.crash_query import (
    CrashDataUnavailable,
    get_endpoint_hotspots,
    route_has_high_speed_zone,
)
from app.services.daylight import is_after_dark
from app.services.geocoding import Coordinates, GeocodingUnavailable, geocode_address
from app.services.mock_data import (
    mock_after_dark,
    mock_geocode,
    mock_rain_at,
    mock_route_metrics,
    mock_trip_hotspots,
)
from app.services.risk_engine import (
    RULE_VERSION,
    ConditionFlags,
    calculate_concern,
    summarise_factors,
)
from app.services.routing import RoutingUnavailable, calculate_route
from app.services.weather import WeatherConditions, get_weather_at

logger = logging.getLogger("uvicorn.error")


class RouteUnavailable(Exception):
    pass


@dataclass(frozen=True)
class DepartureEvaluation:
    concern_level: ConcernLevel
    factors: list[RiskFactor]
    comparison: DepartureComparison
    alternative: AlternativeDeparture | None


def _to_geo_point(coordinates: Coordinates) -> GeoPoint:
    """Convert internal geocoding coordinates into the public GeoPoint schema."""
    return GeoPoint(longitude=coordinates.longitude, latitude=coordinates.latitude)


def _tuple_to_geo_point(coordinates: tuple[float, float]) -> GeoPoint:
    """Convert a mock (longitude, latitude) pair into the public GeoPoint schema."""
    longitude, latitude = coordinates
    return GeoPoint(longitude=longitude, latitude=latitude)


@contextmanager
def _timed_stage(stage: str) -> Iterator[None]:
    started_at = perf_counter()
    try:
        yield
    except Exception as exc:
        logger.warning(
            "Trip check stage '%s' failed after %.2fs (%s)",
            stage,
            perf_counter() - started_at,
            type(exc).__name__,
        )
        raise
    else:
        logger.info(
            "Trip check stage '%s' completed in %.2fs",
            stage,
            perf_counter() - started_at,
        )


def _difference_summary(
    selected_flags: ConditionFlags,
    later_flags: ConditionFlags,
) -> str | None:
    summaries: list[str] = []
    if selected_flags.rain != later_flags.rain:
        summaries.append(
            "Rain is forecast to ease."
            if selected_flags.rain
            else "Rain is forecast for the later option."
        )
    if selected_flags.after_dark != later_flags.after_dark:
        summaries.append(
            "The later option is expected to be in daylight."
            if selected_flags.after_dark
            else "The later option is expected to be after dark."
        )
    return " ".join(summaries) or None


def _evaluate_departures(
    selected_departure: datetime,
    duration_minutes: int,
    selected_flags: ConditionFlags,
    later_flags: ConditionFlags,
) -> DepartureEvaluation:
    selected_level, selected_factors = calculate_concern(selected_flags)
    later_level, later_factors = calculate_concern(later_flags)
    later_departure = selected_departure + timedelta(minutes=30)

    comparison = DepartureComparison(
        selected=DepartureComparisonOption(
            departure_time=selected_departure,
            arrival_time=selected_departure + timedelta(minutes=duration_minutes),
            concern_level=selected_level,
            factor_count=len(selected_factors),
            factors=selected_factors,
            reason=summarise_factors(selected_factors),
        ),
        thirty_minutes_later=DepartureComparisonOption(
            departure_time=later_departure,
            arrival_time=later_departure + timedelta(minutes=duration_minutes),
            concern_level=later_level,
            factor_count=len(later_factors),
            factors=later_factors,
            reason=summarise_factors(later_factors),
        ),
        difference_summary=_difference_summary(selected_flags, later_flags),
    )

    alternative = None
    if len(later_factors) < len(selected_factors):
        alternative = AlternativeDeparture(
            departure_time=later_departure,
            concern_level=later_level,
            factor_count=len(later_factors),
        )

    return DepartureEvaluation(
        concern_level=selected_level,
        factors=selected_factors,
        comparison=comparison,
        alternative=alternative,
    )


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
    later_time = request.departure_time + timedelta(minutes=30)
    later_flags = ConditionFlags(
        rain=mock_rain_at(later_time),
        after_dark=mock_after_dark(later_time),
        high_speed_zone=selected_flags.high_speed_zone,
        significant_crash_history=selected_flags.significant_crash_history,
    )
    departure_evaluation = _evaluate_departures(
        request.departure_time,
        duration_minutes,
        selected_flags,
        later_flags,
    )

    return TripCheckResponse(
        route=RouteSummary(
            origin=request.origin,
            destination=request.destination,
            origin_point=_tuple_to_geo_point(origin_coordinates),
            destination_point=_tuple_to_geo_point(destination_coordinates),
            distance_km=distance_km,
            duration_minutes=duration_minutes,
        ),
        concern_level=departure_evaluation.concern_level,
        factors=departure_evaluation.factors,
        hotspots=mock_trip_hotspots(),
        alternative_departure=departure_evaluation.alternative,
        departure_comparison=departure_evaluation.comparison,
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
            with _timed_stage("geocoding"):
                origin_coordinates, destination_coordinates = await asyncio.gather(
                    geocode_address(request.origin, settings, client),
                    geocode_address(request.destination, settings, client),
                )
            with _timed_stage("routing"):
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
            with _timed_stage("crash-history query"):
                hotspots = get_endpoint_hotspots(
                    session,
                    origin_coordinates.longitude,
                    origin_coordinates.latitude,
                    destination_coordinates.longitude,
                    destination_coordinates.latitude,
                    use_mock_data=False,
                )
            crash_status = DataAvailability.AVAILABLE
        except CrashDataUnavailable:
            hotspots = []
            crash_status = DataAvailability.UNAVAILABLE

        try:
            with _timed_stage("speed-zone query"):
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

        weather_started_at = perf_counter()
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

        weather_available = all(
            isinstance(item, WeatherConditions) for item in weather_results
        )
        if weather_available:
            logger.info(
                "Trip check stage 'weather' completed in %.2fs",
                perf_counter() - weather_started_at,
            )
        else:
            failure_types = sorted(
                {
                    type(item).__name__
                    for item in weather_results
                    if not isinstance(item, WeatherConditions)
                }
            )
            logger.warning(
                "Trip check stage 'weather' returned unavailable data after %.2fs (%s)",
                perf_counter() - weather_started_at,
                ", ".join(failure_types),
            )

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
    later_flags = ConditionFlags(
        rain=later_rain,
        after_dark=is_after_dark(midpoint_latitude, midpoint_longitude, later_midpoint),
        **static_flags,
    )
    departure_evaluation = _evaluate_departures(
        request.departure_time,
        route.duration_minutes,
        selected_flags,
        later_flags,
    )

    return TripCheckResponse(
        route=RouteSummary(
            origin=request.origin,
            destination=request.destination,
            origin_point=_to_geo_point(origin_coordinates),
            destination_point=_to_geo_point(destination_coordinates),
            distance_km=route.distance_km,
            duration_minutes=route.duration_minutes,
        ),
        concern_level=departure_evaluation.concern_level,
        factors=departure_evaluation.factors,
        hotspots=hotspots,
        alternative_departure=departure_evaluation.alternative,
        departure_comparison=departure_evaluation.comparison,
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
