import html
import urllib.request
import json
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
DASHBOARD_REPORT_URL = "http://host.docker.internal:8514/zimabrain-report"

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

    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<LAN_IP>", text)
    text = re.sub(r"(?i)\b(password|passwd|token|secret|api[_-]?key|authorization|bearer)\s*[:=]\s*['\"]?[^'\"\s<>]+", r"\1=<redacted>", text)
    text = re.sub(r"(?i)bearer\s+[a-z0-9._\-]+", "Bearer <redacted>", text)
    text = re.sub(r"\b[a-f0-9]{32,}\b", "<redacted_hex>", text)

    text = re.sub(r"/DATA/AppData/[^\\s'\"<>]+", "/DATA/AppData/<redacted>", text)
    text = re.sub(r"/media/[^\\s'\"<>]+", "/media/<redacted>", text)
    text = re.sub(r"/var/lib/casaos_data/[^\\s'\"<>]+", "/var/lib/casaos_data/<redacted>", text)

    return text


@app.before_request
def security_gate():
    allowed_paths = {"/login", "/setup", "/health", "/api/v1/health"}
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
            "health": "N/A",
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
    try:
        host = request.host.split(":")[0]
        urllib.request.urlopen(f"http://{host}:8514", timeout=1).close()
        return True
    except Exception:
        return False


def local_zimaos_visual_panel(bundle):
    if live_visual_available():
        return f"""
        <p class="small">Live visual layer detected. If it does not load, the native fallback evidence is still used above.</p>
        <details>
          <summary>Show Local ZimaOS Visual</summary>
          <iframe src="//{request.host.split(':')[0]}:8514"></iframe>
        </details>
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

    status_line = "Native fallback active"
    if "Native ZimaBrain local evidence fallback generated" in report:
        status_line = "Native fallback active because live dashboard is not available"

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
          <h4>Docker State</h4>
          {container_html}
        </div>
        <div class="native-containers">
          <h4>Native Evidence Source</h4>
          <div class="native-line"><span class="native-dot"></span><span>Host sysfs</span><b>active</b></div>
          <div class="native-line"><span class="native-dot"></span><span>Host mounts</span><b>active</b></div>
          <div class="native-line"><span class="native-dot"></span><span>Docker socket</span><b>active</b></div>
          <div class="native-line"><span class="native-dot"></span><span>External dashboard</span><b>not required</b></div>
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

        # External dashboard report may contain container alerts but not
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
            exited.append({
                "name": parts[0],
                "status": parts[1],
                "image": parts[2],
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


def normalize_dashboard_evidence(alerts, disks, exited):
    real_alerts = []
    info_alerts = []
    container_alerts = []

    for alert in alerts:
        low = alert.lower()
        if "n/a" in low:
            if alert.startswith("YELLOW:"):
                alert = alert.replace("YELLOW:", "INFO:", 1)
            info_alerts.append(alert + " (SMART value unavailable, not confirmed failure)")
        elif "container exited" in low:
            container_alerts.append(alert)
        else:
            real_alerts.append(alert)

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


def collect_same_report_evidence():
    return {
        "failed_units": run_host_command("systemctl --failed --no-pager --no-legend 2>/dev/null || true"),
        "lsblk": run_host_command("lsblk -o NAME,PKNAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS 2>/dev/null || true"),
        "mounts": run_host_command("findmnt -P -o SOURCE,TARGET,FSTYPE,OPTIONS 2>/dev/null | grep -Ei 'mergerfs|snapraid|/DATA|/media' | head -120 || true"),
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
        "zfw_status": run_host_command("systemctl is-active zfw-ui.service 2>/dev/null || true"),
        "zfw_files": run_host_command("ls -l /var/lib/extensions/zfw.raw /DATA/zfw/zfw /DATA/zfw/rules.json 2>/dev/null || true"),
        "zfw_chains": run_host_command("iptables -S ZFW-IN 2>/dev/null || true; iptables -S ZFW-IN6 2>/dev/null || true; iptables -S DOCKER-USER 2>/dev/null || true"),
        "self_docker_security": run_host_command("docker inspect zimabrain-ce-flask-8601 --format 'User={{.Config.User}} Privileged={{.HostConfig.Privileged}} PidMode={{.HostConfig.PidMode}} SecurityOpt={{.HostConfig.SecurityOpt}} CapAdd={{.HostConfig.CapAdd}}' 2>/dev/null || true; docker inspect zimabrain-ce-flask-8601 --format '{{range .Mounts}}{{if eq .Destination \"/var/run/docker.sock\"}}DockerSock={{.Source}}:{{.RW}}{{end}}{{end}}' 2>/dev/null || true"),
        "host_os": run_host_command("cat /etc/os-release 2>/dev/null || true"),
        "kernel": run_host_command("uname -r 2>/dev/null || true"),
        "uptime": run_host_command("uptime -p 2>/dev/null || true"),
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
    normalized = normalize_dashboard_evidence(alerts, disks, exited)
    same_report_evidence = collect_same_report_evidence()
    critical_findings = evaluate_critical_same_report(same_report_evidence)

    return {
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


def collect_critical_verifier():
    findings = []
    facts = []

    failed_units = run_host_shell("systemctl --failed --no-pager --no-legend 2>/dev/null || true")
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
                if "snapraid-sync.service" in line:
                    findings.append({
                        "level": "RED",
                        "title": "DATA PROTECTION IS DOWN",
                        "evidence": "systemctl --failed shows snapraid-sync.service failed.",
                        "why": "SnapRAID sync is not completing, so parity protection is not current.",
                        "next": "Check journalctl -u snapraid-sync and fix the SnapRAID config/parity before relying on the pool.",
                    })
                else:
                    findings.append({
                        "level": "YELLOW",
                        "title": "Failed systemd unit detected",
                        "evidence": line.strip(),
                        "why": "A failed host unit can indicate a broken scheduled task or system helper.",
                        "next": "Inspect only this failed unit before changing unrelated services.",
                    })

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
    dashboard_url = f"http://{request.host.split(':')[0]}:8514"
    live_visual = live_visual_available()
    dashboard_source_value = "8514" if live_visual else "Native"
    dashboard_source_note = "Live visual dashboard detected" if live_visual else "Native host evidence from this unit"
    n = bundle["normalized"]
    critical = collect_critical_verifier()

    critical_items = critical.get("findings", [])
    critical_html = "".join(
        f"<li>{'🔴' if item['level'] == 'RED' else '🟡'} <b>{esc(item['level'])}: {esc(item['title'])}</b><br><span class='small'>{esc(item['evidence'])}</span></li>"
        for item in critical_items[:8]
    ) or "<li>No same-report critical findings detected.</li>"

    real_alert_html = "".join(f"<li>{esc(severity_dot(a))}</li>" for a in n["real_alerts"]) or "<li>No real alerts parsed.</li>"
    container_alert_html = "".join(f"<li>{esc(severity_dot(a))}</li>" for a in n["container_alerts"]) or "<li>No container alerts parsed.</li>"
    info_alert_html = "".join(f"<li>{esc(severity_dot(a))}</li>" for a in n["info_alerts"][:6]) or "<li>No info alerts parsed.</li>"

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
    <div class="card"><div class="card-title">Real Alerts</div><div class="card-value">{len(n['real_alerts'])}</div><div class="small">Hardware/storage priority</div></div>
    <div class="card"><div class="card-title">Container Alerts</div><div class="card-value">{len(n['container_alerts'])}</div><div class="small">Exited services</div></div>
    <div class="card"><div class="card-title">Info Only</div><div class="card-value">{len(n['info_alerts'])}</div><div class="small">Unsupported/N/A metrics</div></div>
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


  <div class="panel">
    <h3>Local ZimaOS Visual Dashboard</h3>
    {local_zimaos_visual_panel(bundle)}
  </div>

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
      <div class="card"><div class="card-title">Dashboard Source</div><div class="card-value">8514</div><div class="small">{esc(bundle['status'])}</div></div>
      <div class="card"><div class="card-title">Real Alerts</div><div class="card-value">{len(n['real_alerts'])}</div><div class="small">Hardware/storage priority</div></div>
      <div class="card"><div class="card-title">Container Alerts</div><div class="card-value">{len(n['container_alerts'])}</div><div class="small">Exited services</div></div>
      <div class="card"><div class="card-title">Info Only</div><div class="card-value">{len(n['info_alerts'])}</div><div class="small">Unsupported/N/A metrics</div></div>
    </div>
  </div>

  <div class="answer-dashboard-panel">
    <h3>Local ZimaOS Visual Dashboard</h3>
    <div class="small">Live visual if available. Native fallback is used automatically on boards without the dashboard container.</div>
    {local_zimaos_visual_panel(bundle)}
  </div>

  <div class="actions">
    <a class="button" href="/">Back to ZimaBrain</a>
    <a class="button" href="/answer-download">Download Current Answer MD</a>
    <a class="button" href="/answer-download-html">Download Current Answer HTML</a>
    <a class="button" href="/answer-download-json">Download Current Answer JSON</a>
    <a class="button" href="/session-download-html">Download Brain Session HTML</a>
    <a class="button" href="/session-download-json">Download Brain Session JSON</a>
    <a class="button" href="/session-full">Open Full Session View</a>
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
            "sections": _answer_sections(latest.get("answer", "")),
            "answer_markdown": latest.get("answer", ""),
            **metadata,
        }

    return jsonify(data), 200, {"Content-Disposition": f"attachment; filename=zimabrain-answer-{stamp}.json"}


@app.route("/session-download-json")
def session_download_json():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    items = []

    for item in SESSION_HISTORY:
        metadata = _answer_metadata(item.get("answer", ""))
        items.append({
            "question": item.get("question", ""),
            "time": item.get("time", ""),
            "sections": _answer_sections(item.get("answer", "")),
            "answer_markdown": item.get("answer", ""),
            **metadata,
        })

    return jsonify({
        "ok": True,
        "app": APP_VERSION,
        "exported": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "history_count": len(SESSION_HISTORY),
        "items": items,
    }), 200, {"Content-Disposition": f"attachment; filename=zimabrain-session-{stamp}.json"}


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
