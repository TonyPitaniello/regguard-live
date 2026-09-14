"""Weekly pain-scout digest for passive / agentic operators.

Combines in-product demand signals (gotchas, feedback, weak-share ZIPs)
with a curated market-pain checklist so Blank's "what do they want?"
question gets a recurring written answer without sales calls.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_BACKEND = Path(__file__).resolve().parent
_PATH = _BACKEND / "data" / "pain_scout_digests.jsonl"
_LOCK = threading.Lock()

# Curated public-market themes (agent can refresh copy; behavior still decides).
MARKET_PAIN_THEMES: List[Dict[str, str]] = [
    {
        "id": "permit_vs_connection",
        "theme": "Permit fees vs connection / tap / impact fees",
        "who": "Estimators / GCs",
        "implication": "Label fee types explicitly; never bury connection fees in generic contingency.",
    },
    {
        "id": "prebid_permit_risk",
        "theme": "Permitting treated after bid day",
        "who": "GCs / lenders",
        "implication": "Lead with Bid Risk Receipt + contingency before contract — not a code encyclopedia.",
    },
    {
        "id": "correction_lag",
        "theme": "Correction-letter / portal lag kills schedule",
        "who": "Permit runners",
        "implication": "Recheck + stale stamp + ZIP watch are the habit loop, not more PDF pages.",
    },
    {
        "id": "incomplete_submittal",
        "theme": "Incomplete docs → re-review cycles",
        "who": "Subs / GCs",
        "implication": "Densify city-pack document checklist from live results.",
    },
    {
        "id": "parallel_clocks",
        "theme": "AHJ permits vs utility interconnection clocks",
        "who": "Large-load / DC",
        "implication": "Sell screening diligence; never claim interconnect/geotech completeness.",
    },
]


def _iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _recent_gotcha_notes(limit: int = 25) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    path = _BACKEND / "gotcha_credits.jsonl"
    if path.is_file():
        try:
            for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                out.append(
                    {
                        "zip": row.get("zip_code") or row.get("zip") or "",
                        "text": (row.get("note_text") or row.get("text") or "")[:240],
                        "status": row.get("status") or "",
                        "source": "gotcha_credit",
                    }
                )
        except Exception as e:
            logger.debug("gotcha credits read skip: %s", e)
    try:
        from community_gotchas import list_recent_notes  # type: ignore

        for n in list_recent_notes(limit=limit) or []:
            if not isinstance(n, dict):
                continue
            out.append(
                {
                    "zip": n.get("zip") or n.get("zip_code") or "",
                    "text": (n.get("text") or n.get("note") or "")[:240],
                    "status": n.get("status") or "",
                    "source": "community_gotcha",
                }
            )
    except Exception:
        pass
    return out[-limit:]


def build_weekly_digest(*, hours: int = 168, persist: bool = True) -> Dict[str, Any]:
    from product_events import demand_scoreboard, recent

    board = demand_scoreboard(hours=hours)
    recent_rows = recent(80)
    feedback = [
        r
        for r in recent_rows
        if r.get("event") == "demand_feedback"
    ]
    pain_notes = [
        r
        for r in recent_rows
        if r.get("event") in ("pain_scout_note", "gotcha_submitted")
    ]

    weak_share = [
        z
        for z in (board.get("top_zips") or [])
        if (z.get("runs") or 0) >= 3 and (z.get("share_rate") is None or (z.get("share_rate") or 0) < 0.05)
    ]
    strong_share = [
        z
        for z in (board.get("top_zips") or [])
        if (z.get("share_rate") or 0) >= 0.15 and (z.get("shares") or 0) >= 1
    ]

    actions: List[str] = []
    verdict = board.get("verdict") or "NO_SIGNAL"
    if verdict == "NO_SIGNAL":
        actions.append("Drive 20+ real address runs in 1–2 target ZIPs before adding features.")
    if verdict == "USEFUL_NOT_FORWARDABLE":
        actions.append("Rewrite Bid Risk Receipt CTA and first 3 killer lines for GC-forward clarity.")
    if verdict == "VIRAL_WEAK_PAY":
        actions.append("A/B Pro vs IC CTA after share unlock; check city-pack fee density on top ZIPs.")
    if weak_share:
        actions.append(
            f"Investigate weak-share ZIPs: {', '.join(z['zip'] for z in weak_share[:5])} — pack gaps or wrong trade."
        )
    if strong_share:
        actions.append(
            f"Double-down organic SEO/share captions for ZIPs: {', '.join(z['zip'] for z in strong_share[:5])}."
        )
    if not actions:
        actions.append("Keep measuring; freeze net-new surfaces until share→pay rates move.")

    digest: Dict[str, Any] = {
        "generated_at": _iso(),
        "window_hours": hours,
        "verdict": verdict,
        "verdict_plain": board.get("verdict_plain"),
        "funnel": board.get("funnel"),
        "rates": board.get("rates"),
        "top_zips": board.get("top_zips"),
        "weak_share_zips": weak_share[:8],
        "strong_share_zips": strong_share[:8],
        "demand_feedback": board.get("demand_feedback") or {},
        "recent_feedback": [
            {
                "ts": r.get("ts"),
                "zip": r.get("zip"),
                "answer": (r.get("meta") or {}).get("answer") if isinstance(r.get("meta"), dict) else None,
                "note": (r.get("meta") or {}).get("note") if isinstance(r.get("meta"), dict) else None,
            }
            for r in feedback[:15]
        ],
        "gotcha_or_pain_events": [
            {
                "ts": r.get("ts"),
                "event": r.get("event"),
                "zip": r.get("zip"),
                "meta": r.get("meta") or {},
            }
            for r in pain_notes[:20]
        ],
        "community_gotcha_samples": _recent_gotcha_notes(15),
        "market_pain_themes": MARKET_PAIN_THEMES,
        "recommended_actions": actions,
        "blank_reminder": (
            "AI research and premortems are hypotheses. This digest only matters if "
            "share_per_run and pay_per_run move — otherwise narrow the wedge."
        ),
    }

    if persist:
        try:
            with _LOCK:
                _PATH.parent.mkdir(parents=True, exist_ok=True)
                with _PATH.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(digest, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("pain scout digest persist failed: %s", e)

    return digest


def latest_digest() -> Optional[Dict[str, Any]]:
    if not _PATH.is_file():
        return None
    try:
        lines = [ln for ln in _PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception:
        return None


def list_digests(limit: int = 12) -> List[Dict[str, Any]]:
    if not _PATH.is_file():
        return []
    out: List[Dict[str, Any]] = []
    try:
        for line in _PATH.read_text(encoding="utf-8").splitlines()[-limit:]:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return list(reversed(out))
