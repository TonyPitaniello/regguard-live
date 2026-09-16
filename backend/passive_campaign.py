"""Passive beachhead campaign — architecture encoded as data + helpers.

Target: DFW / Austin electrical & GC estimators (permit runners as Partner).
Job-to-be-done: attach a Bid Risk Receipt to a bid today — not another code lookup.
Distribution: SEO metros + forwarded /r/ receipts + free-run email drip.
Honesty: planning aid, not a quote / sealed bid / interconnection study.
"""
from __future__ import annotations

import html as html_lib
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

CAMPAIGN_ID = "rg_passive_beachhead_2026"
APP_HOST = "https://app.regguardagent.com"
SUPPORT_EMAIL = "support@regguardagent.com"

# Paid SKUs this campaign is allowed to sell (no Sponsor, no live RTO).
PRIMARY_SKU = "partner"  # $79 — lowest-friction paid
HABIT_SKU = "contractor_pro"  # $149
WHALE_SKU = "ic_project"  # $1,500

UTM_SHARE = {
    "utm_source": "receipt",
    "utm_medium": "share",
    "utm_campaign": "bid_risk_receipt",
}

DRIP_KINDS = ("free_run_d2", "free_run_d5", "quota_paywall")

# Personas we write every surface for (never homeowners, never “AI code chat”).
PERSONAS = [
    {
        "id": "estimator",
        "who": "Electrical / GC estimator",
        "job": "Price the job without eating AHJ surprises",
        "offer": "Bid Risk Receipt + contingency band + city gotchas",
        "sku": HABIT_SKU,
    },
    {
        "id": "permit_runner",
        "who": "Permit runner / partner",
        "job": "Screen a site for a GC and look competent",
        "offer": "Forwardable /r/ link they can paste into a bid file",
        "sku": PRIMARY_SKU,
    },
    {
        "id": "ic_screener",
        "who": "Large-load / DC screener",
        "job": "Kill bad sites before $10k–$50k interconnect studies",
        "offer": "IC Project Report — screening, not a utility study",
        "sku": WHALE_SKU,
    },
]


def app_base_url() -> str:
    return (
        os.getenv("REG_GUARD_APP_URL")
        or os.getenv("FRONTEND_APP_URL")
        or APP_HOST
    ).rstrip("/")


def _slug_city(city: str) -> str:
    s = (city or "").strip().lower()
    s = s.replace("fort worth", "fort-worth").replace("round rock", "round-rock")
    s = re.sub(r"[^a-z0-9-]+", "-", s).strip("-")
    return s


def metro_pages() -> List[Dict[str, Any]]:
    """One SEO landing per curated city pack (DFW + Austin beachhead)."""
    from city_packs import CITY_PACKS

    out: List[Dict[str, Any]] = []
    for key, pack in CITY_PACKS.items():
        city = str(pack.get("city") or key.split(",")[0].title())
        state = str(pack.get("state") or "TX")
        slug = _slug_city(city)
        path = f"/{slug}-permit-fees"
        ahj = pack.get("ahj") or {}
        gotchas = pack.get("gotchas") or []
        fees = pack.get("fees") or []
        bullets: List[str] = []
        for g in gotchas[:4]:
            if not isinstance(g, dict):
                continue
            title = (g.get("title") or "").strip()
            detail = (g.get("detail") or "").strip()
            if title:
                bullets.append(f"{title} — {detail}" if detail else title)
        fee_bits = []
        for f in fees[:2]:
            if not isinstance(f, dict):
                continue
            label = (f.get("label") or "Permit fee").strip()
            amt = f.get("amount_usd")
            detail = (f.get("detail") or "").strip()
            if amt is not None:
                fee_bits.append(f"{label}: ${amt} planning aid — {detail}".strip(" —"))
            elif detail:
                fee_bits.append(f"{label}: {detail}")
        out.append(
            {
                "slug": slug,
                "path": path,
                "city": city,
                "state": state,
                "pack_key": key,
                "title": f"{city} {state} permit fees & pre-bid gotchas",
                "headline": f"Bid-day CYA for {city} AHJ work — not a code encyclopedia",
                "meta_description": (
                    f"{city} {state} electrical and trade permit diligence for contractors. "
                    f"Forwardable Bid Risk Receipt, city gotchas, Source or Unverified on every line. "
                    f"Planning aid — confirm with the AHJ before you bid."
                ),
                "bullets": bullets
                or [
                    f"Screen {city} AHJ risks before you price the job",
                    "Citeable punch list when sources exist — Unverified when they don’t",
                    "Forward the Bid Risk Receipt to your GC — planning aid, not a quote",
                ],
                "fee_note": (ahj.get("notes") or "")
                or (
                    f"Fee figures are planning aids. Always confirm with {ahj.get('name') or city + ' Building Inspections'} "
                    "before bid or filing."
                ),
                "fee_summary": fee_bits,
                "ahj_name": ahj.get("name") or f"City of {city}",
                "portal_url": ahj.get("portal_url") or "",
                "fees_url": ahj.get("fees_url") or "",
                "phone": ahj.get("phone") or "",
                "documents": pack.get("documents") or [],
                "timeline_hint": pack.get("timeline_hint") or "",
                "search_intents": [
                    f"{city} {state} electrical permit fees",
                    f"{city} building permit checklist contractor",
                    f"{city} AHJ permit gotchas",
                ],
                "cta_path": (
                    f"/?city={city}&state={state}"
                    f"&utm_source=seo&utm_medium=organic"
                    f"&utm_campaign=metro_{slug}&utm_content=permit-fees#free-trial-form"
                ),
            }
        )
    return out


def metro_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    want = (slug or "").strip().lower().replace("_", "-")
    want = want.replace("-permit-fees", "")
    for m in metro_pages():
        if m["slug"] == want:
            return m
    return None


def static_seo_paths() -> List[str]:
    return [
        "/",
        "/pricing",
        "/sample-report",
        "/methodology",
        "/how-it-works",
        "/permit-fees",
        "/affiliate",
        "/guarantee",
        "/data-center",
        "/install",
    ]


def sitemap_xml(*, base: Optional[str] = None) -> str:
    host = (base or app_base_url()).rstrip("/")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = list(static_seo_paths()) + [m["path"] for m in metro_pages()]
    chunks = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in urls:
        loc = f"{host}{path}"
        pri = "1.0" if path == "/" else ("0.9" if path.endswith("-permit-fees") else "0.7")
        chunks.append("  <url>")
        chunks.append(f"    <loc>{html_lib.escape(loc)}</loc>")
        chunks.append(f"    <lastmod>{today}</lastmod>")
        chunks.append("    <changefreq>weekly</changefreq>")
        chunks.append(f"    <priority>{pri}</priority>")
        chunks.append("  </url>")
    chunks.append("</urlset>")
    return "\n".join(chunks) + "\n"


def robots_txt(*, base: Optional[str] = None) -> str:
    host = (base or app_base_url()).rstrip("/")
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /orders\n"
        "Disallow: /checkout\n"
        "Disallow: /jobs\n"
        "Disallow: /my-jobs\n"
        "Disallow: /queue\n"
        "Disallow: /signup\n"
        f"Sitemap: {host}/sitemap.xml\n"
    )


def with_share_params(
    url: str,
    *,
    ref: str = "",
    utm: Optional[Dict[str, str]] = None,
) -> str:
    """Append ?ref= and campaign UTMs to a /r/{id} (or any) URL."""
    raw = (url or "").strip()
    if not raw:
        return ""
    parts = urlsplit(raw)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    params = dict(UTM_SHARE)
    if utm:
        params.update({k: v for k, v in utm.items() if v})
    q.update(params)
    code = (ref or q.get("ref") or "").strip().lower()
    if code:
        q["ref"] = code
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment)
    )


def campaign_share_url(research_id: str, *, ref: str = "") -> str:
    from research_store import share_url_for

    return with_share_params(share_url_for(research_id), ref=ref)


def checkout_url(tier: str, *, email: str = "", research_id: str = "", ref: str = "", campaign: str = "") -> str:
    base = app_base_url()
    path = f"{base}/checkout/{(tier or PRIMARY_SKU).strip().lower()}"
    q: Dict[str, str] = {
        "utm_source": "email",
        "utm_medium": "drip",
        "utm_campaign": campaign or "free_run",
    }
    if email:
        q["email"] = email
    if research_id:
        q["research_id"] = research_id
    if ref:
        q["ref"] = ref
    return f"{path}?{urlencode(q)}"


def drip_email(kind: str, payload: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """Return (subject, html) for a free-run drip step."""
    p = payload or {}
    email = str(p.get("email") or "")
    rid = str(p.get("research_id") or "")
    ref = str(p.get("referral_code") or "")
    city = str(p.get("city") or "").strip()
    address = str(p.get("address") or "your site").strip()
    share = with_share_params(
        str(p.get("share_url") or (campaign_share_url(rid, ref=ref) if rid else "")),
        ref=ref,
        utm={
            "utm_source": "email",
            "utm_medium": "drip",
            "utm_campaign": kind,
        },
    )
    partner = checkout_url(PRIMARY_SKU, email=email, research_id=rid, ref=ref, campaign=kind)
    pro = checkout_url(HABIT_SKU, email=email, research_id=rid, ref=ref, campaign=kind)
    place = f"{address}{(' · ' + city) if city else ''}"
    esc = html_lib.escape

    def wrap(title: str, body: str) -> str:
        return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;padding:24px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;padding:28px;">
    <p style="margin:0 0 8px;color:#059669;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">Reg Guard · Bid Risk Receipt</p>
    <h1 style="margin:0 0 12px;color:#111;font-size:22px;">{esc(title)}</h1>
    {body}
    <p style="margin-top:28px;font-size:12px;color:#888;">
      Planning aid only — not a quote, sealed bid, or interconnection study.
      Confirm fees and timelines with the AHJ. {SUPPORT_EMAIL}
    </p>
  </div>
</body></html>"""

    if kind == "free_run_d2":
        subject = f"Forward this Bid Risk Receipt before bid day — {place}"[:120]
        body = f"""
    <p style="color:#555;font-size:14px;line-height:1.5;">
      You ran <strong>{esc(place)}</strong>. The money is in the forward — GCs buy what they can
      open on a phone, not another research tab.
    </p>
    <p style="margin:20px 0;">
      <a href="{esc(share)}" style="display:inline-block;background:#059669;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:600;">
        Open &amp; forward the receipt
      </a>
    </p>
    <p style="color:#555;font-size:14px;">
      WhatsApp / copy the link. Recipients who later pay are tracked on your
      <code>?ref=</code> for demand — not a cash commission.
    </p>
"""
        return subject, wrap("Send this to your GC", body)

    if kind == "free_run_d5":
        subject = f"Lock {place} into Partner or Pro before the next bid"
        body = f"""
    <p style="color:#555;font-size:14px;line-height:1.5;">
      Same site is still in your account. Partner is for permit runners screening clients.
      Contractor Pro is for weekly bidders who need the habit loop (recheck + stamp).
    </p>
    <p style="margin:20px 0;">
      <a href="{esc(partner)}" style="display:inline-block;background:#059669;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:600;margin:0 8px 8px 0;">
        Partner — $79/mo
      </a>
      <a href="{esc(pro)}" style="display:inline-block;background:#1d4ed8;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:600;margin:0 8px 8px 0;">
        Contractor Pro — $149/mo
      </a>
    </p>
    <p style="color:#555;font-size:14px;">
      <a href="{esc(share)}" style="color:#1d4ed8;">Re-open the receipt</a> first if you still need to forward it.
    </p>
"""
        return subject, wrap("Don't re-research this site from scratch", body)

    if kind == "quota_paywall":
        subject = "Free monthly lookups used — keep the Bid Risk Receipt habit"
        body = f"""
    <p style="color:#555;font-size:14px;line-height:1.5;">
      This email already used this month’s free scans. The next lookup on this address
      (or the next job) needs Partner or Pro — we did not charge you for the blocked run.
    </p>
    <p style="margin:20px 0;">
      <a href="{esc(partner)}" style="display:inline-block;background:#059669;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:600;margin:0 8px 8px 0;">
        Start Partner — $79/mo
      </a>
      <a href="{esc(pro)}" style="display:inline-block;background:#1d4ed8;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:600;margin:0 8px 8px 0;">
        Contractor Pro — $149/mo
      </a>
    </p>
"""
        return subject, wrap("Your free scans are used up this month", body)

    subject = "Your Reg Guard Bid Risk Receipt"
    body = f'<p style="color:#555;font-size:14px;"><a href="{esc(share)}">Open your receipt</a></p>'
    return subject, wrap("Bid Risk Receipt", body)


def architecture_brief() -> Dict[str, Any]:
    """Machine-readable campaign plan (admin / tests / canvas)."""
    return {
        "id": CAMPAIGN_ID,
        "promise": "Forwardable Bid Risk Receipt before bid day — planning aid, not a quote.",
        "geo": "DFW + Austin city packs only until EARLY_DEMAND",
        "do_not": [
            "Nationwide thin coverage",
            "Compete on 7,000-jurisdiction code chat",
            "Sell Sponsor or live interconnection",
            "Add features while share→pay is dead",
        ],
        "personas": PERSONAS,
        "funnel": [
            "SEO metro page or forwarded /r/ link",
            "Free address run (email captured)",
            "Download / share Bid Risk Receipt with ?ref=",
            "GC opens /r/ (crawlable sales page)",
            "Day-2 forward nudge · Day-5 Partner/Pro · quota paywall",
            "Paid: Partner $79 / Pro $149 / IC $1,500",
        ],
        "metros": [m["slug"] for m in metro_pages()],
        "drip": list(DRIP_KINDS),
        "primary_sku": PRIMARY_SKU,
        "habit_sku": HABIT_SKU,
        "whale_sku": WHALE_SKU,
    }
