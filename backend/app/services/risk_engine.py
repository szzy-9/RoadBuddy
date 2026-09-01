from dataclasses import dataclass

from app.schemas.trip import ConcernLevel, RiskFactor

# Prototype-only transparent rule set. It is not a crash probability model.
RULE_VERSION = "prototype-v0.1"


@dataclass(frozen=True)
class ConditionFlags:
    rain: bool = False
    after_dark: bool = False
    high_speed_zone: bool = False
    significant_crash_history: bool = False


FACTOR_LABELS = {
    "rain": "Rain is forecast during the journey",
    "after_dark": "Part of the journey is after dark",
    "high_speed_zone": "The route includes a high-speed road",
    "significant_crash_history": "Relevant historical crash clusters are near the route",
}

# Terse forms for the departure comparison cards, where the full labels above
# are too long to sit under a concern badge.
FACTOR_SHORT_LABELS = {
    "rain": "rain",
    "after_dark": "after dark",
    "high_speed_zone": "high-speed road",
    "significant_crash_history": "crash history",
}


def summarise_factors(factors: list[RiskFactor]) -> str | None:
    """Build a short phrase naming why a departure carries its concern level.

    Args:
        factors: The conditions that applied to this departure option.

    Returns:
        A comma-separated phrase such as "after dark, crash history", or None
        when no conditions applied.
    """
    if not factors:
        return None
    return ", ".join(FACTOR_SHORT_LABELS[factor.type] for factor in factors)


def calculate_concern(flags: ConditionFlags) -> tuple[ConcernLevel, list[RiskFactor]]:
    factors = [
        RiskFactor(type=name, label=FACTOR_LABELS[name])  # type: ignore[arg-type]
        for name, is_present in vars(flags).items()
        if is_present
    ]

    count = len(factors)
    if count >= 3:
        level = ConcernLevel.HIGHER
    elif count == 2:
        level = ConcernLevel.MEDIUM
    else:
        level = ConcernLevel.LOW

    return level, factors

