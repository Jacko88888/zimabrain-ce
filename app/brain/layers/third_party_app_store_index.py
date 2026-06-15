from pathlib import Path
import csv
import re

ROOT = Path("/data")
INDEX_PATHS = [
    ROOT / "docs/app-store/third-party-app-index-raw.csv",
    Path("/DATA/AppData/zimabrain-ce-flask-8601/docs/app-store/third-party-app-index-raw.csv"),
]

RISK_EXPLAIN = {
    "docker-socket": "Can control Docker. Keep private and do not expose publicly.",
    "host-network": "Uses host networking. Check port conflicts and LAN exposure.",
    "latest-tag": "Uses latest tag. Version may change after update/redeploy.",
    "privileged": "Runs privileged. Higher host access risk.",
}


def _index_path():
    for p in INDEX_PATHS:
        if p.exists():
            return p
    return INDEX_PATHS[0]


def _load_rows():
    p = _index_path()
    if not p.exists():
        return []

    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _normalise(text):
    text = (text or "").lower()
    text = text.replace("clouflare", "cloudflare")
    text = text.replace("cloudfare", "cloudflare")
    text = text.replace("cloudflair", "cloudflare")
    text = text.replace("clodflare", "cloudflare")
    text = text.replace("_", " ").replace("-", " ").replace(".", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _question_terms(question):
    q = _normalise(question)

    stop = {
        "how", "do", "i", "install", "setup", "set", "up", "configure",
        "on", "zimaos", "zima", "app", "apps", "store", "is", "the",
        "can", "use", "what", "risk", "risks", "does", "have"
    }

    words = [w for w in q.split() if w not in stop and len(w) > 2]
    phrases = []

    # Keep common multi-word app names.
    for phrase in [
        "home assistant", "open webui", "cloudflare tunnel", "borg web ui",
        "code server", "calibre web", "actual budget", "paperless ngx"
    ]:
        if phrase in q:
            phrases.append(phrase)

    return phrases + words


def search_apps(question, limit=8):
    rows = _load_rows()
    terms = _question_terms(question)

    if not terms:
        return []

    scored = []
    for row in rows:
        app_name = row.get("app_name", "")
        hay = _normalise(" ".join([
            row.get("app_name", ""),
            row.get("description", ""),
            row.get("images", ""),
            row.get("store_name", ""),
        ]))

        score = 0
        for term in terms:
            t = _normalise(term)
            if not t:
                continue
            app_norm = _normalise(app_name)
            if app_norm == t:
                score += 100
            elif t in app_norm:
                score += 55
            elif t in hay:
                score += 20

        if score:
            scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for score, row in scored[:limit]]


def _clean_volume_preview(volumes):
    parts = []
    for raw in (volumes or "").split(";"):
        item = raw.strip()
        low = item.lower()

        if not item:
            continue
        if "http://" in low or "https://" in low or "screenshot" in low:
            continue
        if item.startswith("container:") and "/" not in item and "docker.sock" not in low:
            continue
        if item.startswith("target:") and "/" not in item:
            continue

        if "/" in item or "docker.sock" in low or ":" in item:
            parts.append(item)

    cleaned = []
    for item in parts:
        if item not in cleaned:
            cleaned.append(item)

    return "; ".join(cleaned[:5])


def _find_local_container_evidence(bundle, matches, question=""):
    evidence = bundle.get("same_report_evidence", {}) if isinstance(bundle, dict) else {}
    docker_ps = evidence.get("docker_ps", "") or ""
    docker_access = evidence.get("docker_access", "") or ""

    # Use the actual app terms from the question first.
    # This prevents Portainer questions from pulling unrelated containers that only share generic image words.
    terms = []
    for t in _question_terms(question):
        nt = _normalise(t)
        if nt and nt not in terms:
            terms.append(nt)

    # Fallback to exact app names from top matches only.
    if not terms:
        for m in matches[:3]:
            name = _normalise(m.get("app_name", ""))
            if name and name not in terms:
                terms.append(name)

    found = []

    for src in [docker_ps, docker_access]:
        for raw in src.splitlines():
            clean = raw.strip()
            if not clean:
                continue

            # Compare mainly against the container/app name, not the whole line.
            # docker_ps format: name|image|status|ports
            # docker_access format: /name|mounts|ports
            name_part = clean.split("|", 1)[0].strip().lstrip("/")
            name_norm = _normalise(name_part)

            if any(t and (t == name_norm or t in name_norm or name_norm in t) for t in terms):
                if clean not in found:
                    found.append(clean)

    return found[:6]

def answer(bundle, question=""):
    matches = search_apps(question, limit=5)
    lines = []

    lines.append("- This is a third-party app-store index question.")
    lines.append("- This is not official ZimaOS manual evidence.")
    lines.append("- The answer is based on the local third-party CasaOS/ZimaOS-compatible app index.")
    lines.append("")

    if not matches:
        lines.append("### App-store index result")
        lines.append("- No matching app was found in the indexed third-party app-store manifests.")
        lines.append("- This may still be installable manually with Docker, but it is not confirmed from the current app-store index.")
        return {
            "lines": lines,
            "next_step": "Confirm the app name or source store, then verify ports, volumes, permissions, and local install evidence before installing.",
            "forum_summary": "No matching app was found in the local third-party app-store index. Treat this as unverified app-store guidance, not official ZimaOS manual evidence.",
        }

    local_evidence = _find_local_container_evidence(bundle, matches, question)

    lines.append("### Matching app-store entries")
    for m in matches:
        app = m.get("app_name", "")
        store = m.get("store_name", "")
        image = m.get("images", "")
        ports = m.get("ports", "")
        vols = _clean_volume_preview(m.get("volumes", ""))
        risks = m.get("risk_flags", "")

        lines.append(f"- {app}")
        lines.append(f"  - Store: {store}")
        if image:
            lines.append(f"  - Image: {image[:180]}")
        if ports:
            lines.append(f"  - Ports from manifest: {ports[:180]}")
        if vols:
            lines.append(f"  - Volumes from manifest: {vols[:180]}")
        if risks:
            lines.append(f"  - Risk flags: {risks}")
        else:
            lines.append("  - Risk flags: none parsed from manifest")

    lines.append("")
    lines.append("### Local install evidence")
    if local_evidence:
        for item in local_evidence:
            lines.append(f"- {item}")
    else:
        lines.append("- No matching local container evidence was found in the current report.")

    risk_set = []
    for m in matches:
        for r in (m.get("risk_flags", "") or "").split(";"):
            r = r.strip()
            if r and r not in risk_set:
                risk_set.append(r)

    lines.append("")
    lines.append("### Risk interpretation")
    if risk_set:
        for r in risk_set:
            lines.append(f"- {r}: {RISK_EXPLAIN.get(r, 'Review this permission before installing.')}")
    else:
        lines.append("- No high-risk flags were parsed, but ports, volumes, and permissions still need review before installing.")

    return {
        "lines": lines,
        "next_step": "Before installing, verify the app source, host ports, mapped volumes, access control, and whether local container evidence already exists.",
        "forum_summary": "This app appears in the third-party app-store index. Treat it as third-party app-store guidance, not official ZimaOS manual evidence. Check ports, volumes, permissions, and local install evidence before installing.",
    }
