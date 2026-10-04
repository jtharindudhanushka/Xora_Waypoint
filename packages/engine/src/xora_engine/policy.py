"""Explicit BR-13 assumptions in value units, never currency."""

from dataclasses import dataclass

from xora_engine.models import Order


@dataclass(frozen=True)
class Policy:
    fresh_weight: float = 1.0
    style_weight: float = 0.6
    tech_weight: float = 1.2
    chilled_multiplier: float = 1.8
    days_skip_weight: float = 0.5
    repeat_skip_weight: float = 1.0
    festival_weight: float = 0.5
    mall_multiplier: float = 1.2
    trip_cost: float = 5.0
    litre_cost: float = 0.2


DEFAULT_POLICY = Policy()


def priority(order: Order, festival_ramp: float, policy: Policy = DEFAULT_POLICY) -> float:
    weights = {
        "Fresh": policy.fresh_weight,
        "Style": policy.style_weight,
        "Tech": policy.tech_weight,
    }
    return (
        order.volume_m3
        * weights[order.brand]
        * (policy.chilled_multiplier if order.temp == "chilled" else 1.0)
        * (
            1
            + policy.days_skip_weight * order.days_since_last_served
            + policy.repeat_skip_weight * order.deferred_yesterday
        )
        * (1 + policy.festival_weight * festival_ramp)
        * (policy.mall_multiplier if order.mall_open is not None else 1.0)
    )
