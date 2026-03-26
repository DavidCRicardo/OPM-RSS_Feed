import json
import requests
from xml.dom.minidom import Document
from datetime import datetime, timezone

def json_to_rss(json_data: dict) -> str:
    doc = Document()
    rss = doc.createElement("rss")
    rss.setAttribute("version", "2.0")
    rss.setAttribute("xmlns:atom", "http://www.w3.org/2005/Atom")
    doc.appendChild(rss)

    channel = doc.createElement("channel")
    rss.appendChild(channel)

    for tag, text in [
        ("title", "One Punch Man (Cubari Reader)"),
        ("link", "https://cubari.moe/read/gist/Z2lzdC9mdW5reWhpcHBvLzFkNDBiZDVkYWUxMWUwM2E2YWYyMGU1YTlhMDMwZDgxL3Jhdy9vcG0uanNvbg/"),
        ("description", "One Punch Man chapters"),
        ("lastBuildDate", datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")),
    ]:
        elem = doc.createElement(tag)
        elem.appendChild(doc.createTextNode(text))
        channel.appendChild(elem)

    atom_link = doc.createElementNS("http://www.w3.org/2005/Atom", "atom:link")
    atom_link.setAttribute("rel", "self")
    atom_link.setAttribute("href", "https://raw.githubusercontent.com/DavidCRicardo/OPM-RSS_Feed/main/opm.rss")
    atom_link.setAttribute("type", "application/rss+xml")
    channel.appendChild(atom_link)
    
    cubari_base = "https://cubari.moe/read/gist/Z2lzdC9mdW5reWhpcHBvLzFkNDBiZDVkYWUxMWUwM2E2YWYyMGU1YTlhMDMwZDgxL3Jhdy9vcG0uanNvbg/"

    chapters = json_data.get("chapters", {})
    def num_key(item):
        try:
            return float(item[0])
        except:
            return 0

    sorted_chapters = sorted(chapters.items(), key=num_key, reverse=True)

    for chap_num, chap_data in sorted_chapters:
        item = doc.createElement("item")
        channel.appendChild(item)

        title = doc.createElement("title")
        title.appendChild(doc.createTextNode(f"Chapter {chap_num}: {chap_data.get('title', 'Untitled')}"))
        item.appendChild(title)

        slug = chap_num.replace('.', '-')
        chapter_url = f"{cubari_base}{slug}/1/"
        link_elem = doc.createElement("link")
        link_elem.appendChild(doc.createTextNode(chapter_url))
        item.appendChild(link_elem)

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
        <img src="{first_image}" alt="Chapter cover goes here. But something went wrong :("/>
        <strong>Volume:</strong> {chap_data.get('volume', 'N/A')}<br/>
        <strong>Pages:</strong> {num_pages}<br/>
        <strong>Updated:</strong> {updated_date}<br/><br/>
        <a href="{chapter_url}">🔗 Open full chapter in Cubari reader</a>
        """.strip()

        desc = doc.createElement("description")
        desc.appendChild(doc.createCDATASection(html))
        item.appendChild(desc)

        if isinstance(chap_data.get("last_updated"), (int, float)):
            dt = datetime.fromtimestamp(chap_data["last_updated"], tz=timezone.utc)
            pubdate = doc.createElement("pubDate")
            pubdate.appendChild(doc.createTextNode(dt.strftime("%a, %d %b %Y %H:%M:%S GMT")))
            item.appendChild(pubdate)

        guid = doc.createElement("guid")
        guid.setAttribute("isPermaLink", "false")
        guid.appendChild(doc.createTextNode(f"opm-{chap_num}"))
        item.appendChild(guid)

    return doc.toprettyxml(indent="  ")

# ====================== GIST ======================
url = "https://gist.githubusercontent.com/funkyhippo/1d40bd5dae11e03a6af20e5a9a030d81/raw/opm.json"

response = requests.get(url)
response.raise_for_status()
data = response.json()

rss_output = json_to_rss(data)

with open("opm.rss", "w", encoding="utf-8") as f:
    f.write(rss_output)

print("✅ RSS generated from your Gist")
