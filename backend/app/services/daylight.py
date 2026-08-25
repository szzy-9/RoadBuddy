from datetime import datetime

from astral import Observer
from astral.sun import sun


def is_after_dark(latitude: float, longitude: float, journey_time: datetime) -> bool:
    if journey_time.tzinfo is None:
        raise ValueError("journey_time must be timezone aware")
    solar = sun(
        Observer(latitude=latitude, longitude=longitude),
        date=journey_time.date(),
        tzinfo=journey_time.tzinfo,
    )
    return not (solar["sunrise"] <= journey_time <= solar["sunset"])

