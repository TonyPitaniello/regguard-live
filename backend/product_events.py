"""Product event instrumentation — stamp funnel + zip-watch re-run (72h)."""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_BACKEND = Path(__file__).resolve().parent
_PATH = _BACKEND / "data" / "product_events.jsonl"
_LOCK = threading.Lock()

ALLOWED_EVENTS = frozenset(
    {
        "stamp_share_copy",
        "stamp_share_whatsapp",
        "stamp_share_facebook",
        "stamp_receipt_download",
        "stamp_packet_download",
        "stamp_view",
        "zip_watch_alert_sent",
        "zip_watch_sms_sent",
        "research_rerun_same_zip",
        "partner_mandate_copy",
        "partner_mandate_outreach_logged",
        "job_saved_with_phone",
        "war_room_stamp_attached",
        "war_room_stamp_frozen",
        "refund_case_stamp_attached",
        "forward_receipt_credit",
        "partner_forward_credit",
        "checkout_view",
        "checkout_start",
        "checkout_complete",
        "pricing_view",
        # Blank demand funnel
        "research_run",
        "shared_report_open",
        "demand_feedback",
        "gotcha_submitted",
        "pain_scout_note",
    }
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    d = dt or _utcnow()
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def track_event(
    event: str,
    *,
    research_id: str = "",
    zip_code: str = "",
    stamp_grade: str = "",
    stamp_fingerprint: str = "",
    channel: str = "",
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    name = (event or "").strip()
    if name not in ALLOWED_EVENTS:
        raise ValueError(f"Unknown event: {name}")
    row: Dict[str, Any] = {
        "ts": _iso(),
        "event": name,
        "research_id": (research_id or "")[:80],
        "zip": str(zip_code or "")[:10],
        "stamp_grade": str(stamp_grade or "")[:16],
        "stamp_fingerprint": str(stamp_fingerprint or "")[:40],
        "channel": str(channel or "")[:40],
        "meta": meta or {},
    }
    try:
        with _LOCK:
            _PATH.parent.mkdir(parents=True, exist_ok=True)
            with _PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("product_events append failed: %s", e)
    try:
        _supabase_append(row)
    except Exception as e:
        logger.warning("product_events supabase append failed: %s", e)
    return row


def _supabase_append(row: Dict[str, Any]) -> bool:
    if not (os.getenv("SUPABASE_URL") or "").strip() or not (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    ).strip():
        return False
    try:
        from supabase import create_client

        url = os.environ["SUPABASE_URL"].strip()
        key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY") or "").strip()
        sb = create_client(url, key)
        sb.table("product_events").insert(
            {
                "ts": row.get("ts"),
                "event": row.get("event"),
                "research_id": row.get("research_id") or "",
                "zip": row.get("zip") or "",
                "stamp_grade": row.get("stamp_grade") or "",
                "stamp_fingerprint": row.get("stamp_fingerprint") or "",
                "channel": row.get("channel") or "",
                "meta": row.get("meta") or {},
            }
        ).execute()
        return True
    except Exception as e:
        logger.debug("product_events supabase skip: %s", e)
        return False


def _read_rows(limit: int = 5000) -> List[Dict[str, Any]]:
    if not _PATH.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        lines = _PATH.read_text(encoding="utf-8").splitlines()[-limit:]
        for line in lines:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return rows


def recent(limit: int = 50) -> List[Dict[str, Any]]:
    rows = _read_rows(3000)
    return list(reversed(rows[-limit:]))


def stamp_funnel_stats(*, hours: int = 168) -> Dict[str, Any]:
    """Counts by event + zip-watch → re-run within 72h conversion."""
    cutoff = _utcnow() - timedelta(hours=max(1, hours))
    rows = _read_rows(8000)
    counts: Dict[str, int] = {}
    alerts: List[Dict[str, Any]] = []
    reruns: List[Dict[str, Any]] = []

    def _parse_ts(s: str) -> Optional[datetime]:
        try:
            return datetime.strptime(str(s).replace("Z", ""), "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        except Exception:
            return None

    for r in rows:
        ts = _parse_ts(r.get("ts") or "")
        if not ts or ts < cutoff:
            continue
        ev = r.get("event") or ""
        counts[ev] = counts.get(ev, 0) + 1
        if ev in ("zip_watch_alert_sent", "zip_watch_sms_sent"):
            alerts.append(r)
        if ev == "research_rerun_same_zip":
            reruns.append(r)

    converted = 0
    window = timedelta(hours=72)
    for a in alerts:
        z = str(a.get("zip") or "")
        ats = _parse_ts(a.get("ts") or "")
        if not z or not ats:
            continue
        for rr in reruns:
            if str(rr.get("zip") or "") != z:
                continue
            rts = _parse_ts(rr.get("ts") or "")
            if rts and ats <= rts <= ats + window:
                converted += 1
                break

    alert_n = len(alerts)
    # IC / Pro funnel close rates
    views = counts.get("checkout_view", 0) + counts.get("pricing_view", 0)
    starts = counts.get("checkout_start", 0)
    completes = counts.get("checkout_complete", 0)
    ic_views = 0
    ic_starts = 0
    ic_completes = 0
    pro_completes = 0
    for r in rows:
        ts = _parse_ts(r.get("ts") or "")
        if not ts or ts < cutoff:
            continue
        ev = r.get("event") or ""
        meta = r.get("meta") if isinstance(r.get("meta"), dict) else {}
        tier = str(meta.get("tier") or r.get("channel") or "").lower()
        if ev == "checkout_view" and "ic_project" in tier:
            ic_views += 1
        if ev == "checkout_start" and "ic_project" in tier:
            ic_starts += 1
        if ev == "checkout_complete":
            if "ic_project" in tier or tier == "ic_consultant":
                ic_completes += 1
            if "contractor_pro" in tier or tier == "pro":
                pro_completes += 1

    ic_base = ic_starts if ic_starts else ic_views
    return {
        "window_hours": hours,
        "counts": counts,
        "zip_watch_alerts": alert_n,
        "reruns_same_zip": len(reruns),
        "rerun_within_72h": converted,
        "rerun_within_72h_rate": round(converted / alert_n, 3) if alert_n else None,
        "funnel": {
            "pricing_or_checkout_views": views,
            "checkout_starts": starts,
            "checkout_completes": completes,
            "close_rate": round(completes / starts, 3) if starts else None,
            "ic_project": {
                "views": ic_views,
                "starts": ic_starts,
                "completes": ic_completes,
                "close_rate": round(ic_completes / ic_base, 3) if ic_base else None,
                "price_usd": 1500,
            },
            "contractor_pro_completes": pro_completes,
        },
        "disclaimer": "Planning metrics only — not billing or legal evidence.",
    }


def _parse_ts(s: str) -> Optional[datetime]:
    try:
        return datetime.strptime(str(s).replace("Z", ""), "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except Exception:
        return None


def demand_scoreboard(*, hours: int = 168) -> Dict[str, Any]:
    """
    Blank question, automated:
      research_run → receipt_download → share → shared_report_open → return/paid

    Verdicts are heuristics for a passive operator — not proof of PMF.
    """
    cutoff = _utcnow() - timedelta(hours=max(1, hours))
    rows: List[Dict[str, Any]] = []
    for r in _read_rows(12000):
        ts = _parse_ts(r.get("ts") or "")
        if ts and ts >= cutoff:
            rows.append(r)

    def count(ev: str) -> int:
        return sum(1 for r in rows if r.get("event") == ev)

    runs = count("research_run")
    receipts = count("stamp_receipt_download")
    shares = (
        count("stamp_share_copy")
        + count("stamp_share_whatsapp")
        + count("stamp_share_facebook")
        + count("forward_receipt_credit")
    )
    opens = count("shared_report_open")
    returns = count("research_rerun_same_zip") + count("job_saved_with_phone")
    paid = count("checkout_complete")
    feedback = [r for r in rows if r.get("event") == "demand_feedback"]
    gotchas = count("gotcha_submitted")

    # Unique research ids progressing through funnel (soft)
    rid_runs = {str(r.get("research_id") or "") for r in rows if r.get("event") == "research_run" and r.get("research_id")}
    rid_receipt = {
        str(r.get("research_id") or "")
        for r in rows
        if r.get("event") == "stamp_receipt_download" and r.get("research_id")
    }
    rid_share = {
        str(r.get("research_id") or "")
        for r in rows
        if r.get("event")
        in (
            "stamp_share_copy",
            "stamp_share_whatsapp",
            "stamp_share_facebook",
            "forward_receipt_credit",
        )
        and r.get("research_id")
    }
    rid_open = {
        str(r.get("research_id") or "")
        for r in rows
        if r.get("event") == "shared_report_open" and r.get("research_id")
    }

    def rate(num: int, den: int) -> Optional[float]:
        return round(num / den, 3) if den else None

    zip_counts: Dict[str, Dict[str, int]] = {}
    for r in rows:
        z = str(r.get("zip") or "").strip()[:5]
        if len(z) < 5:
            continue
        bucket = zip_counts.setdefault(z, {"runs": 0, "receipts": 0, "shares": 0, "opens": 0})
        ev = r.get("event") or ""
        if ev == "research_run":
            bucket["runs"] += 1
        elif ev == "stamp_receipt_download":
            bucket["receipts"] += 1
        elif ev in (
            "stamp_share_copy",
            "stamp_share_whatsapp",
            "stamp_share_facebook",
            "forward_receipt_credit",
        ):
            bucket["shares"] += 1
        elif ev == "shared_report_open":
            bucket["opens"] += 1

    top_zips = sorted(
        (
            {
                "zip": z,
                **v,
                "share_rate": rate(v["shares"], v["receipts"] or v["runs"]),
            }
            for z, v in zip_counts.items()
        ),
        key=lambda x: (x["shares"], x["receipts"], x["runs"]),
        reverse=True,
    )[:12]

    feedback_counts: Dict[str, int] = {}
    for r in feedback:
        meta = r.get("meta") if isinstance(r.get("meta"), dict) else {}
        ans = str(meta.get("answer") or meta.get("choice") or "unknown")[:40]
        feedback_counts[ans] = feedback_counts.get(ans, 0) + 1

    # Passive operator verdict
    share_rate = rate(shares, receipts or runs)
    open_rate = rate(opens, shares)
    pay_rate = rate(paid, runs)
    if runs == 0:
        verdict = "NO_SIGNAL"
        verdict_plain = "No research runs yet — Blank’s question is unanswered."
    elif (share_rate or 0) >= 0.15 and (pay_rate or 0) > 0:
        verdict = "EARLY_DEMAND"
        verdict_plain = "People run sites, share receipts, and some pay — keep narrowing the winning ZIPs."
    elif (share_rate or 0) >= 0.1:
        verdict = "VIRAL_WEAK_PAY"
        verdict_plain = "Receipts get shared but pay is weak — fix upgrade CTA / price / pack depth."
    elif (receipts or 0) >= max(5, runs // 5) and (share_rate or 0) < 0.05:
        verdict = "USEFUL_NOT_FORWARDABLE"
        verdict_plain = "People download but don’t forward — improve receipt usefulness / share friction."
    else:
        verdict = "HYPOTHESIS_ONLY"
        verdict_plain = "Activity without clear share→pay loop — treat demand as unproven."

    return {
        "window_hours": hours,
        "blank_question": "Who are the customers and what do they want — proven by behavior, not AI research?",
        "funnel": {
            "research_runs": runs,
            "receipt_downloads": receipts,
            "shares": shares,
            "shared_report_opens": opens,
            "returns_or_saves": returns,
            "checkout_completes": paid,
            "gotcha_submits": gotchas,
            "demand_feedback_n": len(feedback),
        },
        "rates": {
            "receipt_per_run": rate(receipts, runs),
            "share_per_receipt": rate(shares, receipts),
            "share_per_run": share_rate,
            "open_per_share": open_rate,
            "pay_per_run": pay_rate,
        },
        "unique_research_ids": {
            "runs": len(rid_runs),
            "receipts": len(rid_receipt & rid_runs) if rid_runs else len(rid_receipt),
            "shares": len(rid_share),
            "opens": len(rid_open),
        },
        "top_zips": top_zips,
        "demand_feedback": feedback_counts,
        "verdict": verdict,
        "verdict_plain": verdict_plain,
        "stamp_funnel": stamp_funnel_stats(hours=hours),
        "disclaimer": "Planning metrics for a passive operator — not billing proof or PMF certificate.",
    }
