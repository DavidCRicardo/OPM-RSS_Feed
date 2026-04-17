"""
generate_rss.py

Reads opm.json (produced by scrape_weebcentral.py) and generates opm.rss.
"""

import json
import html
from datetime import datetime, timezone
from pathlib import Path
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

INPUT_FILE = Path(__file__).parent / "opm.json"
OUTPUT_FILE = Path(__file__).parent / "opm.rss"

SERIES_URL = "https://weebcentral.com/series/01J76XY7KT7J224EBK6J816Y1Q/Onepunch-Man"
RSS_SELF_LINK = "https://raw.githubusercontent.com/DavidCRicardo/OPM-RSS_Feed/main/opm.rss"


def prettify(elem: Element) -> str:
    """Return a pretty-printed XML string for the given Element."""
    rough = tostring(elem, encoding="utf-8")
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent="  ")


def parse_pub_date(release_date: str, last_updated: int) -> str:
    """
    Convert a release_date string ('YYYY-MM-DD') or last_updated Unix timestamp
    to RFC 2822 format for use in <pubDate>.
    """
    try:
        dt = datetime.strptime(release_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
    except (ValueError, TypeError):
        pass
    try:
        dt = datetime.fromtimestamp(last_updated, tz=timezone.utc)
        return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
    except Exception:
        return "Thu, 01 Jan 1970 00:00:00 GMT"


def build_description(chap_num: str, chap: dict) -> str:
    """Build the HTML description block for an RSS <item>."""
    parts = []

    cover = chap.get("cover_image")
    if cover:
        parts.append(f'<img src="{html.escape(cover)}" alt="Chapter {html.escape(chap_num)} cover" />')

    volume = chap.get("volume")
    if volume:
        parts.append(f"<strong>Volume:</strong> {html.escape(str(volume))}<br/>")

    pages = chap.get("pages")
    if pages:
        parts.append(f"<strong>Pages:</strong> {html.escape(str(pages))}<br/>")

    release_date = chap.get("release_date")
    if release_date:
        parts.append(f"<strong>Updated:</strong> {html.escape(release_date)}<br/>")

    url = chap.get("url", "")
    if url:
        parts.append(f'<a href="{html.escape(url)}">Read on WeebCentral</a>')

    return "\n".join(parts)


def chapters_to_rss(chapters: dict) -> str:
    """Build the full RSS 2.0 XML string from the chapters dict."""
    rss = Element("rss", {"version": "2.0"})
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")

    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = "One Punch Man"
    SubElement(channel, "link").text = SERIES_URL
    SubElement(channel, "description").text = "One Punch Man chapters - sourced from WeebCentral"
    SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )

    atom_link = SubElement(channel, "atom:link")
    atom_link.set("rel", "self")
    atom_link.set("href", RSS_SELF_LINK)
    atom_link.set("type", "application/rss+xml")

    # Sort newest-first by chapter number (handles decimals like 15.5)
    sorted_chapters = sorted(chapters.items(), key=lambda x: float(x[0]), reverse=True)

    for chap_num, chap in sorted_chapters:
        item = SubElement(channel, "item")

        title_text = chap.get("title", f"Chapter {chap_num}")
        SubElement(item, "title").text = f"Ch. {chap_num}: {title_text}"

        chapter_url = chap.get("url", SERIES_URL)
        SubElement(item, "link").text = chapter_url

        description_html = build_description(chap_num, chap)
        SubElement(item, "description").text = description_html

        release_date = chap.get("release_date", "")
        last_updated = chap.get("last_updated", 0)
        SubElement(item, "pubDate").text = parse_pub_date(release_date, last_updated)

        guid = SubElement(item, "guid")
        guid.set("isPermaLink", "false")
        guid.text = f"opm-{chap_num}"

    return prettify(rss)


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"{INPUT_FILE} not found. Run scrape_weebcentral.py first."
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    chapters = data.get("chapters", {})
    if not chapters:
        raise ValueError("opm.json contains no chapters.")

    print(f"Loaded {len(chapters)} chapters from {INPUT_FILE}")

    rss_content = chapters_to_rss(chapters)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(rss_content)

    print(f"RSS feed written to {OUTPUT_FILE} ({len(rss_content)} bytes)")


if __name__ == "__main__":
    main()
