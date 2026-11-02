"""
Build forwardable HTML email: full punch list + sources + share link.
Used by SendGrid and Resend result emails.
"""

from __future__ import annotations

from html import escape
from typing import Any, Dict, List

from honesty import permit_total_line
from research_store import extract_sources, share_url_for


def _honesty_banner(research_data: dict) -> str:
    honesty = research_data.get("honesty") or {}
    unverified = (
        research_data.get("preview")
        or (research_data.get("summary") or {}).get("estimates_unverified")
        or not honesty.get("cost_verified")
        or not honesty.get("risk_verified")
    )
    if not unverified:
        return ""
    return (
        '<tr><td style="padding:16px 30px;background:#fff7ed;border-bottom:1px solid #fed7aa;">'
        '<p style="margin:0;font-size:13px;color:#9a3412;line-height:1.5;">'
        "<strong>Preview / unverified estimates.</strong> "
        "Flood and wetlands stay Unverified until a mapper source is attached. This is not a 0–100 score. "
        "No permit total is printed when the city uses a valuation or floor-area table. "
        "Forward this report to your GC with that context."
        "</p></td></tr>"
    )


def _punch_rows(research_data: dict) -> str:
    punch = (research_data.get("punch_list") or {}).get("punch_list") or []
    if not punch:
        critical = (research_data.get("punch_list") or {}).get("critical_path") or []
        if not critical:
            return (
                '<p style="margin:0;font-size:13px;color:#6b7280;">'
                "No punch items in this preview — open the share link after a full research run."
                "</p>"
            )
        items = "".join(
            f'<li style="margin:0 0 8px 0;font-size:13px;color:#1f2937;">{escape(str(t))}</li>'
            for t in critical[:15]
        )
        return f'<ol style="margin:0;padding-left:20px;">{items}</ol>'

    rows: List[str] = []
    for i, item in enumerate(punch[:25], 1):
        if not isinstance(item, dict):
            continue
        task = escape(str(item.get("task") or f"Item {i}"))
        priority = escape(str(item.get("priority") or ""))
        who = escape(str(item.get("responsible_party") or ""))
        timeline = escape(str(item.get("timeline") or ""))
        cost = item.get("estimated_cost")
        cost_s = f"${float(cost):,.0f}" if isinstance(cost, (int, float)) else ""
        unverified = item.get("cost_verified") is False or (research_data.get("summary") or {}).get(
            "estimates_unverified"
        )
        if cost_s and unverified:
            cost_s += " (unverified)"
        notes = escape(str(item.get("notes") or ""))
        meta = " · ".join(x for x in [priority, who, timeline, cost_s] if x)
        rows.append(
            f'<tr><td style="padding:12px 0;border-bottom:1px solid #f3f4f6;">'
            f'<p style="margin:0 0 4px 0;font-size:14px;color:#111827;font-weight:600;">{i}. {task}</p>'
            f'<p style="margin:0;font-size:12px;color:#6b7280;">{meta}</p>'
            + (f'<p style="margin:4px 0 0 0;font-size:12px;color:#9ca3af;">{notes}</p>' if notes else "")
            + "</td></tr>"
        )
    return (
        '<table width="100%" cellpadding="0" cellspacing="0">'
        + "".join(rows)
        + "</table>"
    )


def _sources_block(research_data: dict) -> str:
    sources = extract_sources(research_data)
    if not sources:
        return (
            '<p style="margin:0;font-size:13px;color:#6b7280;">'
            "No citeable .gov / Municode URLs in this preview. "
            "Full /research runs attach source links when scout hits exist."
            "</p>"
        )
    items = []
    for s in sources[:20]:
        label = escape(str(s.get("label") or "Source"))
        url = str(s.get("url") or "")
        if url.startswith("http"):
            items.append(
                f'<li style="margin:0 0 6px 0;font-size:12px;">'
                f'<a href="{escape(url)}" style="color:#4f46e5;">{label}</a></li>'
            )
        else:
            items.append(f'<li style="margin:0 0 6px 0;font-size:12px;color:#374151;">{label}</li>')
    return f'<ul style="margin:0;padding-left:18px;">{"".join(items)}</ul>'


def build_forwardable_result_html(research_data: dict) -> str:
    """Full forwardable HTML: location, honesty, punch list, sources, share CTA."""
    project = research_data.get("project_info") or {}
    summary = research_data.get("summary") or {}
    honesty = research_data.get("honesty") or {}

    address = escape(str(project.get("address") or "Unknown Address"))
    city = escape(str(project.get("city") or ""))
    state = escape(str(project.get("state") or ""))
    zip_code = escape(str(project.get("zip") or ""))

    timeline = escape(str(summary.get("estimated_timeline") or "Confirm with the AHJ"))
    cost_line = escape(permit_total_line(summary, honesty))
    total_items = int(summary.get("total_punch_list_items") or len(
        (research_data.get("punch_list") or {}).get("punch_list") or []
    ))

    research_id = str(research_data.get("research_id") or "")
    share = research_data.get("share_url") or (share_url_for(research_id) if research_id else "https://app.regguardagent.com/")
    share_esc = escape(share)

    unverified = (
        research_data.get("preview")
        or summary.get("estimates_unverified")
        or not honesty.get("cost_verified")
    )
    cost_label = "Permit total"
    timeline_label = "Timeline (unverified)" if unverified else "Timeline"
    risk_verified = honesty.get("risk_verified") is True
    risk_level = (research_data.get("environmental_screening") or {}).get("risk_level") or "UNAVAILABLE"
    risk_display = escape(str(risk_level if risk_verified else "Unavailable (not parcel-verified)"))

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td style="padding:30px 20px;">
<table width="100%" style="max-width:640px;margin:0 auto;background:white;border-radius:8px;">
  <tr style="background:linear-gradient(135deg,#4f46e5 0%,#6366f1 100%);">
    <td style="padding:32px 28px;text-align:center;border-radius:8px 8px 0 0;">
      <h1 style="margin:0;color:white;font-size:24px;font-weight:700;">RegGuard Site Diligence Report</h1>
      <p style="margin:8px 0 0 0;color:rgba(255,255,255,0.9);font-size:13px;">Forwardable punch list for your bid file</p>
    </td>
  </tr>
  {_honesty_banner(research_data)}
  <tr><td style="padding:28px;border-bottom:1px solid #e5e7eb;">
    <h2 style="margin:0 0 12px 0;font-size:15px;color:#1f2937;">Project location</h2>
    <p style="margin:0;font-size:14px;color:#4b5563;line-height:1.6;"><strong>{address}</strong><br>{city}, {state} {zip_code}</p>
  </td></tr>
  <tr><td style="padding:28px;border-bottom:1px solid #e5e7eb;">
    <h2 style="margin:0 0 16px 0;font-size:15px;color:#1f2937;">Summary</h2>
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:8px 0;"><span style="font-size:12px;color:#6b7280;">Flood / wetlands</span>
          <p style="margin:4px 0 0 0;font-size:16px;color:#1f2937;font-weight:600;">{risk_display}</p></td>
        <td style="padding:8px 0;text-align:right;"><span style="font-size:12px;color:#6b7280;">Punch items</span>
          <p style="margin:4px 0 0 0;font-size:16px;color:#1f2937;font-weight:600;">{total_items}</p></td>
      </tr>
      <tr>
        <td style="padding:8px 0;"><span style="font-size:12px;color:#6b7280;">{timeline_label}</span>
          <p style="margin:4px 0 0 0;font-size:15px;color:#1f2937;">{timeline}</p></td>
        <td style="padding:8px 0;text-align:right;"><span style="font-size:12px;color:#6b7280;">{cost_label}</span>
          <p style="margin:4px 0 0 0;font-size:14px;color:#059669;font-weight:600;">{cost_line}</p></td>
      </tr>
    </table>
  </td></tr>
  <tr><td style="padding:28px;border-bottom:1px solid #e5e7eb;">
    <h2 style="margin:0 0 14px 0;font-size:15px;color:#1f2937;">Full punch list</h2>
    {_punch_rows(research_data)}
  </td></tr>
  <tr><td style="padding:28px;border-bottom:1px solid #e5e7eb;">
    <h2 style="margin:0 0 14px 0;font-size:15px;color:#1f2937;">Sources</h2>
    {_sources_block(research_data)}
  </td></tr>
  <tr><td style="padding:28px;text-align:center;">
    <a href="{share_esc}" style="display:inline-block;background:#4f46e5;color:white;padding:14px 28px;border-radius:6px;text-decoration:none;font-weight:600;font-size:14px;">
      Open shareable report
    </a>
    <p style="margin:12px 0 0 0;font-size:12px;color:#6b7280;word-break:break-all;">{share_esc}</p>
    <p style="margin:8px 0 0 0;font-size:11px;color:#9ca3af;">Paste this link into a bid file or email your GC.</p>
  </td></tr>
  <tr style="background:#f9fafb;"><td style="padding:20px 28px;text-align:center;">
    <p style="margin:0;font-size:11px;color:#9ca3af;">RegGuard © 2026 · Cite or confirm with AHJ before bidding</p>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def build_forwardable_plaintext(research_data: dict) -> str:
    project = research_data.get("project_info") or {}
    summary = research_data.get("summary") or {}
    research_id = str(research_data.get("research_id") or "")
    share = research_data.get("share_url") or (share_url_for(research_id) if research_id else "")
    lines = [
        "RegGuard Site Diligence Report",
        f"Site: {project.get('address', '')}",
        f"{project.get('city', '')}, {project.get('state', '')} {project.get('zip', '')}",
        "",
        "Planning aid for DFW–Austin commercial–industrial work. Not a quote, sealed bid, Phase I ESA, interconnection study, or AHJ filing.",
        f"Timeline: {summary.get('estimated_timeline', 'Confirm with the AHJ')}",
        permit_total_line(summary, research_data.get("honesty") or {}),
        "",
        "PUNCH LIST:",
    ]
    punch = (research_data.get("punch_list") or {}).get("punch_list") or []
    for i, item in enumerate(punch[:25], 1):
        if isinstance(item, dict):
            url = str(item.get("source_url") or item.get("citation_url") or "")
            cost = item.get("estimated_cost")
            cost_bit = (
                f" | ${float(cost):,.0f}"
                if item.get("verified") and url.startswith("http") and isinstance(cost, (int, float)) and float(cost) > 0
                else ""
            )
            lines.append(f"{i}. [{item.get('priority', '')}] {item.get('task', '')}{cost_bit}")
    sources = extract_sources(research_data)
    if sources:
        lines.extend(["", "SOURCES:"])
        for s in sources[:15]:
            lines.append(f"- {s.get('label')} {s.get('url') or ''}".strip())
    if share:
        lines.extend(["", f"Shareable report: {share}"])
    return "\n".join(lines)
