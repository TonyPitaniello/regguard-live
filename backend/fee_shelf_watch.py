"""Weekday check: a cited fee phrase is still in the official file.

holds — every cited phrase is in the file.
moved — the file opened, it is the schedule we cited, and a phrase is gone.
unread — the file did not open, or the page is too thin to be the schedule.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence, Union
from urllib.request import Request, urlopen

Needle = Union[str, Sequence[str]]

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# schedule=True means this exact URL is where the cited dollar was read.
# A missing phrase on that file is "moved". A portal page is not.
CHECKS: List[Dict[str, Any]] = [
    {
        "city": "Frisco",
        "url": "https://www.friscotexas.gov/DocumentCenter/View/864/Permit-Fee-Schedule-PDF",
        "schedule": True,
        "needles": ["80%", ["300"], ["75"], ["10/1/2026", "october 1, 2026"]],
    },
    {
        "city": "Irving",
        "url": "https://irvingtx.gov/gov-rates-fees",
        "schedule": True,
        "needles": ["0.45", ["1,200", "1200"], "2025-11146", "2025-11165"],
    },
    {
        "city": "Garland",
        "url": "https://www.garlandtx.gov/2152/Building-Permit",
        "schedule": True,
        "needles": ["40%", "4.5%"],
    },
    {
        "city": "Carrollton",
        "url": "https://www.cityofcarrollton.com/departments/departments-a-f/building-inspection/fees",
        "schedule": True,
        "needles": [["$6", "6 per", "$6.00"], ["1,000", "1000"], "125", ["re-inspection", "reinspection"]],
    },
    {
        "city": "Round Rock",
        "url": "https://www.roundrocktexas.gov/wp-content/uploads/2025/11/pds-fees-summary.pdf",
        "schedule": True,
        "needles": ["75", ["august 2023", "updated august 2023"]],
    },
    {
        "city": "Houston",
        "url": "https://www.houstonpermittingcenter.org/media/2636/download",
        "schedule": True,
        "needles": ["25%", "2026"],
    },
    {
        "city": "San Antonio",
        "url": "https://docsonline.sanantonio.gov/DSDUploads/CurrentFeeSchedule.pdf",
        "schedule": True,
        "needles": [["october 2026"], ["4%"], ["fy 2027", "fy2027"]],
    },
    {
        "city": "Arlington",
        "url": "https://www.arlingtontx.gov/News-Articles/2025/September/Arlington-Implementing-Phased-Permit-Fee-Adjustments-in-2025",
        "schedule": True,
        "needles": ["phase 2", ["october 1, 2025", "oct 1, 2025", "oct. 1, 2025"]],
    },
    {
        "city": "Plano",
        "url": "https://www.plano.gov/350/Building-Inspections-Permits",
        "schedule": False,
        "needles": ["building inspection"],
    },
    {
        "city": "Dallas",
        "url": "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/Pages/default.aspx",
        "schedule": False,
        "needles": ["building inspection"],
    },
    {
        "city": "Austin",
        "url": "https://www.austintexas.gov/development-services/fees",
        "schedule": False,
        "needles": ["fee"],
    },
    {
        "city": "Fort Worth",
        "url": "https://www.fortworthtexas.gov/departments/development-services",
        "schedule": False,
        "needles": ["development"],
    },
    {
        "city": "McKinney",
        "url": "https://www.mckinneytexas.org/258/Fee-Schedule",
        "schedule": False,
        "needles": ["fee"],
    },
    {
        "city": "Richardson",
        "url": "https://www.cor.net/departments/building-inspection/pdf-forms",
        "schedule": False,
        "needles": [["permit", "fee"]],
    },
]


def _group_hit(low: str, needle: Needle) -> bool:
    options = [needle] if isinstance(needle, str) else list(needle)
    return any(str(opt).lower() in low for opt in options)


def judge_text(text: str, needles: Sequence[Needle], *, schedule: bool) -> Dict[str, Any]:
    compact = " ".join((text or "").split())
    low = compact.lower()
    missing = [n if isinstance(n, str) else " / ".join(n) for n in needles if not _group_hit(low, n)]
    if len(compact) < 800:
        return {"status": "unread", "missing": missing}
    if not missing:
        # A portal page can open without containing the cited dollar.
        return {"status": "holds" if schedule else "portal", "missing": []}
    if schedule:
        return {"status": "moved", "missing": missing}
    return {"status": "unread", "missing": missing}


def _bytes_to_text(url: str, data: bytes, content_type: str) -> str:
    is_pdf = (
        data[:5] == b"%PDF-"
        or "pdf" in (content_type or "").lower()
        or url.lower().split("?")[0].endswith(".pdf")
    )
    if is_pdf:
        from io import BytesIO

        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        parts = []
        for page in reader.pages[:40]:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    return data.decode("utf-8", errors="ignore")


def fetch_text(url: str, timeout: int = 25) -> str:
    req = Request(url, headers={"User-Agent": _UA, "Accept": "text/html,application/pdf,*/*"})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read(8_000_000)
        ctype = resp.headers.get("Content-Type") or ""
    return _bytes_to_text(url, data, ctype)


def run_checks(fetch=fetch_text) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for check in CHECKS:
        url = str(check["url"])
        try:
            text = fetch(url)
            judged = judge_text(text, check["needles"], schedule=bool(check["schedule"]))
            status = judged["status"]
            missing = judged["missing"]
        except Exception as e:
            status = "unread"
            missing = [type(e).__name__]
        rows.append(
            {
                "city": check["city"],
                "url": url,
                "schedule": bool(check["schedule"]),
                "status": status,
                "missing": missing,
            }
        )
    return rows


if __name__ == "__main__":
    print(json.dumps(run_checks(), indent=2))
