"""Plain-text helpers for RegGuard PDF generation (strip markdown, ASCII-safe)."""

from __future__ import annotations

import re
from typing import Any, List
from urllib.parse import urlparse


def ascii_safe(text: Any, limit: int = 2000) -> str:
    s = str(text or "")
    replacements = {
        "\u2022": "-",
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
        "\u2713": "[x]",
        "\u00a9": "(c)",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    s = s.encode("latin-1", errors="replace").decode("latin-1")
    return s[:limit]


def markdown_to_plain(text: Any, *, limit: int = 12_000) -> str:
    """Turn action-plan / scout markdown into readable PDF prose."""
    t = str(text or "")
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = t.replace("**", "")
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"^#{1,6}\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"^- \[[ xX]\]\s*", "- ", t, flags=re.MULTILINE)
    t = re.sub(r"^\*\s+", "- ", t, flags=re.MULTILINE)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return ascii_safe(t.strip(), limit)


def markdown_to_bullets(text: Any, *, limit: int = 40) -> List[str]:
    """Split markdown / checklist into short bullet lines for PDF cards."""
    plain = markdown_to_plain(text, limit=20_000)
    lines: List[str] = []
    for raw in plain.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        elif re.match(r"^\d+[\.\)]\s+", line):
            line = re.sub(r"^\d+[\.\)]\s+", "", line).strip()
        if len(line) < 3:
            continue
        lines.append(ascii_safe(line, 320))
        if len(lines) >= limit:
            break
    return lines


def cite_host(url: str = "", *, label: str = "") -> str:
    """Short citation label for punch-list column."""
    lab = (label or "").strip()
    if lab and lab.upper() not in ("SOURCE", "LINK", "UNVERIFIED"):
        return ascii_safe(lab, 28)
    u = (url or "").strip()
    if not u:
        return "Confirm"
    try:
        host = urlparse(u).netloc or ""
        host = host.replace("www.", "")
        return ascii_safe(host or "Cite", 28)
    except Exception:
        return "Cite"
