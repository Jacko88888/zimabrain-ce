import html
import urllib.request
import json
import sqlite3
import socket
import os
from pathlib import Path
import subprocess
import re
from datetime import datetime
from flask import Flask, request, jsonify, Response, send_from_directory, session, redirect, abort, make_response
from brain import render as brain_render
from brain import answer_builder
import os
import secrets
import hmac
from werkzeug.security import generate_password_hash, check_password_hash

APP_NAME = "ZimaBrain CE"
APP_SUBTITLE = "Local Zima Knowledge Assistant"
APP_DESCRIPTOR = "Verifier-first diagnostic cockpit for ZimaOS"
APP_VERSION = "v1.6.0-beta"
DASHBOARD_REPORT_URL = ""  # old external 8514 dashboard disabled
TREND_DB_PATH = "/data/zimabrain_trends.sqlite"

app = Flask(__name__)


def _load_secret_key():
    env_key = os.environ.get("ZIMABRAIN_SECRET_KEY", "").strip()
    if env_key:
        return env_key

    secret_path = "/data/.zimabrain_secret_key"
    try:
        if os.path.exists(secret_path):
            with open(secret_path, "r", encoding="utf-8") as f:
                existing = f.read().strip()
                if existing:
                    return existing
        generated = secrets.token_hex(32)
        os.makedirs(os.path.dirname(secret_path), exist_ok=True)
        with open(secret_path, "w", encoding="utf-8") as f:
            f.write(generated)
        try:
            os.chmod(secret_path, 0o600)
        except Exception:
            pass
        return generated
    except Exception:
        return "zimabrain-dev-secret-" + secrets.token_hex(16)


app.secret_key = _load_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

ZIMABRAIN_PASSWORD = os.environ.get("ZIMABRAIN_PASSWORD", "").strip()
PASSWORD_HASH_PATH = "/data/.zimabrain_password_hash"


def _read_password_hash():
    try:
        if os.path.exists(PASSWORD_HASH_PATH):
            with open(PASSWORD_HASH_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        return ""
    return ""


def _write_password_hash(password):
    os.makedirs(os.path.dirname(PASSWORD_HASH_PATH), exist_ok=True)
    with open(PASSWORD_HASH_PATH, "w", encoding="utf-8") as f:
        f.write(generate_password_hash(password))
    try:
        os.chmod(PASSWORD_HASH_PATH, 0o600)
    except Exception:
        pass


def password_configured():
    return bool(ZIMABRAIN_PASSWORD or _read_password_hash())


def security_enabled():
    # Security is always enabled. First run goes to setup, then login.
    return True


def is_logged_in():
    return bool(session.get("zimabrain_authenticated"))


def verify_password(password):
    if ZIMABRAIN_PASSWORD:
        return hmac.compare_digest(password, ZIMABRAIN_PASSWORD)

    stored = _read_password_hash()
    if stored:
        try:
            return check_password_hash(stored, password)
        except Exception:
            return False

    return False


def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(24)
        session["csrf_token"] = token
    return token


def csrf_field():
    return f'<input type="hidden" name="csrf_token" value="{csrf_token()}">'


def auth_status_html():
    source = "compose environment" if ZIMABRAIN_PASSWORD else "first-run setup"
    return f"""
    <div class="card">
      <h3>Security</h3>
      <p class="ok">Password gate enabled.</p>
      <p class="muted">Password source: {esc(source)}</p>
      <form method="post" action="/logout">
        {csrf_field()}
        <button class="button" type="submit">Logout</button>
      </form>
    </div>
    """


def redact_support_text(text):
    text = str(text or "")

    # Network addresses
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<LAN_IP>", text)

    # Authorization / bearer tokens first, before generic key=value redaction
    text = re.sub(r"(?i)(authorization\s*[:=]\s*)bearer\s+[^\s'\"<>]+", r"\1Bearer <redacted>", text)
    text = re.sub(r"(?i)\bbearer\s+[^\s'\"<>]+", "Bearer <redacted>", text)

    # Common secret-looking key/value pairs
    text = re.sub(
        r"(?i)\b(password|passwd|token|secret|api[_-]?key)\s*[:=]\s*['\"]?[^'\"\s<>]+",
        r"\1=<redacted>",
        text,
    )

    # Long hex strings commonly used for secrets, tokens, keys or IDs
    text = re.sub(r"\b[a-f0-9]{32,}\b", "<redacted_hex>", text)

    # Private local paths, line-safe
    text = re.sub(r"/DATA/AppData/[^\s'\"<>]+", "/DATA/AppData/<redacted>", text)
    text = re.sub(r"/media/[^\s'\"<>]+", "/media/<redacted>", text)
    text = re.sub(r"/var/lib/casaos_data/[^\s'\"<>]+", "/var/lib/casaos_data/<redacted>", text)

    return text


@app.before_request
def security_gate():
    allowed_paths = {"/login", "/setup", "/health", "/metrics", "/api/v1/health"}
    if request.path.startswith("/assets/") or request.path in allowed_paths:
        return None

    if not password_configured():
        return redirect("/setup")

    if not is_logged_in():
        return redirect("/login")

    if request.method == "POST":
        sent = request.form.get("csrf_token", "") or request.headers.get("X-CSRF-Token", "")
        expected = session.get("csrf_token", "")
        if not expected or not hmac.compare_digest(str(sent), str(expected)):
            abort(400, "CSRF token missing or invalid")

    return None


@app.route("/setup", methods=["GET", "POST"])
def setup_password():
    if password_configured():
        return redirect("/login")

    error = ""
    if request.method == "POST":
        p1 = request.form.get("password", "")
        p2 = request.form.get("password_confirm", "")

        if len(p1) < 8:
            error = "Password must be at least 8 characters."
        elif p1 != p2:
            error = "Passwords do not match."
        else:
            _write_password_hash(p1)
            session["zimabrain_authenticated"] = True
            session["csrf_token"] = secrets.token_hex(24)
            return redirect("/")

    error_html = f"<p style='color:#fecaca;font-weight:800'>{esc(error)}</p>" if error else ""
    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>ZimaBrain CE First Run Setup</title>
<style>
body{{background:#080b10;color:#e8edf2;font-family:Arial,sans-serif;margin:0;padding:30px}}
.card{{max-width:500px;margin:8vh auto;background:#101827;border:1px solid #263241;border-radius:18px;padding:28px}}
input{{width:100%;box-sizing:border-box;padding:13px;margin-top:10px;border-radius:10px;border:1px solid #334155;background:#020617;color:#e8edf2;font-size:16px}}
button{{width:100%;margin-top:16px;padding:12px;border:0;border-radius:10px;background:#2563eb;color:white;font-weight:900;font-size:15px;cursor:pointer}}
.muted{{color:#9aa8b5;font-size:14px;line-height:1.55}}
code{{background:#020617;padding:2px 6px;border-radius:6px}}


</style>
</head>
<body>
<div class="card">
<h2>Create ZimaBrain CE Password</h2>
<p class="muted">First-run setup. Create a password before showing local ZimaOS diagnostics.</p>
{error_html}
<form method="post" action="/setup">
  <input type="password" name="password" placeholder="New password" autofocus>
  <input type="password" name="password_confirm" placeholder="Confirm password">
  <button type="submit">Create Password</button>
</form>
<p class="muted"><b>Forgot password later?</b><br>Remove <code>/DATA/AppData/zimabrain-ce/.zimabrain_password_hash</code> or set <code>ZIMABRAIN_PASSWORD</code> in compose and restart the container.</p>
</div>
</body>
</html>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if not password_configured():
        return redirect("/setup")

    error = ""
    if request.method == "POST":
        password = request.form.get("password", "")
        if verify_password(password):
            session["zimabrain_authenticated"] = True
            session["csrf_token"] = secrets.token_hex(24)
            return redirect("/")
        error = "Incorrect password."

    error_html = f"<p style='color:#fecaca;font-weight:800'>{esc(error)}</p>" if error else ""
    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>ZimaBrain CE Login</title>
<style>
body{{background:#080b10;color:#e8edf2;font-family:Arial,sans-serif;margin:0;padding:30px}}
.card{{max-width:460px;margin:8vh auto;background:#101827;border:1px solid #263241;border-radius:18px;padding:28px}}
input{{width:100%;box-sizing:border-box;padding:13px;border-radius:10px;border:1px solid #334155;background:#020617;color:#e8edf2;font-size:16px}}
button{{width:100%;margin-top:14px;padding:12px;border:0;border-radius:10px;background:#2563eb;color:white;font-weight:900;font-size:15px;cursor:pointer}}
.muted{{color:#9aa8b5;font-size:14px;line-height:1.55}}
code{{background:#020617;padding:2px 6px;border-radius:6px}}
</style>
</head>
<body>
<div class="card">
<h2>ZimaBrain CE</h2>
<p class="muted">Password required before showing local ZimaOS diagnostics.</p>
{error_html}
<form method="post" action="/login">
  <input type="password" name="password" placeholder="Password" autofocus>
  <button type="submit">Login</button>
</form>
<p class="muted"><b>Forgot password?</b><br>Remove <code>/DATA/AppData/zimabrain-ce/.zimabrain_password_hash</code> or edit <code>ZIMABRAIN_PASSWORD</code> in your compose file and restart the container.</p>
</div>
</body>
</html>
"""


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/login" if password_configured() else "/setup")


@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory("assets", filename)


SESSION_HISTORY = []
DASHBOARD_REPORT = ""
DASHBOARD_STATUS = "Dashboard evidence not loaded yet."


def esc(value):
    return html.escape(str(value or ""))


def read_text_file(path, default=""):
    try:
        return Path(path).read_text(errors="replace").strip()
    except Exception:
        return default


def decode_mount_path(path):
    return path.replace("\\040", " ")


def detected_host_name():
    return read_text_file("/host/etc/hostname") or read_text_file("/etc/hostname") or "Local-ZimaOS-Device"


def detected_product_name():
    product = read_text_file("/host/sys/devices/virtual/dmi/id/product_name") or read_text_file("/sys/devices/virtual/dmi/id/product_name")
    if product and product.lower() not in ("default string", "to be filled by o.e.m."):
        return product
    return detected_host_name()


def human_size(num):
    try:
        num = float(num)
        for unit in ["B", "K", "M", "G", "T", "P"]:
            if num < 1024:
                return f"{num:.1f}{unit}" if unit != "B" else f"{int(num)}B"
            num /= 1024
    except Exception:
        pass
    return "N/A"


def base_device_name(name):
    name = str(name or "")
    if re.match(r"^nvme\d+n\d+p\d+$", name):
        return re.sub(r"p\d+$", "", name)
    if re.match(r"^mmcblk\d+p\d+$", name):
        return re.sub(r"p\d+$", "", name)
    return re.sub(r"\d+$", "", name)


def preferred_mount(existing, candidate):
    if not existing or existing == "not mounted":
        return candidate
    priority = ("/media/", "/DATA/.media/", "/DATA", "/var/lib/casaos_data", "/")
    existing_score = next((i for i, p in enumerate(priority) if existing.startswith(p)), 99)
    candidate_score = next((i for i, p in enumerate(priority) if candidate.startswith(p)), 99)
    return candidate if candidate_score < existing_score else existing


def native_smart_health(dev):
    dev = str(dev or "").strip()
    if not re.match(r"^(sd[a-z]+|nvme\d+n\d+|mmcblk\d+)$", dev):
        return "N/A"

    out = run_host_command(f"smartctl -H -A /dev/{dev} 2>&1 | sed -n '1,180p'", timeout=15)
    lower = out.lower()

    if re.search(r"Permission denied|No such device", out, re.I):
        return "N/A"

    if re.search(r"Unavailable|unsupported|Unknown USB bridge|please specify device type|SMART support is:\s*(unavailable|disabled)", out, re.I):
        return "LIMITED; SMART details unavailable"

    overall = "UNKNOWN"
    if re.search(r"SMART overall-health.*FAILED|SMART Health Status:\s*FAILED", out, re.I):
        overall = "FAILED"
    elif re.search(r"SMART overall-health.*PASSED|SMART Health Status:\s*OK", out, re.I):
        overall = "PASSED"

    def last_int(line):
        nums = re.findall(r"\b\d+\b", str(line or ""))
        if not nums:
            return None
        try:
            return int(nums[-1])
        except Exception:
            return None

    risky_attrs = {
        "Reallocated_Sector_Ct": "Reallocated sectors",
        "Current_Pending_Sector": "Pending sectors",
        "Offline_Uncorrectable": "Offline uncorrectable",
        "Reported_Uncorrect": "Reported uncorrectable",
    }

    attention_attrs = {
        "UDMA_CRC_Error_Count": "UDMA CRC errors",
        "CRC_Error_Count": "CRC errors",
        "Command_Timeout": "Command timeouts",
    }

    seen_detail = False
    critical_details = []
    attention_details = []

    for line in out.splitlines():
        for attr, label in risky_attrs.items():
            if attr.lower() in line.lower():
                seen_detail = True
                val = last_int(line)
                if val is not None and val > 0:
                    critical_details.append(f"{label}: {val}")

        for attr, label in attention_attrs.items():
            if attr.lower() in line.lower():
                seen_detail = True
                val = last_int(line)
                if val is not None and val > 0:
                    attention_details.append(f"{label}: {val}")

        if "unsafe_shutdowns" in line.lower() or "unsafe shutdowns" in line.lower():
            seen_detail = True
            val = last_int(line)
            if val is not None and val >= 10:
                attention_details.append(f"NVMe unsafe shutdowns: {val}")

        if "num_err_log_entries" in line.lower() or "error information log entries" in line.lower():
            seen_detail = True
            val = last_int(line)
            if val is not None and val > 0:
                attention_details.append(f"NVMe error log entries: {val}")

    if overall == "FAILED":
        details = critical_details + attention_details
        suffix = "; ".join(details[:4]) if details else "SMART overall: FAILED"
        return f"FAILED; {suffix}"

    if critical_details or attention_details:
        details = critical_details + attention_details
        suffix = "; ".join(details[:4])
        return f"ATTENTION; {suffix}; SMART overall: {overall}"

    if overall == "PASSED" and seen_detail:
        return "PASSED"

    if overall in ("PASSED", "FAILED"):
        return f"LIMITED; SMART overall: {overall}; detailed attributes missing"

    return "N/A"


def collect_mounts():
    mounts = {}
    proc_mounts = read_text_file("/host/proc/1/mounts") or read_text_file("/host/proc/mounts")

    for line in proc_mounts.splitlines():
        parts = line.split()
        if len(parts) < 2 or not parts[0].startswith("/dev/"):
            continue

        dev = parts[0].replace("/dev/", "")
        mount = decode_mount_path(parts[1])

        mounts[dev] = preferred_mount(mounts.get(dev), mount)

        parent = base_device_name(dev)
        if parent != dev:
            mounts[parent] = preferred_mount(mounts.get(parent), mount)

    mdstat = read_text_file("/host/proc/mdstat")
    for line in mdstat.splitlines():
        line = line.strip()
        if " : active " not in line:
            continue

        md_name = line.split(":", 1)[0].strip()
        md_mount = mounts.get(md_name)
        if not md_mount:
            continue

        for member in re.findall(r"\b([a-z]+[a-z]*\d*|nvme\d+n\d+|mmcblk\d+)\[\d+\]", line):
            mounts[member] = preferred_mount(mounts.get(member), md_mount)

    return mounts


def collect_native_disks():
    mounts = collect_mounts()
    rows = []
    root = Path("/host/sys/block")

    if not root.exists():
        root = Path("/sys/block")

    skip_prefixes = ("loop", "ram", "zram", "dm-", "md", "nbd")
    skip_contains = ("boot", "rpmb")

    for dev_path in sorted(root.iterdir(), key=lambda x: x.name):
        dev = dev_path.name
        if dev.startswith(skip_prefixes) or any(x in dev for x in skip_contains):
            continue

        sectors = read_text_file(dev_path / "size")
        try:
            size_bytes = int(sectors) * 512
            if size_bytes <= 0:
                continue
            size = human_size(size_bytes)
        except Exception:
            size = "N/A"

        model = (
            read_text_file(dev_path / "device/model")
            or read_text_file(dev_path / "device/name")
            or ("System Disk" if dev.startswith("mmcblk") else "Disk")
        )

        rows.append({
            "device": dev,
            "model": model,
            "size": size,
            "mount": mounts.get(dev, "not mounted"),
            "health": native_smart_health(dev),
            "temp": "N/A",
            "realloc": "N/A",
            "pending": "N/A",
            "crc": "N/A",
            "power_on": "N/A",
        })

    return rows


def decode_http_chunked(body):
    out = b""
    pos = 0
    while True:
        end = body.find(b"\r\n", pos)
        if end == -1:
            return body
        try:
            size = int(body[pos:end].split(b";", 1)[0], 16)
        except Exception:
            return body
        pos = end + 2
        if size == 0:
            break
        out += body[pos:pos + size]
        pos += size + 2
    return out


def docker_api_get(path):
    sock_path = "/var/run/docker.sock"
    if not Path(sock_path).exists():
        return None

    request = f"GET {path} HTTP/1.1\r\nHost: docker\r\nConnection: close\r\n\r\n".encode()

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(3)
        sock.connect(sock_path)
        sock.sendall(request)
        data = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk

    header, _, body = data.partition(b"\r\n\r\n")
    if b"transfer-encoding: chunked" in header.lower():
        body = decode_http_chunked(body)

    return json.loads(body.decode("utf-8", errors="replace"))


def collect_native_containers():
    try:
        data = docker_api_get("/containers/json?all=1") or []
    except Exception:
        data = []

    rows = []
    for item in data:
        names = item.get("Names") or []
        name = names[0].lstrip("/") if names else item.get("Id", "")[:12]
        rows.append({
            "name": name,
            "state": item.get("State", "unknown"),
            "image": item.get("Image", "unknown"),
        })
    return rows


def build_native_report(reason=""):
    disks = collect_native_disks()
    containers = collect_native_containers()

    lines = []
    lines.append("===== RAW DASHBOARD ALERTS =====")
    lines.append("INFO: Native ZimaBrain local evidence fallback generated.")
    if reason:
        lines.append(f"INFO: {reason}")

    lines.append("")
    lines.append("===== DISKS / SMART SUMMARY =====")
    lines.append("Device | Model | Size | Mount | Health | Temp | Realloc | Pending | CRC | Power_On")
    lines.append("--- | --- | --- | --- | --- | --- | --- | --- | --- | ---")
    for d in disks:
        lines.append(
            f"{d['device']} | {d['model']} | {d['size']} | {d['mount']} | {d['health']} | "
            f"{d['temp']} | {d['realloc']} | {d['pending']} | {d['crc']} | {d['power_on']}"
        )

    lines.append("")
    lines.append("===== CONTAINERS =====")
    running_count = 0
    total_count = len(containers)
    for c in containers:
        state = str(c.get("state", "") or "").lower()
        if state == "running" or state.startswith("up"):
            running_count += 1

    lines.append(f"Containers: {running_count}/{total_count} running")
    lines.append(f"Containers not running: {total_count - running_count}")
    lines.append("")
    lines.append("Name | State | Image")
    lines.append("--- | --- | ---")
    for c in containers:
        lines.append(f"{c['name']} | {c['state']} | {c['image']}")

    lines.append("")
    lines.append("===== NATIVE FALLBACK STATUS =====")
    lines.append(f"Device: {detected_product_name()}")
    lines.append(f"Disks parsed from host sysfs: {len(disks)}")
    lines.append(f"Containers parsed from Docker socket: {len(containers)}")

    return "\n".join(lines)


def live_visual_available():
    # Disabled for release polish.
    # ZimaBrain CE now uses its built-in native visual dashboard.
    return False


def local_zimaos_visual_panel(bundle):
    if live_visual_available():
        return """
        <p class="small">Built-in native visual dashboard. No external visual container is required.</p>
        """

    disks = bundle.get("disks", [])
    report = bundle.get("report", "")
    device = detected_product_name()
    containers = collect_native_containers()
    running = len([c for c in containers if str(c.get("state", "")).lower() == "running"])
    total = len(containers)

    disk_html = ""
    for d in disks:
        dev = esc(d.get("device"))
        model = esc(d.get("model"))
        size = esc(d.get("size"))
        mount = esc(d.get("mount"))
        health = esc(d.get("health", "N/A"))
        disk_html += f"""
          <div class="native-drive">
            <div class="native-drive-head">
              <span class="native-drive-name">{dev}</span>
              <span class="native-pill">DATA</span>
            </div>
            <div class="native-model">{model}</div>
            <div class="native-row"><span>SIZE</span><b>{size}</b></div>
            <div class="native-row"><span>MOUNT</span><b>{mount}</b></div>
            <div class="native-row"><span>HEALTH</span><b>{health}</b></div>
          </div>
        """

    if not disk_html:
        disk_html = '<div class="native-muted">No disk evidence parsed yet.</div>'

    container_html = ""
    for c in containers[:10]:
        container_html += f"""
          <div class="native-line">
            <span class="native-dot"></span>
            <span>{esc(c.get("name"))}</span>
            <b>{esc(c.get("state"))}</b>
          </div>
        """

    if not container_html:
        container_html = '<div class="native-muted">No Docker containers parsed yet.</div>'

    status_line = "Built-in native visual active. External visual dashboard is not required."
    if "Native ZimaBrain local evidence fallback generated" in report:
        status_line = "Built-in native visual active. External visual dashboard is not required."

    return f"""
    <style>
      .native-zima-wrap {{
        background: #020806;
        border: 1px solid #1f4f35;
        border-radius: 14px;
        padding: 18px;
        color: #d9ffe5;
        box-shadow: inset 0 0 40px rgba(0, 255, 120, 0.04);
      }}
      .native-zima-top {{
        display: flex;
        justify-content: space-between;
        gap: 16px;
        border-bottom: 1px solid rgba(130, 255, 170, 0.18);
        padding-bottom: 12px;
        margin-bottom: 14px;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #9cffb8;
        font-size: 12px;
      }}
      .native-zima-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin-bottom: 14px;
      }}
      .native-stat, .native-drive, .native-containers {{
        background: rgba(8, 20, 14, 0.92);
        border: 1px solid rgba(130, 255, 170, 0.18);
        border-radius: 10px;
        padding: 14px;
      }}
      .native-label {{
        color: #8ba0ad;
        font-size: 12px;
        letter-spacing: 0.22em;
        text-transform: uppercase;
      }}
      .native-value {{
        font-size: 28px;
        font-weight: 800;
        margin-top: 8px;
        color: #f4fff8;
      }}
      .native-drive-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
      }}
      .native-drive-head {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
      }}
      .native-drive-name {{
        font-size: 22px;
        font-weight: 800;
        color: #ffffff;
        text-transform: uppercase;
      }}
      .native-pill {{
        border: 1px solid rgba(120, 255, 160, 0.35);
        color: #8dffad;
        padding: 2px 7px;
        border-radius: 5px;
        font-size: 11px;
        font-weight: 700;
      }}
      .native-model {{
        color: #d8ffe2;
        min-height: 34px;
        font-size: 13px;
      }}
      .native-row {{
        display: flex;
        justify-content: space-between;
        gap: 10px;
        border-top: 1px solid rgba(255,255,255,0.06);
        padding-top: 7px;
        margin-top: 7px;
        color: #9badb8;
        font-size: 12px;
      }}
      .native-row b {{
        color: #f4fff8;
        text-align: right;
      }}
      .native-bottom {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-top: 12px;
      }}
      .native-line {{
        display: grid;
        grid-template-columns: 16px 1fr auto;
        gap: 8px;
        align-items: center;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        padding: 6px 0;
        font-size: 13px;
      }}
      .native-dot {{
        width: 7px;
        height: 7px;
        background: #8dffad;
        display: inline-block;
      }}
      .native-muted {{
        color: #9badb8;
        font-size: 13px;
      }}
      @media (max-width: 1100px) {{
        .native-zima-grid, .native-drive-grid, .native-bottom {{
          grid-template-columns: 1fr;
        }}
      }}
    

</style>

    <div class="native-zima-wrap">
      <div class="native-zima-top">
        <div>LOCAL ZIMAOS VISUAL · BUILT INTO ZIMABRAIN CE</div>
        <div>{esc(device)} · NATIVE MODE</div>
      </div>

      <div class="native-zima-grid">
        <div class="native-stat"><div class="native-label">Device</div><div class="native-value">{esc(device)}</div></div>
        <div class="native-stat"><div class="native-label">Visual Mode</div><div class="native-value">Native</div></div>
        <div class="native-stat"><div class="native-label">Disks</div><div class="native-value">{len(disks)}</div></div>
        <div class="native-stat"><div class="native-label">Containers</div><div class="native-value">{running}/{total}</div></div>
      </div>

      <div class="native-muted">{esc(status_line)}</div>

      <h4>Detected Storage</h4>
      <div class="native-drive-grid">{disk_html}</div>

      <div class="native-bottom">
        <div class="native-containers">
          <h4>Container State</h4>
          {container_html}
        </div>
        <div class="native-containers">
          <h4>Native Evidence Source</h4>
          <div class="native-line"><span class="native-dot"></span><span>Host sysfs</span><b>active</b></div>
          <div class="native-line"><span class="native-dot"></span><span>Host mounts</span><b>active</b></div>
          <div class="native-line"><span class="native-dot"></span><span>Docker socket</span><b>active</b></div>
          <div class="native-line"><span class="native-dot"></span><span>External visual dashboard</span><b>not required</b></div>
        </div>
      </div>
    </div>
    """



def fetch_dashboard_report():
    try:
        req = urllib.request.Request(
            DASHBOARD_REPORT_URL,
            headers={"User-Agent": "ZimaBrain-CE-Dashboard-Layer"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            report = resp.read().decode("utf-8", errors="replace")

        # External visual dashboard report may contain container alerts but not
        # the native running/total Docker container count.
        # Append native local evidence so answer layers can verify X/Y running.
        if "Containers:" not in report or "Containers not running:" not in report:
            report = (
                report.rstrip()
                + "\n\n===== NATIVE LOCAL FALLBACK REPORT =====\n"
                + build_native_report("Native local Docker/container summary appended for verification.")
            )

        return report
    except Exception as exc:
        return build_native_report(f"Live dashboard unavailable: {exc}")

def parse_dashboard_alerts(report_text):
    alerts = []
    in_alerts = False

    for raw in report_text.splitlines():
        line = raw.strip()

        if line == "===== RAW DASHBOARD ALERTS =====":
            in_alerts = True
            continue

        if in_alerts and line.startswith("====="):
            break

        if in_alerts and line.startswith("WARN:"):
            alerts.append(line.replace("WARN:", "YELLOW:", 1).strip())
        elif in_alerts and line.startswith("CRITICAL:"):
            alerts.append(line.replace("CRITICAL:", "RED:", 1).strip())
        elif in_alerts and line.startswith("OK:"):
            alerts.append(line.replace("OK:", "INFO:", 1).strip())

    return alerts


def parse_dashboard_disks(report_text):
    disks = []
    in_disks = False

    for raw in report_text.splitlines():
        line = raw.strip()

        if line == "===== DISKS / SMART SUMMARY =====":
            in_disks = True
            continue

        if in_disks and line.startswith("====="):
            break

        if not in_disks or "|" not in line or line.startswith("Device ") or line.startswith("---"):
            continue

        parts = [x.strip() for x in line.split("|")]
        if len(parts) >= 10:
            disks.append({
                "device": parts[0],
                "model": parts[1],
                "size": parts[2],
                "mount": parts[3],
                "health": parts[4],
                "temp": parts[5],
                "realloc": parts[6],
                "pending": parts[7],
                "crc": parts[8],
                "power_on": parts[9],
            })

    return disks


def classify_exited_container(name, image=""):
    name_l = str(name or "").lower()
    image_l = str(image or "").lower()

    completed_markers = [
        "migration", "migrations", "migrate", "init", "setup", "bootstrap",
        "oneshot", "one-shot", "job", "worker-once"
    ]
    duplicate_markers = [
        "fixed", "old", "backup", "bak", "test", "trial", "copy", "full"
    ]
    service_stack_markers = [
        "mailcow", "postfix", "dovecot", "mysql", "mariadb", "postgres",
        "redis", "nginx", "traefik", "immich", "nextcloud", "plex",
        "jellyfin", "qbittorrent"
    ]

    if any(x in name_l for x in completed_markers):
        return {
            "class": "on_demand_completed",
            "severity": "INFO",
            "reason": "Name looks like a one-shot setup/migration container. Exited may be expected.",
        }

    if any(x in name_l for x in duplicate_markers):
        return {
            "class": "manual_or_duplicate",
            "severity": "INFO",
            "reason": "Name looks like a test, fixed, full, old, backup, or duplicate container. Exited may be intentional.",
        }

    if any(x in name_l or x in image_l for x in service_stack_markers):
        return {
            "class": "service_stack_stopped",
            "severity": "YELLOW",
            "reason": "Name/image looks like an application service. Confirm whether it should be running.",
        }

    return {
        "class": "unknown_exited",
        "severity": "YELLOW",
        "reason": "Exited container was detected, but ZimaBrain cannot tell if it is intentional from name/image alone.",
    }


def parse_dashboard_exited_containers(report_text):
    exited = []
    in_containers = False

    for raw in report_text.splitlines():
        line = raw.strip()

        if line == "===== CONTAINERS =====":
            in_containers = True
            continue

        if in_containers and line.startswith("====="):
            break

        if not in_containers or "|" not in line or line.startswith("Name ") or line.startswith("---"):
            continue

        parts = [x.strip() for x in line.split("|")]
        if len(parts) >= 3 and parts[1].lower() == "exited":
            cls = classify_exited_container(parts[0], parts[2])
            exited.append({
                "name": parts[0],
                "status": parts[1],
                "image": parts[2],
                "class": cls["class"],
                "severity": cls["severity"],
                "reason": cls["reason"],
            })

    return exited


def severity_dot(text):
    if text.startswith("YELLOW:"):
        return "🟡 " + text
    if text.startswith("RED:"):
        return "🔴 " + text
    if text.startswith("INFO:"):
        return "ℹ️ " + text
    return text




def parse_dashboard_container_count(report_text):
    """
    Parse visual dashboard container count such as:
    - Containers 44/50
    - CONTAINERS 3/4
    - containers: 4/4 running
    This is dashboard summary evidence, separate from named exited-container rows.
    """
    text = str(report_text or "")
    patterns = [
        r"\bcontainers?\b\s*[:\-]?\s*(\d+)\s*/\s*(\d+)",
        r"\bCONTAINERS?\b\s*[:\-]?\s*(\d+)\s*/\s*(\d+)",
    ]

    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if not m:
            continue
        running = int(m.group(1))
        total = int(m.group(2))
        if total > 0 and 0 <= running <= total:
            return {
                "running": running,
                "total": total,
                "not_running": total - running,
                "source": "visual_dashboard_container_count",
            }

    return {
        "running": None,
        "total": None,
        "not_running": None,
        "source": "not_parsed",
    }


def dashboard_alert_source(alert):
    text = str(alert or "")
    low = text.lower()

    source = "dashboard_alert"
    obj = "unknown"
    condition = "unparsed"

    disk_match = re.search(r'(/dev/[a-z]+[0-9]*|/dev/nvme[0-9]+n[0-9]+|nvme[0-9]+n[0-9]+|sd[a-z][0-9]*)', text, re.IGNORECASE)
    if disk_match:
        source = "disk"
        obj = disk_match.group(1)

    container_match = re.search(r'container\s+(?:exited|stopped|unhealthy)?\s*[:\-]?\s*([A-Za-z0-9_.-]+)', text, re.IGNORECASE)
    if container_match:
        source = "container"
        obj = container_match.group(1)

    service_match = re.search(r'([A-Za-z0-9_.@-]+\.(?:service|timer|mount|socket))', text)
    if service_match:
        source = "service"
        obj = service_match.group(1)

    if "crc" in low:
        condition = "CRC warning"
    elif "pending" in low:
        condition = "pending sectors"
    elif "realloc" in low or "reallocated" in low:
        condition = "reallocated sectors"
    elif "n/a" in low:
        condition = "value unavailable"
    elif "exited" in low or "stopped" in low:
        condition = "not running"
    elif "failed" in low:
        condition = "failed"
    elif "temperature" in low or "temp" in low:
        condition = "temperature"

    return {
        "text": text,
        "source": source,
        "object": obj,
        "condition": condition,
        "parsed": obj != "unknown" or condition != "unparsed",
    }


def normalize_dashboard_evidence(alerts, disks, exited):
    real_alerts = []
    info_alerts = []
    container_alerts = []
    real_alert_details = []
    info_alert_details = []
    container_alert_details = []
    unparsed_alerts = []

    for alert in alerts:
        meta = dashboard_alert_source(alert)
        low = alert.lower()
        if "n/a" in low:
            if alert.startswith("YELLOW:"):
                alert = alert.replace("YELLOW:", "INFO:", 1)
            enriched = alert + " (SMART value unavailable, not confirmed failure)"
            info_alerts.append(enriched)
            meta["text"] = enriched
            info_alert_details.append(meta)
        elif "container exited" in low:
            container_alerts.append(alert)
            container_alert_details.append(meta)
        else:
            real_alerts.append(alert)
            real_alert_details.append(meta)

        if not meta.get("parsed"):
            unparsed_alerts.append(alert)

    disk_attention = []
    disk_ok = []

    for d in disks:
        issues = []
        if d.get("crc") not in ["0", "-", "N/A", "", None]:
            issues.append(f"CRC {d.get('crc')}")
        if d.get("pending") not in ["0", "-", "N/A", "", None]:
            issues.append(f"pending {d.get('pending')}")
        if d.get("realloc") not in ["0", "-", "N/A", "", None]:
            issues.append(f"reallocated {d.get('realloc')}")
        if str(d.get("health", "")).upper() not in ["PASSED", "OK"]:
            issues.append(f"health {d.get('health')}")

        item = dict(d)
        item["issues"] = issues

        if issues:
            disk_attention.append(item)
        else:
            disk_ok.append(item)

    return {
        "real_alerts": real_alerts,
        "info_alerts": info_alerts,
        "container_alerts": container_alerts,
        "real_alert_details": real_alert_details,
        "info_alert_details": info_alert_details,
        "container_alert_details": container_alert_details,
        "unparsed_alerts": unparsed_alerts,
        "unparsed_alert_count": len(unparsed_alerts),
        "disk_attention": disk_attention,
        "disk_ok": disk_ok,
        "exited_containers": exited,
    }




def run_host_command(command, timeout=12):
    try:
        return subprocess.check_output(
            ["nsenter", "-t", "1", "-m", "-u", "-n", "-i", "--", "sh", "-lc", command],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        ).strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip()
    except Exception as e:
        return f"ERROR: {e}"




def host_hardware_metrics_panel(bundle):
    ev = (bundle.get("same_report_evidence") or {})
    trend = bundle.get("trend_snapshot") or {}
    n = bundle.get("normalized") or {}

    def lscpu_value(key):
        for line in str(ev.get("cpu_info", "") or "").splitlines():
            if line.lower().startswith(key.lower() + ":"):
                return line.split(":", 1)[1].strip()
        return "Not captured"

    def trend_int(key):
        try:
            return int(trend.get(key, 0) or 0)
        except Exception:
            return 0

    def os_value(key):
        for line in str(ev.get("host_os", "") or "").splitlines():
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"')
        return "Not captured"

    def count_lsblk(kind):
        names = set()
        for line in str(ev.get("lsblk", "") or "").splitlines():
            parts = line.split()
            if not parts:
                continue

            name = parts[0].strip().replace("├─", "").replace("└─", "").replace("│", "")
            name = name.strip()

            if kind == "nvme":
                if re.match(r"^nvme[0-9]+n[0-9]+$", name):
                    names.add(name)
            elif kind == "sd":
                if re.match(r"^sd[a-z]$", name):
                    names.add(name)

        return len(names)

    cpu_model = lscpu_value("Model name").replace("(R)", "").replace("(TM)", "")
    cpu_model = re.sub(r"\s+", " ", cpu_model).strip()

    cpu_usage = "Not captured"
    m = re.search(r"CPU_USAGE_PERCENT=([0-9.]+|unknown)", str(ev.get("cpu_usage", "") or ""))
    if m:
        cpu_usage = m.group(1) + "%"

    mem_value = "Not captured"
    mem_note = "host memory"
    swap_value = "Not captured"

    for line in str(ev.get("memory", "") or "").splitlines():
        parts = line.split()
        if len(parts) >= 7 and parts[0] == "Mem:":
            total = int(parts[1])
            used = int(parts[2])
            avail = int(parts[6])
            pct = (used / total * 100) if total else 0
            mem_value = f"{pct:.0f}%"
            mem_note = f"{used/1024:.1f} GiB / {total/1024:.1f} GiB - {avail/1024:.1f} GiB avail"
        if len(parts) >= 4 and parts[0] == "Swap:":
            total = int(parts[1])
            used = int(parts[2])
            pct = (used / total * 100) if total else 0
            swap_value = f"{used/1024:.1f} GiB / {total/1024:.1f} GiB - {pct:.0f}%"

    load = "Not captured"
    lp = str(ev.get("loadavg", "") or "").split()
    if len(lp) >= 3:
        load = f"{lp[0]} / {lp[1]} / {lp[2]}"

    temp_values = []
    thermal_lines = []
    for src in [ev.get("thermal_zones", ""), ev.get("sensors", "")]:
        for line in str(src or "").splitlines():
            original = line.strip()
            if not original:
                continue
            line2 = original.split("(", 1)[0] if any(x in original.lower() for x in ["high =", "crit =", "low ="]) else original
            found = False
            for mm in re.finditer(r"([+-]?[0-9]+(?:\.[0-9]+)?)\s*°?C", line2):
                try:
                    v = float(mm.group(1))
                    if -20 <= v <= 150:
                        temp_values.append(v)
                        found = True
                except Exception:
                    pass
            if found and len(thermal_lines) < 8:
                thermal_lines.append(line2.strip())

    max_temp = f"{max(temp_values):.1f}C" if temp_values else "Not captured"

    lan_ip = "unknown"
    for line in str(ev.get("port_reachability", "") or "").splitlines():
        if line.startswith("HOST_LAN_IP="):
            lan_ip = line.split("=", 1)[1].strip() or "unknown"
            break

    docker_lines = [x for x in str(ev.get("docker_ps", "") or "").splitlines() if x.strip()]
    running_containers = trend_int("running_containers") or len(docker_lines)
    published_ports = trend_int("published_ports")
    lan_reachable = trend_int("lan_reachable_ports")
    localhost_only = trend_int("localhost_only_ports")
    possible_blocked = trend_int("possible_blocked_ports")

    real_alerts = len(n.get("real_alerts", []) or [])
    container_alerts = len(n.get("container_alerts", []) or [])

    smart_markers = trend_int("smart_warning_markers")
    nvme_markers = trend_int("nvme_warning_markers")

    zfw_status = str(ev.get("zfw_status", "") or "not captured").strip()
    zbrain_security = str(ev.get("self_docker_security", "") or "not captured").strip()
    zbrain_security = re.sub(r"\s+", " ", zbrain_security)

    tiles = [
        ("CPU", cpu_model, "verified host CPU model"),
        ("CPU USE", cpu_usage, "1 second live sample"),
        ("CORES", lscpu_value("Core(s) per socket"), f"{lscpu_value('CPU(s)')} logical CPUs"),
        ("MEM", mem_value, mem_note),
        ("SWAP", swap_value, "host swap usage"),
        ("LOAD", load, "1 / 5 / 15 minute load"),
        ("TEMP", max_temp, "highest live sensor reading"),
        ("UPTIME", str(ev.get("uptime", "") or "Not captured").strip(), "host uptime"),
        ("OS", os_value("PRETTY_NAME"), "host operating system"),
        ("KERNEL", str(ev.get("kernel", "") or "Not captured").strip(), "running kernel"),
        ("SATA / USB", str(count_lsblk("sd")), "physical SATA/USB drives detected"),
        ("NVMe Drives", str(count_lsblk("nvme")), "physical NVMe drives detected"),
        ("Containers", str(running_containers), "running containers"),
        ("Published Ports", str(published_ports), "container ports published to host"),
        ("Open on LAN", str(lan_reachable), f"reachable on LAN IP {lan_ip}"),
        ("Local Only", str(localhost_only), "ports only reachable from this host"),
        ("Blocked or Hidden", str(possible_blocked), "possible firewall, ZFW, VLAN, or bind blocks"),
        ("Dashboard Alerts", str(real_alerts + container_alerts), f"{real_alerts} hardware/storage / {container_alerts} container"),
        ("Storage Review", str(smart_markers), "SMART items to review, not a failure count"),
        ("NVMe Review", str(nvme_markers), "NVMe items to review, not a failure count"),
        ("Firewall", zfw_status, "ZFW firewall service status"),
    ]

    tile_html = ""
    for title, value, note in tiles:
        tile_html += (
            '<div class="hw-tile">'
            '<div class="hw-title">' + esc(title) + '</div>'
            '<div class="hw-value">' + esc(value) + '</div>'
            '<div class="hw-note">' + esc(note) + '</div>'
            '</div>'
        )

    thermal_html = ""
    if thermal_lines:
        for line in thermal_lines[:8]:
            clean = str(line).strip()
            label = "sensor"
            reading = clean

            m = re.match(r"^([A-Za-z0-9_ .:#/-]+?)\s+([+-]?[0-9]+(?:\.[0-9]+)?\s*°?C)$", clean)
            if m:
                label = m.group(1).strip().rstrip(":")
                reading = m.group(2).strip()
            elif ":" in clean:
                left, right = clean.split(":", 1)
                label = left.strip()
                reading = right.strip()

            thermal_html += '<div class="hw-line"><span>' + esc(label) + '</span><b>' + esc(reading) + '</b></div>'
    else:
        thermal_html = '<div class="hw-line"><span>sensor</span><b>Not captured</b></div>'

    system_html = (
        '<div class="hw-line"><span>host date</span><b>' + esc(str(ev.get("host_date", "") or "Not captured").strip()) + '</b></div>'
        '<div class="hw-line"><span>zfw</span><b>' + esc(zfw_status) + '</b></div>'
        '<div class="hw-line"><span>Security mode</span><b>Elevated Local Verifier</b></div>'
        '<div class="hw-line"><span>Diagnostic access</span><b>' + esc('host mode, Docker socket read-only' if 'PidMode=host' in zbrain_security else zbrain_security[:120]) + '</b></div>'
        '<div class="hw-line"><span>prometheus</span><b>/metrics</b></div>'
    )

    style_html = """
<style>
.host-hw-panel .hw-cockpit {
  margin-top:14px;
  padding:16px;
  border:1px solid rgba(120,255,170,.24);
  background:
    linear-gradient(rgba(110,255,170,.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(110,255,170,.035) 1px, transparent 1px),
    radial-gradient(circle at top left, rgba(120,255,170,.11), transparent 36%),
    #050908;
  background-size:28px 28px, 28px 28px, auto, auto;
  box-shadow:inset 0 0 34px rgba(90,255,150,.07);
  border-radius:12px;
}
.host-hw-panel .hw-topline {
  display:flex;
  align-items:center;
  gap:10px;
  color:#8dffb2;
  font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size:11px;
  letter-spacing:3px;
  margin-bottom:14px;
}
.host-hw-panel .hw-dot {
  width:7px;
  height:7px;
  background:#9cffb3;
  box-shadow:0 0 10px rgba(156,255,179,.75);
  display:inline-block;
}
.host-hw-panel .hw-grid {
  display:grid;
  grid-template-columns:repeat(4, minmax(0, 1fr));
  gap:8px;
}
.host-hw-panel .hw-tile {
  min-height:92px;
  padding:13px;
  border:1px solid rgba(120,255,170,.18);
  background:rgba(4,12,10,.78);
  box-shadow:inset 0 0 18px rgba(100,255,170,.035);
}
.host-hw-panel .hw-title {
  color:#7cff9d;
  font-size:11px;
  font-weight:900;
  letter-spacing:2px;
  font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.host-hw-panel .hw-value {
  color:#eafff0;
  font-size:22px;
  line-height:1.15;
  font-weight:900;
  margin-top:12px;
  word-break:break-word;
}
.host-hw-panel .hw-note {
  color:#9db5aa;
  font-size:12px;
  margin-top:7px;
}
.host-hw-panel .hw-section-title {
  margin-top:16px;
  padding-top:12px;
  border-top:1px solid rgba(120,255,170,.16);
  color:#7cff9d;
  font-size:11px;
  letter-spacing:3px;
  font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-weight:900;
}
.host-hw-panel .hw-lines {
  margin-top:8px;
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:6px 12px;
}
.host-hw-panel .hw-line {
  display:flex;
  justify-content:space-between;
  gap:10px;
  border-bottom:1px solid rgba(120,255,170,.10);
  padding:6px 0;
  color:#9db5aa;
  font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size:12px;
}
.host-hw-panel .hw-line b {
  color:#eafff0;
  font-weight:800;
  text-align:right;
}
@media (max-width:900px) {
  .host-hw-panel .hw-grid { grid-template-columns:repeat(2, minmax(0, 1fr)); }
  .host-hw-panel .hw-lines { grid-template-columns:1fr; }
}
</style>
"""

    return (
        style_html + '<details class="visual-dashboard-panel host-hw-panel">'
        '<summary><span class="visual-dashboard-arrow">&#9656;</span> Show local system metrics cockpit</summary>'
        '<div class="hw-cockpit">'
        '<div class="hw-topline"><span class="hw-dot"></span><span>LOCAL SYSTEM METRICS COCKPIT - VERIFIED EVIDENCE</span></div>'
        '<div class="hw-grid">' + tile_html + '</div>'
        '<div class="hw-section-title">THERMAL EVIDENCE</div>'
        '<div class="hw-lines">' + thermal_html + '</div>'
        '<div class="hw-section-title">SYSTEM / SECURITY / MONITORING</div>'
        '<div class="hw-lines">' + system_html + '</div>'
        '</div>'
        '</details>'
    )


def collect_same_report_evidence():
    return {
        "failed_units": run_host_command("systemctl --failed --plain --no-pager --no-legend 2>/dev/null || true"),
        "active_services": run_host_command("systemctl list-units --type=service --state=running,failed --plain --no-pager --no-legend 2>/dev/null | head -220 || true", timeout=15),
        "service_hotlist": run_host_command("for u in zimaos-welcome.service systemd-networkd-wait-online.service systemd-networkd.service zima-cron-fix.service casaos-gateway.service casaos-user-service.service casaos-local-storage.service docker.service containerd.service; do echo \"===== $u =====\"; systemctl is-active \"$u\" 2>/dev/null || true; systemctl show \"$u\" -p Id -p ActiveState -p SubState -p Result -p MainPID -p ExecMainPID -p ExecMainStatus -p ExecMainStartTimestamp -p FragmentPath --no-pager 2>/dev/null || true; done", timeout=20),
        "process_top": run_host_command("ps -eo pid,ppid,comm,stat,pcpu,pmem,args --sort=-pcpu 2>/dev/null | head -25 || true", timeout=10),
        "io_top": run_host_command("if command -v pidstat >/dev/null 2>&1; then pidstat -d 1 1 2>/dev/null | sed -n '1,80p'; else echo 'pidstat not installed'; echo '---PROC_IO_TOP_APPROX---'; for p in /proc/[0-9]*; do pid=${p##*/}; comm=$(cat \"$p/comm\" 2>/dev/null || true); r=$(awk '/read_bytes/{print $2}' \"$p/io\" 2>/dev/null || echo 0); w=$(awk '/write_bytes/{print $2}' \"$p/io\" 2>/dev/null || echo 0); [ -n \"$comm\" ] && echo \"$r $w $pid $comm\"; done | sort -nrk1,1 -nrk2,2 | head -20; fi", timeout=20),
        "iostat_brief": run_host_command("if command -v iostat >/dev/null 2>&1; then iostat -dx 1 1 2>/dev/null | sed -n '1,100p'; else echo 'iostat not installed'; echo '---DISKSTATS---'; cat /proc/diskstats 2>/dev/null | head -60; fi", timeout=20),
        "lsblk": run_host_command("lsblk -o NAME,PKNAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS 2>/dev/null || true"),
        "mounts": run_host_command("findmnt -P -o SOURCE,TARGET,FSTYPE,OPTIONS 2>/dev/null | grep -Ei 'mergerfs|snapraid|/DATA|/media|\\.media' | grep -v '/docker/overlay2/' | head -160 || true"),
        "media_paths": run_host_command("ls -ld /DATA /DATA/AppData /media /DATA/.media /var/lib/casaos_data/.media 2>/dev/null || true; echo ---MEDIA_ROOTS---; find /media -maxdepth 1 -mindepth 1 -type d -printf '%M %u %g %p\\n' 2>/dev/null | head -80", timeout=12),
        "docker_ps": run_host_command("docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}' 2>/dev/null | head -120 || true"),
        "docker_access": run_host_command(
            "for c in $(docker ps -q 2>/dev/null); do "
            "docker inspect --format '{{.Name}}|{{range .Mounts}}{{.Source}}->{{.Destination}}:{{.RW}};{{end}}|{{range $p,$v := .NetworkSettings.Ports}}{{$p}}=>{{range $v}}{{.HostIp}}:{{.HostPort}},{{end}};{{end}}' $c; "
            "done 2>/dev/null | head -200 || true",
            timeout=20,
        ),
        "nvidia": run_host_command("nvidia-smi -L 2>&1 || true"),
        "smart": run_host_command("for d in /dev/sd?; do echo \"===== SMART $d =====\"; smartctl -H -A \"$d\" 2>&1 | sed -n '1,140p'; done 2>/dev/null || true", timeout=30),
        "nvme_smart": run_host_command("for n in /dev/nvme?n1; do echo \"===== NVME $n =====\"; nvme smart-log \"$n\" 2>&1 | sed -n '1,90p'; done 2>/dev/null || true", timeout=30),
"port_reachability": run_host_command(
            r"""LAN_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')
[ -z "$LAN_IP" ] && LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo "HOST_LAN_IP=${LAN_IP:-unknown}"
docker ps --format '{{.Names}}|{{.Ports}}' 2>/dev/null | while IFS='|' read -r name ports; do
  echo "$ports" | grep -oE '([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:|:::|0.0.0.0:|\[::\]:)?[0-9]+->' | sed 's/.*://;s/->//' | sort -nu | while read -r port; do
    [ -z "$port" ] && continue
    LOCAL="closed"
    LAN="unknown"
    python3 - "$port" <<'PY2' >/dev/null 2>&1 && LOCAL="open"
import socket, sys
port=int(sys.argv[1])
s=socket.create_connection(("127.0.0.1", port), timeout=1.5)
s.close()
PY2
    if [ -n "$LAN_IP" ]; then
      python3 - "$LAN_IP" "$port" <<'PY2' >/dev/null 2>&1 && LAN="open" || LAN="closed"
import socket, sys
host=sys.argv[1]
port=int(sys.argv[2])
s=socket.create_connection((host, port), timeout=1.5)
s.close()
PY2
    fi
    echo "${name}|${port}|localhost=${LOCAL}|lan=${LAN}|lan_ip=${LAN_IP:-unknown}"
  done
done | head -120""",
            timeout=45,
        ),
                "zfw_status": run_host_command("systemctl is-active zfw-ui.service 2>/dev/null || true"),
        "zfw_files": run_host_command("ls -l /var/lib/extensions/zfw.raw /DATA/zfw/zfw /DATA/zfw/rules.json 2>/dev/null || true"),
        "zfw_chains": run_host_command("iptables -S ZFW-IN 2>/dev/null || true; iptables -S ZFW-IN6 2>/dev/null || true; iptables -S DOCKER-USER 2>/dev/null || true"),
        "auditd": run_host_command("systemctl is-active auditd.service 2>/dev/null || true; systemctl status auditd.service --no-pager 2>/dev/null | head -80; echo ---AUDIT_PATHS---; ls -ld /var/log/audit 2>/dev/null || true; ls -l /var/log/audit/audit.log 2>/dev/null || true", timeout=12),
        "self_docker_security": run_host_command("docker inspect zimabrain-ce-flask-8601 --format 'User={{.Config.User}} Privileged={{.HostConfig.Privileged}} PidMode={{.HostConfig.PidMode}} SecurityOpt={{.HostConfig.SecurityOpt}} CapAdd={{.HostConfig.CapAdd}}' 2>/dev/null || true; docker inspect zimabrain-ce-flask-8601 --format '{{range .Mounts}}{{if eq .Destination \"/var/run/docker.sock\"}}DockerSock={{.Source}}:{{.RW}}{{end}}{{end}}' 2>/dev/null || true"),
        "host_os": run_host_command("cat /etc/os-release 2>/dev/null || true"),
        "kernel": run_host_command("uname -r 2>/dev/null || true"),
        "uptime": run_host_command("uptime -p 2>/dev/null || true"),
        "cpu_info": run_host_command("lscpu 2>/dev/null | sed -n '1,45p' || true"),
        "cpu_usage": run_host_command("awk '/^cpu /{u1=$2+$4; t1=$2+$3+$4+$5+$6+$7+$8} END{print u1,t1}' /proc/stat; sleep 1; awk '/^cpu /{u2=$2+$4; t2=$2+$3+$4+$5+$6+$7+$8} END{if ((t2-t1)>0) printf \"CPU_USAGE_PERCENT=%.1f\\n\", (u2-u1)*100/(t2-t1); else print \"CPU_USAGE_PERCENT=unknown\"}' u1=0 t1=0 /proc/stat 2>/dev/null || true"),
        "memory": run_host_command("free -m 2>/dev/null || true; echo; awk '/MemTotal|MemAvailable|SwapTotal|SwapFree/ {print}' /proc/meminfo 2>/dev/null || true"),
        "loadavg": run_host_command("cat /proc/loadavg 2>/dev/null || true"),
        "thermal_zones": run_host_command("for z in /sys/class/thermal/thermal_zone*; do [ -e \"$z/temp\" ] || continue; type=$(cat \"$z/type\" 2>/dev/null || echo unknown); temp=$(cat \"$z/temp\" 2>/dev/null || echo); if [ -n \"$temp\" ]; then awk -v type=\"$type\" -v temp=\"$temp\" 'BEGIN { printf \"%s %.1fC\\n\", type, temp/1000 }'; fi; done 2>/dev/null | head -40 || true"),
        "sensors": run_host_command("sensors 2>/dev/null | sed -n '1,120p' || true"),
        "rauc": run_host_command("rauc status 2>&1 || true"),
        "cmdline": run_host_command("cat /proc/cmdline 2>/dev/null || true"),
        "host_date": run_host_command("date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || true"),
    }


def evaluate_critical_same_report(evidence):
    findings = []
    failed = evidence.get("failed_units", "")
    lsblk_text = evidence.get("lsblk", "")
    mounts = evidence.get("mounts", "")
    docker_ps = evidence.get("docker_ps", "")
    docker_access = evidence.get("docker_access", "")
    nvidia = evidence.get("nvidia", "")

    low_failed = failed.lower()
    low_mounts = mounts.lower()
    low_ps = docker_ps.lower()
    low_access = docker_access.lower()
    low_nvidia = nvidia.lower()

    active_services = evidence.get("active_services", "") or ""
    service_hotlist = evidence.get("service_hotlist", "") or ""
    process_top = evidence.get("process_top", "") or ""
    io_top = evidence.get("io_top", "") or ""
    iostat_brief = evidence.get("iostat_brief", "") or ""
    low_service_hotlist = service_hotlist.lower()
    low_process_top = process_top.lower()
    low_io_top = io_top.lower()

    def _service_block(unit_name):
        marker = f"===== {unit_name} ====="
        if marker not in service_hotlist:
            return ""
        part = service_hotlist.split(marker, 1)[1]
        next_marker = part.find("=====")
        if next_marker >= 0:
            part = part[:next_marker]
        return part.strip()

    def _service_value(block, key):
        prefix = key + "="
        for line in block.splitlines():
            line = line.strip()
            if line.startswith(prefix):
                return line.split("=", 1)[1].strip()
        return ""

    def _pidstat_average_lines():
        rows = []
        for line in io_top.splitlines():
            s = line.strip()
            if not s.startswith("Average:"):
                continue
            if "Command" in s or "UID" in s:
                continue
            parts = s.split()
            if len(parts) < 8:
                continue
            try:
                rd = float(parts[3])
                wr = float(parts[4])
            except Exception:
                continue
            cmd = parts[-1]
            rows.append((rd + wr, rd, wr, cmd, s))
        rows.sort(reverse=True, key=lambda x: x[0])
        return rows

    welcome_block = _service_block("zimaos-welcome.service")
    if welcome_block:
        welcome_state = _service_value(welcome_block, "ActiveState")
        welcome_sub = _service_value(welcome_block, "SubState")
        welcome_result = _service_value(welcome_block, "Result")
        level = "YELLOW" if welcome_state == "failed" or welcome_result not in ("", "success") else "INFO"
        title = "zimaos-welcome service status captured"
        if welcome_state == "inactive" and welcome_result == "success":
            title = "zimaos-welcome is inactive after successful exit"
        elif welcome_state == "active":
            title = "zimaos-welcome is currently active"
        elif welcome_state == "failed":
            title = "zimaos-welcome service failure detected"
        findings.append({
            "level": level,
            "title": title,
            "detail": welcome_block[:700],
            "why": "Service-specific status is now captured so questions about zimaos-welcome do not fall back to generic guidance.",
            "next": "If the user reports UI, welcome, or first-run behaviour, compare this status with journal evidence before restarting services.",
        })

    wait_block = _service_block("systemd-networkd-wait-online.service")
    if wait_block:
        wait_state = _service_value(wait_block, "ActiveState")
        wait_result = _service_value(wait_block, "Result")
        if wait_state == "failed" or "systemd-networkd-wait-online.service" in low_failed:
            findings.append({
                "level": "YELLOW",
                "title": "systemd-networkd-wait-online service failure detected",
                "detail": wait_block[:700],
                "why": "This failed unit can explain boot/wait-online differences between exported reports.",
                "next": "Compare this service status with /proc/cmdline and the matching export timestamp before blaming kernel parameters.",
            })
        elif wait_state == "inactive" and wait_result == "success":
            findings.append({
                "level": "INFO",
                "title": "systemd-networkd-wait-online is not currently failed",
                "detail": wait_block[:700],
                "why": "The service is present in the hotlist and currently exited successfully, which helps compare default vs modified cmdline reports.",
                "next": "If another report shows this unit failed, treat it as a confirmed report-to-report state change, not yet as proof of root cause.",
            })

    pidstat_rows = _pidstat_average_lines()
    if pidstat_rows:
        total, rd, wr, cmd, raw = pidstat_rows[0]
        if total >= 500 and "python" not in cmd.lower():
            findings.append({
                "level": "INFO",
                "title": "Active disk I/O process observed",
                "detail": raw,
                "why": "pidstat captured a process doing measurable disk I/O during the report. This helps diagnose unusual disk activity instead of relying only on SMART data.",
                "next": "If the user reports constant disk activity, ask whether this process remains on top across repeated exports.",
            })

    cpu_lines = []
    for line in process_top.splitlines()[1:12]:
        parts = line.split(None, 6)
        if len(parts) < 7:
            continue
        try:
            pcpu = float(parts[4])
        except Exception:
            continue
        cmdline = parts[6]
        noisy_collectors = ("collect_same_report_evidence", "python3 -", "ps -eo ", " sort=", "head -25")
        if pcpu >= 50 and not any(x in cmdline for x in noisy_collectors):
            cpu_lines.append(line.strip())
    if cpu_lines:
        findings.append({
            "level": "YELLOW",
            "title": "High CPU process observed during report",
            "detail": "\n".join(cpu_lines[:5]),
            "why": "A process was using high CPU while the report was collected. This can help explain loaded CPU symptoms or regressions.",
            "next": "Re-run the report after a few minutes and confirm whether the same process remains high before restarting anything.",
        })

    auditd = evidence.get("auditd", "")
    low_auditd = auditd.lower()
    audit_lines = [x.strip() for x in auditd.splitlines() if x.strip()]
    audit_path_lines = [x for x in audit_lines if "/var/log/audit" in x]

    if "auditd.service" in low_auditd and ("failed" in low_auditd or "inactive" in low_auditd or "permission denied" in low_auditd):
        expected_dir = any("drwx------" in x and "root root" in x and "/var/log/audit" in x for x in audit_path_lines)
        expected_log = any("-rw-------" in x and "root root" in x and "audit.log" in x for x in audit_path_lines)
        bad_owner_or_mode = bool(audit_path_lines) and not (expected_dir and expected_log)

        if bad_owner_or_mode or "permission denied" in low_auditd:
            findings.append({
                "level": "YELLOW",
                "title": "auditd may be failing from audit log ownership or permissions",
                "detail": "\n".join(audit_path_lines[:4]) or auditd[:300],
                "why": "auditd normally needs /var/log/audit owned by root:root with restrictive permissions. Wrong ownership or mode can stop audit logging.",
                "next": "Verify /var/log/audit and audit.log ownership/mode before restarting auditd or changing audit rules.",
            })
        else:
            findings.append({
                "level": "YELLOW",
                "title": "auditd service issue detected",
                "detail": auditd[:300],
                "why": "auditd is not active or has failure evidence, but ownership/permission root cause was not confirmed from this report.",
                "next": "Collect auditd status, journal, and /var/log/audit ownership/mode before repair.",
            })

    media_paths = evidence.get("media_paths", "")
    media_lines = [x.strip() for x in mounts.splitlines() if x.strip()]
    path_lines = [x.strip() for x in media_paths.splitlines() if x.strip()]
    odd_media_targets = [x for x in media_lines if "/media/" in x and "-/dev/" in x]
    readonly_media = [x for x in media_lines if 'TARGET="/media/' in x and 'OPTIONS="ro,' in x]
    readonly_non_iso = [x for x in readonly_media if 'FSTYPE="iso9660"' not in x]
    appdata_line = next((x for x in path_lines if " /DATA/AppData -> " in x or "/DATA/AppData ->" in x), "")
    has_data_media = any("/DATA/.media" in x for x in path_lines)
    has_casa_media = any("/var/lib/casaos_data/.media" in x for x in path_lines)

    if odd_media_targets:
        findings.append({
            "level": "YELLOW",
            "title": "Files/AppData media mount naming issue detected",
            "detail": "\n".join(odd_media_targets[:4]),
            "why": "A media target contains an embedded device path such as -/dev/sdb. This can confuse Files app paths, AppData paths, and Docker bind paths.",
            "next": "Verify local-storage metadata and current mount names before moving AppData or editing containers.",
        })

    if readonly_non_iso:
        findings.append({
            "level": "YELLOW",
            "title": "Writable media path appears mounted read-only",
            "detail": "\n".join(readonly_non_iso[:4]),
            "why": "A non-ISO media mount is read-only. Apps may show files but fail to write, delete, upload, or update AppData.",
            "next": "Confirm filesystem health and mount options before changing permissions.",
        })

    if readonly_media and not readonly_non_iso:
        findings.append({
            "level": "INFO",
            "title": "Read-only ISO/media mount detected",
            "detail": "\n".join(readonly_media[:3]),
            "why": "Read-only iso9660 media is expected for installer/ISO-style mounts and should not be treated as a storage failure.",
            "next": "Ignore this unless the user expected the device to be writable storage.",
        })

    if appdata_line:
        findings.append({
            "level": "INFO",
            "title": "AppData symlink target detected",
            "detail": appdata_line,
            "why": "ZimaOS AppData is redirected through a symlink. App issues should verify both /DATA/AppData and the real target path.",
            "next": "Check the symlink target mount before diagnosing AppData, Files, or container volume issues.",
        })

    if not has_data_media or not has_casa_media:
        findings.append({
            "level": "YELLOW",
            "title": "ZimaOS media mirror path missing",
            "detail": media_paths[:300],
            "why": "ZimaOS normally exposes storage through /media, /DATA/.media, and /var/lib/casaos_data/.media. Missing mirror paths can cause Files app or app path confusion.",
            "next": "Verify ZimaOS local-storage state before treating this as an app problem.",
        })

    if failed.strip():
        findings.append({
            "level": "YELLOW",
            "title": "Failed systemd unit detected",
            "detail": failed.splitlines()[0],
            "why": "A failed host unit can indicate a broken scheduled task, service, or maintenance layer.",
            "next": "Inspect the exact failed unit before changing anything.",
        })

    if "snapraid-sync.service" in low_failed and "failed" in low_failed:
        level = "RED" if ("mergerfs" in low_mounts or "snapraid" in low_mounts) else "YELLOW"
        findings.append({
            "level": level,
            "title": "DATA PROTECTION MAY BE DOWN",
            "detail": "snapraid-sync.service is failed in the same host report.",
            "why": "If a mergerfs/SnapRAID pool depends on this sync, parity protection is not completing.",
            "next": "Check journalctl -u snapraid-sync and verify SnapRAID config/parity before trusting protection.",
        })

    # Holger rule: data + parity partitions on same physical disk.
    sr_rows = []
    for raw in lsblk_text.splitlines():
        line = raw.strip()
        if "SR-DATA" in line or "SR-PARITY" in line:
            sr_rows.append(line)

    if sr_rows:
        physical_roots = set()
        has_data = False
        has_parity = False

        for line in sr_rows:
            parts = line.split()
            if not parts:
                continue
            name = parts[0].replace("└─", "").replace("├─", "")
            root = name
            if name.startswith("sd") and len(name) > 3:
                root = name[:3]
            if "SR-DATA" in line:
                has_data = True
            if "SR-PARITY" in line:
                has_parity = True
            physical_roots.add(root)

        if has_data and has_parity and len(physical_roots) == 1:
            findings.append({
                "level": "RED",
                "title": "SnapRAID parity has no physical fault tolerance",
                "detail": "Data and parity labels appear on the same physical disk.",
                "why": "If that disk dies, both data and parity die together.",
                "next": "Move parity to a separate physical disk before treating the pool as protected.",
            })

    # Exposed full data access rule.
    for raw in docker_access.splitlines():
        line = raw.strip()
        if not line or "|" not in line:
            continue

        name = line.split("|", 1)[0].lstrip("/")
        line_low = line.lower()

        # Strict Holger rule:
        # flag only full host /DATA mounted back as /DATA read-write,
        # not normal app folders like /DATA/AppData/app -> /data.
        has_full_data_rw = (
            "/DATA->/DATA:True" in line
            or "/DATA->/DATA:true" in line
            or "/DATA->/DATA:rw" in line
            or "/host/DATA->/DATA:True" in line
            or "/host/DATA->/DATA:true" in line
            or "/host/DATA->/DATA:rw" in line
        )

        publishes_lan = (
            "0.0.0.0:" in line_low
            or ":::" in line_low
            or "192.168." in line_low
            or "10." in line_low
        )

        if has_full_data_rw and publishes_lan:
            findings.append({
                "level": "RED",
                "title": "Container has full /DATA write access and published ports",
                "detail": name,
                "why": "A no-auth web/VNC/desktop service here could expose all user data to the network.",
                "next": "Verify authentication and restrict/firewall the published ports before trusting it.",
            })

    # exFAT warning.
    exfat_rows = [line.strip() for line in lsblk_text.splitlines() if " exfat " in f" {line.lower()} "]
    if exfat_rows:
        findings.append({
            "level": "YELLOW",
            "title": "exFAT storage detected",
            "detail": "; ".join(exfat_rows[:3]),
            "why": "exFAT has no POSIX permissions and no journaling, so it is weaker for NAS workload safety.",
            "next": "Use exFAT only when portability is required, and avoid treating it like a robust NAS filesystem.",
        })

    # GPU runtime warning.
    ai_running = ("ollama" in low_ps or "open-webui" in low_ps or "pdf-ai" in low_ps)
    gpu_bad = (
        "failed" in low_nvidia
        or "not found" in low_nvidia
        or "couldn't communicate" in low_nvidia
        or "no devices were found" in low_nvidia
        or "error" in low_nvidia
    )

    if ai_running and gpu_bad:
        findings.append({
            "level": "YELLOW",
            "title": "GPU acceleration may not be active",
            "detail": nvidia.splitlines()[0] if nvidia.strip() else "nvidia-smi returned no GPU.",
            "why": "AI containers may be running CPU-only even though GPU workloads are expected.",
            "next": "Verify nvidia-smi and container GPU runtime before assuming Ollama/Open WebUI is GPU accelerated.",
        })

    return findings


def critical_badge(level):
    if level == "RED":
        return "🔴 RED"
    if level == "YELLOW":
        return "🟡 YELLOW"
    return "ℹ️ INFO"


def _count_published_ports_from_evidence(evidence):
    text = evidence.get("port_reachability", "") or ""
    count = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("HOST_LAN_IP="):
            continue
        parts = line.split("|")
        if len(parts) >= 5:
            count += 1
    return count


def _count_reachability_groups(evidence):
    text = evidence.get("port_reachability", "") or ""
    lan_reachable = 0
    localhost_only = 0
    possible_blocked = 0

    bind_map = {}
    docker_access = evidence.get("docker_access", "") or ""

    for raw in docker_access.splitlines():
        parts = raw.strip().split("|", 2)
        if len(parts) != 3:
            continue
        name = parts[0].lstrip("/")
        port_blob = parts[2]
        for item in port_blob.split(";"):
            if "=>" not in item:
                continue
            right = item.split("=>", 1)[1]
            for hp in right.split(","):
                hp = hp.strip()
                if not hp or ":" not in hp:
                    continue
                host_ip, host_port = hp.rsplit(":", 1)
                host_ip = host_ip.strip("[]") or "unknown"
                host_port = host_port.strip()
                if host_port.isdigit():
                    bind_map.setdefault((name, host_port), set()).add(host_ip)

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("HOST_LAN_IP="):
            continue

        parts = line.split("|")
        if len(parts) < 5:
            continue

        name = parts[0].strip()
        port = parts[1].strip()
        localhost = ""
        lan = ""

        for part in parts[2:]:
            if part.startswith("localhost="):
                localhost = part.split("=", 1)[1].strip()
            elif part.startswith("lan="):
                lan = part.split("=", 1)[1].strip()

        bind_ips = bind_map.get((name, port), set())
        localhost_bind = bool(bind_ips) and all(ip in {"127.0.0.1", "::1", "localhost"} for ip in bind_ips)

        if lan == "open":
            lan_reachable += 1
        elif localhost == "open" and lan == "closed" and localhost_bind:
            localhost_only += 1
        elif localhost == "open" and lan == "closed":
            possible_blocked += 1

    return lan_reachable, localhost_only, possible_blocked


def _count_smart_warnings(evidence):
    smart = (evidence.get("smart", "") or "").lower()
    nvme = (evidence.get("nvme_smart", "") or "").lower()

    smart_warnings = 0
    nvme_warnings = 0

    for marker in [
        "reallocated_sector_ct",
        "current_pending_sector",
        "offline_uncorrectable",
        "udma_crc_error_count",
        "smart overall-health self-assessment test result: failed",
        "smart support is: unavailable",
        "unknown usb bridge",
        "please specify device type",
    ]:
        if marker in smart:
            smart_warnings += 1

    for marker in [
        "critical_warning",
        "media_errors",
        "num_err_log_entries",
        "unsafe_shutdowns",
    ]:
        if marker in nvme:
            nvme_warnings += 1

    return smart_warnings, nvme_warnings


def _count_running_containers(evidence):
    docker_ps = evidence.get("docker_ps", "") or ""
    count = 0
    for line in docker_ps.splitlines():
        if "|" in line:
            count += 1
    return count


def record_trend_snapshot(bundle):
    try:
        evidence = bundle.get("same_report_evidence", {}) if isinstance(bundle, dict) else {}

        published_ports = _count_published_ports_from_evidence(evidence)
        lan_reachable, localhost_only, possible_blocked = _count_reachability_groups(evidence)
        smart_warnings, nvme_warnings = _count_smart_warnings(evidence)
        running_containers = _count_running_containers(evidence)

        with sqlite3.connect(TREND_DB_PATH, timeout=5) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS trend_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    app_version TEXT NOT NULL,
                    running_containers INTEGER NOT NULL,
                    published_ports INTEGER NOT NULL,
                    lan_reachable_ports INTEGER NOT NULL,
                    localhost_only_ports INTEGER NOT NULL,
                    possible_blocked_ports INTEGER NOT NULL,
                    smart_warning_markers INTEGER NOT NULL,
                    nvme_warning_markers INTEGER NOT NULL
                )
            """)
            con.execute("""
                INSERT INTO trend_snapshots (
                    created_at,
                    app_version,
                    running_containers,
                    published_ports,
                    lan_reachable_ports,
                    localhost_only_ports,
                    possible_blocked_ports,
                    smart_warning_markers,
                    nvme_warning_markers
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                APP_VERSION,
                running_containers,
                published_ports,
                lan_reachable,
                localhost_only,
                possible_blocked,
                smart_warnings,
                nvme_warnings,
            ))
            con.commit()

        return {
            "ok": True,
            "running_containers": running_containers,
            "published_ports": published_ports,
            "lan_reachable_ports": lan_reachable,
            "localhost_only_ports": localhost_only,
            "possible_blocked_ports": possible_blocked,
            "smart_warning_markers": smart_warnings,
            "nvme_warning_markers": nvme_warnings,
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }



def dashboard_bundle():
    global DASHBOARD_REPORT, DASHBOARD_STATUS

    if not DASHBOARD_REPORT.strip():
        try:
            DASHBOARD_REPORT = fetch_dashboard_report()
            DASHBOARD_STATUS = f"Dashboard evidence loaded: {len(DASHBOARD_REPORT):,} characters."
        except Exception as e:
            DASHBOARD_STATUS = f"Dashboard evidence unavailable: {e}"

    alerts = parse_dashboard_alerts(DASHBOARD_REPORT)
    disks = parse_dashboard_disks(DASHBOARD_REPORT)
    exited = parse_dashboard_exited_containers(DASHBOARD_REPORT)
    container_count = parse_dashboard_container_count(DASHBOARD_REPORT)

    same_report_evidence = collect_same_report_evidence()
    normalized = normalize_dashboard_evidence(alerts, disks, exited)
    critical_findings = evaluate_critical_same_report(same_report_evidence)

    bundle = {
        "report": DASHBOARD_REPORT,
        "status": DASHBOARD_STATUS,
        "alerts": alerts,
        "disks": disks,
        "exited": exited,
        "container_count": container_count,
        "normalized": normalized,
        "same_report_evidence": same_report_evidence,
        "critical_findings": critical_findings,
    }

    bundle["trend_snapshot"] = record_trend_snapshot(bundle)

    return bundle



def run_host_shell(command, timeout=12):
    try:
        return subprocess.check_output(
            ["nsenter", "-t", "1", "-m", "-u", "-n", "-i", "--", "sh", "-lc", command],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        ).strip()
    except subprocess.CalledProcessError as e:
        return (e.output or "").strip()
    except Exception as e:
        return f"ERROR: {e}"


def parse_lsblk_pairs(text):
    rows = []
    for line in text.splitlines():
        item = {}
        for key, value in re.findall(r'(\w+)="([^"]*)"', line):
            item[key] = value
        if item:
            rows.append(item)
    return rows




def extract_failed_unit_name(line):
    clean = line.replace("●", " ").strip()
    for token in clean.split():
        token = token.strip()
        if re.search(r'\.(service|timer|mount|socket)$', token):
            return token
    return clean.split()[0] if clean else ""


def shell_quote(value):
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def parse_systemctl_show(text):
    props = {}
    for raw in text.splitlines():
        if "=" in raw:
            key, value = raw.split("=", 1)
            props[key.strip()] = value.strip()
    return props


def execstart_paths(execstart):
    paths = []
    for match in re.findall(r'(?<![\w.-])/(?:[A-Za-z0-9._@:+-]+/?)+', execstart or ""):
        p = match.rstrip(" ;,}")
        if p and p not in paths:
            paths.append(p)
    return paths


def docker_exec_tokens(execstart):
    text = execstart or ""
    m = re.search(r'argv\[\]=([^}]*)', text)
    raw = m.group(1) if m else text
    return [x.strip(" ;'\\\"") for x in raw.split() if x.strip(" ;'\\\"")]


def detect_docker_name_mismatch(execstart):
    tokens = docker_exec_tokens(execstart)
    if not tokens or not any(t.endswith("/docker") or t == "docker" for t in tokens):
        return None

    docker_verbs = {"start", "restart", "stop", "exec", "logs", "inspect"}
    target = ""

    for i, t in enumerate(tokens):
        if t in docker_verbs and i + 1 < len(tokens):
            target = tokens[i + 1]
            break

    if not target or target.startswith("-"):
        return None

    names = run_host_shell("docker ps -a --format '{{.Names}}' 2>/dev/null || true", timeout=12).splitlines()
    names = [n.strip() for n in names if n.strip()]

    if target in names:
        return None

    matches = [n for n in names if target.lower() in n.lower() or n.lower() in target.lower()]
    if matches:
        return {"old_name": target, "possible_names": matches[:5]}

    return {"old_name": target, "possible_names": []}


def related_service_name(unit):
    if not unit:
        return ""
    if unit.endswith("-watchdog.service"):
        return unit.replace("-watchdog.service", ".service")
    if unit.endswith("-delay.service"):
        return unit.replace("-delay.service", ".service")
    return ""


def related_service_state(unit):
    related = related_service_name(unit)
    if not related:
        return None

    out = run_host_shell(
        "systemctl show "
        + shell_quote(related)
        + " -p Id -p LoadState -p ActiveState -p SubState --no-pager 2>/dev/null || true",
        timeout=8,
    )
    props = parse_systemctl_show(out)
    if not props.get("Id"):
        return None

    return {
        "unit": related,
        "active": props.get("ActiveState", ""),
        "sub": props.get("SubState", ""),
        "load": props.get("LoadState", ""),
    }


def path_state(path):
    out = run_host_shell(f"test -e {shell_quote(path)} && echo EXISTS || echo MISSING", timeout=5)
    return "EXISTS" if "EXISTS" in out else "MISSING"


def build_failed_unit_finding(line):
    unit = extract_failed_unit_name(line)
    raw_line = line.strip()

    if "snapraid-sync.service" in raw_line:
        return {
            "level": "RED",
            "title": "DATA PROTECTION IS DOWN",
            "evidence": "systemctl --failed shows snapraid-sync.service failed.",
            "detail": "systemctl --failed shows snapraid-sync.service failed.",
            "why": "SnapRAID sync is not completing, so parity protection is not current.",
            "next": "Check journalctl -u snapraid-sync and fix the SnapRAID config/parity before relying on the pool.",
        }

    show = ""
    props = {}
    if unit:
        show = run_host_shell(
            "systemctl show "
            + shell_quote(unit)
            + " -p Id -p LoadState -p ActiveState -p SubState -p Result -p FragmentPath "
              "-p ExecMainStatus -p ExecMainCode -p ActiveEnterTimestamp -p InactiveEnterTimestamp -p StateChangeTimestamp -p ExecStart -p ExecStartPre -p ExecStartPost --no-pager 2>/dev/null || true",
            timeout=10,
        )
        props = parse_systemctl_show(show)

    fragment = props.get("FragmentPath", "")
    execstart = props.get("ExecStart", "")
    active = props.get("ActiveState", "")
    sub = props.get("SubState", "")
    result = props.get("Result", "")
    status = props.get("ExecMainStatus", "")
    state_change = props.get("StateChangeTimestamp", "")
    active_enter = props.get("ActiveEnterTimestamp", "")

    checked_paths = []
    missing_paths = []

    for p in ([fragment] if fragment else []) + execstart_paths(execstart):
        if not p or p in checked_paths:
            continue
        checked_paths.append(p)
        if path_state(p) == "MISSING":
            missing_paths.append(p)

    evidence_parts = [raw_line]
    if unit:
        evidence_parts.append(f"unit={unit}")
    if active or sub or result:
        evidence_parts.append(f"state={active}/{sub}, result={result}, exit={status}")
    if state_change:
        evidence_parts.append(f"failed_since={state_change}")
    elif active_enter:
        evidence_parts.append(f"active_since={active_enter}")
    if fragment:
        evidence_parts.append(f"unit_file={fragment}")
    if execstart:
        evidence_parts.append(f"exec={execstart}")
    if checked_paths:
        evidence_parts.append("checked_paths=" + ", ".join(checked_paths))
    if missing_paths:
        evidence_parts.append("missing_paths=" + ", ".join(missing_paths))

    title = "Failed systemd unit detected"
    why = "A failed host unit can indicate a broken scheduled task or system helper."
    next_step = "Inspect only this failed unit before changing unrelated services."

    docker_mismatch = detect_docker_name_mismatch(execstart)
    related_state = related_service_state(unit)

    missing_os_paths = [
        p for p in missing_paths
        if p.startswith(("/usr/libexec/", "/usr/lib/systemd/", "/usr/bin/", "/usr/sbin/", "/lib/systemd/"))
    ]
    missing_data_paths = [p for p in missing_paths if p.startswith("/DATA/")]

    if missing_os_paths:
        title = "Possible ZimaOS packaging regression"
        why = "The failed unit references an OS-managed helper or executable that is missing from the host image."
        next_step = "Verify the ZimaOS version and failed unit evidence before treating this as local configuration damage."
    elif missing_data_paths:
        title = "Failed systemd unit references missing local AppData/DATA path"
        why = "The unit points to a local /DATA path that is not present on the host."
        next_step = "Verify whether the path was removed, moved, or belongs to an obsolete local service before changing anything."
    elif missing_paths:
        title = "Failed systemd unit references missing file/path"
        why = "The unit points to a file or path that is not present on the host."
        next_step = "Verify the missing path and whether the unit is obsolete before changing services."
    elif docker_mismatch:
        title = "Failed systemd unit may reference old Docker container name"
        evidence_parts.append("docker_reference=" + docker_mismatch["old_name"])
        if docker_mismatch.get("possible_names"):
            evidence_parts.append("possible_current_container=" + ", ".join(docker_mismatch["possible_names"]))
        why = "The unit appears to call Docker with a container name that does not exist, while a similar current container name may exist."
        next_step = "Verify the service file container name against docker ps -a before restarting or editing the unit."
    elif related_state and related_state.get("active") == "active":
        title = "Failed watchdog/helper unit, but related service is running"
        evidence_parts.append(
            "related_service="
            + related_state["unit"]
            + " "
            + related_state.get("active", "")
            + "/"
            + related_state.get("sub", "")
        )
        why = "The failed unit appears to be a helper/watchdog, while the main related service is currently active."
        next_step = "Verify whether the helper failure is historical before restarting the main service."
    elif unit and "cron" in (unit + " " + execstart).lower():
        cron_ps = run_host_shell("ps -ef | grep -E '[c]rond|[c]ron' || true", timeout=8)
        if cron_ps.strip():
            title = "Failed systemd unit, but related cron process is running"
            evidence_parts.append("related_process=cron/crond process currently exists")
            why = "This may be a historical failed helper or duplicate cron unit rather than a current cron outage."
            next_step = "Verify whether this old cron-fix unit is still required before changing or disabling it."

    evidence = " | ".join(evidence_parts)

    return {
        "level": "YELLOW",
        "title": title,
        "evidence": evidence,
        "detail": evidence,
        "why": why,
        "next": next_step,
    }


def collect_critical_verifier():
    findings = []
    facts = []

    failed_units = run_host_shell("systemctl --failed --plain --no-pager --no-legend 2>/dev/null || true")
    lsblk_text = run_host_shell("lsblk -P -o NAME,PKNAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS 2>/dev/null || true")
    mounts_text = run_host_shell("findmnt -o SOURCE,TARGET,FSTYPE,OPTIONS 2>/dev/null | grep -Ei 'mergerfs|snapraid|/DATA|/media' | head -250 || true")
    docker_ps = run_host_shell("docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || true", timeout=15)
    docker_inspect = run_host_shell(
        "for id in $(docker ps -q 2>/dev/null); do docker inspect --format '{{.Name}}|{{range .Mounts}}{{.Source}}>{{.Destination}}>{{.RW}};{{end}}|{{json .NetworkSettings.Ports}}' \"$id\"; done 2>/dev/null || true",
        timeout=25,
    )
    docker_user = run_host_shell("iptables -S DOCKER-USER 2>/dev/null || true")
    gpu_text = run_host_shell("docker info 2>/dev/null | grep -i -A4 'Runtimes' || true; echo '---NVIDIA---'; nvidia-smi -L 2>&1 || true", timeout=12)

    failed_lower = failed_units.lower()
    mounts_lower = mounts_text.lower()
    docker_lower = docker_ps.lower()
    gpu_lower = gpu_text.lower()

    if failed_units.strip():
        facts.append("systemctl --failed returned one or more failed units.")
        for line in failed_units.splitlines():
            if line.strip():
                findings.append(build_failed_unit_finding(line))

    mergerfs_mounted = "mergerfs" in mounts_lower
    if mergerfs_mounted:
        facts.append("A mergerfs mount is present in findmnt output.")

    if "snapraid-sync.service" in failed_lower and mergerfs_mounted:
        findings.append({
            "level": "RED",
            "title": "MergerFS pool present while SnapRAID sync is failed",
            "evidence": "findmnt shows mergerfs and systemctl --failed shows snapraid-sync.service failed.",
            "why": "The pool may look usable, but parity protection is not completing.",
            "next": "Fix SnapRAID sync first, then verify snapraid status/sync/scrub.",
        })

    rows = parse_lsblk_pairs(lsblk_text)
    sr_data = []
    sr_parity = []

    for r in rows:
        label = r.get("LABEL", "")
        fstype = r.get("FSTYPE", "")
        name = r.get("NAME", "")
        pkname = r.get("PKNAME", "") or name
        size = r.get("SIZE", "")

        if label.upper().startswith("SR-DATA"):
            sr_data.append((name, pkname, label))
        if "PARITY" in label.upper():
            sr_parity.append((name, pkname, label))

        if fstype.lower() == "exfat":
            findings.append({
                "level": "YELLOW",
                "title": "exFAT disk detected",
                "evidence": f"{name} label={label} size={size} fstype=exfat.",
                "why": "exFAT has no POSIX permissions and no journaling, so it is fragile under NAS workload.",
                "next": "Use it only with clear intent, and verify backups before depending on it.",
            })

    if sr_data and sr_parity:
        data_pk = {x[1] for x in sr_data}
        parity_pk = {x[1] for x in sr_parity}
        overlap = sorted(data_pk.intersection(parity_pk))
        if overlap:
            findings.append({
                "level": "RED",
                "title": "SnapRAID parity is on the same physical disk as data",
                "evidence": f"Data labels {sr_data} and parity labels {sr_parity} share physical disk(s): {', '.join(overlap)}.",
                "why": "If that physical disk fails, data and parity are lost together.",
                "next": "Move parity to a separate physical disk before treating the pool as protected.",
            })

    docker_user_open = "-A DOCKER-USER -j RETURN" in docker_user or "RETURN" in docker_user

    for line in docker_inspect.splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue

        name, mounts, ports = parts
        cname = name.lstrip("/")

        has_data_rw = ">/DATA>true" in mounts or ">/host/DATA>true" in mounts
        has_ports = '"HostPort"' in ports and ports not in ["{}", "null"]

        if has_data_rw and has_ports:
            level = "RED" if docker_user_open else "YELLOW"
            findings.append({
                "level": level,
                "title": "Published container has full read-write /DATA access",
                "evidence": f"{cname} has /DATA rw and published ports: {ports[:240]}",
                "why": "If the service has no authentication or weak authentication, LAN access can become full data access.",
                "next": "Verify authentication and firewall exposure for this container before exposing it further.",
            })

    if ("ollama" in docker_lower or "open-webui" in docker_lower) and (
        "failed" in gpu_lower
        or "not found" in gpu_lower
        or "couldn't communicate" in gpu_lower
        or "no devices were found" in gpu_lower
    ):
        findings.append({
            "level": "YELLOW",
            "title": "GPU acceleration may not be active",
            "evidence": "ollama/open-webui is running, but nvidia-smi did not return a usable GPU list.",
            "why": "AI containers may be running CPU-only even if GPU runtime appears configured.",
            "next": "Verify nvidia-smi on host and inside the intended AI container before assuming GPU acceleration.",
        })

    if not facts:
        facts.append("Critical verifier collected host evidence but found no high-confidence structural facts.")

    red_count = len([f for f in findings if f["level"] == "RED"])
    yellow_count = len([f for f in findings if f["level"] == "YELLOW"])

    return {
        "findings": findings,
        "facts": facts,
        "red_count": red_count,
        "yellow_count": yellow_count,
    }


def critical_to_text(critical):
    lines = []
    findings = critical.get("findings", [])

    if not findings:
        lines.append("- No RED/YELLOW same-report critical findings were detected by the current verifier layer.")
        return lines

    for item in findings:
        icon = "🔴" if item["level"] == "RED" else "🟡"
        lines.append(f"- {icon} {item['level']}: {item['title']}")
        lines.append(f"  Evidence: {item['evidence']}")
        lines.append(f"  Why it matters: {item['why']}")
        lines.append(f"  Next safest step: {item['next']}")

    return lines




def build_verifier_summary(bundle):
    n = bundle["normalized"]
    critical = bundle.get("critical_findings", [])
    summary = []

    summary.append("#### Top verified issues")

    if critical:
        for finding in critical:
            summary.append(f"- {critical_badge(finding['level'])}: {finding['title']}")
    else:
        summary.append("- No critical same-report findings detected.")

    if n.get("real_alerts"):
        for alert in n["real_alerts"]:
            summary.append(f"- {severity_dot(alert)}")

    if n.get("container_alerts"):
        summary.append(f"- 🟡 YELLOW: {len(n['container_alerts'])} exited container/service alerts")

    if n.get("info_alerts"):
        summary.append(f"- ℹ️ INFO: {len(n['info_alerts'])} unsupported/N/A SMART metrics, not confirmed disk failures")

    summary.append("")
    summary.append("#### Checked but not detected in this report")

    titles = " ".join(item.get("title", "") for item in critical).lower()

    if "data protection" not in titles and "snapraid-sync" not in titles:
        summary.append("- No failed snapraid-sync.service protection failure was detected in this report.")

    if "physical fault tolerance" not in titles and "same physical disk" not in titles:
        summary.append("- No SnapRAID data/parity-on-same-physical-disk issue was detected in this report.")

    if "full /data write access" not in titles:
        summary.append("- No full host /DATA mounted back as /DATA with published ports was detected in this report.")

    if "gpu acceleration" not in titles:
        summary.append("- No GPU acceleration failure was detected by the current critical rules.")

    return summary




def simplify_mount_line(line):
    # Preferred format from: findmnt -P -o SOURCE,TARGET,FSTYPE,OPTIONS
    pairs = dict(re.findall(r'([A-Z]+)="([^"]*)"', line))

    if pairs:
        source = pairs.get("SOURCE", "")
        target = pairs.get("TARGET", "")
        fstype = pairs.get("FSTYPE", "")
        opts = pairs.get("OPTIONS", "")
        mode = "ro" if opts.startswith("ro") or ",ro" in opts else "rw"

        label = f"{source} -> {target}"
        if fstype:
            label += f" [{fstype}]"
        label += f" {mode}"
        return label.strip()

    # Fallback for older raw findmnt tree output.
    cleaned = line.replace("│", " ").replace("├─", " ").replace("└─", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned



def answer_question(question):
    bundle = dashboard_bundle()
    return answer_builder.answer_question(
        question,
        bundle,
        build_verifier_summary,
        critical_badge,
        severity_dot,
    )





def build_installed_apps_port_map_html(bundle):
    import html
    import re

    evidence = bundle.get("same_report_evidence", {}) if isinstance(bundle, dict) else {}
    docker_ps = evidence.get("docker_ps", "") or ""

    rows = []
    used_ports = {}
    exposed_count = 0

    admin_terms = [
        "portainer", "netdata", "grafana", "prometheus", "open-webui",
        "nextcloud", "immich", "jellyfin", "qbittorrent", "homepage",
        "wazuh", "zima", "webui", "dashboard"
    ]

    def esc(v):
        return html.escape(str(v or ""))

    def extract_host_ports(port_text, app_name):
        ports = []
        for m in re.finditer(r"(?:(0\.0\.0\.0|127\.0\.0\.1|\[::\]|:::|::):)?(\d{2,5})->", port_text or ""):
            host = m.group(1) or ""
            port = m.group(2)
            label = port
            if host in ("0.0.0.0", ":::", "::", "[::]"):
                label = f"{port} LAN"
            elif host == "127.0.0.1":
                label = f"{port} local"
            ports.append(label)
            used_ports.setdefault(port, set()).add(app_name)
        return sorted(set(ports), key=lambda x: int(re.sub(r"\D", "", x) or 0))

    for raw in docker_ps.splitlines():
        line = raw.strip()
        if not line or "|" not in line:
            continue

        parts = line.split("|", 3)
        if len(parts) != 4:
            continue

        name, image, status, ports_text = [x.strip() for x in parts]
        host_ports = extract_host_ports(ports_text, name)

        if not host_ports:
            continue

        low = f"{name} {image} {ports_text}".lower()
        risk = []
        if "0.0.0.0:" in ports_text or ":::" in ports_text or "[::]:" in ports_text:
            risk.append("LAN")
        if any(t in low for t in admin_terms):
            risk.append("Admin UI")

        if "LAN" in risk:
            exposed_count += 1

        rows.append({
            "name": name,
            "image": image,
            "status": status,
            "ports": ", ".join(host_ports),
            "risk": ", ".join(risk) if risk else "Local/check"
        })

    rows = sorted(rows, key=lambda r: r["name"].lower())

    port_badges = []
    for port in sorted(used_ports.keys(), key=lambda x: int(x)):
        apps = ", ".join(sorted(used_ports[port])[:4])
        port_badges.append(
            f"<span title='{esc(apps)}' style='display:inline-block; background:#172554; color:#dbeafe; border:1px solid #3b82f6; border-radius:999px; padding:4px 9px; margin:3px; font-family:Consolas,monospace; font-size:12px;'>{esc(port)}</span>"
        )

    table_rows = []
    for idx, r in enumerate(rows[:120]):
        bg = "background:#0b1220;" if idx % 2 == 0 else "background:#111827;"
        table_rows.append(
            f"<tr style='{bg} border-bottom:1px solid #334155;'>"
            f"<td style='padding:9px 11px; white-space:nowrap;'><strong>{esc(r['name'])}</strong></td>"
            f"<td style='padding:9px 11px; white-space:nowrap;'><code>{esc(r['ports'])}</code></td>"
            f"<td style='padding:9px 11px;'>{esc(r['risk'])}</td>"
            f"<td style='padding:9px 11px; color:#94a3b8;'>{esc(r['status'])}</td>"
            "</tr>"
        )

    if not table_rows:
        table_rows.append("<tr><td colspan='4'>No published Docker host ports were parsed from the current report.</td></tr>")

    return f"""
  <div class="panel">
    <h3>Installed Apps / Port Map</h3>
    <div class="small">Compact port allocation view before adding new apps.</div>

    <div class="chips">
      <span class="chip">Apps with ports: {len(rows)}</span>
      <span class="chip">Unique host ports: {len(used_ports)}</span>
      <span class="chip">LAN exposed: {exposed_count}</span>
    </div>

    <div style="margin-top:12px;">
      <div class="small" style="margin-bottom:6px;">Used host ports</div>
      {''.join(port_badges)}
    </div>

    <details style="margin-top:14px;">
      <summary style="cursor:pointer; font-weight:800; color:#dbeafe;">Show full installed app port table</summary>
      <div style="overflow:auto; margin-top:12px;">
        <table style="width:100%; border-collapse:separate; border-spacing:0 4px; font-size:13px;">
          <thead>
            <tr>
              <th style="text-align:left; padding:10px 12px; border-bottom:2px solid #475569; color:#bfdbfe;">App / Container</th>
              <th style="text-align:left; padding:10px 12px; border-bottom:2px solid #475569; color:#bfdbfe;">Host Ports</th>
              <th style="text-align:left; padding:10px 12px; border-bottom:2px solid #475569; color:#bfdbfe;">Note</th>
              <th style="text-align:left; padding:10px 12px; border-bottom:2px solid #475569; color:#bfdbfe;">State</th>
            </tr>
          </thead>
          <tbody>
            {''.join(table_rows)}
          </tbody>
        </table>
      </div>
    </details>
  </div>
"""


@app.route("/")
def index():
    bundle = dashboard_bundle()
    dashboard_url = ""
    live_visual = False
    dashboard_source_value = "Native"
    dashboard_source_note = "Built-in native visual evidence from this unit"
    n = bundle["normalized"]
    critical = collect_critical_verifier()

    critical_items = critical.get("findings", [])
    critical_html = "".join(
        f"<li>{'🔴' if item['level'] == 'RED' else '🟡'} <b>{esc(item['level'])}: {esc(item['title'])}</b>"
        f"<br><span class='small'>Evidence: {esc(item.get('evidence', item.get('detail', '')))}</span>"
        f"<br><span class='small'>Why: {esc(item.get('why', ''))}</span>"
        f"<br><span class='small'>Next: {esc(item.get('next', ''))}</span>"
        f"</li>"
        for item in critical_items[:8]
    ) or "<li>No same-report critical findings detected.</li>"

    real_items = []
    for meta in n.get("real_alert_details", []):
        real_items.append(
            f"<li>{esc(severity_dot(meta.get('text', '')))}"
            f"<br><span class='small'>Source: {esc(meta.get('source', 'unknown'))}</span>"
            f"<br><span class='small'>Object: {esc(meta.get('object', 'unknown'))}</span>"
            f"<br><span class='small'>Condition: {esc(meta.get('condition', 'unknown'))}</span>"
            f"</li>"
        )

    if not real_items:
        real_items = [f"<li>{esc(severity_dot(a))}</li>" for a in n.get("real_alerts", [])]

    if critical_items:
        real_items.append(f"<li><b>Summary:</b> {len(critical_items)} verified host/system issue(s) detected.</li>")

    for item in critical_items[:8]:
        level = item.get("level", "YELLOW")
        icon = "🔴" if level == "RED" else "🟡"
        real_items.append(
            f"<li>{icon} <b>{esc(level)}: {esc(item.get('title', 'Alert'))}</b>"
            f"<br><span class='small'>Evidence: {esc(item.get('evidence', item.get('detail', '')))}</span>"
            f"<br><span class='small'>Why: {esc(item.get('why', ''))}</span>"
            f"<br><span class='small'>Next: {esc(item.get('next', ''))}</span>"
            f"</li>"
        )

    exited = n.get("exited_containers", []) or []
    mailcow = [c for c in exited if "mailcow" in c.get("name", "").lower()]
    other = [c for c in exited if "mailcow" not in c.get("name", "").lower()]

    info_items = []
    container_items = []
    for meta in n.get("container_alert_details", []):
        container_items.append(
            f"<li>{esc(severity_dot(meta.get('text', '')))}"
            f"<br><span class='small'>Source: {esc(meta.get('source', 'unknown'))}</span>"
            f"<br><span class='small'>Object: {esc(meta.get('object', 'unknown'))}</span>"
            f"<br><span class='small'>Condition: {esc(meta.get('condition', 'unknown'))}</span>"
            f"</li>"
        )

    if not container_items:
        container_items = [f"<li>{esc(severity_dot(a))}</li>" for a in n.get("container_alerts", [])]

    exited_faults = [c for c in exited if c.get("severity") == "YELLOW"]
    exited_expected = [c for c in exited if c.get("severity") == "INFO"]

    if exited:
        container_items.append(
            f"<li><b>Summary:</b> {len(exited_faults)} possible container fault(s), "
            f"{len(exited_expected)} likely intentional/on-demand stopped container(s).</li>"
        )

    if exited_faults:
        fault_list = ""
        for c in exited_faults[:10]:
            name = c.get("name", "unknown").replace("mailcowdockerized-", "").replace("-mailcow-1", "")
            fault_list += (
                f"<li>🟡 <b>YELLOW: Container/service may need attention</b>"
                f"<br><span class='small'>Name: {esc(name)}</span>"
                f"<br><span class='small'>Image: {esc(c.get('image', 'unknown'))}</span>"
                f"<br><span class='small'>Class: {esc(c.get('class', 'unknown'))}</span>"
                f"<br><span class='small'>Reason: {esc(c.get('reason', ''))}</span>"
                f"</li>"
            )
        container_items.append(fault_list)

    if exited_expected:
        expected_list = ""
        for c in exited_expected[:10]:
            name = c.get("name", "unknown")
            expected_list += (
                f"<li>ℹ️ <b>INFO: Exited container appears intentional or on-demand</b>"
                f"<br><span class='small'>Name: {esc(name)}</span>"
                f"<br><span class='small'>Image: {esc(c.get('image', 'unknown'))}</span>"
                f"<br><span class='small'>Class: {esc(c.get('class', 'unknown'))}</span>"
                f"<br><span class='small'>Reason: {esc(c.get('reason', ''))}</span>"
                f"</li>"
            )
        info_items.append(expected_list)

    container_alert_html = "".join(container_items) or "<li>No container/service alerts detected.</li>"

    for meta in n.get("info_alert_details", []):
        info_items.append(
            f"<li>{esc(severity_dot(meta.get('text', '')))}"
            f"<br><span class='small'>Source: {esc(meta.get('source', 'unknown'))}</span>"
            f"<br><span class='small'>Object: {esc(meta.get('object', 'unknown'))}</span>"
            f"<br><span class='small'>Condition: {esc(meta.get('condition', 'unknown'))}</span>"
            f"</li>"
        )

    if not info_items:
        info_items = [f"<li>{esc(severity_dot(a))}</li>" for a in n.get("info_alerts", [])]

    if n.get("unparsed_alert_count", 0):
        examples = ", ".join(str(x) for x in (n.get("unparsed_alerts", []) or [])[:3])
        info_items.append(
            f"<li>ℹ️ <b>INFO: Alert count detected, but underlying alert detail could not be parsed</b>"
            f"<br><span class='small'>Unparsed alert count: {esc(str(n.get('unparsed_alert_count', 0)))}</span>"
            f"<br><span class='small'>Examples: {esc(examples or 'not available')}</span>"
            f"<br><span class='small'>Meaning: ZimaBrain saw an alert count, but could not safely map every alert back to a disk, service, container, or condition.</span>"
            f"</li>"
        )

    disk_ok_count = len(n.get("disk_ok", []) or [])
    disk_attention = n.get("disk_attention", []) or []

    confirmed_disk_attention = []
    unavailable_disk_info = []

    for d in disk_attention:
        issues = d.get("issues", []) or []
        if any("N/A" in str(x) for x in issues):
            unavailable_disk_info.append(d)
        else:
            confirmed_disk_attention.append(d)

    total_disks = disk_ok_count + len(disk_attention)

    for d in confirmed_disk_attention:
        real_items.append(
            f"<li>🟡 <b>YELLOW: Disk/storage issue detected</b>"
            f"<br><span class='small'>Device: {esc(d.get('device', 'unknown'))}</span>"
            f"<br><span class='small'>Mount: {esc(d.get('mount', 'unknown'))}</span>"
            f"<br><span class='small'>Issue: {esc(', '.join(d.get('issues', [])))}</span>"
            f"</li>"
        )

    for d in unavailable_disk_info[:8]:
        info_items.append(
            f"<li>ℹ️ <b>INFO: Disk health value unavailable</b>"
            f"<br><span class='small'>Device: {esc(d.get('device', 'unknown'))}</span>"
            f"<br><span class='small'>Mount: {esc(d.get('mount', 'unknown'))}</span>"
            f"<br><span class='small'>Meaning: SMART value unavailable, not confirmed disk failure.</span>"
            f"</li>"
        )

    real_alert_html = "".join(real_items) or "<li>No real host/storage alerts detected.</li>"

    info_items.append(
        f"<li>ℹ️ <b>INFO: Native evidence check completed</b>"
        f"<br><span class='small'>Dashboard source: built-in native local evidence.</span>"
        f"<br><span class='small'>Disks checked: {total_disks} total, {len(confirmed_disk_attention)} confirmed disk/storage issue(s), {len(unavailable_disk_info)} unavailable value(s).</span>"
        f"<br><span class='small'>Exited containers detected: {len(exited)}.</span>"
        f"</li>"
    )

    info_alert_html = "".join(info_items) or "<li>No info alerts parsed.</li>"

    host_ev = bundle.get("same_report_evidence", {})
    host_os_raw = host_ev.get("host_os", "")
    host_os_name = "Unknown"
    host_os_version = "Unknown"

    for line in host_os_raw.splitlines():
        if line.startswith("PRETTY_NAME="):
            host_os_name = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("VERSION="):
            host_os_version = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("VERSION_ID=") and host_os_version == "Unknown":
            host_os_version = line.split("=", 1)[1].strip().strip('"')

    host_kernel = host_ev.get("kernel", "").strip() or "Unknown"
    host_uptime = host_ev.get("uptime", "").strip() or "Unknown"
    host_date = host_ev.get("host_date", "").strip() or "Unknown"
    self_health_raw = run_host_command("docker inspect zimabrain-ce-flask-8601 --format '{{json .State.Health.Status}}' 2>/dev/null || true").strip().strip('"')
    self_health = self_health_raw if self_health_raw and self_health_raw != "<no value>" else "Unknown"
    host_rauc_raw = host_ev.get("rauc", "").strip()
    host_rauc = "Unavailable"
    if host_rauc_raw and "not found" not in host_rauc_raw.lower():
        useful_rauc = []
        for line in host_rauc_raw.splitlines():
            clean = line.strip()
            low = clean.lower()
            if not clean:
                continue
            if clean.startswith("==="):
                continue
            if "system info" in low:
                continue
            useful_rauc.append(clean)
        host_rauc = (useful_rauc[0] if useful_rauc else "Available")[:120]

    history_html = ""
    for idx, item in enumerate(reversed(SESSION_HISTORY[-5:]), 1):
        history_html += f"""
        <details>
          <summary>{idx}. {esc(item['question'][:55])}</summary>
          <div class="small">{esc(item['time'])}</div>
          <pre>{esc(item['answer'][:350])}</pre>
        </details>
        """

    if not history_html:
        history_html = '<div class="small">No questions asked yet.</div>'

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{APP_NAME}</title>
<style>
:root {{
  --bg:#080b10; --panel:#111722; --panel2:#0d1320; --line:#263241;
  --text:#e8edf2; --muted:#9aa8b5; --blue:#93c5fd; --green:#22c55e;
  --yellow:#facc15; --red:#ef4444;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--bg); color:var(--text);
  font-family: Inter, Arial, sans-serif;
}}
.sidebar {{
  position:fixed; left:0; top:0; bottom:0; width:330px;
  overflow:auto; background:#111722; border-right:1px solid var(--line);
  padding:18px;
}}
.main {{
  margin-left:330px; padding:24px 28px 40px 28px;
}}
h1 {{ font-size:42px; margin:0; }}
.subtitle {{ color:var(--muted); margin-top:6px; }}
.badge {{
  display:inline-block; margin-top:12px; padding:6px 12px;
  border-radius:999px; background:#1e293b; border:1px solid #334155;
  color:var(--blue); font-weight:700; font-size:13px;
}}
.rule {{
  margin-top:16px; padding:14px 18px; border-radius:14px;
  background:linear-gradient(90deg,#111827,#162033);
  border:1px solid #2c3b4d; color:#dbeafe; font-weight:700;
}}
.cards {{
  display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-top:18px;
}}
.card {{
  background:var(--panel); border:1px solid var(--line); border-radius:16px;
  padding:16px; min-height:112px;
}}
.card-title {{ color:var(--blue); font-size:13px; font-weight:800; text-transform:uppercase; }}
.card-value {{ font-size:22px; font-weight:900; margin-top:8px; }}
.small {{ color:var(--muted); font-size:13px; line-height:1.45; }}
.chips {{ margin-top:18px; }}
.chip {{
  display:inline-block; background:#172033; border:1px solid #304156; color:#dbeafe;
  border-radius:999px; padding:6px 10px; margin:3px; font-size:13px;
}}
.grid3 {{
  display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; margin-top:16px;
}}
ul {{ padding-left:20px; }}
.panel {{
  background:var(--panel); border:1px solid var(--line); border-radius:16px;
  padding:16px; margin-top:18px;
}}
.question {{
  width:100%; height:100px; background:#050814; color:var(--text);
  border:1px solid var(--line); border-radius:12px; padding:12px;
  font-family:monospace;
}}
button, .button {{
  background:linear-gradient(90deg,#2563eb,#7c3aed);
  color:white; border:0; border-radius:12px; padding:10px 14px;
  font-weight:800; cursor:pointer; text-decoration:none; display:inline-block;
}}
pre {{
  white-space:pre-wrap; background:#050814; color:#dbeafe;
  border:1px solid var(--line); border-radius:12px; padding:14px;
  max-height:650px; overflow:auto;
}}
details {{
  border:1px solid var(--line); border-radius:12px; padding:10px;
  margin-bottom:10px; background:#0d1320;
}}
summary {{ cursor:pointer; font-weight:800; color:#dbeafe; }}
iframe {{
  width:100%; height:580px; border:0; border-radius:14px; background:#050814;
}}


{{brain_render.COPY_CODE_CSS}}


</style>

<style>
.layer-columns {{
  display: grid;
  grid-template-columns: repeat(3, minmax(260px, 1fr));
  gap: 12px;
  align-items: stretch;
  margin-top: 12px;
  width: 100%;
}}

.layer-col {{
  background: rgba(15,23,42,.72);
  border: 1px solid rgba(148,163,184,.18);
  border-radius: 14px;
  padding: 11px;
  min-height: 0;
  box-shadow: 0 10px 24px rgba(0,0,0,.20);
}}

.layer-col-title {{
  font-size: 12px;
  font-weight: 900;
  letter-spacing: .18em;
  color: #bfdbfe;
  text-transform: uppercase;
  margin-bottom: 8px;
}}

.layer-list-clean {{
  display: grid;
  gap: 6px;
}}

.layer-chip-clean {{
  display: block;
  background: rgba(30,41,59,.88);
  border: 1px solid rgba(148,163,184,.16);
  color: #e5e7eb;
  border-radius: 9px;
  padding: 6px 9px;
  font-size: 12px;
  line-height: 1.25;
  min-height: 18px;
}}

.layer-chip-clean.quality {{
  border-color: rgba(34,197,94,.55);
  background: linear-gradient(90deg, rgba(22,101,52,.72), rgba(30,41,59,.88));
  color: #dcfce7;
  font-weight: 900;
}}

.layer-chip-clean.manual {{
  border-color: rgba(96,165,250,.50);
  background: linear-gradient(90deg, rgba(30,64,175,.55), rgba(30,41,59,.88));
  color: #dbeafe;
  font-weight: 800;
}}

@media (max-width: 1300px) {{
  .layer-columns {{
    grid-template-columns: repeat(2, minmax(260px, 1fr));
  }}
}}

@media (max-width: 760px) {{
  .layer-columns {{
    grid-template-columns: 1fr;
  }}
}}


</style>



<style>
.visual-dashboard-panel {{
  margin-top: 18px;
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 18px;
  background: rgba(15,23,42,.75);
  padding: 14px;
}}

.visual-dashboard-panel summary {{
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 800;
  font-size: 18px;
  color: #f8fafc;
}}

.visual-dashboard-panel summary::-webkit-details-marker {{
  display: none;
}}

.visual-dashboard-arrow {{
  font-size: 18px;
  min-width: 18px;
}}

.visual-dashboard-frame-wrap {{
  margin-top: 14px;
}}


</style>


</head>
<body>
<div class="sidebar">
  <h2>Brain Session</h2>
  <form method="post" action="/clear-session">\n    {csrf_field()}
    <button style="width:100%;">Clear Brain Session</button>
  </form>
  <p><a class="button" style="width:100%; text-align:center; margin-top:10px;" href="/session-full">Open Full Session View</a></p>
  <p><a class="button" style="width:100%; text-align:center;" href="/session-download">Download Brain Session</a></p>\n  <p><a class="button" style="width:100%; text-align:center;" href="/session-download-redacted">Download Redacted Support Report</a></p>\n  {auth_status_html()}
  <hr style="border-color:#263241;">
  {history_html}
</div>

<div class="main">
  <div style="display:flex;align-items:center;gap:14px;"><img src="/assets/zimabrain-ce-logo.svg" alt="ZimaBrain CE logo" style="width:56px;height:56px;border-radius:14px;"><h1>{APP_NAME}</h1></div>
  <div class="subtitle">{APP_SUBTITLE}</div>
  <div class="subtitle">{APP_DESCRIPTOR}</div>
  <div class="badge">App {APP_VERSION} · Reliable Flask mode · Local verifier</div>
  <div class="rule">Analyze first → Verifier second → Explainer third → Repair guide last</div>

  <div class="panel">
    <h3>Ask ZimaBrain CE</h3>
    <form method="post" action="/ask">\n    {csrf_field()}
      <textarea class="question" name="question" placeholder="Paste or type a new question here..."></textarea>
      <p><button type="submit">Analyse Report</button></p>
    </form>
  </div>

  <div class="cards">
    <div class="card"><div class="card-title">Dashboard Source</div><div class="card-value">{esc(dashboard_source_value)}</div><div class="small">{esc(dashboard_source_note)}</div></div>
    <div class="card"><div class="card-title">Real Alerts</div><div class="card-value">{len(n.get('real_alert_details', [])) + len(n.get('disk_attention', [])) + len(bundle.get('critical_findings', []))}</div><div class="small">Mapped to source/object where parsed</div></div>
    <div class="card"><div class="card-title">Container Alerts</div><div class="card-value">{len([c for c in n.get('exited_containers', []) if c.get('severity') == 'YELLOW']) + len(n.get('container_alert_details', []))}</div><div class="small">Possible faults only</div></div>
    <div class="card"><div class="card-title">Info Only</div><div class="card-value">{len(n.get('info_alert_details', [])) + len([c for c in n.get('exited_containers', []) if c.get('severity') == 'INFO'])}</div><div class="small">Unavailable or likely intentional</div></div>
  </div>


  <div class="panel">
    <h3>New Verifier Improvements</h3>
    <div class="small">Recent verifier upgrades now visible in the UI.</div>
    <div class="chips">
      <span class="chip">Alert mapping: source / object / condition</span>
      <span class="chip">Real alerts mapped where parsed</span>
      <span class="chip">Info Only items listed</span>
      <span class="chip">On-demand containers separated</span>
      <span class="chip">Files / AppData / media checks</span>
      <span class="chip">auditd ownership / permission checks</span>
      <span class="chip">Evidence trust: verified / partial / guidance only</span>
    </div>
  </div>

  <div class="panel">
    <h3>Build / Version Status</h3>
    <div class="small">Public quality checkpoint passed: router, manual relevance, and answer quality scorecards are 100%.</div>
    <div class="chips">
      <span class="chip">ZimaBrain: {APP_VERSION}</span>
      <span class="chip">Host OS: {esc(host_os_name)}</span>
      <span class="chip">Host Version: {esc(host_os_version)}</span>
      <span class="chip">Kernel: {esc(host_kernel)}</span>
      <span class="chip">Uptime: {esc(host_uptime)}</span>
      <span class="chip">RAUC: {esc(host_rauc)}</span>
      <span class="chip">Evidence refreshed: {esc(host_date)}</span>
      <span class="chip">Docker Health: {esc(self_health)}</span>
      <span class="chip">Security mode: Elevated Local Verifier</span>
      <span class="chip">Render module: active</span>
      <span class="chip">Router module: active</span>
      <span class="chip">Answer builder: active</span>
      <span class="chip">Intent Brain Router: active</span>
      <span class="chip">Checkpoint: 20260614-153118</span>
      <span class="chip">Port: 8601</span>
    </div>
  </div>

  
  {build_installed_apps_port_map_html(bundle)}


<h3>ZimaOS / ZimaBrain Layers</h3>\n<div class="small">Layer map is collapsed to save dashboard space. Open only when needed.</div>

<details style="margin-top:12px;">
  <summary style="cursor:pointer; font-weight:900; color:#dbeafe; background:#0f172a; border:1px solid #263241; border-radius:12px; padding:12px 14px;">
    Show full ZimaBrain layer map
  </summary>
<div class="layer-columns">

  <div class="layer-col">
    <div class="layer-col-title">Core Verification</div>
    <div class="layer-list-clean">
      <span class="layer-chip-clean quality">Public Quality Scorecards 100%</span>
      <span class="layer-chip-clean">Dashboard Evidence Loader</span>
      <span class="layer-chip-clean">Evidence Normalizer</span>
      <span class="layer-chip-clean">Critical Same-Report Verifier</span>
      <span class="layer-chip-clean quality">Dashboard Container Count Verification</span>
      <span class="layer-chip-clean">Question Router</span>
      <span class="layer-chip-clean">Intent Brain Router</span>
      <span class="layer-chip-clean">Verified Answer Builder</span>
      <span class="layer-chip-clean">Brain Session / Review</span>
      <span class="layer-chip-clean">Forum Issue Intake</span>
      <span class="layer-chip-clean manual">Official Manual Knowledge Engine</span>
      <span class="layer-chip-clean manual">App Verified Install Guides</span>
      <span class="layer-chip-clean manual">Third-Party App Store Index</span>
      <span class="layer-chip-clean manual">Hardware Compatibility Layer</span>
    </div>
  </div>

  <div class="layer-col">
    <div class="layer-col-title">Dashboard / System</div>
    <div class="layer-list-clean">
      <span class="layer-chip-clean">Dashboard Alerts</span>
      <span class="layer-chip-clean">Failed Units</span>
      <span class="layer-chip-clean">Container State</span>
      <span class="layer-chip-clean quality">Container Running Count</span>
      <span class="layer-chip-clean">Report Comparison</span>
      <span class="layer-chip-clean">Trend Alerts</span>
      <span class="layer-chip-clean">Trend History</span>
      <span class="layer-chip-clean">Host Hardware Metrics</span>
      <span class="layer-chip-clean">Log Intake / Uploaded Evidence</span>
      <span class="layer-chip-clean">Final Recommendation / Repair Planner</span>
    </div>
  </div>

  <div class="layer-col">
    <div class="layer-col-title">Disk / Storage</div>
    <div class="layer-list-clean">
      <span class="layer-chip-clean">Disk Inventory / Drive Count</span>
      <span class="layer-chip-clean">Disk Health</span>
      <span class="layer-chip-clean">Disk CRC</span>
      <span class="layer-chip-clean">Filesystem Usage</span>
      <span class="layer-chip-clean quality">SMART / NVMe Health Layer</span>
      <span class="layer-chip-clean">SMART Trend</span>
      <span class="layer-chip-clean">Storage / Mounts</span>
      <span class="layer-chip-clean">Read-Only Storage Diagnostics</span>
      <span class="layer-chip-clean">SnapRAID / MergerFS</span>
      <span class="layer-chip-clean">RAID / Add Drive Planning</span>
      <span class="layer-chip-clean">Backup / Borg Layer</span>
    </div>
  </div>

  <div class="layer-col">
    <div class="layer-col-title">Docker / Apps</div>
    <div class="layer-list-clean">
      <span class="layer-chip-clean">Docker Bind-Mount Verifier</span>
      <span class="layer-chip-clean">Docker Daemon Diagnostics</span>
      <span class="layer-chip-clean">App Storage-Path Verifier</span>
      <span class="layer-chip-clean">App Runtime Diagnostics</span>
      <span class="layer-chip-clean">App Setup / Version Playbook</span>
      <span class="layer-chip-clean">Container Commands</span>
    </div>
  </div>

  <div class="layer-col">
    <div class="layer-col-title">Network / Access</div>
    <div class="layer-list-clean">
      <span class="layer-chip-clean">Network Exposure / Firewall</span>
      <span class="layer-chip-clean quality">ZFW Firewall Verification</span>
      <span class="layer-chip-clean quality">ZimaBrain CE Self-Audit</span>
      <span class="layer-chip-clean">Network Connectivity Diagnostics</span>
      <span class="layer-chip-clean">SMB / Shares Diagnostics</span>
      <span class="layer-chip-clean">Permissions / Ownership Diagnostics</span>
    </div>
  </div>

  <div class="layer-col">
    <div class="layer-col-title">Install / Platform</div>
    <div class="layer-list-clean">
      <span class="layer-chip-clean">ZimaOS Update / Regression</span>
      <span class="layer-chip-clean">ZimaOS Update / Rollback Safety</span>
      <span class="layer-chip-clean">Install / Boot Diagnostics</span>
      <span class="layer-chip-clean">GPU / AI Runtime</span>
      <span class="layer-chip-clean manual">PCIe / Hardware Compatibility</span>
      <span class="layer-chip-clean">Disk Commands</span>
      <span class="layer-chip-clean">System Commands</span>
      <span class="layer-chip-clean">Network Commands</span>
    </div>
  </div>

</div>
</details>



  <details class="panel">
    <summary>Show dashboard alert panels</summary>
    <div class="grid3">
      <div class="panel"><h3>Real Alerts</h3><ul>{real_alert_html}</ul></div>
      <div class="panel"><h3>Container / Service Alerts</h3><ul>{container_alert_html}</ul></div>
      <div class="panel"><h3>Info Only</h3><ul>{info_alert_html}</ul></div>
    </div>
  </details>

  <details class="panel">
    <summary>Show Critical Same-Report Verifier</summary>
    <div class="small">This layer runs before question routing and flags high-confidence risks from the same report.</div>
    <ul>{critical_html}</ul>
  </details>


  <details class="panel visual-dashboard-panel">
    <summary><span class="visual-dashboard-arrow">&#9656;</span> Show Local ZimaOS Visual Dashboard</summary>
    {local_zimaos_visual_panel(bundle)}
    {host_hardware_metrics_panel(bundle)}
  </details>

  <script>
  document.querySelectorAll(".visual-dashboard-panel").forEach(function(panel) {{
    const arrow = panel.querySelector(".visual-dashboard-arrow");
    function syncArrow() {{
      arrow.textContent = panel.open ? "▾" : "▸";
    }}
    panel.addEventListener("toggle", syncArrow);
    syncArrow();
  }});
  </script>


</div>


{brain_render.COPY_CODE_JS}
</body>
</html>"""





@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question", "").strip()
    answer = answer_question(question)
    dashboard_source_value = "Native"
    dashboard_source_note = "Built-in native visual evidence from this unit"

    SESSION_HISTORY.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "answer": answer,
    })

    bundle = dashboard_bundle()
    n = bundle["normalized"]
    html_answer = brain_render.render_answer_html(answer)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>ZimaBrain Answer</title>
<style>
:root {{
  --bg:#080b10; --panel:#111722; --line:#263241;
  --text:#e8edf2; --muted:#9aa8b5; --blue:#93c5fd;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--bg); color:var(--text);
  font-family:Arial,sans-serif;
}}
.wrap {{ padding:24px; max-width:1600px; margin:auto; }}
.header {{ margin-bottom:18px; }}
h1 {{ font-size:38px; margin:0; }}
.subtitle {{ color:var(--muted); margin-top:6px; }}
.badge {{
  display:inline-block; margin-top:12px; padding:6px 12px;
  border-radius:999px; background:#1e293b; border:1px solid #334155;
  color:var(--blue); font-weight:700; font-size:13px;
}}
.rule {{
  margin-top:14px; padding:14px 18px; border-radius:14px;
  background:linear-gradient(90deg,#111827,#162033);
  border:1px solid #2c3b4d; color:#dbeafe; font-weight:700;
}}
.cards {{
  display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-top:18px;
}}
.card {{
  background:var(--panel); border:1px solid var(--line); border-radius:16px;
  padding:16px; min-height:96px;
}}
.card-title {{ color:var(--blue); font-size:13px; font-weight:800; text-transform:uppercase; }}
.card-value {{ font-size:22px; font-weight:900; margin-top:8px; }}
.small {{ color:var(--muted); font-size:13px; line-height:1.45; }}
pre {{
  white-space:pre-wrap; background:#050814; color:#dbeafe;
  border:1px solid var(--line); border-radius:14px; padding:18px;
  line-height:1.45;
}}
.answer-rendered {{
  background:#050814;
  color:#dbeafe;
  border:1px solid var(--line);
  border-radius:16px;
  padding:28px;
  line-height:1.7;
  font-size:16px;
  max-width:1180px;
}}
.answer-rendered h2 {{
  font-size:30px;
  margin:22px 0 12px;
  color:#ffffff;
  line-height:1.25;
}}
.answer-rendered h3 {{
  font-size:23px;
  margin:22px 0 12px;
  color:#dbeafe;
  line-height:1.3;
}}
.answer-rendered h4 {{
  font-size:19px;
  margin:20px 0 10px;
  color:#bfdbfe;
  line-height:1.35;
}}
.answer-rendered h2:first-child {{
  margin-top:0;
}}
.answer-rendered h2 + h3 {{
  background:#0f172a;
  border:1px solid #334155;
  border-left:5px solid #38bdf8;
  border-radius:12px;
  padding:14px 16px;
  margin-top:10px;
  color:#ffffff;
}}
.answer-rendered p {{
  margin:9px 0;
}}
.answer-rendered .md-bullet,
.answer-rendered .md-number {{
  margin:7px 0;
  padding-left:4px;
}}
.answer-rendered code {{
  background:#111827;
  color:#e5e7eb;
  padding:3px 7px;
  border-radius:6px;
  font-size:0.95em;
}}
.answer-rendered .codeblock {{
  white-space:pre;
  overflow-x:auto;
  background:#020617;
  color:#dbeafe;
  border:1px solid #475569;
  border-left:5px solid #38bdf8;
  border-radius:14px;
  padding:18px;
  margin:16px 0;
  font-family:Consolas, Monaco, monospace;
  font-size:15px;
  line-height:1.6;
}}
.answer-rendered .codeblock code {{
  background:transparent;
  padding:0;
  color:#dbeafe;
  font-size:15px;
}}
.answer-rendered blockquote {{
  border-left:5px solid #38bdf8;
  background:#0f172a;
  padding:12px 16px;
  border-radius:10px;
}}
.button {{
  background:linear-gradient(90deg,#2563eb,#7c3aed);
  color:white; border-radius:12px; padding:10px 14px;
  text-decoration:none; font-weight:800; display:inline-block;
}}
.actions {{ margin:18px 0; }}
.answer-dashboard-panel {{
  background:#111722; border:1px solid #263241; border-radius:16px;
  padding:16px; margin-top:18px;
}}
.answer-dashboard-panel iframe {{
  width:100%; height:760px; border:0; border-radius:14px; background:#050814;
}}
.answer-dashboard-panel summary {{
  cursor:pointer; font-weight:800; color:#dbeafe;
}}


</style>

<style>
.layer-columns {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
  align-items: start;
  margin-top: 14px;
}}
.layer-col {{
  border: 1px solid rgba(148,163,184,.18);
  border-radius: 14px;
  background: rgba(15,23,42,.45);
  padding: 12px;
}}
.layer-col-title {{
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: #93c5fd;
  margin: 0 0 10px 0;
}}
.layer-list-clean {{
  display: flex;
  flex-direction: column;
  gap: 7px;
  align-items: stretch;
}}
.layer-chip-clean {{
  display: block;
  text-align: left;
  padding: 7px 10px;
  border-radius: 999px;
  background: rgba(30,41,59,.92);
  border: 1px solid rgba(148,163,184,.22);
  color: #e5e7eb;
  font-size: 13px;
  line-height: 1.2;
  white-space: normal;
}}
.layer-chip-clean.quality {{
  border-color: rgba(34,197,94,.45);
  background: rgba(20,83,45,.35);
}}
.layer-chip-clean.manual {{
  border-color: rgba(96,165,250,.45);
  background: rgba(30,64,175,.32);
}}


</style>



<style>
.visual-dashboard-panel {{
  margin-top: 18px;
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 18px;
  background: rgba(15,23,42,.75);
  padding: 14px;
}}

.visual-dashboard-panel summary {{
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 800;
  font-size: 18px;
  color: #f8fafc;
}}

.visual-dashboard-panel summary::-webkit-details-marker {{
  display: none;
}}

.visual-dashboard-arrow {{
  font-size: 18px;
  min-width: 18px;
}}

.visual-dashboard-frame-wrap {{
  margin-top: 14px;
}}


</style>


</head>
<body>
<div class="wrap">
  <div class="header">
    <div style="display:flex;align-items:center;gap:14px;"><img src="/assets/zimabrain-ce-logo.svg" alt="ZimaBrain CE logo" style="width:56px;height:56px;border-radius:14px;"><h1>{APP_NAME}</h1></div>
    <div class="subtitle">{APP_SUBTITLE}</div>
    <div class="subtitle">{APP_DESCRIPTOR}</div>
    <div class="badge">App {APP_VERSION} · Reliable Flask mode · Local verifier</div>
    <div class="rule">Analyze first → Verifier second → Explainer third → Repair guide last</div>

    <div class="cards">
      <div class="card"><div class="card-title">Dashboard Source</div><div class="card-value">{esc(dashboard_source_value)}</div><div class="small">{esc(dashboard_source_note)}</div></div>
      <div class="card"><div class="card-title">Real Alerts</div><div class="card-value">{len(n.get('real_alert_details', [])) + len(n.get('disk_attention', [])) + len(bundle.get('critical_findings', []))}</div><div class="small">Mapped to source/object where parsed</div></div>
      <div class="card"><div class="card-title">Container Alerts</div><div class="card-value">{len([c for c in n.get('exited_containers', []) if c.get('severity') == 'YELLOW']) + len(n.get('container_alert_details', []))}</div><div class="small">Possible faults only</div></div>
      <div class="card"><div class="card-title">Info Only</div><div class="card-value">{len(n.get('info_alert_details', [])) + len([c for c in n.get('exited_containers', []) if c.get('severity') == 'INFO'])}</div><div class="small">Unavailable or likely intentional</div></div>
    </div>
  </div>


  <div class="panel">
    <h3>New Verifier Improvements</h3>
    <div class="small">Recent verifier upgrades now visible in the UI.</div>
    <div class="chips">
      <span class="chip">Alert mapping: source / object / condition</span>
      <span class="chip">Real alerts mapped where parsed</span>
      <span class="chip">Info Only items listed</span>
      <span class="chip">On-demand containers separated</span>
      <span class="chip">Files / AppData / media checks</span>
      <span class="chip">auditd ownership / permission checks</span>
      <span class="chip">Evidence trust: verified / partial / guidance only</span>
    </div>
  </div>

  <details class="answer-dashboard-panel visual-dashboard-panel">
    <summary><span class="visual-dashboard-arrow">&#9656;</span> Show Local ZimaOS Visual Dashboard</summary>
    <div class="small">Built-in native visual dashboard. No external visual container is required.</div>
    {local_zimaos_visual_panel(bundle)}
    {host_hardware_metrics_panel(bundle)}
  </details>

  <style>
    .answer-actions-grid {{
      display: grid;
      grid-template-columns: 1.1fr 1fr 1fr 1fr;
      gap: 14px;
      margin: 18px 0;
      align-items: stretch;
    }}
    .answer-action-group {{
      border: 1px solid rgba(148,163,184,.20);
      border-radius: 16px;
      background: rgba(15,23,42,.45);
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .answer-action-title {{
      font-size: 12px;
      font-weight: 900;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: #93c5fd;
      margin-bottom: 2px;
    }}
    .answer-actions-grid .button {{
      width: 100%;
      text-align: center;
      margin: 0;
      box-sizing: border-box;
      white-space: normal;
      line-height: 1.25;
      min-height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .answer-actions-grid .button-back {{
      background: linear-gradient(135deg, #991b1b, #ef4444);
      color: #fff;
      font-weight: 900;
      border: 1px solid rgba(248,113,113,.65);
    }}
    .answer-actions-grid .button-redacted {{
      background: linear-gradient(135deg, #15803d, #22c55e);
      color: #f8fafc;
      font-weight: 900;
      border: 1px solid rgba(34,197,94,.65);
      box-shadow: 0 0 0 1px rgba(34,197,94,.18) inset;
    }}
    .answer-actions-grid .button-view {{
      background: linear-gradient(135deg, #1d4ed8, #7c3aed);
      font-weight: 900;
    }}
    .answer-actions-grid .button:hover {{
      filter: brightness(1.08);
    }}
    @media (max-width: 1100px) {{
      .answer-actions-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
    @media (max-width: 650px) {{
      .answer-actions-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>

  <div class="answer-actions-grid">
    <div class="answer-action-group">
      <div class="answer-action-title">Navigation / Support</div>
      <a class="button button-back" href="/">Back to ZimaBrain</a>
      <a class="button button-redacted" href="/session-download-redacted">Download Redacted Support Report</a>
    </div>

    <div class="answer-action-group">
      <div class="answer-action-title">Current Answer</div>
      <a class="button" href="/answer-download">Download MD</a>
      <a class="button" href="/answer-download-html">Download HTML</a>
      <a class="button" href="/answer-download-json">Download JSON</a>
    </div>

    <div class="answer-action-group">
      <div class="answer-action-title">Brain Session</div>
      <a class="button" href="/session-download">Download MD</a>
      <a class="button" href="/session-download-html">Download HTML</a>
      <a class="button" href="/session-download-json">Download JSON</a>
    </div>

    <div class="answer-action-group">
      <div class="answer-action-title">View</div>
      <a class="button button-view" href="/session-full">Open Full Session View</a>
    </div>
  </div>

  <div class="answer-rendered">{html_answer}</div>
</div>


</body>
</html>"""






@app.route("/clear-session", methods=["POST"])
def clear_session():
    SESSION_HISTORY.clear()
    return Response("<script>window.location='/'</script>", mimetype="text/html")


@app.route("/session-full")
def session_full():
    body = build_session_export()
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Brain Session</title>
<style>body{{background:#080b10;color:#e8edf2;font-family:Arial,sans-serif;padding:24px;}}pre{{white-space:pre-wrap;background:#050814;border:1px solid #263241;border-radius:14px;padding:18px;}}

</style>

<style>
.layer-columns {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
  align-items: start;
  margin-top: 14px;
}}
.layer-col {{
  border: 1px solid rgba(148,163,184,.18);
  border-radius: 14px;
  background: rgba(15,23,42,.45);
  padding: 12px;
}}
.layer-col-title {{
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: #93c5fd;
  margin: 0 0 10px 0;
}}
.layer-list-clean {{
  display: flex;
  flex-direction: column;
  gap: 7px;
  align-items: stretch;
}}
.layer-chip-clean {{
  display: block;
  text-align: left;
  padding: 7px 10px;
  border-radius: 999px;
  background: rgba(30,41,59,.92);
  border: 1px solid rgba(148,163,184,.22);
  color: #e5e7eb;
  font-size: 13px;
  line-height: 1.2;
  white-space: normal;
}}
.layer-chip-clean.quality {{
  border-color: rgba(34,197,94,.45);
  background: rgba(20,83,45,.35);
}}
.layer-chip-clean.manual {{
  border-color: rgba(96,165,250,.45);
  background: rgba(30,64,175,.32);
}}


</style>



<style>
.visual-dashboard-panel {{
  margin-top: 18px;
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 18px;
  background: rgba(15,23,42,.75);
  padding: 14px;
}}

.visual-dashboard-panel summary {{
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 800;
  font-size: 18px;
  color: #f8fafc;
}}

.visual-dashboard-panel summary::-webkit-details-marker {{
  display: none;
}}

.visual-dashboard-arrow {{
  font-size: 18px;
  min-width: 18px;
}}

.visual-dashboard-frame-wrap {{
  margin-top: 14px;
}}


</style>


</head><body><p><a href="/">Back</a> | <a href="/session-download">Download</a></p><pre>{esc(body)}</pre></body></html>"""


@app.route("/session-download")
def session_download():
    body = build_session_export()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Response(
        body,
        mimetype="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=zimabrain-session-{stamp}.md"},
    )




@app.route("/session-download-redacted")
def session_download_redacted():
    body = redact_support_text(build_session_export())
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Response(
        body,
        mimetype="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=zimabrain-session-redacted-{stamp}.md"},
    )







def _answer_blocks(answer):
    sections = _answer_sections(answer)

    block_order = [
        ("direct_answer", "Direct Answer", "text"),
        ("attention_items", "Attention Items", "list"),
        ("critical_findings", "Critical Findings", "list"),
        ("warnings", "Warnings", "list"),
        ("info_items", "Info / Unavailable Evidence", "list"),
        ("healthy_evidence", "Healthy / Normal Evidence", "list"),
        ("latest_trend_snapshot", "Latest Trend Snapshot", "list"),
        ("change_since_previous_scan", "Change Since Previous Scan", "list"),
        ("recent_snapshots", "Recent Snapshots", "list"),
        ("trend_alerts", "Trend Alerts", "list"),
        ("stable_trend_checks", "Stable Trend Checks", "list"),
        ("latest_alert_baseline", "Latest Alert Baseline", "list"),
        ("next_safest_step", "Next Safest Step", "text"),
        ("safe_recommendation", "Safe Recommendation", "text"),
        ("forum_ready_summary", "Forum Ready Summary", "text"),
    ]

    blocks = []
    for key, title, kind in block_order:
        value = sections.get(key, [] if kind == "list" else "")

        if kind == "list":
            if not value:
                continue

            if isinstance(value, str):
                value = [line.strip() for line in value.splitlines() if line.strip()]

            blocks.append({
                "key": key,
                "title": title,
                "type": "list",
                "items": value,
            })
        else:
            if not str(value).strip():
                continue
            blocks.append({
                "key": key,
                "title": title,
                "type": "text",
                "text": str(value).strip(),
            })

    return blocks


def _answer_rows(answer):
    sections = _answer_sections(answer)
    rows = []

    for group_key, group_title in [
        ("attention_items", "Attention"),
        ("critical_findings", "Critical"),
        ("warnings", "Warning"),
        ("info_items", "Info"),
        ("healthy_evidence", "Healthy"),
    ]:
        for item in sections.get(group_key, []):
            device = ""
            detail = item

            if ":" in item:
                device, detail = item.split(":", 1)
                device = device.strip()
                detail = detail.strip()

            rows.append({
                "group": group_title,
                "device": device,
                "detail": detail,
                "raw": item,
            })

    return rows


def json_download_response(data, filename):
    body = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return Response(
        body,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/answer-download-json")
def answer_download_json():
    latest = SESSION_HISTORY[-1] if SESSION_HISTORY else None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if not latest:
        data = {
            "ok": False,
            "app": APP_VERSION,
            "message": "No answer yet.",
        }
    else:
        metadata = _answer_metadata(latest.get("answer", ""))
        data = {
            "ok": True,
            "app": APP_VERSION,
            "question": latest.get("question", ""),
            "time": latest.get("time", ""),
            "verification_status": metadata.get("verification_status", "UNKNOWN"),
            "active_layer": metadata.get("active_layer", ""),
            "layer_file": metadata.get("layer_file", ""),
            "answer_blocks": _answer_blocks(latest.get("answer", "")),
            "answer_rows": _answer_rows(latest.get("answer", "")),
        }

    return json_download_response(data, f"zimabrain-answer-{stamp}.json")


@app.route("/session-download-json")
def session_download_json():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    items = []

    for item in SESSION_HISTORY:
        metadata = _answer_metadata(item.get("answer", ""))
        items.append({
            "question": item.get("question", ""),
            "time": item.get("time", ""),
            "verification_status": metadata.get("verification_status", "UNKNOWN"),
            "active_layer": metadata.get("active_layer", ""),
            "layer_file": metadata.get("layer_file", ""),
            "answer_blocks": _answer_blocks(item.get("answer", "")),
            "answer_rows": _answer_rows(item.get("answer", "")),
        })

    return json_download_response({
        "ok": True,
        "app": APP_VERSION,
        "exported": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "history_count": len(SESSION_HISTORY),
        "items": items,
    }, f"zimabrain-session-{stamp}.json")


@app.route("/answer-download-html")
def answer_download_html():
    answer = SESSION_HISTORY[-1]["answer"] if SESSION_HISTORY else "No answer yet."
    body_html = '<div class="answer-rendered">' + brain_render.render_answer_html(answer) + '</div>'
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Response(
        brain_render.rendered_download_page("ZimaBrain Current Answer", body_html),
        mimetype="text/html",
        headers={"Content-Disposition": f"attachment; filename=zimabrain-answer-{stamp}.html"},
    )


@app.route("/session-download-html")
def session_download_html():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if not SESSION_HISTORY:
        body_html = '<div class="answer-rendered"><h2>ZimaBrain CE Brain Session</h2><p>No questions asked yet.</p></div>'
    else:
        parts = ['<div class="answer-rendered"><h2>ZimaBrain CE Brain Session</h2><p>Exported: ' + esc(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + '</p></div>']
        for idx, item in enumerate(SESSION_HISTORY, 1):
            parts.append(
                '<div class="session-item"><div class="session-meta">Question '
                + esc(str(idx))
                + ' · '
                + esc(item.get("time", ""))
                + '</div><div class="answer-rendered">'
                + brain_render.render_answer_html(item.get("answer", ""))
                + '</div></div>'
            )
        body_html = "\n".join(parts)

    return Response(
        brain_render.rendered_download_page("ZimaBrain Brain Session", body_html),
        mimetype="text/html",
        headers={"Content-Disposition": f"attachment; filename=zimabrain-session-{stamp}.html"},
    )


@app.route("/answer-download")
def answer_download():
    answer = SESSION_HISTORY[-1]["answer"] if SESSION_HISTORY else "No answer yet."
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Response(
        answer,
        mimetype="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=zimabrain-answer-{stamp}.md"},
    )




def _answer_metadata(answer):
    text = str(answer or "")
    status = "UNKNOWN"
    layer = ""
    layer_file = ""

    m = re.search(r"@@VERIFY:([^@]+)@@", text)
    if m:
        status = m.group(1).strip()

    m = re.search(r"Active layer:\s*`?([^`\n]+)`?", text)
    if m:
        layer = m.group(1).strip()

    m = re.search(r"Layer file:\s*`?([^`\n]+)`?", text)
    if m:
        layer_file = m.group(1).strip()

    warnings = []
    critical = []

    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        low = line.lower()

        if low.startswith("#### critical") or low.startswith("### critical"):
            section = "critical"
            continue
        if low.startswith("#### warnings") or low.startswith("### warnings"):
            section = "warnings"
            continue
        if line.startswith("#### ") or line.startswith("### "):
            section = ""

        if line.startswith("- "):
            item = line[2:].strip()
            if section == "critical" and item and item.lower() != "none parsed.":
                critical.append(item)
            if section == "warnings" and item and item.lower() != "none parsed.":
                warnings.append(item)

    return {
        "verification_status": status,
        "active_layer": layer,
        "layer_file": layer_file,
        "critical_findings": critical[:50],
        "warnings": warnings[:50],
    }




def _answer_sections(answer):
    text = str(answer or "")

    heading_map = {
        "direct answer / severity": "direct_answer",
        "critical findings": "critical_findings",
        "warnings / context": "warnings",
        "healthy / normal parsed evidence": "healthy_evidence",
        "latest trend snapshot": "latest_trend_snapshot",
        "change since previous scan": "change_since_previous_scan",
        "recent snapshots": "recent_snapshots",
        "trend alerts": "trend_alerts",
        "stable trend checks": "stable_trend_checks",
        "latest alert baseline": "latest_alert_baseline",
        "next safest step": "next_safest_step",
        "safe recommendation": "safe_recommendation",
        "forum-ready summary": "forum_ready_summary",
        "forum ready summary": "forum_ready_summary",
    }

    inline_map = {
        "disks needing attention from real values:": "attention_items",
        "info only / unavailable smart fields:": "info_items",
        "disks that look ok from available fields:": "healthy_evidence",
        "healthy / normal parsed evidence:": "healthy_evidence",
    }

    sections = {
        "direct_answer": [],
        "attention_items": [],
        "critical_findings": [],
        "warnings": [],
        "info_items": [],
        "healthy_evidence": [],
        "latest_trend_snapshot": [],
        "change_since_previous_scan": [],
        "recent_snapshots": [],
        "trend_alerts": [],
        "stable_trend_checks": [],
        "latest_alert_baseline": [],
        "next_safest_step": [],
        "safe_recommendation": [],
        "forum_ready_summary": [],
    }

    current = None

    for raw in text.splitlines():
        line = raw.rstrip()
        clean = line.strip()

        if not clean:
            continue

        low = clean.lower()

        if clean.startswith("#### ") or clean.startswith("### "):
            title = clean.lstrip("#").strip().lower()
            current = heading_map.get(title)
            continue

        if low in inline_map:
            current = inline_map[low]
            continue

        if current:
            if clean.startswith("- "):
                clean = clean[2:].strip()
            if clean and clean.lower() != "none parsed.":
                sections[current].append(clean)

    list_keys = {
        "attention_items",
        "critical_findings",
        "warnings",
        "info_items",
        "healthy_evidence",
    }

    out = {}
    for key, value in sections.items():
        if key in list_keys:
            out[key] = value
        else:
            out[key] = "\n".join(value).strip()

    return out


@app.route("/api/v1/health")
def api_v1_health():
    return jsonify({
        "ok": True,
        "app": APP_VERSION,
        "api": "v1",
        "security": {
            "password_configured": password_configured(),
            "authenticated": is_logged_in(),
        },
        "history": len(SESSION_HISTORY),
        "dashboard_loaded": bool(DASHBOARD_REPORT.strip()),
    })


@app.route("/api/v1/summary")
def api_v1_summary():
    latest = SESSION_HISTORY[-1] if SESSION_HISTORY else None
    return jsonify({
        "ok": True,
        "app": APP_VERSION,
        "api": "v1",
        "security": {
            "password_configured": password_configured(),
            "authenticated": is_logged_in(),
        },
        "dashboard": {
            "loaded": bool(DASHBOARD_REPORT.strip()),
            "status": DASHBOARD_STATUS,
            "characters": len(DASHBOARD_REPORT or ""),
        },
        "history": {
            "count": len(SESSION_HISTORY),
            "latest_question": latest.get("question") if latest else None,
            "latest_time": latest.get("time") if latest else None,
            "latest_metadata": _answer_metadata(latest.get("answer", "")) if latest else None,
        },
        "endpoints": [
            "GET /api/v1/health",
            "GET /api/v1/summary",
            "POST /api/v1/ask",
        ],
    })


@app.route("/api/v1/ask", methods=["POST"])
def api_v1_ask():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question") or request.form.get("question", "")).strip()

    if not question:
        return jsonify({"ok": False, "error": "question is required"}), 400

    global DASHBOARD_REPORT, DASHBOARD_STATUS

    if not DASHBOARD_REPORT.strip():
        try:
            DASHBOARD_REPORT = fetch_dashboard_report()
            DASHBOARD_STATUS = f"Dashboard evidence loaded: {len(DASHBOARD_REPORT):,} characters."
        except Exception as e:
            DASHBOARD_STATUS = f"Dashboard evidence unavailable: {e}"

    answer = answer_question(question)

    SESSION_HISTORY.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "answer": answer,
    })

    metadata = _answer_metadata(answer)

    return jsonify({
        "ok": True,
        "question": question,
        "sections": _answer_sections(answer),
        "answer_blocks": _answer_blocks(answer),
        "answer_rows": _answer_rows(answer),
        "answer_markdown": answer,
        **metadata,
    })


@app.route("/load-dashboard")
def load_dashboard():
    global DASHBOARD_REPORT, DASHBOARD_STATUS
    try:
        DASHBOARD_REPORT = fetch_dashboard_report()
        DASHBOARD_STATUS = f"Dashboard evidence loaded: {len(DASHBOARD_REPORT):,} characters."
        return jsonify({"ok": True, "status": DASHBOARD_STATUS})
    except Exception as e:
        DASHBOARD_STATUS = f"Dashboard evidence unavailable: {e}"
        return jsonify({"ok": False, "status": DASHBOARD_STATUS}), 500



@app.route("/metrics")
def metrics():
    bundle = dashboard_bundle()
    trend = bundle.get("trend_snapshot") or {}

    metrics_map = {
        "zimabrain_running_containers": trend.get("running_containers", 0),
        "zimabrain_published_ports": trend.get("published_ports", 0),
        "zimabrain_lan_reachable_ports": trend.get("lan_reachable_ports", 0),
        "zimabrain_localhost_only_ports": trend.get("localhost_only_ports", 0),
        "zimabrain_possible_blocked_ports": trend.get("possible_blocked_ports", 0),
        "zimabrain_smart_warning_markers": trend.get("smart_warning_markers", 0),
        "zimabrain_nvme_warning_markers": trend.get("nvme_warning_markers", 0),
        "zimabrain_dashboard_alerts": len(bundle.get("alerts", []) or []),
        "zimabrain_exited_containers": len(bundle.get("exited", []) or []),
        "zimabrain_critical_findings": len(bundle.get("critical_findings", []) or []),
    }

    lines = []
    lines.append("# HELP zimabrain_info ZimaBrain CE build information")
    lines.append("# TYPE zimabrain_info gauge")
    lines.append(f'zimabrain_info{{app_version="{APP_VERSION}"}} 1')

    for name, value in metrics_map.items():
        safe_value = int(value or 0)
        lines.append(f"# HELP {name} ZimaBrain CE metric")
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {safe_value}")

    lines.append("")
    return Response("\n".join(lines), mimetype="text/plain; version=0.0.4; charset=utf-8")

@app.route("/health")
def health():
    return jsonify({"ok": True, "app": APP_VERSION, "history": len(SESSION_HISTORY), "dashboard_loaded": bool(DASHBOARD_REPORT.strip())})


def build_session_export():
    lines = []
    lines.append("# ZimaBrain CE Brain Session")
    lines.append("")
    lines.append(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    if not SESSION_HISTORY:
        lines.append("No questions asked yet.")
        return "\n".join(lines)

    for idx, item in enumerate(SESSION_HISTORY, 1):
        lines.append(f"## {idx}. {item['question']}")
        lines.append("")
        lines.append(f"Time: {item['time']}")
        lines.append("")
        lines.append(item["answer"])
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8601)
