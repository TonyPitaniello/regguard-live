"""Server-rendered /share/{id} HTML — OG tags for WhatsApp/iMessage + sales CTA.

Humans and crawlers get the same page: Bid Risk Receipt highlights, honesty,
Run-my-address, Partner/Pro checkout with ?ref= preserved.
"""
from __future__ import annotations

import html as html_lib
from typing import Any, Dict, Optional

from passive_campaign import APP_HOST, PRIMARY_SKU, HABIT_SKU, app_base_url, with_share_params


def _esc(v: Any) -> str:
    return html_lib.escape(str(v or ""), quote=True)


def _site_label(analysis: Dict[str, Any]) -> str:
    pi = analysis.get("project_info") or {}
    parts = [pi.get("address"), pi.get("city"), pi.get("state"), pi.get("zip")]
    return ", ".join(str(p).strip() for p in parts if p and str(p).strip()) or "This site"


def _killers(analysis: Dict[str, Any], n: int = 3) -> list:
    items = analysis.get("margin_killers") or []
    if not items:
        raw = (analysis.get("punch_list") or {}).get("critical_path") or []
        items = [{"title": (t if isinstance(t, str) else t.get("task")), "priority": "HIGH"} for t in raw]
    out = []
    for it in items[:n]:
        if isinstance(it, dict):
            out.append(it)
        elif it:
            out.append({"title": str(it), "priority": "NOTE"})
    return out


def render_share_html(
    analysis: Dict[str, Any],
    *,
    research_id: str,
    ref: str = "",
    preview: bool = False,
) -> str:
    base = app_base_url()
    site = _site_label(analysis)
    stamp = analysis.get("regguard_stamp") or {}
    grade = str(stamp.get("grade") or analysis.get("stamp_grade") or "").upper()
    band = analysis.get("contingency_band") or {}
    killers = _killers(analysis)
    ahj = (analysis.get("ahj_card") or {}).get("name") or "Local AHJ"
    run_qs = (
        f"utm_source=sharepage&utm_medium=referral&utm_campaign=bid_risk_receipt"
        f"{'&ref=' + ref if ref else ''}"
    )
    run_url = f"{base}/?{run_qs}#free-trial-form"
    spa_url = with_share_params(f"{base}/r/{research_id}", ref=ref)
    partner = with_share_params(
        f"{base}/checkout/{PRIMARY_SKU}",
        ref=ref,
        utm={"utm_source": "sharepage", "utm_medium": "cta", "utm_campaign": "bid_risk_receipt"},
    )
    pro = with_share_params(
        f"{base}/checkout/{HABIT_SKU}",
        ref=ref,
        utm={"utm_source": "sharepage", "utm_medium": "cta", "utm_campaign": "bid_risk_receipt"},
    )
    title = f"Bid Risk Receipt — {site}"
    if grade in ("PASS", "CAUTION", "FAIL"):
        title = f"{grade} · {title}"
    desc_bits = [f"AHJ: {ahj}"]
    if band.get("pct_low") is not None and band.get("pct_high") is not None:
        desc_bits.append(f"Contingency +{band.get('pct_low')}% to +{band.get('pct_high')}% (planning aid, not a quote)")
    if killers:
        desc_bits.append(str(killers[0].get("title") or "")[:80])
    description = " · ".join(x for x in desc_bits if x)[:200]
    og_image = f"{base}/icons/apple-touch-icon.png"
    killer_html = ""
    if killers:
        lis = "".join(
            f"<li><strong>{_esc(k.get('priority') or 'NOTE')}</strong> {_esc(k.get('title') or '')}</li>"
            for k in killers
        )
        killer_html = f"<h2>Top risk flags</h2><ol>{lis}</ol>"
    band_html = ""
    if band.get("pct_low") is not None:
        band_html = (
            f"<p class='band'>Contingency band +{_esc(band.get('pct_low'))}% – +{_esc(band.get('pct_high'))}% "
            f"(mid {_esc(band.get('pct_mid'))}%) — planning aid, not a quote.</p>"
        )
    preview_note = (
        "<p class='warn'><strong>Preview / Unverified estimates.</strong> Confirm every fee with the AHJ before you bid.</p>"
        if preview or analysis.get("preview")
        else ""
    )
    valid_until = str(stamp.get("valid_until") or analysis.get("stamp_valid_until") or "")[:10]
    bid_due_html = (
        f"<p class='warn'><strong>Re-run before you submit the bid.</strong> Stamp valid until "
        f"{_esc(valid_until or 'this run')}. Fees and portal asks move.</p>"
    )
    fee_html = ""
    fees = ((analysis.get("fee_card") or {}).get("fees")) or []
    if isinstance(fees, list) and fees:
        from fee_kind import classify_fee_kind

        lis = ""
        for row in fees[:8]:
            if not isinstance(row, dict):
                continue
            label = str(row.get("label") or row.get("name") or "Fee")
            kind = classify_fee_kind(label, str(row.get("detail") or ""), str(row.get("trade") or ""))
            lis += f"<li><strong>{_esc(kind)}</strong> {_esc(label)}</li>"
        if lis:
            fee_html = (
                "<h2>Fee types — permit vs tap vs impact</h2>"
                "<p class='fine'>Do not mix these. Impact and tap fees are often larger than the permit.</p>"
                f"<ol>{lis}</ol>"
            )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(title)}</title>
  <meta name="description" content="{_esc(description)}" />
  <link rel="canonical" href="{_esc(spa_url.split('?')[0] if spa_url else base + '/r/' + research_id)}" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{_esc(title)}" />
  <meta property="og:description" content="{_esc(description)}" />
  <meta property="og:url" content="{_esc(spa_url or (base + '/r/' + research_id))}" />
  <meta property="og:image" content="{_esc(og_image)}" />
  <meta property="og:site_name" content="Reg Guard" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{_esc(title)}" />
  <meta name="twitter:description" content="{_esc(description)}" />
  <style>
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#020617; color:#e2e8f0; }}
    .wrap {{ max-width:640px; margin:0 auto; padding:28px 20px 64px; }}
    .kicker {{ color:#34d399; font-size:12px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }}
    h1 {{ font-size:28px; margin:8px 0 12px; color:#fff; }}
    h2 {{ font-size:16px; color:#fcd34d; }}
    a.btn {{ display:inline-block; margin:6px 8px 6px 0; padding:12px 18px; border-radius:10px; font-weight:700; text-decoration:none; }}
    a.primary {{ background:#059669; color:#fff; }}
    a.ghost {{ background:#1e293b; color:#e2e8f0; border:1px solid #334155; }}
    .band {{ background:#064e3b; border:1px solid #34d39955; padding:12px; border-radius:10px; }}
    .warn {{ background:#78350f33; border:1px solid #f59e0b66; padding:12px; border-radius:10px; color:#fde68a; }}
    .fine {{ color:#94a3b8; font-size:13px; }}
    ol {{ padding-left:20px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <p class="kicker">Reg Guard Bid Risk Receipt</p>
    <h1>{_esc(site)}</h1>
    <p class="fine">Stamp { _esc(grade or '—') } · AHJ { _esc(ahj) } · planning aid, not a quote or sealed bid.</p>
    {preview_note}
    {bid_due_html}
    {band_html}
    {killer_html}
    {fee_html}
    <p>
      <a class="btn primary" href="{_esc(run_url)}">Run my address</a>
      <a class="btn ghost" href="{_esc(spa_url)}">Open full receipt</a>
    </p>
    <p>
      <a class="btn ghost" href="{_esc(partner)}">Partner $79/mo</a>
      <a class="btn ghost" href="{_esc(pro)}">Contractor Pro $149/mo</a>
    </p>
    <p class="fine">
      Confirm fees and timelines with the AHJ before you bid. We do not store cards — Stripe handles payment.
      Source: <a href="{_esc(APP_HOST)}" style="color:#34d399">app.regguardagent.com</a>
    </p>
  </div>
</body>
</html>
"""


def share_html_for_id(research_id: str, *, ref: str = "") -> Optional[str]:
    from research_store import get_analysis

    analysis = get_analysis(research_id)
    if not analysis:
        return None
    return render_share_html(
        analysis,
        research_id=research_id,
        ref=ref,
        preview=bool(analysis.get("preview")),
    )
