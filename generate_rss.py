from weeb_central import Weeb, Manga, NetworkError, ParsingError
import json
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime, timezone
import os

# ====================== PRETTIFY ======================
def prettify(elem):
    rough = tostring(elem, encoding="utf-8")
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent="  ")

# ====================== MAIN ======================
print("🔄 Starting One Punch Man RSS generation from WeebCentral...")

weeb = Weeb()

try:
    # Search and get the manga
    search_results = weeb.search(query="One Punch Man")
    if not search_results:
        print("❌ No results found.")
        exit(1)

    my_manga = search_results[0]
    print(f"✅ Found: {my_manga.title}")

    print("📚 Fetching full chapter list...")
    all_chapters = list(my_manga.get_chapters())

    print(f"Total chapters found: {len(all_chapters)}")

    # Build chapter list
    chapters_list = []
    for chapter in all_chapters:
        # Get first image as cover
        try:
            pages = chapter.get_pages()
            first_image = pages[0].url if pages and hasattr(pages[0], 'url') else ""
        except:
            first_image = ""

        chapters_list.append({
            "number": chapter.index,
            "title": getattr(chapter, 'title', None) or f"Chapter {chapter.index}",
            "url": chapter.url,
            "date": getattr(chapter, 'date', None),
            "first_image": first_image
        })

    # Save JSON for reference / future use
    data = {
        "title": my_manga.title,
        "source": "https://weebcentral.com/series/01J76XY7KT7J224EBK6J816Y1Q/Onepunch-Man",
        "last_updated": datetime.now().isoformat(),
        "total_chapters": len(chapters_list),
        "chapters": chapters_list
    }

    with open("opm_weebcentral.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("📄 Saved chapter data to opm_weebcentral.json")

    # ====================== GENERATE RSS ======================
    rss = Element("rss", {"version": "2.0"})
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")

    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = "One Punch Man (WeebCentral)"
    SubElement(channel, "link").text = "https://weebcentral.com/series/01J76XY7KT7J224EBK6J816Y1Q/Onepunch-Man"
    SubElement(channel, "description").text = "One Punch Man chapters with cover images"
    SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    atom_link = SubElement(channel, "atom:link")
    atom_link.set("rel", "self")
    atom_link.set("href", "https://raw.githubusercontent.com/DavidCRicardo/OPM-RSS_Feed/main/opm.rss")
    atom_link.set("type", "application/rss+xml")

    # Newest chapters on top
    for chap in reversed(chapters_list):
        item = SubElement(channel, "item")

        # Title format: "Chapter X - Title"
        title_text = f"Chapter {chap['number']} - {chap['title']}"
        SubElement(item, "title").text = title_text

        SubElement(item, "link").text = chap["url"]

        first_image = chap.get("first_image", "")

        html = f"""
<img src="{first_image}" alt="Chapter cover" style="max-width:100%; height:auto; display:block; margin:0 auto 15px;" />
<strong>Chapter:</strong> {chap['number']}<br/>
<strong>Updated:</strong> {chap.get('date') or 'Unknown'}<br/><br/>
<a href="{chap['url']}">🔗 Open full chapter on WeebCentral</a>
        """.strip()

        desc = SubElement(item, "description")
        desc.text = html

        guid = SubElement(item, "guid")
        guid.set("isPermaLink", "false")
        guid.text = f"opm-weeb-{chap['number']}"

    rss_output = prettify(rss)
    with open("opm.rss", "w", encoding="utf-8") as f:
        f.write(rss_output)

    print("✅ opm.rss generated successfully!")
    print(f"Total chapters: {len(chapters_list)}")

except Exception as e:
    print(f"❌ Error: {e}")
