"""
scrape_weebcentral.py

Scrapes WeebCentral for all OPM chapters and produces opm.json.
Run this before generate_rss.py.

Output structure (opm.json):
{
  "chapters": {
    "228": {
      "title": "Mag Version 228",
      "volume": null,
      "pages": 15,
      "release_date": "2026-04-08",
      "last_updated": 1744156871,
      "cover_image": "https://...",
      "url": "https://weebcentral.com/chapters/..."
    },
    ...
  }
}
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, BrowserContext

SERIES_ID = "01J76XY7KT7J224EBK6J816Y1Q"
CHAPTER_LIST_URL = f"https://weebcentral.com/series/{SERIES_ID}/full-chapter-list"
OUTPUT_FILE = Path(__file__).parent / "opm.json"
REQUEST_DELAY = 0.5  # seconds between chapter detail requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def parse_chapter_number(title: str) -> str | None:
    """
    Extract chapter number from titles like:
      'Punch 15', 'Punch 15.5', 'Official Scans 218', 'Mag Version 228',
      'ReDraw 224.5'
    Returns the number as a string (e.g. '15', '15.5', '218').
    """
    # Match trailing number (possibly decimal)
    m = re.search(r"(\d+(?:\.\d+)?)$", title.strip())
    if m:
        num = m.group(1)
        # Normalise: if it ends in .0 keep as integer string
        if num.endswith(".0"):
            return num[:-2]
        return num
    return None


def parse_release_date(iso_string: str) -> tuple[str, int]:
    """
    Convert ISO 8601 datetime string (e.g. '2026-04-08T23:41:11.597327Z')
    to ('2026-04-08', unix_timestamp).
    """
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
        timestamp = int(dt.timestamp())
        return date_str, timestamp
    except Exception:
        return "1970-01-01", 0


def fetch_html(ctx: BrowserContext, url: str, wait_until: str = "domcontentloaded") -> str:
    """Fetch a URL using a Playwright browser page and return the rendered HTML."""
    page = ctx.new_page()
    try:
        page.goto(url, wait_until=wait_until, timeout=30000)
        return page.content()
    finally:
        page.close()


def fetch_chapter_list(ctx: BrowserContext) -> list[dict]:
    """
    Fetch the full chapter list page and return a list of dicts:
      {chapter_number, title, release_date, last_updated, url}
    """
    print(f"Fetching chapter list from {CHAPTER_LIST_URL} ...")
    soup = BeautifulSoup(fetch_html(ctx, CHAPTER_LIST_URL, wait_until="networkidle"), "lxml")

    chapters = []
    seen_numbers = set()

    # Every chapter link is an <a href="https://weebcentral.com/chapters/...">
    # Its parent div has x-data="{ new_chapter: checkNewChapter('ISO_DATE') }"
    # span[2] (0-indexed) inside the <a> contains the display title
    # <time> element inside the <a> contains the ISO date string

    links = soup.find_all("a", href=True)
    for a in links:
        href = a.get("href", "")
        if "/chapters/" not in href:
            continue

        # Extract title from the text spans
        spans = a.find_all("span")
        if len(spans) < 3:
            continue
        title = spans[2].get_text(strip=True)

        chapter_num = parse_chapter_number(title)
        if chapter_num is None:
            print(f"  WARNING: could not parse chapter number from title {repr(title)}, skipping")
            continue

        # Skip duplicates (shouldn't happen, but guard anyway)
        if chapter_num in seen_numbers:
            continue
        seen_numbers.add(chapter_num)

        # Get date from <time> element inside this link
        time_el = a.find("time")
        if time_el:
            iso_date = time_el.get_text(strip=True)
        else:
            # Fallback: parse from parent x-data attribute
            parent = a.parent
            x_data = parent.get("x-data", "") if parent else ""
            m = re.search(r"checkNewChapter\('([^']+)'\)", x_data)
            iso_date = m.group(1) if m else "1970-01-01T00:00:00Z"

        release_date, last_updated = parse_release_date(iso_date)

        chapters.append({
            "chapter_number": chapter_num,
            "title": title,
            "release_date": release_date,
            "last_updated": last_updated,
            "url": href,
        })

    print(f"  Found {len(chapters)} chapters in listing.")
    return chapters


def fetch_chapter_details(ctx: BrowserContext, chapter_url: str) -> dict:
    """
    Fetch an individual chapter page and extract:
      - cover_image (first page, from <link rel='preload'> or og:image)
      - pages (count of page-number buttons)
      - volume (always null — not exposed on the page)
    """
    details = {"cover_image": None, "pages": None, "volume": None}
    try:
        soup = BeautifulSoup(fetch_html(ctx, chapter_url), "lxml")

        # Cover image: prefer <link rel="preload"> (actual first manga page)
        preload = soup.find("link", rel="preload", href=True)
        if preload:
            details["cover_image"] = preload["href"]
        else:
            # Fallback: og:image (series cover thumbnail)
            og = soup.find("meta", property="og:image")
            if og:
                details["cover_image"] = og.get("content")

        # Page count: count the page-number buttons in the page-select modal
        page_buttons = soup.find_all("button", string=re.compile(r"^\d+$"))
        page_nums = [
            int(b.get_text(strip=True))
            for b in page_buttons
            if b.get_text(strip=True).isdigit()
        ]
        if page_nums:
            details["pages"] = max(page_nums)

    except Exception as exc:
        print(f"    WARNING: could not fetch details for {chapter_url}: {exc}")

    return details


def load_existing_json() -> dict:
    """Load opm.json if it exists, otherwise return empty structure."""
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"Loaded existing opm.json with {len(data.get('chapters', {}))} chapters.")
            return data
        except Exception as exc:
            print(f"WARNING: could not load existing opm.json ({exc}), starting fresh.")
    return {"chapters": {}}


def save_json(data: dict) -> None:
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main() -> None:
    # 1. Load existing data
    existing = load_existing_json()
    chapters_db = existing.get("chapters", {})

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=USER_AGENT)

        # 2. Fetch the full chapter listing
        listing = fetch_chapter_list(ctx)

        # 3. Identify chapters that need detail fetching
        new_chapters = [ch for ch in listing if ch["chapter_number"] not in chapters_db]
        print(f"{len(new_chapters)} new chapter(s) need detail fetching.")

        # 4. Fetch details for new chapters
        for i, ch in enumerate(new_chapters, 1):
            num = ch["chapter_number"]
            print(f"  [{i}/{len(new_chapters)}] Fetching details for Ch. {num}: {ch['title']} ...")
            details = fetch_chapter_details(ctx, ch["url"])
            chapters_db[num] = {
                "title": ch["title"],
                "volume": details["volume"],
                "pages": details["pages"],
                "release_date": ch["release_date"],
                "last_updated": ch["last_updated"],
                "cover_image": details["cover_image"],
                "url": ch["url"],
            }
            # Save incrementally so a crash doesn't lose progress
            save_json({"chapters": chapters_db})
            if i < len(new_chapters):
                time.sleep(REQUEST_DELAY)

        browser.close()

    # 5. Also update release_date / last_updated for existing chapters
    #    (in case WeebCentral updated a timestamp), but keep existing details.
    updates = 0
    for ch in listing:
        num = ch["chapter_number"]
        if num in chapters_db:
            entry = chapters_db[num]
            if (
                entry.get("release_date") != ch["release_date"]
                or entry.get("last_updated") != ch["last_updated"]
                or entry.get("url") != ch["url"]
            ):
                entry["release_date"] = ch["release_date"]
                entry["last_updated"] = ch["last_updated"]
                entry["url"] = ch["url"]
                entry["title"] = ch["title"]
                updates += 1

    if updates:
        print(f"Updated metadata for {updates} existing chapter(s).")
        save_json({"chapters": chapters_db})

    print(f"\nDone. opm.json contains {len(chapters_db)} chapters.")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
