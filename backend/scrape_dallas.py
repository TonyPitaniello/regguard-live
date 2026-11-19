"""
Reg Guard — Dallas Open Data / Supabase compliance URL tracking.
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

SCRIPT_DIR = Path(__file__).resolve().parent
CHANGE_LOG_PATH = SCRIPT_DIR / "scrape_changes.log"


def _supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get(
        "SUPABASE_ANON_KEY"
    )
    if not url or not key:
        return None
    from supabase import create_client

    return create_client(url, key)


def _snapshot_path(source: str) -> Path:
    return SCRIPT_DIR / f".last_urls_{source}.json"


def _load_previous_urls(source: str) -> set[str]:
    client = _supabase_client()
    if client:
        res = (
            client.table("scraped_compliance_urls")
            .select("url")
            .eq("source", source)
            .execute()
        )
        return {row["url"] for row in (res.data or [])}
    path = _snapshot_path(source)
    if not path.exists():
        return set()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("urls", []))


def _append_change_log(source: str, added: set[str], removed: set[str]) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"\n{'=' * 60}\n",
        f"{ts} source={source} added={len(added)} removed={len(removed)}\n",
    ]
    for u in sorted(added):
        lines.append(f"  + {u}\n")
    for u in sorted(removed):
        lines.append(f"  - {u}\n")
    text = "".join(lines)
    with open(CHANGE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(text)
    print(text.rstrip())


def sync_urls_to_supabase_and_log(urls: list[str], source: str = "dallas_building") -> None:
    """
    Compares the latest scrape to the last stored set (Supabase if configured,
    else a local JSON snapshot), appends any additions/removals to scrape_changes.log,
    then persists the current URL set.

    Supabase: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY
    with RLS policies that allow read/write).

    Table (example):

        create table scraped_compliance_urls (
          id uuid primary key default gen_random_uuid(),
          source text not null,
          url text not null,
          updated_at timestamptz default now(),
          unique (source, url)
        );
    """
    current = set(urls)
    previous = _load_previous_urls(source)
    added = current - previous
    removed = previous - current

    if added or removed:
        _append_change_log(source, added, removed)
    else:
        print("No URL changes since last run.")

    now = datetime.now(timezone.utc).isoformat()
    client = _supabase_client()

    if client:
        rows = [{"source": source, "url": u, "updated_at": now} for u in current]
        if rows:
            client.table("scraped_compliance_urls").upsert(
                rows, on_conflict="source,url"
            ).execute()
            for u in removed:
                client.table("scraped_compliance_urls").delete().eq(
                    "source", source
                ).eq("url", u).execute()
        else:
            client.table("scraped_compliance_urls").delete().eq(
                "source", source
            ).execute()
    else:
        path = _snapshot_path(source)
        first_snapshot = not path.exists()
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"urls": sorted(current), "updated_at": now}, f, indent=2)
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get(
            "SUPABASE_ANON_KEY"
        )
        if first_snapshot and (not url or not key):
            print(
                "Supabase not configured; using local snapshot "
                f"{path.name}. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
                "(or SUPABASE_ANON_KEY) to sync to the database."
            )


async def scrape_dallas():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0")
        page = await context.new_page()

        # 1. Scrape Plumbing & Mechanical Permits
        print("Scraping Dallas Plumbing/Mechanical Permits...")
        await page.goto(
            "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/Pages/plumbing_mechanical.aspx"
        )

        # Extract specific headers for adopted codes (IPC, IMC)
        codes = await page.locator("h3, strong").all_text_contents()
        relevant_codes = [c for c in codes if "2021" in c]

        # 2. Search for Code Amendments (Simulating user search)
        print("Searching for 2021 Code Amendments...")
        await page.goto(
            "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/DCH%20documents/feesummary_725.pdf"
        )
        # Note: Dallas site uses specific search containers; we look for PDF buttons
        amendment_links = await page.locator(
            "a:has-text('Amendment'), a:has-text('2021')"
        ).all()

        dallas_pdfs = []
        for link in amendment_links:
            href = await link.get_attribute("href")
            if href and ".pdf" in href.lower():
                dallas_pdfs.append(href)

        print(f"Adopted Codes Found: {relevant_codes}")
        print(f"Amendment PDFs Found: {len(dallas_pdfs)}")

        await browser.close()
        return dallas_pdfs


async def main():
    pdfs = await scrape_dallas()
    sync_urls_to_supabase_and_log(pdfs, source="dallas_building")


if __name__ == "__main__":
    asyncio.run(main())
