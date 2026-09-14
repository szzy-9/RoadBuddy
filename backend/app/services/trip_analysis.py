import asyncio
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import perf_counter

import httpx
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.schemas.indicator import IndicatorExplanation
from app.schemas.trip import (
    AlternativeDeparture,
    ConcernLevel,
    DataAvailability,
    DepartureComparison,
    DepartureComparisonOption,
    GeoLineString,
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
    get_route_segment_crash_counts,
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
from app.services.route_segments import split_route
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
    selected_explanations: dict[str, IndicatorExplanation] | None = None,
    later_explanations: dict[str, IndicatorExplanation] | None = None,
) -> DepartureEvaluation:
    selected_level, selected_factors = calculate_concern(selected_flags)
    later_level, later_factors = calculate_concern(later_flags)
    selected_factors = [
        factor.model_copy(update={"explanation": (selected_explanations or {}).get(factor.type)})
        for factor in selected_factors
    ]
    later_factors = [
        factor.model_copy(update={"explanation": (later_explanations or {}).get(factor.type)})
        for factor in later_factors
    ]
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


def _trip_factor_explanations(
    flags: ConditionFlags,
    midpoint: datetime,
    weather: WeatherConditions | None,
    qualifying_hotspot_count: int,
) -> dict[str, IndicatorExplanation]:
    """Describe only the available observations behind the evaluated factors."""
    explanations: dict[str, IndicatorExplanation] = {}
    if flags.rain and weather is not None:
        explanations["rain"] = IndicatorExplanation(
            source="Open-Meteo",
            trigger=(f"{weather.precipitation_mm:g} mm precipitation is forecast "
                     "around the route midpoint."),
        )
    if flags.after_dark:
        explanations["after_dark"] = IndicatorExplanation(
            source="Astral daylight calculation",
            trigger=(f"The journey midpoint at {midpoint:%H:%M} is after dark "
                     "at the route midpoint."),
        )
    if flags.high_speed_zone:
        explanations["high_speed_zone"] = IndicatorExplanation(
            source="Vicmap Speed Zones",
            trigger="The route intersects a recorded high-speed zone.",
        )
    if flags.significant_crash_history and qualifying_hotspot_count:
        subject = ("1 nearby crash cluster has" if qualifying_hotspot_count == 1
                   else f"{qualifying_hotspot_count} nearby crash clusters have")
        explanations["significant_crash_history"] = IndicatorExplanation(
            source="Victorian Road Crash Data",
            trigger=f"{subject} at least 5 recorded injury crashes.",
        )
    return explanations


def _mock_factor_explanations(departure: datetime) -> dict[str, IndicatorExplanation]:
    """The development sample evaluates its boolean conditions at departure."""
    triggers = {
        "rain": f"The sample rain condition is enabled for departure at {departure:%H:%M}.",
        "after_dark": f"The sample marks departure at {departure:%H:%M} as after dark.",
        "high_speed_zone": "The sample route is flagged as including a high-speed road.",
        "significant_crash_history": "The sample route is flagged for significant crash history.",
    }
    return {
        factor_type: IndicatorExplanation(source="RoadBuddy development sample", trigger=trigger)
        for factor_type, trigger in triggers.items()
    }


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
    mock_points = [origin_coordinates, destination_coordinates]
    if origin_coordinates == destination_coordinates:
        # Mock geocoding resolves whole suburbs to one point. Give two addresses
        # in that suburb a deterministic sample loop rather than a collapsed line.
        longitude, latitude = origin_coordinates
        mock_points = [origin_coordinates, (longitude + .003, latitude + .002),
                       (longitude + .003, latitude), destination_coordinates]
    geometry = GeoLineString(type="LineString", coordinates=mock_points)
    segments = split_route(geometry)
    for segment in segments:
        segment.nearby_crash_count = (0, 5, 10, 20, 50)[segment.index % 5]

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
        selected_explanations=_mock_factor_explanations(request.departure_time),
        later_explanations=_mock_factor_explanations(later_time),
    )

    return TripCheckResponse(
        route=RouteSummary(
            origin=request.origin,
            destination=request.destination,
            origin_point=_tuple_to_geo_point(origin_coordinates),
            destination_point=_tuple_to_geo_point(destination_coordinates),
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            geometry=geometry,
            segments=segments,
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
                geometry = GeoLineString.model_validate(route.geometry)
        except (GeocodingUnavailable, RoutingUnavailable, ValidationError) as exc:
            raise RouteUnavailable from exc

        route_geojson = json.dumps(route.geometry, separators=(",", ":"))
        segments = split_route(geometry)
        try:
            with _timed_stage("crash-history query"):
                hotspots = get_endpoint_hotspots(
                    session,
                    origin_coordinates.longitude,
                    origin_coordinates.latitude,
                    destination_coordinates.longitude,
                    destination_coordinates.latitude,
                    use_mock_data=False,
                    route_geojson=route_geojson,
                )
            crash_status = DataAvailability.AVAILABLE
        except CrashDataUnavailable:
            session.rollback()
            hotspots = []
            crash_status = DataAvailability.UNAVAILABLE

        try:
            with _timed_stage("route-section crash query"):
                counts = get_route_segment_crash_counts(session, segments)
            for segment in segments:
                segment.nearby_crash_count = counts.get(segment.index)
            if any(segment.nearby_crash_count is None for segment in segments):
                crash_status = DataAvailability.UNAVAILABLE
        except CrashDataUnavailable:
            session.rollback()
            crash_status = DataAvailability.UNAVAILABLE

        try:
            with _timed_stage("speed-zone query"):
                high_speed_zone = route_has_high_speed_zone(session, route_geojson)
            speed_status = DataAvailability.AVAILABLE
        except CrashDataUnavailable:
            session.rollback()
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
    qualifying_hotspot_count = sum(hotspot.crash_count >= 5 for hotspot in hotspots)
    departure_evaluation = _evaluate_departures(
        request.departure_time,
        route.duration_minutes,
        selected_flags,
        later_flags,
        selected_explanations=_trip_factor_explanations(
            selected_flags, journey_midpoint,
            weather_results[0] if isinstance(weather_results[0], WeatherConditions) else None,
            qualifying_hotspot_count,
        ),
        later_explanations=_trip_factor_explanations(
            later_flags, later_midpoint,
            weather_results[1] if isinstance(weather_results[1], WeatherConditions) else None,
            qualifying_hotspot_count,
        ),
    )

    return TripCheckResponse(
        route=RouteSummary(
            origin=request.origin,
            destination=request.destination,
            origin_point=_to_geo_point(origin_coordinates),
            destination_point=_to_geo_point(destination_coordinates),
            distance_km=route.distance_km,
            duration_minutes=route.duration_minutes,
            geometry=geometry,
            segments=segments,
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
