from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.connection import get_db
from app.schemas.trip import (
    LocationSuggestion,
    LocationSuggestionsResponse,
    TripCheckRequest,
    TripCheckResponse,
)
from app.services.geocoding import GeocodingUnavailable, autocomplete_address
from app.services.trip_analysis import RouteUnavailable, analyse_trip

router = APIRouter(prefix="/trip", tags=["trip"])


@router.get("/locations", response_model=LocationSuggestionsResponse)
async def locations(
    q: Annotated[str, Query(max_length=200)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LocationSuggestionsResponse:
    query = q.strip()
    if len(query) < 3:
        return LocationSuggestionsResponse(suggestions=[])

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.request_timeout_seconds)
        ) as client:
            results = await autocomplete_address(query, settings, client)
    except GeocodingUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="Location search is temporarily unavailable. Please try again.",
        ) from exc

    return LocationSuggestionsResponse(
        suggestions=[
            LocationSuggestion(
                label=result.label,
                longitude=result.longitude,
                latitude=result.latitude,
            )
            for result in results
        ]
    )


@router.post("/check", response_model=TripCheckResponse)
async def check_trip(
    request: TripCheckRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[Session, Depends(get_db)],
) -> TripCheckResponse:
    try:
        return await analyse_trip(request, settings, session)
    except RouteUnavailable as exc:
        raise HTTPException(
            status_code=502,
            detail="We could not calculate this route. Please check the locations and try again.",
        ) from exc
