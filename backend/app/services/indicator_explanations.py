TRIP_INDICATOR_LIMITATIONS: dict[str, str] = {
    "rain": (
        "Does not account for local visibility, road drainage, standing water or "
        "rapidly changing weather along every part of the route."
    ),
    "after_dark": (
        "Does not account for street lighting, headlight condition, glare or "
        "the driver's actual visibility."
    ),
    "high_speed_zone": (
        "Does not account for the driver's actual speed, temporary speed restrictions, "
        "traffic flow or current roadworks."
    ),
    "significant_crash_history": (
        "Historical crash records do not account for current traffic, passengers or "
        "individual driver behaviour, and do not predict a future crash."
    ),
}

RADAR_CLUSTER_LIMITATION = (
    "Historical crash records describe recorded past crashes only. They do not account "
    "for current traffic or individual driver behaviour and do not predict where the "
    "next crash will occur."
)
