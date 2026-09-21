"""
IC Diligence Bundle — ZIP for IC / sponsor / lender buyers ($1,500 deliverable).

Contents:
  00_README.txt
  01_DECISION_MEMO.pdf          — 1-page Bid Risk Receipt (HOLD/CLEAR + contingency + top 3)
  02_IC_DILIGENCE_COUNSEL.docx  — editable Word with evidence binder + hyperlinks
  03_FEE_PUNCH_SCHEDULE.csv     — trade / owner / due window / exhibit_id / source_url
  04_EVIDENCE_INDEX.csv         — numbered exhibits + claim map
"""

from __future__ import annotations

import io
import zipfile
from typing import Any, Dict, Optional, Tuple


def build_ic_diligence_bundle_zip(
    analysis: Dict[str, Any],
    *,
    generated_for: str = "",
    share_url: str = "",
) -> Tuple[bytes, str]:
    """
    Return (zip_bytes, suggested_filename).

    Raises on generation failure for any required part.
    """
    from artifact_naming import document_download_filename, site_line_from_analysis
    from bid_risk_receipt_pdf import generate_bid_risk_receipt_pdf_bytes
    from bid_sheet_export import analysis_to_bid_csv
    from ic_boardroom_docx import generate_ic_boardroom_docx_bytes
    from ic_package_composer import compose_ic_package, evidence_index_to_csv

    data = dict(analysis or {})
    package = compose_ic_package(
        data,
        generated_for=generated_for,
        share_url=share_url,
    )
    site = site_line_from_analysis(data) or str((package.get("cover") or {}).get("site") or "SITE")
    share = str(share_url or package.get("share_url") or data.get("share_url") or "").strip()

    memo_pdf = generate_bid_risk_receipt_pdf_bytes(
        data,
        generated_for=generated_for or None,
        share_url=share or None,
    )
    docx = generate_ic_boardroom_docx_bytes(
        data,
        generated_for=generated_for,
        share_url=share,
    )
    # Prefer punch/fees that already carry exhibit_id from composer
    data_for_csv = dict(data)
    data_for_csv["share_url"] = share
    # Overlay stamped punch items from package when present
    punch_pkg = (package.get("punch_list") or {}).get("items") or []
    if punch_pkg:
        existing = data_for_csv.get("punch_list") if isinstance(data_for_csv.get("punch_list"), dict) else {}
        data_for_csv["punch_list"] = {
            **existing,
            "punch_list": punch_pkg,
            "timeline_summary": (package.get("punch_list") or {}).get("timeline_summary")
            or existing.get("timeline_summary"),
        }
    fees_pkg = ((package.get("site_findings") or {}).get("fees")) or []
    if fees_pkg:
        fee_card = data_for_csv.get("fee_card") if isinstance(data_for_csv.get("fee_card"), dict) else {}
        # Map composer fee shape back to fee_card rows when needed
        mapped = []
        for f in fees_pkg:
            mapped.append(
                {
                    "label": f.get("name"),
                    "trade": f.get("trade"),
                    "amount_usd": None,
                    "detail": f.get("note") or f.get("amount"),
                    "source_url": f.get("source_url"),
                    "source_label": f.get("source_label"),
                    "exhibit_id": f.get("exhibit_id"),
                    "owner": "Estimator / Permit runner",
                }
            )
        data_for_csv["fee_card"] = {**fee_card, "fees": mapped or fee_card.get("fees") or []}

    schedule_csv = analysis_to_bid_csv(data_for_csv)
    evidence_csv = evidence_index_to_csv(
        package.get("evidence_binder") or {},
        site=site,
    )

    stamp = ((package.get("decision_memo") or {}).get("stamp") or {})
    display = str(stamp.get("display") or stamp.get("grade") or "UNKNOWN")
    binder = package.get("evidence_binder") or {}
    summary = binder.get("summary") or {}
    clocks = package.get("parallel_clocks_track") or {}

    readme = "\n".join(
        [
            "REG GUARD — IC DILIGENCE BUNDLE",
            f"Site: {site}",
            f"Stamp: {display}",
            f"Prepared for: {generated_for or package.get('generated_for') or 'Authorized recipient'}",
            f"Generated: {package.get('generated_at') or ''}",
            "",
            "This is the $1,500 IC Project paid deliverable for IC / sponsor / lender buyers.",
            "The Bid Risk Receipt PDF is the forwardable stamp; the DOCX + CSVs are the working package.",
            "",
            "Contents:",
            "  01_DECISION_MEMO.pdf         — 1-page HOLD/CLEAR + contingency + top 3 drivers",
            "  02_IC_DILIGENCE_COUNSEL.docx — editable Word for counsel redlines (live hyperlinks + evidence binder)",
            "  03_FEE_PUNCH_SCHEDULE.csv    — trade / owner / due_window / exhibit_id / source_url",
            "  04_EVIDENCE_INDEX.csv        — numbered exhibits mapped to each claim",
            "",
            f"Evidence: {summary.get('exhibit_count', 0)} exhibits | "
            f"{summary.get('exhibited_claims', 0)} cited claims | "
            f"{summary.get('unverified_claims', 0)} unverified",
            f"Parallel clocks track: {'YES' if clocks.get('enabled') else 'n/a'}",
            "",
            "PLANNING AID ONLY — not a quote, sealed bid, interconnection study, geotech report,",
            "or AHJ filing. Confirm every fee and timeline with the AHJ before bid.",
            "",
            f"Share: {share or '(open results in Reg Guard)'}",
            "",
        ]
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("00_README.txt", readme)
        zf.writestr("01_DECISION_MEMO.pdf", memo_pdf)
        zf.writestr("02_IC_DILIGENCE_COUNSEL.docx", docx)
        zf.writestr("03_FEE_PUNCH_SCHEDULE.csv", schedule_csv)
        zf.writestr("04_EVIDENCE_INDEX.csv", evidence_csv)

    filename = document_download_filename(site, "IC DILIGENCE BUNDLE", "zip")
    return buf.getvalue(), filename
