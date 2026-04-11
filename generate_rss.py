import json
import requests
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime, timezone

def prettify(elem):
    rough = tostring(elem, encoding="utf-8")
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent="  ")

def json_to_rss(json_data: dict) -> str:
    rss = Element("rss", {"version": "2.0"})
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")

    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = "One Punch Man (WeebCentral)"
    SubElement(channel, "link").text = "https://weebcentral.com/series/01J76XY7KT7J224EBK6J816Y1Q/Onepunch-Man"
    SubElement(channel, "description").text = "One Punch Man chapters with cover images"
    SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Self link
    atom_link = SubElement(channel, "atom:link")
    atom_link.set("rel", "self")
    atom_link.set("href", "https://raw.githubusercontent.com/DavidCRicardo/OPM-RSS_Feed/main/opm.rss")
    atom_link.set("type", "application/rss+xml")

    weeb_central_base = "https://weebcentral.com/series/01J76XY7KT7J224EBK6J816Y1Q/Onepunch-Man/"
    #weeb_central_base = "https://weebcentral.com/chapters"

    chapters = json_data.get("chapters", {})
    sorted_chapters = sorted(chapters.items(), key=lambda x: float(x[0]), reverse=True)

    for chap_num, chap_data in sorted_chapters:
        item = SubElement(channel, "item")

        title_text = chap_data.get('title', f"Chapter {chap_num}")
        SubElement(item, "title").text = title_text

        slug = chap_num.replace('.', '-')
        chapter_url = f"{weeb_central_base}{slug}/1/"
        SubElement(item, "link").text = chapter_url

        # First image
        first_image = ""
        groups = chap_data.get("groups", {})
        if groups:
            urls = next(iter(groups.values()), [])
            if urls:
                first_image = urls[0]

        num_pages = len(next(iter(groups.values()), [])) if groups else 0
        updated_date = datetime.fromtimestamp(
            chap_data.get('last_updated', 0), tz=timezone.utc
        ).strftime('%Y-%m-%d')

        html = f"""
<img src="{first_image}" alt="Chapter {chap_num} cover" />
<strong>Volume:</strong> {chap_data.get('volume', 'N/A')}<br/>
<strong>Pages:</strong> {num_pages}<br/>
<strong>Updated:</strong> {updated_date}<br/><br/>
<a href="{chapter_url}">🔗 Open full chapter in Cubari reader</a>
        """.strip()

        desc = SubElement(item, "description")
        desc.text = html 

        # PubDate + GUID
        if isinstance(chap_data.get("last_updated"), (int, float)):
            dt = datetime.fromtimestamp(chap_data["last_updated"], tz=timezone.utc)
            SubElement(item, "pubDate").text = dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

        guid = SubElement(item, "guid")
        guid.set("isPermaLink", "false")
        guid.text = f"opm-{chap_num}"

    return prettify(rss)


# ====================== GIST ======================
url = "https://gist.githubusercontent.com/funkyhippo/1d40bd5dae11e03a6af20e5a9a030d81/raw/opm.json"
response = requests.get(url)
response.raise_for_status()
data = response.json()

rss_output = json_to_rss(data)

with open("opm.rss", "w", encoding="utf-8") as f:
    f.write(rss_output)
    
print("✅ RSS generated from your Gist")
