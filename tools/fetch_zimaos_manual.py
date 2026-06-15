#!/usr/bin/env python3
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlparse, urldefrag
from pathlib import Path
import json
import re
import time

BASE = "https://www.zimaspace.com/docs/zimaos/"
START_URLS = [
    "https://www.zimaspace.com/docs/zimaos/",
    "https://www.zimaspace.com/docs/zimaos/index",
    "https://www.zimaspace.com/docs/zimaos/User-Guide",
]

OUT = Path("docs/zimaos-official")
RAW = OUT / "raw"
PAGES = OUT / "pages"
MANIFEST = OUT / "manifest.json"

RAW.mkdir(parents=True, exist_ok=True)
PAGES.mkdir(parents=True, exist_ok=True)

class LinkTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.text = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1
            return
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs.get("href"))
        if tag in ("h1", "h2", "h3", "h4"):
            self.text.append("\n\n")
        if tag in ("p", "li", "br", "div", "section", "article"):
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.skip:
            self.skip -= 1
        if tag in ("h1", "h2", "h3", "h4", "p", "li"):
            self.text.append("\n")

    def handle_data(self, data):
        if self.skip:
            return
        data = data.strip()
        if data:
            self.text.append(data + " ")

def fetch(url):
    req = Request(url, headers={"User-Agent": "ZimaBrainCE-ManualFetcher/1.0"})
    with urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")

def clean_url(url):
    url, _ = urldefrag(url)
    return url.rstrip("/")

def allowed(url):
    p = urlparse(url)
    return p.scheme in ("http", "https") and p.netloc == "www.zimaspace.com" and p.path.startswith("/docs/zimaos")

def slug_for(url):
    p = urlparse(url).path.strip("/").replace("/", "__")
    p = re.sub(r"[^A-Za-z0-9_.-]+", "_", p)
    return p or "index"

def clean_text(text):
    text = "\n".join(line.strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()

seen = set()
queue = [clean_url(u) for u in START_URLS]
pages = []

while queue and len(seen) < 250:
    url = clean_url(queue.pop(0))
    if url in seen or not allowed(url):
        continue

    print("FETCH", url)
    seen.add(url)

    try:
        html = fetch(url)
    except Exception as e:
        pages.append({"url": url, "status": "error", "error": str(e)})
        continue

    parser = LinkTextParser()
    parser.feed(html)

    slug = slug_for(url)
    raw_path = RAW / f"{slug}.html"
    md_path = PAGES / f"{slug}.md"

    raw_path.write_text(html, encoding="utf-8")

    text = clean_text("".join(parser.text))
    title = text.splitlines()[0] if text.splitlines() else slug

    md = f"# {title}\n\nSource: {url}\n\n{text}\n"
    md_path.write_text(md, encoding="utf-8")

    pages.append({
        "url": url,
        "title": title,
        "raw": str(raw_path),
        "markdown": str(md_path),
        "chars": len(text),
        "status": "ok",
    })

    for href in parser.links:
        nxt = clean_url(urljoin(url + "/", href))
        if allowed(nxt) and nxt not in seen and nxt not in queue:
            queue.append(nxt)

    time.sleep(0.25)

MANIFEST.write_text(json.dumps({
    "base": BASE,
    "page_count": len([p for p in pages if p.get("status") == "ok"]),
    "error_count": len([p for p in pages if p.get("status") == "error"]),
    "pages": pages,
}, indent=2), encoding="utf-8")

print("")
print("DONE")
print("Pages saved:", len([p for p in pages if p.get("status") == "ok"]))
print("Errors:", len([p for p in pages if p.get("status") == "error"]))
print("Manifest:", MANIFEST)
