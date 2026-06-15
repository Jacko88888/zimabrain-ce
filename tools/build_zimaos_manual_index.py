#!/usr/bin/env python3
import json
import re
from pathlib import Path

manifest = Path("docs/zimaos-official/manifest.json")
out = Path("docs/zimaos-official/manual-index.json")
mdout = Path("docs/zimaos-official/manual-index.md")

m = json.loads(manifest.read_text())

good = []
seen_titles = set()
seen_urls = set()

bad_patterns = [
    "/index/",
    ".html/index",
    ".html/get-started",
    ".html/how-to-install",
    ".html/features",
    ".html/remote-access",
]

for p in m.get("pages", []):
    if p.get("status") != "ok":
        continue

    url = p.get("url", "")
    title = (p.get("title") or "").strip()
    md = p.get("markdown", "")

    if not title or title.lower() == "none":
        continue

    if any(x in url for x in bad_patterns):
        continue

    key = re.sub(r"\s+", " ", title.lower())
    if key in seen_titles or url in seen_urls:
        continue

    seen_titles.add(key)
    seen_urls.add(url)

    good.append({
        "title": title,
        "url": url,
        "markdown": md,
        "chars": p.get("chars", 0),
    })

good = sorted(good, key=lambda x: x["title"].lower())

out.write_text(json.dumps({
    "source": "ZimaOS Official Docs",
    "clean_page_count": len(good),
    "pages": good,
}, indent=2), encoding="utf-8")

lines = ["# ZimaOS Official Manual Clean Index", "", f"Clean pages: {len(good)}", ""]
for p in good:
    lines.append(f"- {p['title']} | {p['url']} | {p['markdown']}")

mdout.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("Clean pages:", len(good))
print("Written:", out)
print("Written:", mdout)
