"""
Bid Risk Receipt — forward-first one-pager, branded to match the Reg Guard app.
Dark slate canvas, big emerald contingency %, amber HIGH / Unverified badges.
ASCII-only for Helvetica compatibility.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fpdf import FPDF

from fee_kind import classify_fee_kind

logger = logging.getLogger(__name__)

APP_URL = os.getenv("FRONTEND_APP_URL", "https://app.regguardagent.com").rstrip("/")

BG = (15, 23, 42)
CARD = (30, 41, 59)
CARD_EDGE = (51, 65, 85)
EMERALD = (16, 185, 129)
EMERALD_SOFT = (52, 211, 153)
AMBER = (245, 158, 11)
AMBER_SOFT = (251, 191, 36)
WHITE = (248, 250, 252)
MUTED = (148, 163, 184)
DIM = (100, 116, 139)

PAGE_W = 215.9
PAGE_H = 279.4
MARGIN = 12
CONTENT_W = PAGE_W - (MARGIN * 2)

CYA = (
    "PLANNING AID ONLY - citeable pre-bid diligence, not a quote or sealed bid. "
    "Not an interconnection study, geotech report, or AHJ filing. "
    "Unverified lines need confirm-with-AHJ before bid."
)


def _ascii(text: str) -> str:
    return (
        (text or "")
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2022", "-")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def _fmt_pct(v: Any) -> Optional[str]:
    if v is None:
        return None
    try:
        return f"{float(v):.1f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return None


def _badge(
    pdf: FPDF,
    label: str,
    *,
    fg: Tuple[int, int, int],
    bg: Tuple[int, int, int],
    x: float,
    y: float,
) -> float:
    pdf.set_font("Helvetica", "B", 7)
    w = pdf.get_string_width(_ascii(label)) + 4
    pdf.set_fill_color(*bg)
    pdf.set_text_color(*fg)
    pdf.set_xy(x, y)
    pdf.cell(w, 5, _ascii(label), fill=True, align="C")
    return w


def _soft_cut(text: str, limit: int) -> str:
    """Truncate on a word boundary — never mid-word. ASCII ellipsis only (Helvetica)."""
    t = _ascii(str(text or "")).strip()
    if limit <= 0 or len(t) <= limit:
        return t
    cut = t[:limit].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0].rstrip(".,;:")
    # Use "..." not "…" — latin-1 replace turns U+2026 into "?" (awkward "the?")
    return (cut + "...") if cut else _ascii(t[:limit])


def _ensure_space(pdf: "BidRiskReceiptPDF", need_mm: float = 28.0) -> bool:
    """
    True if there is room for need_mm on this page.
    Bid Risk Receipt is a hard 1-pager — never start a continuation page.
    """
    floor = PAGE_H - 22
    return pdf.get_y() + need_mm <= floor


def _clock_lines(data: Dict[str, Any]) -> list:
    """Normalize parallel clock rows; drop blanks (never print '- : ')."""
    raw = ((data.get("parallel_clocks") or {}).get("clocks")) or []
    out = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        label = str(
            c.get("label") or c.get("name") or c.get("track") or c.get("clock") or ""
        ).strip()
        status = str(
            c.get("status") or c.get("detail") or c.get("note") or c.get("owner") or ""
        ).strip()
        if not label and not status:
            continue
        if not label:
            label = "Parallel clock"
        out.append((label, status))
    return out[:3]


def _top_risk_flags(data: Dict[str, Any], killers: list) -> list:
    """Surface up to 3 forwardable flags — killers, then stamp drivers, then gotchas."""
    flags: list = []
    seen = set()

    def _add(priority: str, title: str, detail: str, source_url: str = "", verified: Any = None) -> None:
        t = (title or "").strip()
        if not t:
            return
        key = t.lower()
        if key in seen:
            return
        seen.add(key)
        flags.append(
            {
                "priority": (priority or "NOTE").upper().replace("FAIL", "CRITICAL"),
                "title": t,
                "detail": detail or "",
                "source_url": source_url or "",
                "verified": verified,
            }
        )

    for k in killers or []:
        if not isinstance(k, dict):
            continue
        _add(
            str(k.get("priority") or "NOTE"),
            str(k.get("title") or k.get("label") or ""),
            str(k.get("detail") or ""),
            str(k.get("source_url") or ""),
            k.get("verified"),
        )
        if len(flags) >= 3:
            return flags[:3]

    rg = data.get("regguard_stamp") if isinstance(data.get("regguard_stamp"), dict) else {}
    for d in (rg.get("drivers") or []):
        if not isinstance(d, dict):
            continue
        _add(
            str(d.get("severity") or "HIGH"),
            str(d.get("label") or d.get("title") or ""),
            str(d.get("detail") or ""),
            str(d.get("source_url") or ""),
        )
        if len(flags) >= 3:
            return flags[:3]

    for g in ((data.get("gotcha_watchlist") or {}).get("items")) or []:
        if not isinstance(g, dict):
            continue
        _add(
            str(g.get("priority") or "HIGH"),
            str(g.get("title") or ""),
            str(g.get("detail") or ""),
            str(g.get("source_url") or ""),
            bool(g.get("source_url")),
        )
        if len(flags) >= 3:
            return flags[:3]
    return flags[:3]


def _stamp_is_stale(rg: Dict[str, Any]) -> bool:
    if rg.get("is_stale"):
        return True
    valid = str(rg.get("valid_until") or "").strip()
    if not valid:
        return False
    try:
        from datetime import timezone

        raw = valid.replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt < datetime.now(timezone.utc)
    except Exception:
        return False


def _receipt_product_face(data: Dict[str, Any], free_preview: bool) -> tuple:
    """Kicker, document label, lede, footer — match the tier that paid for this page."""
    if free_preview:
        return (
            "FREE LOOKUPS PREVIEW",
            "BID RISK RECEIPT - FREE PREVIEW",
            "Bid-or-walk preview only - contingency and most punch lines stay locked until Estimator.",
            "FREE PREVIEW - Estimator / Permit Runner ($79/mo) unlocks contingency + full punch habit.",
        )
    depth = str(data.get("research_depth") or "").strip().lower()
    tier = str(data.get("depth_tier") or "").strip().lower()
    access = str(data.get("access_tier") or "").strip().lower()
    if data.get("ic_package") is True or depth in ("ic", "ic_full") or tier == "ic_full":
        return (
            "IC DILIGENCE - DECISION MEMO",
            "DECISION MEMO - IC DILIGENCE BUNDLE",
            "1-page HOLD/CLEAR memo for this site. Planning aid - not a quote, filing, or interconnection study.",
            "IC DILIGENCE BUNDLE - this memo, plus boardroom PDF, counsel Word, and Excel.",
        )
    if depth.startswith("pro") or tier.startswith("pro") or access == "contractor_pro":
        return (
            "CONTRACTOR PRO - FORWARDABLE RECEIPT",
            "BID RISK RECEIPT - CONTRACTOR PRO",
            "Forward this Receipt. City Pack, fee CSV, and bid packet are the rest of the Pro desk.",
            "CONTRACTOR PRO - Receipt plus City Pack, fee CSV, and bid packet.",
        )
    return (
        "ESTIMATOR / PERMIT RUNNER - FORWARDABLE",
        "BID RISK RECEIPT - ESTIMATOR HABIT",
        "Full Bid Risk Receipt habit - forward to GC / owner / client before bid.",
        "ESTIMATOR HABIT - forward this Receipt. Contractor Pro adds City Pack / fee dollars.",
    )


class BidRiskReceiptPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(format="Letter", unit="mm")
        # Hard 1-page stamp — Pricing promises a one-page HOLD/CLEAR memo
        self.set_auto_page_break(auto=False, margin=16)

    def header(self) -> None:
        self.set_fill_color(*BG)
        self.rect(0, 0, PAGE_W, PAGE_H, "F")

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "I", 6.5)
        self.set_text_color(*DIM)
        page = f" — {self.page_no()}" if self.page_no() > 1 else ""
        self.multi_cell(0, 3.2, _ascii(CYA + page), align="C")


def generate_bid_risk_receipt_pdf(
    analysis_data: Dict[str, Any],
    output_path: Optional[str] = None,
    *,
    generated_for: Optional[str] = None,
    share_url: Optional[str] = None,
) -> str:
    """Write a branded 1-page forwardable Bid Risk Receipt; return path."""
    data = dict(analysis_data or {})
    band = data.get("contingency_band") or {}
    if (
        not band
        or band.get("pct_low") is None
        or band.get("pct_high") is None
        or not data.get("margin_killers")
        or not data.get("ahj_card")
    ):
        from arbitrage_enrichment import enrich_analysis_with_arbitrage

        data = enrich_analysis_with_arbitrage(data)

    pi = data.get("project_info") or {}
    address = _ascii(str(pi.get("address") or "Site"))
    city = _ascii(str(pi.get("city") or ""))
    state = _ascii(str(pi.get("state") or ""))
    zip_code = _ascii(str(pi.get("zip") or ""))
    who = _ascii((generated_for or "").strip() or "Estimator")
    try:
        from research_store import resolve_forward_share_url

        resolved = resolve_forward_share_url(data, share_url=share_url)
    except Exception:
        resolved = (share_url or "").strip()
        if "utm_source=bid_receipt" in resolved or "/r/" not in resolved:
            resolved = ""
    if resolved:
        cta = _ascii(resolved)
        cta_line = f"Full shareable report: {cta}"
    else:
        cta = ""
        cta_line = "Full shareable report: unavailable — re-open results in Reg Guard (do not use homepage link)."

    killers = data.get("margin_killers")
    if not isinstance(killers, list) or not killers:
        killers = build_margin_killers(data, limit=3)

    band = data.get("contingency_band") or {}
    ahj = data.get("ahj_card") or {}
    dc = data.get("dc_positioning") or {}

    low_s = _fmt_pct(band.get("pct_low"))
    mid_s = _fmt_pct(band.get("pct_mid"))
    high_s = _fmt_pct(band.get("pct_high"))

    from artifact_naming import document_display_title, site_line_from_analysis
    from habit_ladder_shape import is_free_preview_receipt

    free_preview = is_free_preview_receipt(data)
    site_line = site_line_from_analysis(data)
    kicker, receipt_label, lede, footer_product = _receipt_product_face(data, free_preview)
    doc_title = document_display_title(site_line, receipt_label)

    pdf = BidRiskReceiptPDF()
    try:
        pdf.set_title(_ascii(doc_title)[:120])
        pdf.set_author("Reg Guard")
    except Exception:
        pass
    pdf.add_page()
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_y(8)

    # Brand bar — amber for Free preview, emerald for Estimator habit
    pdf.set_fill_color(*(AMBER if free_preview else EMERALD))
    pdf.rect(0, 0, PAGE_W, 3.2, "F")

    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*(AMBER_SOFT if free_preview else EMERALD_SOFT))
    pdf.cell(
        CONTENT_W,
        6,
        kicker,
        ln=1,
    )
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(CONTENT_W, 4, _ascii(doc_title))
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        CONTENT_W,
        3.5,
        _ascii(
            lede
        ),
    )
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*AMBER)
    pdf.multi_cell(
        CONTENT_W,
        3.2,
            _ascii(
                "SCREENING MEMO - not an interconnection study, Phase I ESA, geotech, or AHJ approval."
            ),
    )
    pdf.ln(1)

    # HOLD/CLEAR stamp up front (counsel density) — never print FAIL
    from pdf_stamp_helpers import (
        citation_badge_and_url,
        draw_frosted_contingency,
        stamp_display_grade,
        stamp_plain_text,
    )

    rg = data.get("regguard_stamp") if isinstance(data.get("regguard_stamp"), dict) else {}
    if not rg.get("grade"):
        try:
            from regguard_stamp import apply_regguard_stamp

            data = apply_regguard_stamp(dict(data))
            rg = data.get("regguard_stamp") or {}
        except Exception:
            pass
    grade = str(rg.get("grade") or data.get("stamp_grade") or "").upper()
    display = stamp_display_grade(grade)
    if display and display not in ("—", "-", ""):
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 14)
        stamp_color = AMBER if display == "HOLD" else (AMBER_SOFT if display == "CAUTION" else EMERALD_SOFT)
        pdf.set_text_color(*stamp_color)
        pdf.cell(CONTENT_W, 6, _ascii(f"REGGUARD STAMP: {display}"), ln=1)
    else:
        display = ""
    if _stamp_is_stale(rg):
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*AMBER)
        pdf.multi_cell(
            CONTENT_W,
            3.5,
            _ascii(
                "STALE STAMP — valid_until has passed. Re-run this address before "
                "forwarding or locking a number."
            ),
        )
    plain = stamp_plain_text(rg, grade=grade)
    if plain:
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*DIM)
        pdf.multi_cell(CONTENT_W, 3.2, _ascii(_soft_cut(plain, 200)))
    # AHJ portal / fee schedule / Accela — citeable links above the fold
    fees_u = str(ahj.get("fees_url") or "").strip()
    portal_u = str(ahj.get("portal_url") or "").strip()
    apply_u = str(ahj.get("apply_url") or "").strip()
    # Prefer ultralocal fee PDF when present
    ultra = data.get("ultralocal_scout") if isinstance(data.get("ultralocal_scout"), dict) else {}
    for pg in ultra.get("confirmed_pages") or []:
        if not isinstance(pg, dict):
            continue
        title = str(pg.get("title") or "").lower()
        url = str(pg.get("url") or "").strip()
        if "fee" in title and url.startswith("http"):
            fees_u = url
            break
    if portal_u or fees_u or apply_u:
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*EMERALD)
        pdf.cell(CONTENT_W, 4, "AHJ LINKS (confirm before bid)", ln=1)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*MUTED)
        for kind, url in (("Portal", portal_u), ("Fee schedule", fees_u), ("Apply", apply_u)):
            if not url:
                continue
            pdf.set_x(MARGIN)
            from pdf_stamp_helpers import buyer_url_label, paint_linked_block

            paint_linked_block(
                pdf,
                _ascii(f"{kind}: {buyer_url_label(url)}"),
                url,
                width=CONTENT_W,
                line_h=3.0,
            )
    pdf.ln(1)

    # Site card
    y0 = pdf.get_y()
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*EMERALD)
    pdf.rect(MARGIN, y0, CONTENT_W, 22, "DF")
    pdf.set_xy(MARGIN + 4, y0 + 2.5)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*EMERALD)
    pdf.cell(CONTENT_W - 8, 4, "THIS SITE", ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W - 8, 6, address[:88], ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(CONTENT_W - 8, 4, f"{city}, {state} {zip_code}".strip(), ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*WHITE)
    pdf.cell(
        CONTENT_W - 8,
        4,
        _ascii(f"AHJ: {str(ahj.get('name') or 'Local AHJ')}"),
        ln=1,
    )
    identity = data.get("ahj_identity") or {}
    if identity.get("conflict") and identity.get("note"):
        pdf.set_x(MARGIN + 4)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*AMBER)
        pdf.multi_cell(CONTENT_W - 8, 3.2, _ascii(str(identity.get("note"))[:160]))
    pdf.set_y(y0 + 24)

    # Portal/fees already printed under AHJ LINKS — only show pack verified here
    verified = str(ahj.get("last_verified") or "").strip()
    if verified:
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*EMERALD)
        pdf.cell(CONTENT_W, 3.5, _ascii(f"Pack last verified: {verified}"), ln=1)
    if dc.get("headline") and _ensure_space(pdf, 18):
        clock_lines = _clock_lines(data)
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*EMERALD)
        pdf.cell(CONTENT_W, 4, _ascii("DATA CENTER - PARALLEL CLOCKS"), ln=1)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*DIM)
        if clock_lines:
            for label, status in clock_lines:
                if not _ensure_space(pdf, 8):
                    break
                pdf.set_x(MARGIN)
                line = f"- {_soft_cut(label, 40)}"
                if status:
                    line += f": {_soft_cut(status, 52)}"
                pdf.multi_cell(CONTENT_W, 3.0, _ascii(line))
        else:
            pdf.set_x(MARGIN)
            pdf.multi_cell(
                CONTENT_W,
                3.2,
                _ascii("AHJ + utility often run on parallel clocks (not an interconnect study)."),
            )
    pdf.ln(1.5)

    # BIG contingency — Free preview keeps the band locked; Estimator unlocks it.
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*(AMBER if free_preview else EMERALD))
    pdf.cell(
        CONTENT_W,
        5,
        "CONTINGENCY (locked on Free)" if free_preview else "CONTINGENCY (screenshot this)",
        ln=1,
    )

    y1 = pdf.get_y()
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*(AMBER if free_preview else EMERALD))
    pdf.rect(MARGIN, y1, CONTENT_W, 26 if free_preview else 24, "DF")
    pdf.set_xy(MARGIN + 4, y1 + 3)
    if free_preview and low_s and high_s:
        # Real % silhouette, frosted — not +##% placeholders
        draw_frosted_contingency(
            pdf,
            x=MARGIN + 4,
            y=y1 + 3,
            w=CONTENT_W - 8,
            h=14,
            low_s=low_s,
            high_s=high_s,
            mid_s=mid_s,
            card_rgb=CARD,
            amber_soft=AMBER_SOFT,
            muted=MUTED,
        )
    elif free_preview:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*AMBER_SOFT)
        pdf.multi_cell(
            CONTENT_W - 8,
            4.5,
            _ascii(
                "Contingency band locked on Free — Estimator unlocks the clear % you can forward."
            ),
        )
    elif low_s and high_s:
        pdf.set_font("Helvetica", "B", 26)
        pdf.set_text_color(*EMERALD_SOFT)
        pdf.cell(CONTENT_W - 8, 11, f"+{low_s}%  to  +{high_s}%", ln=1)
        pdf.set_x(MARGIN + 4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*EMERALD)
        pdf.cell(
            CONTENT_W - 8,
            5,
            _ascii(f"mid {mid_s}%   |   planning aid - NOT a quote"),
            ln=1,
        )
    else:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*AMBER_SOFT)
        pdf.multi_cell(
            CONTENT_W - 8,
            5,
            _ascii("Set contingency after confirming Critical/High items with AHJ."),
        )
    pdf.set_y(y1 + (28 if free_preview else 26))

    # Prefer citeable AHJ fee table over polluted fee_card budget rows
    fee_rows = []
    ahj_block = data.get("ahj") if isinstance(data.get("ahj"), dict) else {}
    if isinstance(ahj_block.get("ahj_fee_table"), list) and ahj_block.get("ahj_fee_table"):
        fee_rows = ahj_block["ahj_fee_table"]
    else:
        fc = data.get("fee_card") or {}
        if isinstance(fc.get("fees"), list) and fc.get("fees"):
            fee_rows = [
                r
                for r in fc["fees"]
                if isinstance(r, dict)
                and not str(r.get("label") or r.get("name") or "").lower().startswith("budget ")
            ]
        if not fee_rows:
            lp_fees = (data.get("local_pack") or {}).get("fees")
            if isinstance(lp_fees, list):
                fee_rows = lp_fees
    if fee_rows and not free_preview:
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*AMBER)
        pdf.cell(CONTENT_W, 5, "FEE TYPES (permit vs tap vs impact)", ln=1)
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*DIM)
        pdf.multi_cell(
            CONTENT_W,
            3.2,
            _ascii("Do not mix these. Impact and tap fees are often larger than the building permit."),
        )
        for row in fee_rows[:4]:
            if not isinstance(row, dict):
                continue
            if not _ensure_space(pdf, 10):
                break
            label = _soft_cut(str(row.get("label") or row.get("name") or "Fee"), 52)
            kind = classify_fee_kind(
                label,
                str(row.get("detail") or ""),
                str(row.get("trade") or ""),
            )
            amt = row.get("amount_usd")
            # Estimator shows kinds + labels; dollar amounts stay a Pro desk unlock.
            amt_s = "confirm on AHJ schedule"
            pdf.set_x(MARGIN)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*WHITE)
            pdf.multi_cell(CONTENT_W, 3.3, _ascii(f"[{kind}] {label} - {amt_s}"))
        pdf.ln(0.5)
    elif fee_rows and free_preview:
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*AMBER)
        pdf.cell(CONTENT_W, 5, "FEE SCHEDULE (locked on Free)", ln=1)
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*DIM)
        pdf.multi_cell(
            CONTENT_W,
            3.2,
            _ascii("Estimator unlocks fee types on the Receipt. Contractor Pro adds dollar lines."),
        )
        pdf.ln(0.5)

    # Top risk flags — Free shows 1 clear + locked teasers; Estimator shows full top 3
    risk_flags = _top_risk_flags(data, list(killers) if isinstance(killers, list) else [])
    clear_n = 1 if free_preview else 3
    try:
        clear_n = max(1, min(3, int(data.get("receipt_risk_clear") or clear_n)))
    except (TypeError, ValueError):
        pass
    if risk_flags and _ensure_space(pdf, 48):
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*(AMBER if free_preview else EMERALD))
        pdf.cell(
            CONTENT_W,
            5,
            (
                "TOP RISK (1 of 3 clear - Estimator unlocks the rest)"
                if free_preview
                else "TOP 3 RISK FLAGS  (Source or Unverified)"
            ),
            ln=1,
        )

        for i, k in enumerate(risk_flags[:3], 1):
            if not isinstance(k, dict):
                continue
            locked = free_preview and i > clear_n
            ver, cite_url = citation_badge_and_url(k)
            pri = str(k.get("priority") or "NOTE").upper()
            title = _soft_cut(str(k.get("title") or "Item"), 72)
            detail = _soft_cut(str(k.get("detail") or ""), 110)
            pe = k.get("planning_exposure") or {}
            if locked:
                title = "Additional punch / risk line locked on Free"
                detail = "Estimator unlocks the rest of the punch list with owner · due · Source or Unverified."
                pe = {}
                ver = "LOCKED"
                cite_url = None

            box_h = 14 + (3.2 if detail else 0) + (3.0 if cite_url else 0)
            if isinstance(pe, dict) and pe.get("usd_mid") is not None and not free_preview:
                box_h += 3.2
            if not _ensure_space(pdf, box_h + 14):
                break
            y = pdf.get_y()
            pdf.set_fill_color(*CARD)
            pdf.set_draw_color(*(AMBER if locked else CARD_EDGE))
            pdf.rect(MARGIN, y, CONTENT_W, box_h, "DF")
            bx, by = MARGIN + 4, y + 2

            pdf.set_xy(bx, by)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*WHITE)
            pdf.cell(8, 4.5, f"{i}.", ln=0)
            bx2 = bx + 8
            if locked:
                bx2 += _badge(pdf, "LOCKED", fg=BG, bg=AMBER_SOFT, x=bx2, y=by)
            elif pri in ("CRITICAL", "HIGH"):
                bx2 += _badge(
                    pdf,
                    pri,
                    fg=BG,
                    bg=AMBER if pri == "HIGH" else (239, 68, 68),
                    x=bx2,
                    y=by,
                )
            else:
                bx2 += _badge(pdf, pri, fg=WHITE, bg=CARD_EDGE, x=bx2, y=by)
            bx2 += 2
            if not locked:
                bg_c = (
                    AMBER_SOFT
                    if ver == "UNVERIFIED"
                    else EMERALD
                    if ver.startswith("SOURCE")
                    else (56, 189, 248)
                )
                bw = _badge(pdf, ver[:42], fg=BG, bg=bg_c, x=bx2, y=by)
                if cite_url:
                    try:
                        pdf.link(bx2, by, bw, 5, cite_url)
                    except Exception:
                        pass

            pdf.set_xy(bx, by + 5)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*WHITE)
            pdf.multi_cell(CONTENT_W - 12, 3.5, title)
            if detail:
                pdf.set_x(bx)
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(*MUTED)
                pdf.multi_cell(CONTENT_W - 12, 3.0, detail)
            if cite_url:
                pdf.set_x(bx)
                pdf.set_font("Helvetica", "", 6.5)
                pdf.set_text_color(*EMERALD)
                from pdf_stamp_helpers import buyer_url_label, paint_linked_block

                paint_linked_block(
                    pdf,
                    _ascii(buyer_url_label(cite_url)),
                    cite_url,
                    width=CONTENT_W - 12,
                    line_h=2.8,
                )
            if (
                not free_preview
                and isinstance(pe, dict)
                and pe.get("usd_mid") is not None
            ):
                pdf.set_x(bx)
                pdf.set_font("Helvetica", "B", 7)
                pdf.set_text_color(*EMERALD_SOFT)
                pdf.multi_cell(
                    CONTENT_W - 12,
                    3.0,
                    _ascii(
                        f"Planning exposure - ${int(pe.get('usd_low') or 0):,}"
                        f"-${int(pe.get('usd_high') or 0):,} - not guaranteed savings"
                    ),
                )
            pdf.set_y(y + box_h + 1.5)

    if not free_preview:
        punch = ((data.get("punch_list") or {}).get("punch_list") or [])[:5]
        if punch and _ensure_space(pdf, 28):
            pdf.set_x(MARGIN)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*EMERALD)
            pdf.cell(CONTENT_W, 5, "UNLOCKED PUNCH (owner · due · Source or Unverified)", ln=1)
            for item in punch:
                if not isinstance(item, dict):
                    continue
                if not _ensure_space(pdf, 8):
                    break
                task = _soft_cut(str(item.get("task") or "Punch line"), 62)
                owner = _soft_cut(str(item.get("owner") or item.get("responsible_party") or "Owner"), 32)
                due = _soft_cut(str(item.get("due_window") or item.get("timeline") or "Pre-bid"), 12)
                src, punch_url = citation_badge_and_url(item)
                pdf.set_x(MARGIN)
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(*WHITE)
                pdf.multi_cell(CONTENT_W, 3.0, _ascii(f"- {task}  [{owner} · {due} · {src}]"))
                if punch_url:
                    pdf.set_x(MARGIN + 3)
                    pdf.set_font("Helvetica", "", 6)
                    pdf.set_text_color(*EMERALD)
                    pdf.multi_cell(CONTENT_W - 3, 2.6, _ascii(punch_url[:100]))
            pdf.ln(0.5)

    # Compact footer — stamp already shown above the fold (no duplicate HOLD / drivers)
    rg = data.get("regguard_stamp") or {}
    stamp_date = datetime.utcnow().strftime("%Y-%m-%d")
    valid = str(rg.get("valid_until") or "")[:10]
    footer_bits = [
        f"Flagged by: {who}",
        f"Date: {stamp_date} UTC"
        + (f"  |  Valid until {valid}" if valid else ""),
        footer_product,
        "Re-run before you submit the bid. Fees and portal asks move.",
    ]
    if rg.get("is_stale") and rg.get("stale_reason"):
        footer_bits.append(_soft_cut(f"STALE: {rg.get('stale_reason')}", 120))
    # Keep footer above page CYA strip
    need = 4 + 3.2 * len(footer_bits) + 8
    if pdf.get_y() + need > PAGE_H - 18:
        pdf.set_y(max(MARGIN, PAGE_H - 18 - need))
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(CONTENT_W, 3.2, _ascii("\n".join(footer_bits)))
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*DIM)
    pdf.multi_cell(CONTENT_W, 3.2, _ascii(_soft_cut(cta_line, 140)))

    if not output_path:
        out_dir = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data") / "bid_receipts"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in address)[:40]
        output_path = str(
            out_dir / f"bid_receipt_{safe}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        )

    pdf.output(output_path)
    logger.info("Bid Risk Receipt PDF (branded) -> %s", output_path)
    return output_path


def generate_bid_risk_receipt_pdf_bytes(
    analysis: Dict[str, Any],
    *,
    generated_for: Optional[str] = None,
    share_url: Optional[str] = None,
) -> bytes:
    """Return PDF bytes in-process (multi-instance safe; no token cache)."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="bid_receipt_") as tmp:
        path = os.path.join(tmp, "RegGuard_Bid_Risk_Receipt.pdf")
        generate_bid_risk_receipt_pdf(
            analysis,
            output_path=path,
            generated_for=generated_for,
            share_url=share_url,
        )
        raw = Path(path).read_bytes()
    if raw[:4] != b"%PDF":
        raise RuntimeError("Bid Risk Receipt PDF generation failed")
    return raw
