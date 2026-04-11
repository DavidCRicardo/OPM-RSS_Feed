from weeb import Weeb, Manga, NetworkError, ParsingError
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
print("🔄 Starting update...")

weeb = Weeb()

try:
    # 1. Search
    search_results = weeb.search(query="One Punch Man")
    if not search_results:
        print("❌ No results found.")
        exit(1)

    my_manga = search_results[0]
    print(f"✅ Found: {my_manga.title}")

    # 2. Load existing JSON (if exists)
    existing_chapters = {}
    if os.path.exists("opm_weebcentral.json"):
        with open("opm_weebcentral.json", "r", encoding="utf-8") as f:
            old_data = json.load(f)
            existing_chapters = {ch["number"]: ch for ch in old_data.get("chapters", [])}
        print(f"Loaded {len(existing_chapters)} existing chapters from JSON")

    # 3. Fetch current full list from WeebCentral
    print("📚 Fetching current chapter list from WeebCentral...")
    all_chapters = list(my_manga.get_chapters())

    print(f"Total chapters currently on WeebCentral: {len(all_chapters)}")

    # 4. Add only NEW chapters
    new_chapters_added = 0
    chapters_list = list(existing_chapters.values())

    for chapter in all_chapters:
        chap_num = chapter.index
        if chap_num not in existing_chapters:
            # New chapter!
            try:
                pages = chapter.get_pages()
                first_image = pages[0].url if pages and hasattr(pages[0], 'url') else ""
            except:
                first_image = ""

            new_chap = {
                "number": chap_num,
                "title": f"Chapter {chap_num}",
                "url": chapter.url,
                "date": getattr(chapter, 'date', None),
                "first_image": first_image
            }
            chapters_list.append(new_chap)
            new_chapters_added += 1

    # Sort by chapter number (newest last)
    chapters_list.sort(key=lambda x: float(x["number"]))
    
    # 5. Save updated JSON
    data = {
        "title": my_manga.title,
        "source": "https://weebcentral.com/series/01J76XY7KT7J224EBK6J816Y1Q/Onepunch-Man",
        "last_updated": datetime.now().isoformat(),
        "total_chapters": len(chapters_list),
        "chapters": chapters_list
    }

    with open("opm_weebcentral.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated JSON — {new_chapters_added} new chapter(s) added!")

    # 6. Generate RSS
    rss = Element("rss", {"version": "2.0"})
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = "One Punch Man (WeebCentral)"
    SubElement(channel, "link").text = data["source"]
    SubElement(channel, "description").text = "One Punch Man chapters with cover images"
    SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    atom_link = SubElement(channel, "atom:link")
    atom_link.set("rel", "self")
    atom_link.set("href", "https://raw.githubusercontent.com/DavidCRicardo/OPM-RSS_Feed/main/opm.rss")
    atom_link.set("type", "application/rss+xml")

    for chap in chapters_list:
        item = SubElement(channel, "item")
        chap_num = chap["number"]
        SubElement(item, "title").text = f"{chap['title']}"
        SubElement(item, "link").text = chap["url"]

        first_image = chap.get("first_image", "")
        html = f"""
<img src="{first_image}" alt="Chapter cover" style="max-width:100%; height:auto; display:block; margin:0 auto 15px;" />
<strong>Chapter:</strong> {chap_num}<br/>
<strong>Updated:</strong> {chap.get('date') or 'Unknown'}<br/><br/>
<a href="{chap['url']}">🔗 Open full chapter on WeebCentral</a>
        """.strip()

        desc = SubElement(item, "description")
        desc.text = html

        guid = SubElement(item, "guid")
        guid.set("isPermaLink", "false")
        guid.text = f"opm-weeb-{chap_num}"

    rss_output = prettify(rss)
    with open("opm.rss", "w", encoding="utf-8") as f:
        f.write(rss_output)

    print("✅ opm.rss updated successfully!")
    print(f"Total chapters in feed: {len(chapters_list)}")

except Exception as e:
    print(f"❌ Error: {e}")
