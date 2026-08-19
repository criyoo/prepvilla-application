from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any


SUBSCRIPTION_CURRENCY = "NGN"

# This catalog is the single source of truth for subscription names, prices,
# durations, and benefits. The frontend reads the same values through the
# subscription-plans API, while checkout resolves amounts directly from here.
SUBSCRIPTION_PLANS: tuple[dict[str, Any], ...] = (
    {
        "code": "free",
        "name": "14 Days Free",
        "price": Decimal("0.00"),
        "duration_days": 14,
        "badge": "Start here",
        "summary": "Explore PrepVilla free for 14 days.",
        "features": (
            "14 days of platform access",
            "Manage your dashboard and profile",
            "Explore the core learning and teaching tools",
            "No payment required",
        ),
    },
    {
        "code": "silver",
        "name": "Silver Package",
        "price": Decimal("500.00"),
        "duration_days": 30,
        "badge": "Essential",
        "summary": "Access for regular tutoring.",
        "features": (
            "Everything in the free package",
            "30 days of platform access",
            "Bookings and messaging tools",
            "Standard customer support",
        ),
    },
    {
        "code": "gold",
        "name": "Gold Package",
        "price": Decimal("750.00"),
        "duration_days": 30,
        "badge": "Most popular",
        "summary": "More support for active students/tutors.",
        "features": (
            "Everything in the Silver Package",
            "30 days of platform access",
            "Complete dashboard tools",
            "Priority customer support",
        ),
    },
    {
        "code": "platinum",
        "name": "Platinum Package",
        "price": Decimal("1000.00"),
        "duration_days": 30,
        "badge": "Premium",
        "summary": "PrepVilla's premium subscription experience.",
        "features": (
            "Everything in the Gold Package",
            "30 days of platform access",
            "Premium dashboard experience",
            "Premium customer support",
        ),
    },
)


def get_subscription_plan(code: str) -> dict[str, Any] | None:
    normalized_code = str(code or "").strip().lower()
    return next((plan for plan in SUBSCRIPTION_PLANS if plan["code"] == normalized_code), None)


def get_subscription_plan_catalog() -> dict[str, Any]:
    plans = []
    for plan in SUBSCRIPTION_PLANS:
        serialized_plan = deepcopy(plan)
        price = serialized_plan["price"]
        serialized_plan["price"] = int(price) if price == price.to_integral_value() else float(price)
        serialized_plan["durationDays"] = serialized_plan.pop("duration_days")
        serialized_plan["features"] = list(serialized_plan["features"])
        plans.append(serialized_plan)
    return {"currency": SUBSCRIPTION_CURRENCY, "plans": plans}
