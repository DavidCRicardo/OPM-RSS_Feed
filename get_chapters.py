from weeb_central import Weeb, NetworkError, ParsingError
import json
from datetime import datetime
import os

print("🔄 Fetching One Punch Man chapters from WeebCentral...")

weeb = Weeb()

try:
    search_results = weeb.search(query="One Punch Man")
    if not search_results:
        print("❌ No results found.")
        exit(1)

    my_manga = search_results[0]
    print(f"✅ Found: {my_manga.title}")

    print("📚 Fetching full chapter list...")
    all_chapters = list(my_manga.get_chapters())

    print(f"Total chapters found: {len(all_chapters)}")

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
            "title": f"Chapter {chapter.index}",
            "url": chapter.url,
            "date": getattr(chapter, 'date', None),
            "first_image": first_image
        })

    # Save JSON
    data = {
        "title": my_manga.title,
        "source": "https://weebcentral.com/series/01J76XY7KT7J224EBK6J816Y1Q/Onepunch-Man",
        "last_updated": datetime.now().isoformat(),
        "total_chapters": len(chapters_list),
        "chapters": chapters_list
    }

    with open("opm_weebcentral.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ opm_weebcentral.json updated successfully!")
    print(f"Total chapters saved: {len(chapters_list)}")

except Exception as e:
    print(f"❌ Error: {e}")
