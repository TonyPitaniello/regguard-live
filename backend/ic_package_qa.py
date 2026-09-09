"""Boardroom package quality gate — structural + GC-forward checks (Q2–Q5).

Q1 ("forward without apology") stays human / spot-audit.
Q2–Q5 are automated and required for Boardroom PASS.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

BOARDROOM_PASS_SCORE = 80

# Beachhead metros where sister-city fee confusion is a known failure mode
SISTER_CITY_BEACHHEAD = frozenset(
    {
        "plano",
        "dallas",
        "austin",
        "fort worth",
        "frisco",
        "arlington",
        "irving",
        "garland",
        "mckinney",
        "richardson",
        "carrollton",
        "round rock",
    }
)

_QUOTE_BANNED = re.compile(
    r"\b("
    r"firm\s+quote|guaranteed\s+(?:price|cost|fee|savings)|"
    r"will\s+cost\s+exactly|not\s+a?\s*estimate\s+but\s+a\s+quote|"
    r"binding\s+quote|fixed[- ]price\s+bid\s+from\s+regguard"
    r")\b",
    re.I,
)
_PLANNING_AID = re.compile(r"planning\s+aid|not\s+a\s+quote|confirm\s+with\s+(?:the\s+)?ahj", re.I)

_LARGE_LOAD = re.compile(
    r"data[\s-]?center|large[\s-]?load|interconnect|mission[\s-]?critical|"
    r"colo(?:cation)?|utility\s+clock|parallel\s+clock|ercot|tdsp",
    re.I,
)

_SISTER_CITY = re.compile(
    r"sister[\s-]?city|do\s+not\s+use\s+(?:plano|dallas|austin|frisco|fort\s+worth).*"
    r"(?:fee|fees)|(?:plano|dallas|austin|frisco).*(?:fee|fees).*(?:not|as)\s+",
    re.I,
)


def _s(v: Any) -> str:
    return str(v or "").strip()


def _city_key(package: Dict[str, Any]) -> str:
    cover = package.get("cover") or {}
    return _s(cover.get("city")).lower()


def _is_large_load_site(package: Dict[str, Any]) -> bool:
    cover = package.get("cover") or {}
    blob_parts: List[str] = [
        _s(cover.get("project_type")),
        _s(cover.get("depth_badge")),
    ]
    ex = package.get("executive_summary") or {}
    for k in ex.get("top_risks") or []:
        if isinstance(k, dict):
            blob_parts.append(_s(k.get("title")))
            blob_parts.append(_s(k.get("detail")))
    findings = package.get("site_findings") or {}
    for g in findings.get("gotcha_cards") or findings.get("gotchas") or []:
        if isinstance(g, dict):
            blob_parts.append(_s(g.get("title")))
            blob_parts.append(_s(g.get("detail")))
    for c in findings.get("parallel_clocks") or []:
        if isinstance(c, dict):
            blob_parts.append(_s(c.get("name")))
            blob_parts.append(_s(c.get("detail")))
    return bool(_LARGE_LOAD.search(" ".join(blob_parts)))


def _contingency_not_a_quote(package: Dict[str, Any]) -> Tuple[bool, str]:
    """GC Q2 — contingency explained without sounding like a quote."""
    ex = package.get("executive_summary") or {}
    band = ex.get("contingency") if isinstance(ex.get("contingency"), dict) else {}
    receipt = package.get("bid_risk_receipt") or {}
    texts = [
        _s(band.get("plain")),
        _s(band.get("disclaimer")),
        _s(band.get("label")),
        _s(receipt.get("disclaimer")),
        " ".join(_s(d) for d in (package.get("disclaimers") or [])),
    ]
    blob = " ".join(t for t in texts if t)
    if not blob:
        return False, "No contingency plain-English / disclaimer text"
    if _QUOTE_BANNED.search(blob):
        return False, "Contingency language sounds like a firm quote"
    if not _PLANNING_AID.search(blob):
        return False, "Missing planning-aid / not-a-quote / confirm-with-AHJ language"
    if not (band.get("driver_table") or {}).get("rows"):
        return False, "Contingency driver table missing"
    return True, "ok"


def _high_critical_have_confirm_or_unverified(package: Dict[str, Any]) -> Tuple[bool, str]:
    """GC Q3 — every HIGH/CRITICAL line has confirm step or Unverified."""
    findings = package.get("site_findings") or {}
    items: List[Dict[str, Any]] = []
    ex = package.get("executive_summary") or {}
    for k in ex.get("top_risks") or []:
        if isinstance(k, dict):
            items.append(k)
    for g in findings.get("gotcha_cards") or []:
        if isinstance(g, dict):
            items.append(g)
    for g in ex.get("local_gotchas") or []:
        if isinstance(g, dict):
            items.append(g)
    for p in (package.get("punch_list") or {}).get("items") or []:
        if isinstance(p, dict):
            items.append(
                {
                    "priority": p.get("priority"),
                    "title": p.get("task"),
                    "confirm_step": None,
                    "source_url": p.get("source_url"),
                    "source_label": p.get("citation"),
                    "citation": p.get("citation"),
                }
            )

    high = [
        it
        for it in items
        if _s(it.get("priority")).upper() in ("HIGH", "CRITICAL", "FAIL", "HOLD")
    ]
    if not high:
        return True, "ok"  # N/A — nothing high-severity

    bad: List[str] = []
    for it in high:
        confirm = _s(it.get("confirm_step") or it.get("action"))
        url = _s(it.get("source_url") or it.get("citation_url"))
        label = _s(it.get("source_label") or it.get("citation")).lower()
        unverified = "unverified" in label or (not url and not confirm)
        ok = bool(confirm) or bool(url) or unverified
        # Require explicit Unverified label if no URL and no confirm
        if not confirm and not url:
            if "unverified" not in label:
                bad.append(_s(it.get("title") or it.get("task") or "item")[:80])
                continue
        if not ok:
            bad.append(_s(it.get("title") or it.get("task") or "item")[:80])
    if bad:
        return False, f"HIGH/CRITICAL missing confirm or Unverified: {'; '.join(bad[:3])}"
    return True, "ok"


def _sister_city_called_out(package: Dict[str, Any]) -> Tuple[bool, str]:
    """GC Q4 — sister-city fee mistakes called out for beachhead AHJs."""
    city = _city_key(package)
    if not city:
        return False, "Cover city missing"
    if city not in SISTER_CITY_BEACHHEAD:
        return True, "ok"  # N/A outside beachhead

    findings = package.get("site_findings") or {}
    blob_parts: List[str] = []
    for g in findings.get("gotcha_cards") or findings.get("gotchas") or []:
        if isinstance(g, dict):
            blob_parts.extend(
                [
                    _s(g.get("id")),
                    _s(g.get("title")),
                    _s(g.get("detail")),
                    " ".join(_s(x) for x in (g.get("anti_patterns") or [])),
                ]
            )
    for g in (package.get("executive_summary") or {}).get("local_gotchas") or []:
        if isinstance(g, dict):
            blob_parts.append(_s(g.get("title")))
            blob_parts.append(_s(g.get("detail")))
    blob = " ".join(blob_parts)
    if _SISTER_CITY.search(blob) or "sister" in blob.lower():
        return True, "ok"
    # Also accept pack-style anti-pattern mentioning another DFW city + fee
    if re.search(
        r"(plano|dallas|austin|frisco|fort\s+worth|arlington).{0,40}fee",
        blob,
        re.I,
    ) and re.search(r"\b(not|do not|don't|never)\b", blob, re.I):
        return True, "ok"
    return False, f"No sister-city fee warning for beachhead city {city.title()}"


def _parallel_clocks_if_large_load(package: Dict[str, Any]) -> Tuple[bool, str]:
    """GC Q5 — AHJ + utility parallel clocks visible when large-load."""
    if not _is_large_load_site(package):
        return True, "ok"  # N/A
    findings = package.get("site_findings") or {}
    clocks = findings.get("parallel_clocks") or []
    if len(clocks) >= 2:
        return True, "ok"
    # One clock that mentions utility/AHJ pair still helps; require 2 for pass
    if len(clocks) == 1:
        detail = " ".join(
            _s(c.get("name")) + " " + _s(c.get("detail"))
            for c in clocks
            if isinstance(c, dict)
        )
        if _LARGE_LOAD.search(detail) and re.search(r"ahj|permit|municipal|utility", detail, re.I):
            return False, "Large-load site needs both AHJ and utility clocks (found 1)"
    return False, "Large-load / data-center site missing parallel AHJ + utility clocks"


def score_gc_forward_checks(package: Dict[str, Any]) -> Dict[str, Any]:
    """Return per-question GC forward results for Q2–Q5 (Q1 is human)."""
    q2_ok, q2_detail = _contingency_not_a_quote(package)
    q3_ok, q3_detail = _high_critical_have_confirm_or_unverified(package)
    q4_ok, q4_detail = _sister_city_called_out(package)
    q5_ok, q5_detail = _parallel_clocks_if_large_load(package)
    items = [
        {
            "id": "Q2",
            "question": "Contingency explained without sounding like a quote",
            "ok": q2_ok,
            "detail": q2_detail,
            "agentic": True,
        },
        {
            "id": "Q3",
            "question": "Every HIGH/CRITICAL has confirm step or Unverified",
            "ok": q3_ok,
            "detail": q3_detail,
            "agentic": True,
        },
        {
            "id": "Q4",
            "question": "Sister-city fee mistakes called out for this AHJ",
            "ok": q4_ok,
            "detail": q4_detail,
            "agentic": True,
        },
        {
            "id": "Q5",
            "question": "AHJ + utility parallel clocks visible if large-load",
            "ok": q5_ok,
            "detail": q5_detail,
            "agentic": True,
        },
        {
            "id": "Q1",
            "question": "Would forward page 1 to an owner without apology",
            "ok": None,
            "detail": "Human / spot-audit only",
            "agentic": False,
        },
    ]
    agentic = [i for i in items if i["agentic"]]
    return {
        "all_agentic_ok": all(bool(i["ok"]) for i in agentic),
        "failed": [i["id"] for i in agentic if not i["ok"]],
        "items": items,
        "large_load_site": _is_large_load_site(package),
        "city": _city_key(package),
    }


def score_boardroom_package(package: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a compose_ic_package() payload for $1,500 boardroom bar.
    PASS requires structural score >= 80% AND GC forward Q2–Q5 all ok.
    """
    checks: List[Tuple[str, bool, int]] = []
    cover = package.get("cover") or {}
    ex = package.get("executive_summary") or {}
    stamp = ex.get("stamp") or {}
    band = ex.get("contingency") if isinstance(ex.get("contingency"), dict) else None
    findings = package.get("site_findings") or {}
    punch = (package.get("punch_list") or {}).get("items") or []
    sources = package.get("sources") or []
    gotcha_cards = findings.get("gotcha_cards") or findings.get("gotchas") or []

    checks.append(("Cover has site + AHJ", bool(cover.get("site") and cover.get("ahj_name")), 10))
    checks.append(("Stamp CLEAR/CAUTION/HOLD present", bool(stamp.get("display") or stamp.get("grade")), 10))
    checks.append(("Stamp plain-English explanation", bool(stamp.get("plain") or stamp.get("headline")), 5))
    checks.append(("Contingency band present", bool(band and band.get("pct_low") is not None), 10))
    checks.append(
        (
            "Contingency driver table (low/mid/high)",
            bool(band and (band.get("driver_table") or {}).get("rows")),
            10,
        )
    )
    checks.append(
        (
            "Top risks or gotchas (>=2)",
            len(ex.get("top_risks") or []) + len(ex.get("local_gotchas") or []) >= 2,
            10,
        )
    )
    checks.append(("Gotcha confirm cards (>=2)", len(gotcha_cards) >= 2, 10))
    checks.append(
        (
            "Punch list or actions (>=3)",
            len(punch) >= 3 or len(package.get("action_plan_summary") or []) >= 3,
            10,
        )
    )
    checks.append(("Source appendix (>=3 http)", len(sources) >= 3, 10))
    checks.append(("Disclaimers present", len(package.get("disclaimers") or []) >= 2, 5))
    checks.append(
        ("Prepared-for or research id", bool(package.get("generated_for") or cover.get("research_id")), 5)
    )

    gc = score_gc_forward_checks(package)
    # Weighted GC checks (Q2–Q5)
    for item in gc["items"]:
        if not item["agentic"]:
            continue
        checks.append((f"GC {item['id']}: {item['question']}", bool(item["ok"]), 15))

    score = sum(w for _, ok, w in checks if ok)
    max_score = sum(w for _, _, w in checks)
    gaps = [name for name, ok, _ in checks if not ok]
    checklist = [{"item": name, "ok": ok, "weight": w} for name, ok, w in checks]
    pct = round(100.0 * score / max_score) if max_score else 0
    structural_ok = pct >= BOARDROOM_PASS_SCORE
    gc_ok = bool(gc.get("all_agentic_ok"))
    return {
        "score": score,
        "max_score": max_score,
        "pct": pct,
        "pass": structural_ok and gc_ok,
        "structural_pass": structural_ok,
        "gc_forward_pass": gc_ok,
        "gaps": gaps,
        "checklist": checklist,
        "gc_forward": gc,
        "human_remaining": [
            {
                "id": "Q1",
                "question": "Would forward page 1 to an owner without apology",
                "note": "Spot-audit / first packages per city / HOLD stamps",
            }
        ],
    }
