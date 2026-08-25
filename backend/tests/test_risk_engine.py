import pytest

from app.schemas.trip import ConcernLevel
from app.services.risk_engine import RULE_VERSION, ConditionFlags, calculate_concern


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        (ConditionFlags(), ConcernLevel.LOW),
        (ConditionFlags(rain=True), ConcernLevel.LOW),
        (ConditionFlags(rain=True, after_dark=True), ConcernLevel.MEDIUM),
        (
            ConditionFlags(
                rain=True,
                after_dark=True,
                high_speed_zone=True,
            ),
            ConcernLevel.HIGHER,
        ),
        (
            ConditionFlags(
                rain=True,
                after_dark=True,
                high_speed_zone=True,
                significant_crash_history=True,
            ),
            ConcernLevel.HIGHER,
        ),
    ],
)
def test_prototype_concern_thresholds(flags: ConditionFlags, expected: ConcernLevel) -> None:
    level, factors = calculate_concern(flags)

    assert level == expected
    assert len(factors) == sum(vars(flags).values())


def test_rule_version_is_explicit() -> None:
    assert RULE_VERSION == "prototype-v0.1"

