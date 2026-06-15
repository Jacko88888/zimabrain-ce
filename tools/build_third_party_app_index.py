from pathlib import Path
from urllib.request import urlopen, Request
import csv
import re
import shutil
import zipfile

ROOT = Path("/DATA/AppData/zimabrain-ce-flask-8601")
SRC = ROOT / "docs/app-store/third-party-store-sources.csv"
DL = ROOT / "docs/app-store/downloads"
RAW = ROOT / "docs/app-store/raw"
OUT = ROOT / "docs/app-store/third-party-app-index-raw.csv"
SUMMARY = ROOT / "docs/app-store/third-party-app-index-summary.md"

DL.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

def safe_name(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", s).strip("-")

def read_sources():
    with SRC.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def fetch(url, dest):
    req = Request(url, headers={"User-Agent": "ZimaBrain-CE-AppIndex/1.0"})
    with urlopen(req, timeout=20) as r:
        dest.write_bytes(r.read())

def pick_value(text, keys):
    for key in keys:
        patterns = [
            rf"(?im)^\s*{re.escape(key)}\s*:\s*[\"']?([^\"'\n#]+)",
            rf"(?im)^\s*{re.escape(key)}\s*=\s*[\"']?([^\"'\n#]+)",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return m.group(1).strip()
    return ""

def detect_images(text):
    vals = re.findall(r"(?im)^\s*image\s*:\s*[\"']?([^\"'\n#]+)", text)
    return "; ".join(sorted(set(v.strip() for v in vals if v.strip()))[:5])

def detect_ports(text):
    vals = re.findall(r"(?im)^\s*-\s*[\"']?([0-9]{2,5}\s*:\s*[0-9]{2,5}|[0-9]{2,5}/tcp|[0-9]{2,5}/udp)", text)
    return "; ".join(sorted(set(v.replace(" ", "") for v in vals))[:10])

def detect_volumes(text):
    vals = re.findall(r"(?im)^\s*-\s*[\"']?([^\"'\n#]+:[^\"'\n#]+)", text)
    cleaned = []
    for v in vals:
        v = v.strip()
        if "/" in v or "$" in v or ":" in v:
            cleaned.append(v)
    return "; ".join(sorted(set(cleaned))[:10])

def risk_flags(text):
    low = text.lower()
    flags = []
    if "docker.sock" in low:
        flags.append("docker-socket")
    if "privileged: true" in low or "privileged:true" in low:
        flags.append("privileged")
    if "network_mode: host" in low or "network: host" in low:
        flags.append("host-network")
    if "latest" in low:
        flags.append("latest-tag")
    return ";".join(flags)

rows = []
summary = []
summary.append("# Third-party app store raw index")
summary.append("")

for source in read_sources():
    store = source["store_name"]
    url = source["source_url"]
    name = safe_name(store)
    zip_path = DL / f"{name}.zip"
    extract_dir = RAW / name

    try:
        print(f"Fetching {store} ...")
        fetch(url, zip_path)

        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path) as z:
            z.extractall(extract_dir)

        files = []
        for ext in ("*.yml", "*.yaml", "*.json"):
            files.extend(extract_dir.rglob(ext))

        found = 0
        for fp in files:
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            low = text.lower()
            if not any(x in low for x in ["image:", "x-casaos", "services:", "docker-compose", "name:"]):
                continue

            app_name = (
                pick_value(text, ["name", "title", "app_name", "container_name"])
                or fp.parent.name
                or fp.stem
            )

            desc = pick_value(text, ["description", "tagline"])
            category = pick_value(text, ["category", "group"])

            rows.append({
                "app_name": app_name,
                "store_name": store,
                "store_type": source["store_type"],
                "source_url": url,
                "category": category,
                "description": desc,
                "images": detect_images(text),
                "ports": detect_ports(text),
                "volumes": detect_volumes(text),
                "risk_flags": risk_flags(text),
                "manifest_path": str(fp.relative_to(extract_dir)),
            })
            found += 1

        summary.append(f"- {store}: downloaded, candidate manifests indexed: {found}")

    except Exception as e:
        summary.append(f"- {store}: ERROR: {e}")

with OUT.open("w", newline="", encoding="utf-8") as f:
    fields = ["app_name", "store_name", "store_type", "source_url", "category", "description", "images", "ports", "volumes", "risk_flags", "manifest_path"]
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

summary.append("")
summary.append(f"Total indexed candidate app manifests: {len(rows)}")
SUMMARY.write_text("\n".join(summary), encoding="utf-8")

print(f"Wrote: {OUT}")
print(f"Wrote: {SUMMARY}")
print(f"Total rows: {len(rows)}")
