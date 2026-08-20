"""
Email Service: Sends research memos to trial users
Supports SendGrid, Resend, or simple email backend
"""

import os
import logging
import traceback
from typing import Optional

logger = logging.getLogger(__name__)


def _app_base_url() -> str:
    return (
        (os.getenv("REG_GUARD_APP_URL") or os.getenv("FRONTEND_APP_URL") or "https://app.regguardagent.com")
        .rstrip("/")
    )


def build_research_result_html(research_data: dict) -> str:
    """Shared HTML for SendGrid + Resend research-result delivery."""
    import html as html_lib

    project_info = research_data.get("project_info") or {}
    summary = research_data.get("summary") or {}
    punch = (research_data.get("punch_list") or {}).get("punch_list") or []
    killers = research_data.get("margin_killers") or []
    band = research_data.get("contingency_band") or {}

    address = html_lib.escape(str(project_info.get("address") or "Unknown Address"))
    city = html_lib.escape(str(project_info.get("city") or ""))
    state = html_lib.escape(str(project_info.get("state") or ""))
    zip_code = html_lib.escape(str(project_info.get("zip") or ""))

    high_risk = int(summary.get("high_risk_count") or 0)
    total_risks = int(summary.get("total_environmental_risks") or 0)
    try:
        total_cost = float(summary.get("estimated_total_cost") or 0)
    except (TypeError, ValueError):
        total_cost = 0.0
    timeline = html_lib.escape(str(summary.get("estimated_timeline") or "TBD"))
    total_items = int(summary.get("total_punch_list_items") or len(punch) or 0)

    share = str(research_data.get("share_url") or "").strip()
    rid = research_data.get("research_id")
    try:
        from research_store import resolve_forward_share_url

        share = resolve_forward_share_url(research_data, share_url=share, research_id=rid)
    except Exception:
        if not share and rid:
            share = f"{_app_base_url()}/r/{rid}"
        if (
            not share
            or share.endswith("/r/")
            or share.endswith("/r")
            or "utm_source=bid_receipt" in share
            or share.rstrip("/").endswith("regguardagent.com")
        ):
            share = f"{_app_base_url()}/r/{rid}" if rid else ""
    share_esc = html_lib.escape(share) if share else ""
    share_cta_html = (
        f"""
                            <a href="{share_esc}" style="display: inline-block; background: linear-gradient(135deg, #059669 0%, #047857 100%); color: white; padding: 14px 32px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px;">
                                Open shareable report
                            </a>
                            <p style="margin:12px 0 0 0;font-size:12px;color:#6b7280;word-break:break-all;">{share_esc}</p>
"""
        if share_esc
        else """
                            <p style="margin:0;font-size:13px;color:#b45309;font-weight:600;">
                                Share link unavailable — open your results in the Reg Guard app (this email will not send you to the homepage form).
                            </p>
"""
    )

    punch_rows = []
    for i, item in enumerate(punch[:8], 1):
        if not isinstance(item, dict):
            continue
        task = html_lib.escape(str(item.get("task") or "")[:160])
        pri = html_lib.escape(str(item.get("priority") or "NOTE"))
        if not task:
            continue
        punch_rows.append(
            f'<li style="margin:0 0 8px 0;font-size:13px;color:#374151;"><strong>[{pri}]</strong> {task}</li>'
        )
    for i, k in enumerate(killers[:3], 1):
        if not isinstance(k, dict):
            continue
        title = html_lib.escape(str(k.get("title") or "")[:140])
        pri = html_lib.escape(str(k.get("priority") or "NOTE"))
        if title:
            punch_rows.append(
                f'<li style="margin:0 0 8px 0;font-size:13px;color:#374151;"><strong>Risk [{pri}]</strong> {title}</li>'
            )
    punch_html = "".join(punch_rows) or (
        '<li style="margin:0;font-size:13px;color:#6b7280;">Open the share link for the full punch list.</li>'
    )

    band_html = ""
    if band.get("pct_low") is not None and band.get("pct_high") is not None:
        band_html = (
            f'<p style="margin:12px 0 0 0;font-size:14px;color:#047857;font-weight:600;">'
            f'Contingency (planning aid): +{band.get("pct_low")}% – +{band.get("pct_high")}%</p>'
        )

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td style="padding: 30px 20px;">
                <table width="100%" style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.1);">
                    <tr style="background: linear-gradient(135deg, #059669 0%, #047857 100%);">
                        <td style="padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: white; font-size: 26px; font-weight: 700;">Reg Guard Bid Risk Receipt</h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">Planning aid — confirm with AHJ before bid</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 30px; border-bottom: 1px solid #e5e7eb;">
                            <h2 style="margin: 0 0 15px 0; font-size: 16px; color: #1f2937; font-weight: 600;">Project location</h2>
                            <p style="margin: 0; font-size: 14px; color: #4b5563; line-height: 1.6;">
                                <strong>{address}</strong><br>
                                {city}, {state} {zip_code}
                            </p>
                            {band_html}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 30px; border-bottom: 1px solid #e5e7eb;">
                            <h2 style="margin: 0 0 20px 0; font-size: 16px; color: #1f2937; font-weight: 600;">Snapshot</h2>
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #f0f0f0;">
                                        <span style="font-size: 13px; color: #6b7280;">Environmental risks</span>
                                        <p style="margin: 5px 0 0 0; font-size: 18px; color: #1f2937; font-weight: 600;">{total_risks}</p>
                                    </td>
                                    <td style="padding: 12px 0 12px 20px; border-bottom: 1px solid #f0f0f0; text-align: right;">
                                        <span style="font-size: 13px; color: #dc2626;">High-risk items</span>
                                        <p style="margin: 5px 0 0 0; font-size: 18px; color: #dc2626; font-weight: 600;">{high_risk}</p>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 0;">
                                        <span style="font-size: 13px; color: #6b7280;">Timeline</span>
                                        <p style="margin: 5px 0 0 0; font-size: 16px; color: #1f2937; font-weight: 500;">{timeline}</p>
                                    </td>
                                    <td style="padding: 12px 0 0 20px; text-align: right;">
                                        <span style="font-size: 13px; color: #6b7280;">Est. total cost</span>
                                        <p style="margin: 5px 0 0 0; font-size: 18px; color: #059669; font-weight: 600;">${total_cost:,.0f}</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 30px; border-bottom: 1px solid #e5e7eb;">
                            <h2 style="margin: 0 0 15px 0; font-size: 16px; color: #1f2937; font-weight: 600;">Top flags ({total_items} punch items)</h2>
                            <ul style="margin:0;padding-left:18px;">{punch_html}</ul>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 30px; text-align: center;">
                            {share_cta_html}
                        </td>
                    </tr>
                    <tr style="background: #f9fafb; border-top: 1px solid #e5e7eb;">
                        <td style="padding: 25px 30px; text-align: center;">
                            <p style="margin: 0 0 10px 0; font-size: 12px; color: #888;">
                                Planning aid only — confirm with AHJ. Not a filing.
                            </p>
                            <p style="margin: 0 0 10px 0; font-size: 12px; color: #888;">
                                Questions? <strong>support@regguardagent.com</strong>
                            </p>
                            <p style="margin: 5px 0 0 0; font-size: 11px; color: #aaa;">
                                Reg Guard © 2026
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""




class EmailService:
    """Base email service"""

    async def send_research_memo(
        self,
        to_email: str,
        address: str,
        research_memo: str,
        trial_id: str,
    ) -> bool:
        """Send research memo to trial user"""
        raise NotImplementedError

    async def send_research_result(
        self,
        to_email: str,
        research_data: dict,
    ) -> dict:
        """Send research result to user email. Returns dict with status and email_id."""
        raise NotImplementedError

    async def send_order_pdfs_ready(
        self,
        to_email: str,
        order_id: str,
        pdfs: list,
    ) -> bool:
        """Notify buyer that IC Project PDF downloads are ready."""
        raise NotImplementedError

    async def send_ic_next_step(
        self,
        to_email: str,
        order_id: str,
        download_token: str,
    ) -> bool:
        """Tell IC buyer the next step after payment (run site lookup)."""
        raise NotImplementedError

    async def send_weekly_job_reminder(
        self,
        to_email: str,
        jobs: list,
    ) -> bool:
        """Weekly Saved Jobs digest — nudge to re-run or bid."""
        raise NotImplementedError

    async def send_plan_win_email(
        self,
        to_email: str,
        tier: str,
        *,
        day7: bool = False,
    ) -> bool:
        """Welcome (day 0) or Day-7 win email for Partner / Pro."""
        raise NotImplementedError

    def _build_plan_win_html(self, tier: str, *, day7: bool = False) -> str:
        app_url = os.getenv("FRONTEND_APP_URL", "https://app.regguardagent.com").rstrip("/")
        tier_l = (tier or "").strip().lower()
        name = "Partner" if tier_l == "partner" else "Contractor Pro"
        if day7:
            subject_line = f"Week 1 with {name} — save every site you bid"
            body = f"""
    <h1 style="margin:0 0 8px;color:#111;font-size:22px;">Bid week habit check</h1>
    <p style="color:#555;font-size:14px;line-height:1.5;">
      You're on <strong>{name}</strong>. Pros who stick save every site they bid this week,
      re-run before submit, and forward only lines with a Source (or clearly mark Unverified).
    </p>
    <ul style="color:#333;font-size:14px;line-height:1.6;">
      <li>Open Saved Jobs and confirm this week's sites are listed</li>
      <li>Re-run any site that changed scope or AHJ</li>
      <li>Strongest citeable coverage: Dallas / Plano / Austin</li>
    </ul>
    <p style="margin:20px 0;">
      <a href="{app_url}/jobs" style="display:inline-block;background:#1d4ed8;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:600;">
        Open Saved Jobs
      </a>
    </p>
"""
            if tier_l == "partner":
                body += f"""
    <p style="color:#555;font-size:14px;">
      Running your own bids too?
      <a href="{app_url}/checkout/contractor_pro" style="color:#1d4ed8;">Upgrade to Contractor Pro ($149/mo)</a>
    </p>
"""
        else:
            subject_line = f"Welcome to {name} — unlock deeper research"
            body = f"""
    <h1 style="margin:0 0 8px;color:#111;font-size:22px;">You're in — one step left</h1>
    <p style="color:#555;font-size:14px;line-height:1.5;">
      <strong>{name}</strong> is active on this email. Run a site lookup with the <em>same email</em>
      to unlock deeper scout research. Save every site you bid this week.
    </p>
    <p style="margin:20px 0;">
      <a href="{app_url}/?unlock=1" style="display:inline-block;background:#059669;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:600;">
        Unlock deeper results
      </a>
    </p>
    <p style="color:#555;font-size:14px;">
      Prefer a lighter plan later?
      <a href="{app_url}/checkout/partner" style="color:#1d4ed8;">Partner is $79/mo</a>
      · Need a full PDF package?
      <a href="{app_url}/checkout/ic_project" style="color:#1d4ed8;">IC Project Report ($1,500)</a>
      (planning worksheets — not official AHJ filings).
    </p>
"""
        # subject_line unused in HTML; kept for callers via naming
        _ = subject_line
        return f"""
<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;padding:24px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;padding:28px;">
    {body}
    <p style="margin-top:28px;font-size:12px;color:#888;">Reg Guard · support@regguardagent.com</p>
  </div>
</body></html>
"""

    def _build_weekly_jobs_html(self, jobs: list) -> str:
        from datetime import datetime, timezone

        app_url = os.getenv("FRONTEND_APP_URL", "https://app.regguardagent.com").rstrip("/")
        stale_days = int(os.getenv("JOB_STALE_DAYS") or "7")
        now = datetime.now(timezone.utc)

        def _job_li(j: dict) -> str:
            addr = j.get("address") or "Saved site"
            city = j.get("city") or ""
            state = j.get("state") or ""
            loc = f"{city}, {state}".strip(", ")
            share = j.get("share_url") or f"{app_url}/jobs"
            return (
                f'<li style="margin:10px 0;color:#333;font-size:14px;">'
                f"<strong>{addr}</strong>"
                f'{(" — " + loc) if loc else ""}'
                f' · <a href="{share}" style="color:#1d4ed8;">Open</a></li>'
            )

        fresh: list = []
        stale: list = []
        for j in jobs or []:
            raw = j.get("last_run_at") or j.get("updated_at") or ""
            is_stale = True
            try:
                dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                is_stale = (now - dt).days >= stale_days
            except Exception:
                is_stale = True
            (stale if is_stale else fresh).append(j)

        fresh_rows = "".join(_job_li(j) for j in fresh[:12])
        stale_rows = "".join(_job_li(j) for j in stale[:12])
        if not fresh_rows and not stale_rows:
            fresh_rows = (
                "<li style='color:#666;'>No active saved jobs — run a free lookup to start.</li>"
            )

        stale_block = ""
        if stale_rows:
            stale_block = f"""
    <h2 style="margin:24px 0 8px;color:#b45309;font-size:16px;">Needs re-check (stale {stale_days}+ days)</h2>
    <p style="color:#555;font-size:13px;line-height:1.5;">
      These sites have not been re-run recently. Re-check before you bid — fees and portal text change.
    </p>
    <ul style="padding-left:18px;">{stale_rows}</ul>
"""
        fresh_block = ""
        if fresh_rows:
            fresh_block = f"""
    <h2 style="margin:16px 0 8px;color:#111;font-size:16px;">Active Saved Jobs</h2>
    <ul style="padding-left:18px;">{fresh_rows}</ul>
"""
        return f"""
<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;padding:24px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;padding:28px;">
    <h1 style="margin:0 0 8px;color:#111;font-size:22px;">Your Saved Jobs this week</h1>
    <p style="color:#555;font-size:14px;line-height:1.5;">
      Bid-week habit from Reg Guard — re-check stale sites, then forward only Source or clearly Unverified lines.
    </p>
    {stale_block}
    {fresh_block}
    <p style="margin:20px 0;">
      <a href="{app_url}/jobs" style="display:inline-block;background:#1d4ed8;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:600;">
        View Saved Jobs / re-check
      </a>
    </p>
    <p style="margin-top:28px;font-size:12px;color:#888;">Reg Guard · support@regguardagent.com · Unsubscribe: reply STOP</p>
  </div>
</body></html>
"""

    def _build_ic_next_step_html(self, order_id: str, download_token: str, to_email: str = "") -> str:
        from urllib.parse import quote

        app_url = os.getenv("FRONTEND_APP_URL", "https://app.regguardagent.com").rstrip("/")
        short_id = (order_id or "")[:8]
        token = (download_token or "").strip()
        email_q = quote((to_email or "").strip().lower())
        lookup_url = f"{app_url}/?email={email_q}" if email_q else f"{app_url}/"
        orders_url = f"{app_url}/orders"
        if email_q:
            orders_url = f"{app_url}/orders?email={email_q}"
        token_block = ""
        if token:
            token_block = f"""
    <div style="margin:20px 0;padding:16px;background:#ecfdf5;border:2px solid #059669;border-radius:8px;">
      <p style="margin:0 0 6px;font-size:12px;color:#047857;font-weight:700;text-transform:uppercase;letter-spacing:0.04em;">
        Your IC access code
      </p>
      <p style="margin:0;font-size:22px;font-family:ui-monospace,Menlo,Consolas,monospace;color:#064e3b;font-weight:700;letter-spacing:0.06em;word-break:break-all;">
        {token}
      </p>
      <p style="margin:10px 0 0;font-size:12px;color:#065f46;">
        Keep this code. Open My Orders with the same email to download PDFs after your site lookup.
      </p>
    </div>
"""
        return f"""
<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;padding:24px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;padding:28px;">
    <h1 style="margin:0 0 8px;color:#111;font-size:22px;">Payment received — IC Project Report</h1>
    <p style="color:#555;font-size:14px;line-height:1.5;">
      Order #{short_id} is paid. Use the access code below, then run a site lookup with
      <strong>this same email</strong> to generate your Research Memo, Punch List, and Permit Package PDFs.
    </p>
    {token_block}
    <p style="color:#555;font-size:14px;line-height:1.5;">
      These are planning diligence PDFs (not an official AHJ filing). Confirm fees and filings with the local AHJ.
    </p>
    <p style="margin:20px 0;">
      <a href="{lookup_url}" style="display:inline-block;background:#059669;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:600;">
        Run site lookup
      </a>
    </p>
    <p style="margin-top:16px;">
      <a href="{orders_url}" style="color:#059669;font-weight:600;">Open My Orders</a>
    </p>
    <p style="margin-top:28px;font-size:12px;color:#888;">Reg Guard · support@regguardagent.com</p>
  </div>
</body></html>
"""

    def _build_order_pdfs_html(self, order_id: str, pdfs: list) -> str:
        app_url = os.getenv("FRONTEND_APP_URL", "https://app.regguardagent.com").rstrip("/")
        links = ""
        for p in pdfs or []:
            name = p.get("name") or p.get("type") or "PDF"
            url = p.get("url") or f"{app_url}/orders"
            links += (
                f'<p style="margin:12px 0;">'
                f'<a href="{url}" style="display:inline-block;background:#1d4ed8;color:#fff;'
                f'padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:600;">'
                f"Download {name}</a></p>"
            )
        short_id = (order_id or "")[:8]
        return f"""
<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;padding:24px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;padding:28px;">
    <h1 style="margin:0 0 8px;color:#111;font-size:22px;">Your IC Project Report is ready</h1>
    <p style="color:#555;font-size:14px;line-height:1.5;">
      Order #{short_id} includes your research memo, contractor punch list, and permit package worksheet.
      These are planning diligence PDFs — confirm fees and filings with the local AHJ before bid or submittal.
    </p>
    {links}
    <p style="margin-top:24px;">
      <a href="{app_url}/orders" style="color:#1d4ed8;">Open My Orders</a>
    </p>
    <p style="margin-top:28px;font-size:12px;color:#888;">Reg Guard · support@regguardagent.com</p>
  </div>
</body></html>
"""


class SendGridEmailService(EmailService):
    """SendGrid email service"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            self.sg = SendGridAPIClient(api_key)
            self.Mail = Mail
        except ImportError:
            logger.error("sendgrid package not installed")
            self.sg = None
            self.Mail = None

    async def send_research_memo(
        self,
        to_email: str,
        address: str,
        research_memo: str,
        trial_id: str,
    ) -> bool:
        """Send research memo via SendGrid"""
        if not self.sg or not self.Mail:
            logger.error("❌ SendGrid not configured")
            return False

        try:
            logger.info(f"📧 Building SendGrid message for {to_email}...")
            message = self.Mail(
                from_email=os.getenv("RESEND_FROM_EMAIL", "noreply@regguardagent.com"),
                to_emails=to_email,
                subject="Your RegGuard Free Research Memo is Ready",
                html_content=self._build_html_email(address, research_memo, trial_id),
                plain_text_content=self._build_text_email(address, research_memo, trial_id),
            )

            logger.info(f"📧 Sending via SendGrid...")
            response = self.sg.send(message)
            success = 200 <= response.status_code < 300

            if success:
                logger.info(f"✅ Research memo sent to {to_email} via SendGrid (status: {response.status_code})")
            else:
                logger.error(f"❌ SendGrid error: {response.status_code} - {response.body}")

            return success

        except Exception as e:
            logger.error(f"❌ Error sending email via SendGrid: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def _build_html_email(self, address: str, research_memo: str, trial_id: str) -> str:
        """Build HTML email with research memo"""
        memo_html = research_memo.replace("\n", "<br>")
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td style="padding: 30px 20px;">
                <table width="100%" style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                    <!-- Header -->
                    <tr style="background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);">
                        <td style="padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: white; font-size: 24px; font-weight: 600;">Your Research Memo</h1>
                        </td>
                    </tr>
                    
                    <!-- Memo Content -->
                    <tr>
                        <td style="padding: 30px; font-size: 14px; line-height: 1.7; color: #2c3e50;">
                            <pre style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace; white-space: pre-wrap; word-wrap: break-word; margin: 0; color: #2c3e50; background: #f9fafb; padding: 20px; border-radius: 6px; border-left: 4px solid #4f46e5; font-size: 13px; line-height: 1.6;">{memo_html}</pre>
                        </td>
                    </tr>
                    
                    <!-- CTA -->
                    <tr>
                        <td style="padding: 0 30px 30px 30px; text-align: center;">
                            <div style="background: linear-gradient(135deg, #f0f7ff 0%, #f3e8ff 100%); padding: 25px; border-radius: 6px; margin: 20px 0;">
                                <p style="margin: 0 0 15px 0; font-size: 14px; font-weight: 600; color: #1f2937;">
                                    Ready for the Complete Report?
                                </p>
                                <p style="margin: 0 0 20px 0; font-size: 13px; color: #555;">
                                    The premium report includes actionable punch list, complete permit package, and full environmental assessment.
                                </p>
                                <a href="https://app.regguardagent.com/order?trial={trial_id}" style="display: inline-block; background: #4f46e5; color: white; padding: 12px 28px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 13px;">
                                    Upgrade Now ($15,000)
                                </a>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr style="border-top: 1px solid #e5e7eb;">
                        <td style="padding: 20px 30px; text-align: center; font-size: 12px; color: #888;">
                            <p style="margin: 0;">Questions? Reply to this email or contact <strong>support@regguardagent.com</strong></p>
                            <p style="margin: 5px 0 0 0;">RegGuard © 2026</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """

    def _build_text_email(self, address: str, research_memo: str, trial_id: str) -> str:
        """Build plain text email"""
        return f"""{research_memo}

───────────────────────────────────────────────────────────────
UPGRADE TO FULL REPORT ($15,000)
───────────────────────────────────────────────────────────────

This memo gives you research direction. The premium report includes:
✓ Actionable punch list (what to do)
✓ Complete permit package (ready to file)
✓ Full environmental assessment
✓ Professional formatting

Ready? Get your complete analysis:
https://app.regguardagent.com/order?trial={trial_id}

Questions? Reply to this email.

RegGuard © 2026
"""

    def _build_result_html_email(self, research_data: dict) -> str:
        """Build professional HTML email for research result delivery"""
        return build_research_result_html(research_data)


    async def send_research_result(
        self,
        to_email: str,
        research_data: dict,
    ) -> dict:
        """Send research result via SendGrid"""
        if not self.sg or not self.Mail:
            logger.error("❌ SendGrid not configured")
            raise Exception("SendGrid not configured")

        try:
            project_info = research_data.get("project_info", {})
            city = project_info.get("city", "Unknown")
            state = project_info.get("state", "")

            logger.info(f"📧 Building SendGrid result email for {to_email}...")
            message = self.Mail(
                from_email=os.getenv("RESEND_FROM_EMAIL", "noreply@regguardagent.com"),
                to_emails=to_email,
                subject=f"Your RegGuard Research Results - {city}, {state}",
                html_content=self._build_result_html_email(research_data),
            )

            logger.info(f"📧 Sending result via SendGrid...")
            response = self.sg.send(message)
            success = 200 <= response.status_code < 300

            if success:
                logger.info(f"✅ Research result sent to {to_email} via SendGrid")
                return {
                    "status": "sent",
                    "email_id": getattr(response, "headers", {}).get("X-Message-ID", ""),
                    "email": to_email,
                }
            else:
                logger.error(f"❌ SendGrid error: {response.status_code}")
                raise Exception(f"SendGrid error: {response.status_code}")

        except Exception as e:
            logger.error(f"❌ Error sending result via SendGrid: {str(e)}")
            raise

    async def send_order_pdfs_ready(
        self,
        to_email: str,
        order_id: str,
        pdfs: list,
    ) -> bool:
        if not self.sg or not self.Mail:
            logger.error("❌ SendGrid not configured")
            return False
        try:
            message = self.Mail(
                from_email=os.getenv("RESEND_FROM_EMAIL", "noreply@regguardagent.com"),
                to_emails=to_email,
                subject="Your Reg Guard IC Project Report PDFs are ready",
                html_content=self._build_order_pdfs_html(order_id, pdfs),
            )
            response = self.sg.send(message)
            ok = 200 <= response.status_code < 300
            if ok:
                logger.info("✅ IC PDF ready email sent to %s via SendGrid", to_email)
            else:
                logger.error("SendGrid IC PDF email failed: %s", response.status_code)
            return ok
        except Exception as e:
            logger.error("SendGrid send_order_pdfs_ready failed: %s", e)
            return False

    async def send_ic_next_step(
        self,
        to_email: str,
        order_id: str,
        download_token: str,
    ) -> bool:
        if not self.sg or not self.Mail:
            logger.error("❌ SendGrid not configured")
            return False
        try:
            message = self.Mail(
                from_email=os.getenv("RESEND_FROM_EMAIL", "noreply@regguardagent.com"),
                to_emails=to_email,
                subject=f"Reg Guard IC Project — access code {((download_token or '')[:8] + '…') if download_token else 'ready'}",
                html_content=self._build_ic_next_step_html(order_id, download_token, to_email),
            )
            response = self.sg.send(message)
            return 200 <= response.status_code < 300
        except Exception as e:
            logger.error("SendGrid send_ic_next_step failed: %s", e)
            return False

    async def send_weekly_job_reminder(self, to_email: str, jobs: list) -> bool:
        if not self.sg or not self.Mail:
            return False
        try:
            message = self.Mail(
                from_email=os.getenv("RESEND_FROM_EMAIL", "noreply@regguardagent.com"),
                to_emails=to_email,
                subject="Reg Guard — your Saved Jobs this week",
                html_content=self._build_weekly_jobs_html(jobs),
            )
            response = self.sg.send(message)
            return 200 <= response.status_code < 300
        except Exception as e:
            logger.error("SendGrid weekly job reminder failed: %s", e)
            return False

    async def send_plan_win_email(
        self, to_email: str, tier: str, *, day7: bool = False
    ) -> bool:
        if not self.sg or not self.Mail:
            return False
        tier_l = (tier or "").strip().lower()
        name = "Partner" if tier_l == "partner" else "Contractor Pro"
        subject = (
            f"Reg Guard — week 1 with {name}"
            if day7
            else f"Reg Guard — welcome to {name}"
        )
        try:
            message = self.Mail(
                from_email=os.getenv("RESEND_FROM_EMAIL", "noreply@regguardagent.com"),
                to_emails=to_email,
                subject=subject,
                html_content=self._build_plan_win_html(tier, day7=day7),
            )
            response = self.sg.send(message)
            return 200 <= response.status_code < 300
        except Exception as e:
            logger.error("SendGrid plan win email failed: %s", e)
            return False


class ResendEmailService(EmailService):
    """Resend email service (alternative to SendGrid)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.resend = None
        
        try:
            import resend as resend_lib
            logger.info("📦 resend module imported successfully")
            
            # Configure Resend with API key
            resend_lib.api_key = api_key
            self.resend = resend_lib
            logger.info(f"✅ Resend initialized with API key: {api_key[:20]}...")
        except ImportError as e:
            logger.error(f"❌ resend package not installed. Install with: pip install resend")
            logger.error(f"   ImportError: {e}")
            self.resend = None
        except AttributeError as e:
            logger.error(f"❌ Error setting resend.api_key: {e}")
            self.resend = None
        except Exception as e:
            logger.error(f"❌ Unexpected error initializing Resend: {type(e).__name__}: {e}")
            self.resend = None

    async def send_research_memo(
        self,
        to_email: str,
        address: str,
        research_memo: str,
        trial_id: str,
    ) -> bool:
        """Send research memo via Resend"""
        if not self.resend:
            logger.error("❌ Resend not configured")
            return False

        try:
            # Simple, clean HTML email with preformatted memo
            memo_html = research_memo.replace("\n", "<br>")
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td style="padding: 30px 20px;">
                <table width="100%" style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                    <!-- Header -->
                    <tr style="background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);">
                        <td style="padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: white; font-size: 24px; font-weight: 600;">Your Research Memo</h1>
                        </td>
                    </tr>
                    
                    <!-- Memo Content -->
                    <tr>
                        <td style="padding: 30px; font-size: 14px; line-height: 1.7; color: #2c3e50;">
                            <pre style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace; white-space: pre-wrap; word-wrap: break-word; margin: 0; color: #2c3e50; background: #f9fafb; padding: 20px; border-radius: 6px; border-left: 4px solid #4f46e5; font-size: 13px; line-height: 1.6;">{memo_html}</pre>
                        </td>
                    </tr>
                    
                    <!-- CTA -->
                    <tr>
                        <td style="padding: 0 30px 30px 30px; text-align: center;">
                            <div style="background: linear-gradient(135deg, #f0f7ff 0%, #f3e8ff 100%); padding: 25px; border-radius: 6px; margin: 20px 0;">
                                <p style="margin: 0 0 15px 0; font-size: 14px; font-weight: 600; color: #1f2937;">
                                    Ready for the Complete Report?
                                </p>
                                <p style="margin: 0 0 20px 0; font-size: 13px; color: #555;">
                                    The premium report includes actionable punch list, complete permit package, and full environmental assessment.
                                </p>
                                <a href="https://app.regguardagent.com/order?trial={trial_id}" style="display: inline-block; background: #4f46e5; color: white; padding: 12px 28px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 13px;">
                                    Upgrade Now ($15,000)
                                </a>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr style="border-top: 1px solid #e5e7eb;">
                        <td style="padding: 20px 30px; text-align: center; font-size: 12px; color: #888;">
                            <p style="margin: 0;">Questions? Reply to this email or contact <strong>support@regguardagent.com</strong></p>
                            <p style="margin: 5px 0 0 0;">RegGuard © 2026</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
            """

            logger.info(f"📧 Preparing Resend API call for {to_email}...")
            # Resend API call
            try:
                logger.info(f"📧 Calling Resend.Emails.send()...")
                response = self.resend.Emails.send({
                    "from": os.getenv("RESEND_FROM_EMAIL", "noreply@regguardagent.com"),
                    "to": to_email,
                    "subject": "Your Site Diligence Research Memo",
                    "html": html_content,
                })
                logger.info(f"📧 Resend response: {response}")
            except Exception as e:
                logger.error(f"❌ Resend API error: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return False

            success = response.get("id") is not None

            if success:
                logger.info(f"✅ Research memo sent to {to_email} via Resend (id: {response.get('id')})")
            else:
                logger.error(f"❌ Resend error: {response}")

            return success

        except Exception as e:
            logger.error(f"❌ Error sending email via Resend: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    async def send_order_pdfs_ready(
        self,
        to_email: str,
        order_id: str,
        pdfs: list,
    ) -> bool:
        if not self.resend:
            logger.error("❌ Resend not configured")
            return False
        try:
            response = self.resend.Emails.send({
                "from": os.getenv("RESEND_FROM_EMAIL", "noreply@regguardagent.com"),
                "to": to_email,
                "subject": "Your Reg Guard IC Project Report PDFs are ready",
                "html": self._build_order_pdfs_html(order_id, pdfs),
            })
            ok = bool(response.get("id")) if isinstance(response, dict) else bool(getattr(response, "id", None))
            if ok:
                logger.info("✅ IC PDF ready email sent to %s via Resend", to_email)
            else:
                logger.error("Resend IC PDF email failed: %s", response)
            return ok
        except Exception as e:
            logger.error("Resend send_order_pdfs_ready failed: %s", e)
            return False

    async def send_ic_next_step(
        self,
        to_email: str,
        order_id: str,
        download_token: str,
    ) -> bool:
        if not self.resend:
            logger.error("❌ Resend not configured")
            return False
        try:
            response = self.resend.Emails.send({
                "from": os.getenv("RESEND_FROM_EMAIL", "noreply@regguardagent.com"),
                "to": to_email,
                "subject": f"Reg Guard IC Project — access code {((download_token or '')[:8] + '…') if download_token else 'ready'}",
                "html": self._build_ic_next_step_html(order_id, download_token, to_email),
            })
            ok = bool(response.get("id")) if isinstance(response, dict) else bool(getattr(response, "id", None))
            if not ok:
                logger.error("Resend IC next-step failed: %s", response)
            return ok
        except Exception as e:
            logger.error("Resend send_ic_next_step failed: %s", e)
            return False

    async def send_weekly_job_reminder(self, to_email: str, jobs: list) -> bool:
        if not self.resend:
            return False
        try:
            response = self.resend.Emails.send({
                "from": os.getenv("RESEND_FROM_EMAIL", "noreply@regguardagent.com"),
                "to": to_email,
                "subject": "Reg Guard — your Saved Jobs this week",
                "html": self._build_weekly_jobs_html(jobs),
            })
            return bool(response.get("id")) if isinstance(response, dict) else bool(getattr(response, "id", None))
        except Exception as e:
            logger.error("Resend weekly job reminder failed: %s", e)
            return False

    async def send_plan_win_email(
        self, to_email: str, tier: str, *, day7: bool = False
    ) -> bool:
        if not self.resend:
            return False
        tier_l = (tier or "").strip().lower()
        name = "Partner" if tier_l == "partner" else "Contractor Pro"
        subject = (
            f"Reg Guard — week 1 with {name}"
            if day7
            else f"Reg Guard — welcome to {name}"
        )
        try:
            response = self.resend.Emails.send({
                "from": os.getenv("RESEND_FROM_EMAIL", "noreply@regguardagent.com"),
                "to": to_email,
                "subject": subject,
                "html": self._build_plan_win_html(tier, day7=day7),
            })
            return bool(response.get("id")) if isinstance(response, dict) else bool(getattr(response, "id", None))
        except Exception as e:
            logger.error("Resend plan win email failed: %s", e)
            return False

    async def send_research_result(
        self,
        to_email: str,
        research_data: dict,
    ) -> dict:
        """Send research result via Resend"""
        if not self.resend:
            logger.error("❌ Resend not configured")
            raise Exception("Resend not configured")

        try:
            project_info = research_data.get("project_info", {})
            city = project_info.get("city", "Unknown")
            state = project_info.get("state", "")

            html_content = self._build_result_html_email(research_data)

            logger.info(f"📧 Preparing Resend API call for result to {to_email}...")
            response = self.resend.Emails.send({
                "from": os.getenv("RESEND_FROM_EMAIL", "noreply@regguardagent.com"),
                "to": to_email,
                "subject": f"Your RegGuard Research Results - {city}, {state}",
                "html": html_content,
            })
            logger.info(f"📧 Resend response: {response}")

            if response.get("id"):
                logger.info(f"✅ Research result sent to {to_email} via Resend")
                return {
                    "status": "sent",
                    "email_id": response.get("id", ""),
                    "email": to_email,
                }
            else:
                logger.error(f"❌ Resend error: {response}")
                raise Exception(f"Resend error: {response}")

        except Exception as e:
            logger.error(f"❌ Error sending result via Resend: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _build_result_html_email(self, research_data: dict) -> str:
        """Build professional HTML email for research result delivery"""
        return build_research_result_html(research_data)



def get_email_service() -> Optional[EmailService]:
    """Get configured email service (SendGrid or Resend)"""
    sendgrid_key = os.getenv("SENDGRID_API_KEY")
    resend_key = os.getenv("RESEND_API_KEY")

    logger.info(f"🔍 Email service check: SendGrid={'SET' if sendgrid_key else 'NOT SET'}, Resend={'SET' if resend_key else 'NOT SET'}")

    if sendgrid_key:
        logger.info("📧 Using SendGrid email service")
        return SendGridEmailService(sendgrid_key)
    elif resend_key:
        logger.info("📧 Using Resend email service")
        return ResendEmailService(resend_key)
    else:
        logger.error("❌ No email service configured (SENDGRID_API_KEY or RESEND_API_KEY not set)")
        return None
