"""Classify AHJ fee lines so estimators do not mix permit vs tap vs impact."""

from __future__ import annotations

from typing import Tuple

KIND_PERMIT = "permit"
KIND_TAP = "tap / connection"
KIND_IMPACT = "impact"
KIND_OTHER = "other — confirm AHJ"

_HINTS = {
    KIND_PERMIT: "Permit / review — not a tap or impact fee",
    KIND_TAP: "Utility tap / connection — not the building permit",
    KIND_IMPACT: "Impact / capacity — often larger than the permit",
    KIND_OTHER: "Unlabeled — confirm kind on the official schedule",
}


def classify_fee_kind(label: str = "", detail: str = "", trade: str = "") -> str:
    t = f"{label} {detail} {trade}".lower()
    if any(
        x in t
        for x in (
            "impact fee",
            "impact fees",
            "roadway impact",
            "park impact",
            "pro rata",
            "pro-rata",
            "capital recovery",
        )
    ):
        return KIND_IMPACT
    if any(
        x in t
        for x in (
            "tap fee",
            "water tap",
            "sewer tap",
            "meter ",
            "connection fee",
            "water connection",
            "wastewater connection",
            "service connection",
        )
    ):
        return KIND_TAP
    if any(
        x in t
        for x in (
            "permit",
            "plan review",
            "building fee",
            "inspection fee",
            "electrical permit",
            "mechanical permit",
            "plumbing permit",
        )
    ):
        return KIND_PERMIT
    return KIND_OTHER


def fee_kind_hint(kind: str) -> str:
    return _HINTS.get(kind, _HINTS[KIND_OTHER])


def fee_kind_badge(label: str = "", detail: str = "", trade: str = "") -> Tuple[str, str]:
    kind = classify_fee_kind(label, detail, trade)
    return kind, fee_kind_hint(kind)
