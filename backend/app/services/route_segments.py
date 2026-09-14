"""Split an existing driving polyline without needing a database or routing API."""

from math import asin, cos, radians, sin, sqrt

from app.schemas.trip import GeoLineString, RouteRiskSegment

ROUTE_SECTION_METRES = 450


def distance_metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance, sufficient for approximately 450 metre sections."""
    lon1, lat1 = map(radians, a)
    lon2, lat2 = map(radians, b)
    haversine = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6_371_008.8 * asin(sqrt(min(1.0, haversine)))


def split_route(geometry: GeoLineString) -> list[RouteRiskSegment]:
    """Retain every road vertex and share interpolated endpoints between sections.

    Splitting in memory keeps the whole route available during a database outage.
    The last section may be shorter; repeated vertices do not create extra sections.
    """
    sections: list[list[tuple[float, float]]] = []
    current = [geometry.coordinates[0]]
    remaining = float(ROUTE_SECTION_METRES)
    for endpoint in geometry.coordinates[1:]:
        start = current[-1]
        distance = distance_metres(start, endpoint)
        while distance >= remaining:
            fraction = remaining / distance
            boundary = (
                start[0] + (endpoint[0] - start[0]) * fraction,
                start[1] + (endpoint[1] - start[1]) * fraction,
            )
            current.append(boundary)
            sections.append(current)
            current = [boundary]
            start = boundary
            distance = distance_metres(start, endpoint)
            remaining = float(ROUTE_SECTION_METRES)
        if endpoint != current[-1]:
            current.append(endpoint)
        remaining -= distance
    if len(current) > 1:
        sections.append(current)
    if not sections:
        sections = [[geometry.coordinates[0], geometry.coordinates[-1]]]
    return [
        RouteRiskSegment(
            index=index,
            geometry=GeoLineString(type="LineString", coordinates=coordinates),
            nearby_crash_count=None,
        )
        for index, coordinates in enumerate(sections)
    ]
