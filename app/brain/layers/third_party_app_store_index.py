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
        "code server", "calibre web", "actual budget", "paperless ngx",
        "reverse proxy", "nginx proxy manager", "nginxproxymanager"
    ]:
        if phrase in q:
            phrases.append(phrase)

    return phrases + words




def _is_reverse_proxy_question(question):
    q = _normalise(question)
    return (
        "reverse proxy" in q
        or "nginx proxy" in q
        or "nginxproxymanager" in q
        or ("nginx" in q and "proxy" in q)
    )


def _is_bad_reverse_proxy_match(row):
    blob = _normalise(" ".join([
        row.get("app_name", ""),
        row.get("description", ""),
        row.get("images", ""),
        row.get("store_name", ""),
    ]))

    bad_terms = [
        "reverse shell",
        "reverse_shell",
        "reverse shell generator",
        "pentest",
        "vulnerability",
        "vuldocker",
        "exploit",
    ]

    return any(term in blob for term in bad_terms)


def _reverse_proxy_bonus(question, row):
    if not _is_reverse_proxy_question(question):
        return 0

    blob = _normalise(" ".join([
        row.get("app_name", ""),
        row.get("description", ""),
        row.get("images", ""),
    ]))
    compact = _compact(blob)

    bonus = 0

    if "nginx proxy manager" in blob or "nginxproxymanager" in compact:
        bonus += 180
    if "jc21 nginx proxy manager" in blob or "jc21nginxproxymanager" in compact:
        bonus += 80
    if "reverse proxy" in blob:
        bonus += 70
    if "nginx" in blob and "proxy" in blob:
        bonus += 60

    return bonus

def search_apps(question, limit=8):
    rows = _load_rows()
    terms = _question_terms(question)

    if not terms:
        return []

    scored = []
    reverse_proxy_question = _is_reverse_proxy_question(question)

    for row in rows:
        if reverse_proxy_question and _is_bad_reverse_proxy_match(row):
            continue

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

        score += _reverse_proxy_bonus(question, row)

        if score:
            scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for score, row in scored[:limit]]


def _split_manifest_field(value):
    return [x.strip() for x in (value or "").split(";") if x.strip()]


def _dedupe(items, limit=8):
    out = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out[:limit]


def _clean_port_preview(ports):
    found = []
    for item in _split_manifest_field(ports):
        low = item.lower()
        if re.match(r"^\d+\s*:\s*\d+(?:/(?:tcp|udp))?$", low):
            found.append(item)
    return "; ".join(_dedupe(found, 10))


def _clean_volume_preview(volumes):
    found = []
    for raw in _split_manifest_field(volumes):
        item = raw.strip()
        low = item.lower()

        if not item:
            continue
        if "http://" in low or "https://" in low or "screenshot" in low:
            continue

        # Drop port mappings that were flattened into the volume column by the CSV builder.
        if re.match(r"^\d+\s*:\s*\d+(?:/(?:tcp|udp))?$", low):
            continue

        # Drop CasaOS metadata-only entries. These are not host volume mappings.
        if item.startswith("container:") or item.startswith("target:"):
            continue

        # Drop environment entries flattened into the volume column, such as KEY=value.
        if re.match(r"^[A-Z][A-Z0-9_]{1,}=.*$", item):
            continue

        if "/" in item or "docker.sock" in low:
            found.append(item)

    return "; ".join(_dedupe(found, 8))


def _extract_env_preview(volumes):
    envs = []
    for raw in _split_manifest_field(volumes):
        item = raw.strip()

        if re.match(r"^[A-Z][A-Z0-9_]{1,}=.*$", item):
            envs.append(item.split("=", 1)[0].strip())
            continue

        if item.startswith("container:"):
            name = item.replace("container:", "", 1).strip()
            if re.match(r"^[A-Z][A-Z0-9_]{1,}$", name):
                envs.append(name)
    return "; ".join(_dedupe(envs, 12))


def _infer_special_notes(app, image, volumes, risks):
    blob = " ".join([app or "", image or "", volumes or "", risks or ""]).lower()
    notes = []

    if "gluetun" in blob:
        notes.append("VPN gateway container. Apps routed through it must expose their service ports through Gluetun.")
        notes.append("Requires VPN provider settings before first start.")
    if "/dev/net/tun" in blob:
        notes.append("Requires /dev/net/tun device mapping.")
    if "net_admin" in blob or "net-admin" in blob:
        notes.append("Requires NET_ADMIN capability.")
    if "openvpn_user" in blob or "openvpn_password" in blob:
        notes.append("Requires VPN credentials or a valid VPN config.")

    return _dedupe(notes, 8)


def _compact(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _strip_store_prefix(name):
    n = _normalise(name)
    prefixes = [
        "big bear ",
        "linuxserver ",
        "linux server ",
        "lsio ",
        "casaos ",
    ]
    changed = True
    while changed:
        changed = False
        for pref in prefixes:
            if n.startswith(pref):
                n = n[len(pref):].strip()
                changed = True
    return n


def _local_name_matches(term, name_norm):
    if not term or not name_norm:
        return False

    term_norm = _normalise(term)
    term_compact = _compact(term_norm)
    name_compact = _compact(name_norm)

    # Exact and compact exact matches are safe.
    if term_norm == name_norm or term_compact == name_compact:
        return True

    # Multi-word app names may appear compacted as container names.
    # Example: "home assistant" -> "homeassistant".
    if " " in term_norm and term_compact and term_compact == name_compact:
        return True

    # Single-word app names must be specific enough.
    # This allows firefox/gluetun but prevents home -> homepage.
    if " " not in term_norm and len(term_norm) >= 6:
        return term_norm in name_norm or term_compact in name_compact

    return False


def _find_local_container_evidence(bundle, matches, question=""):
    evidence = bundle.get("same_report_evidence", {}) if isinstance(bundle, dict) else {}
    docker_ps = evidence.get("docker_ps", "") or ""
    docker_access = evidence.get("docker_access", "") or ""

    terms = []

    question_terms = [_normalise(t) for t in _question_terms(question)]
    phrase_terms = [t for t in question_terms if " " in t]

    # Prefer full phrases when present.
    for t in phrase_terms:
        if t and t not in terms:
            terms.append(t)

    # Add specific single-word terms only when no phrase exists.
    if not terms:
        for t in question_terms:
            if t and len(t) >= 6 and t not in terms:
                terms.append(t)

    # Add exact-ish app names from top matches, with common store prefixes removed.
    for m in matches[:3]:
        for raw_name in [m.get("app_name", ""), _strip_store_prefix(m.get("app_name", ""))]:
            name = _normalise(raw_name)
            if name and name not in terms:
                terms.append(name)

    found = []

    for src in [docker_ps, docker_access]:
        for raw in src.splitlines():
            clean = raw.strip()
            if not clean:
                continue

            name_part = clean.split("|", 1)[0].strip().lstrip("/")
            name_norm = _normalise(name_part)

            if any(_local_name_matches(t, name_norm) for t in terms):
                if clean not in found:
                    found.append(clean)

    return found[:6]

def answer(bundle, question=""):
    ql = (question or "").lower()
    show_all_words = ["show all", "all options", "all variants", "list all", "every option"]

    if any(w in ql for w in show_all_words):
        matches = search_apps(question, limit=8)
    else:
        matches = search_apps(question, limit=3)

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
        ports_raw = m.get("ports", "")
        volumes_raw = m.get("volumes", "")
        ports = _clean_port_preview(ports_raw)
        vols = _clean_volume_preview(volumes_raw)
        envs = _extract_env_preview(volumes_raw)
        risks = m.get("risk_flags", "")
        notes = _infer_special_notes(app, image, volumes_raw, risks)

        lines.append(f"- {app}")
        lines.append(f"  - Store: {store}")
        if image:
            lines.append(f"  - Image: {image[:180]}")
        if ports:
            lines.append(f"  - Ports from manifest: {ports[:180]}")
        if vols:
            lines.append(f"  - Volumes/devices from manifest: {vols[:220]}")
        if envs:
            lines.append(f"  - Required/config env from manifest: {envs[:220]}")
        if risks:
            lines.append(f"  - Risk flags: {risks}")
        else:
            lines.append("  - Risk flags: none parsed from manifest")
        if notes:
            lines.append("  - Special notes:")
            for note in notes:
                lines.append(f"    - {note}")

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
