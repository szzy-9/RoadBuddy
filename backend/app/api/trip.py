from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.connection import get_db
from app.schemas.trip import TripCheckRequest, TripCheckResponse
from app.services.trip_analysis import RouteUnavailable, analyse_trip

router = APIRouter(prefix="/trip", tags=["trip"])


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
