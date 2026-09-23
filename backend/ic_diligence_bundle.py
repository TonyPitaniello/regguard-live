"""
IC Diligence Bundle — primary $1,500 deliverable.

Must match frontend IC_BUNDLE.contents / Pricing “What’s in the ZIP” exactly:

  01_DECISION_MEMO.pdf               — 1-page HOLD/CLEAR Bid Risk Receipt
  02_IC_DILIGENCE_BOARDROOM.pdf      — full boardroom brief (stamp, clocks, punch, exhibits)
  03_IC_DILIGENCE_COUNSEL.docx       — editable Word (same brief + hyperlinks + parallel clocks)
  04_FEE_PUNCH_EVIDENCE.xlsx         — estimator workbook (Cover | Fees | Punch | Evidence)
  05_EVIDENCE_INDEX.xlsx             — evidence index (Cover | Exhibits | Claims | Index)
  optional/FEE_PUNCH_SCHEDULE.csv    — optional paste export (fee/punch)
  optional/EVIDENCE_INDEX.csv        — optional paste export (evidence index)

Parallel clocks live inside the boardroom PDF and counsel DOCX.
No README.txt — Pricing does not promise one.
"""

from __future__ import annotations

import io
import zipfile
from typing import Any, Dict, Tuple

# Canonical archive member names — keep in lockstep with IC_BUNDLE.contents
BUNDLE_REQUIRED = (
    "01_DECISION_MEMO.pdf",
    "02_IC_DILIGENCE_BOARDROOM.pdf",
    "03_IC_DILIGENCE_COUNSEL.docx",
    "04_FEE_PUNCH_EVIDENCE.xlsx",
    "05_EVIDENCE_INDEX.xlsx",
)
BUNDLE_OPTIONAL_CSV = (
    "optional/FEE_PUNCH_SCHEDULE.csv",
    "optional/EVIDENCE_INDEX.csv",
)
BUNDLE_MEMBERS = BUNDLE_REQUIRED + BUNDLE_OPTIONAL_CSV


def build_ic_diligence_bundle_zip(
    analysis: Dict[str, Any],
    *,
    generated_for: str = "",
    share_url: str = "",
) -> Tuple[bytes, str]:
    """
    Return (zip_bytes, suggested_filename).

    Raises on generation failure for any required Pricing member.
    """
    from artifact_naming import document_download_filename, site_line_from_analysis
    from bid_risk_receipt_pdf import generate_bid_risk_receipt_pdf_bytes
    from bid_sheet_export import analysis_to_bid_csv
    from bid_sheet_xlsx import (
        analysis_to_evidence_index_xlsx,
        analysis_to_fee_punch_evidence_xlsx,
    )
    from ic_boardroom_docx import generate_ic_boardroom_docx_bytes
    from ic_boardroom_pdf import generate_ic_boardroom_pdf_bytes
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
    if not memo_pdf or memo_pdf[:4] != b"%PDF":
        raise RuntimeError("Decision memo PDF failed — required by Pricing Bundle contract")

    boardroom_pdf = generate_ic_boardroom_pdf_bytes(
        data,
        generated_for=generated_for,
        share_url=share,
    )
    if not boardroom_pdf or boardroom_pdf[:4] != b"%PDF" or len(boardroom_pdf) < 8_000:
        raise RuntimeError("Boardroom PDF failed — required by Pricing Bundle contract")

    docx = generate_ic_boardroom_docx_bytes(
        data,
        generated_for=generated_for,
        share_url=share,
    )
    if not docx or docx[:2] != b"PK" or len(docx) < 4_000:
        raise RuntimeError("Counsel DOCX failed — required by Pricing Bundle contract")

    data_for_sheet = dict(data)
    data_for_sheet["share_url"] = share
    punch_pkg = (package.get("punch_list") or {}).get("items") or []
    if punch_pkg:
        existing = data_for_sheet.get("punch_list") if isinstance(data_for_sheet.get("punch_list"), dict) else {}
        data_for_sheet["punch_list"] = {
            **existing,
            "punch_list": punch_pkg,
            "timeline_summary": (package.get("punch_list") or {}).get("timeline_summary")
            or existing.get("timeline_summary"),
        }
    fees_pkg = ((package.get("site_findings") or {}).get("fees")) or []
    if fees_pkg:
        fee_card = data_for_sheet.get("fee_card") if isinstance(data_for_sheet.get("fee_card"), dict) else {}
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
        data_for_sheet["fee_card"] = {**fee_card, "fees": mapped or fee_card.get("fees") or []}

    binder = package.get("evidence_binder") or {}
    xlsx = analysis_to_fee_punch_evidence_xlsx(
        data_for_sheet,
        binder=binder,
        site=site,
    )
    if not xlsx or xlsx[:2] != b"PK" or len(xlsx) < 2_000:
        raise RuntimeError("Fee / punch / evidence Excel failed — required by Pricing Bundle contract")

    evidence_xlsx = analysis_to_evidence_index_xlsx(
        data_for_sheet,
        binder=binder,
        site=site,
    )
    if not evidence_xlsx or evidence_xlsx[:2] != b"PK" or len(evidence_xlsx) < 1_500:
        raise RuntimeError("Evidence index Excel failed — required by Pricing Bundle contract")

    schedule_csv = analysis_to_bid_csv(data_for_sheet)
    if not schedule_csv or "source_url" not in schedule_csv:
        raise RuntimeError("Fee / punch CSV (optional export) failed")

    evidence_csv = evidence_index_to_csv(binder, site=site)
    if not evidence_csv or ("EX-" not in evidence_csv and "exhibit" not in evidence_csv.lower()):
        raise RuntimeError("Evidence index CSV (optional export) failed")

    parts = {
        BUNDLE_MEMBERS[0]: memo_pdf,
        BUNDLE_MEMBERS[1]: boardroom_pdf,
        BUNDLE_MEMBERS[2]: docx,
        BUNDLE_MEMBERS[3]: xlsx,
        BUNDLE_MEMBERS[4]: evidence_xlsx,
        BUNDLE_MEMBERS[5]: schedule_csv.encode("utf-8")
        if isinstance(schedule_csv, str)
        else schedule_csv,
        BUNDLE_MEMBERS[6]: evidence_csv.encode("utf-8")
        if isinstance(evidence_csv, str)
        else evidence_csv,
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in BUNDLE_MEMBERS:
            zf.writestr(name, parts[name])

    # Hard guarantee — no README, no missing Pricing members
    with zipfile.ZipFile(io.BytesIO(buf.getvalue()), "r") as zf:
        names = set(zf.namelist())
    missing = [m for m in BUNDLE_REQUIRED if m not in names]
    if missing:
        raise RuntimeError(f"Bundle missing Pricing members: {missing}")
    if any(n.lower().endswith(".txt") for n in names):
        raise RuntimeError("Bundle must not include README.txt — Pricing does not promise one")

    filename = document_download_filename(site, "IC DILIGENCE BUNDLE", "zip")
    return buf.getvalue(), filename
