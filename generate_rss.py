import json
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime, timezone

def prettify(elem):
    rough = tostring(elem, encoding="utf-8")
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent="  ")

# ====================== LOAD JSON ======================
with open("opm_weebcentral.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("📄 Generating RSS from opm_weebcentral.json...")

# ====================== GENERATE RSS ======================
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

# Newest chapters on top
chapters = data.get("chapters", [])
for chap in reversed(chapters):
    item = SubElement(channel, "item")

    chap_num = chap["number"]
    SubElement(item, "title").text = f"Chapter {chap_num}"

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

print("✅ opm.rss generated successfully!")
print(f"Total chapters in feed: {len(chapters)}")
