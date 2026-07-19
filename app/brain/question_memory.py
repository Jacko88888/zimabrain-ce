import hashlib
import re
import sqlite3
from datetime import datetime


def _redact(value):
    text = str(value or "")
    patterns = [
        r"(?i)(password\s*[=:]\s*)\S+",
        r"(?i)(secret(?:_key)?\s*[=:]\s*)\S+",
        r"(?i)(api[_ -]?key\s*[=:]\s*)\S+",
        r"(?i)(token\s*[=:]\s*)\S+",
    ]
    for pattern in patterns:
        text = re.sub(pattern, r"\1[REDACTED]", text)
    return text[:2000]


def _hash(value):
    return hashlib.sha256(
        str(value or "").encode("utf-8")
    ).hexdigest()


def _label_values(text, labels):
    flat = " ".join(str(text or "").split())
    values = []

    for label in labels:
        match = re.search(
            rf"(?i)(?:^|\s){re.escape(label)}:\s*"
            rf"(.*?)(?=\s+[A-Za-z][A-Za-z0-9 /_-]{{1,60}}:\s|$)",
            flat,
        )
        if match:
            values.append(
                f"{label}: {match.group(1).strip()}"
            )

    return values



def _comparison_value(
    memory_key,
    active_layer,
    direct_answer,
):
    key = str(memory_key or "").strip().lower()
    layer = str(active_layer or "").strip().lower()
    flat = " ".join(str(direct_answer or "").split())

    def field(label, stop_labels=()):
        match = re.search(
            rf"(?i)(?:^|\s){re.escape(label)}:\s*",
            flat,
        )
        if not match:
            return ""

        start = match.end()
        end = len(flat)

        for stop in stop_labels:
            stop_match = re.search(
                rf"(?i)\s+{re.escape(stop)}:\s*",
                flat[start:],
            )
            if stop_match:
                end = min(end, start + stop_match.start())

        return flat[start:end].strip(" -|")

    def number(label):
        match = re.search(
            rf"(?i)(?:^|\s){re.escape(label)}:\s*(\d+)",
            flat,
        )
        return match.group(1) if match else ""

    def section(start_label, stop_label=None):
        match = re.search(
            rf"(?i)(?:^|\s){re.escape(start_label)}:\s*",
            flat,
        )
        if not match:
            return ""

        start = match.end()
        end = len(flat)

        if stop_label:
            stop = re.search(
                rf"(?i)\s+{re.escape(stop_label)}:\s*",
                flat[start:],
            )
            if stop:
                end = start + stop.start()

        value = flat[start:end]
        value = re.sub(
            r"(?i)\s+restart count\s+\d+",
            " restart-count",
            value,
        )
        return " ".join(value.split())

    semantic = []

    if "memory" in key:
        value = field(
            "Memory pressure assessment",
            ("Memory available", "Memory", "Swap"),
        )
        if value:
            semantic.append(
                f"memory-pressure={value}"
            )

    elif key.startswith("containers:"):
        if "configuration" in key:
            labels = (
                "Privileged containers",
                "Docker-socket containers",
                "Host-PID containers",
                "Containers with added capabilities",
            )
            for label in labels:
                value = number(label)
                if value:
                    semantic.append(
                        f"{label.lower()}={value}"
                    )
        else:
            for label in (
                "Exited containers",
                "Restarting containers",
                "Unhealthy running containers",
            ):
                value = number(label)
                if value:
                    semantic.append(
                        f"{label.lower()}={value}"
                    )

            restarting = section(
                "Restarting containers",
                "Unhealthy running containers",
            )
            unhealthy = section(
                "Unhealthy running containers",
                "Exited containers",
            )

            if restarting:
                semantic.append(
                    f"restarting-list={restarting}"
                )
            if unhealthy:
                semantic.append(
                    f"unhealthy-list={unhealthy}"
                )

    elif "smart-nvme" in key:
        value = field("SMART/NVMe trend assessment")
        if value:
            semantic.append(f"smart-trend={value}")

    elif key.endswith(":update"):
        value = field("Update comparison assessment")
        if value:
            semantic.append(f"update-comparison={value}")

    elif key.endswith(":dns-routing"):
        dns = field(
            "DNS/routing assessment",
            ("Routing-conflict assessment",),
        )
        routing = field("Routing-conflict assessment")

        if dns:
            semantic.append(f"dns={dns}")
        if routing:
            semantic.append(f"routing={routing}")

    elif key.endswith(":tailscale"):
        value = field("Tailscale assessment")
        if value:
            semantic.append(f"tailscale={value}")

    elif key.endswith(":listeners"):
        value = field("Listening-service assessment")
        if value:
            semantic.append(f"listeners={value}")

    elif key.startswith("services:"):
        count = number("Failed-unit assessment")
        names = sorted(set(re.findall(
            r"(?i)Failed unit:\s*([^\s]+)",
            flat,
        )))

        if count:
            semantic.append(f"failed-count={count}")
        if names:
            semantic.append(
                "failed-units=" + ",".join(names)
            )

    elif "read-only" in key:
        count = number(
            "Unexpectedly read-only writable-storage mounts"
        )
        if not count:
            count = number("Unexpected read-only mounts")
        if count:
            semantic.append(f"read-only-count={count}")

    if semantic:
        return " | ".join(semantic).lower()[:1200]

    normalized = flat.lower()
    normalized = re.sub(
        r"\b\d{4}-\d{2}-\d{2}[t ]"
        r"\d{2}:\d{2}:\d{2}(?:\.\d+)?z?\b",
        "[timestamp]",
        normalized,
    )
    return normalized[:1200]



def _init_db(con):
    con.executescript("""
        CREATE TABLE IF NOT EXISTS question_memory_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_key TEXT NOT NULL,
            scan_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            question TEXT NOT NULL,
            verification_state TEXT NOT NULL,
            active_layer TEXT NOT NULL,
            direct_answer TEXT NOT NULL,
            answer_hash TEXT NOT NULL,
            UNIQUE(memory_key, scan_id)
        );
        CREATE INDEX IF NOT EXISTS idx_question_memory_key
            ON question_memory_entries(memory_key, scan_id DESC);
    """)


def _previous(con, memory_key):
    con.row_factory = sqlite3.Row
    row = con.execute("""
        SELECT memory_key, scan_id, created_at, updated_at, question,
               verification_state, active_layer, direct_answer, answer_hash
        FROM question_memory_entries
        WHERE memory_key = ?
        ORDER BY scan_id DESC, id DESC
        LIMIT 1
    """, (memory_key,)).fetchone()
    return dict(row) if row else None


def record_and_compare(
    memory_key,
    question,
    scan_id,
    verification_state,
    active_layer,
    direct_answer,
    db_path,
    created_at=None,
):
    key = str(memory_key or "").strip().lower()
    if not key:
        return {"ok": False, "state": "disabled", "lines": []}

    timestamp = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    question = _redact(question)
    direct_answer = _redact(direct_answer)
    verification_state = str(verification_state or "UNKNOWN")[:80]
    active_layer = str(active_layer or "Unknown")[:200]
    scan_id = int(scan_id or 0)
    comparison_value = _comparison_value(
        key, active_layer, direct_answer
    )
    answer_hash = _hash(
        f"{verification_state}|{active_layer}|{comparison_value}"
    )

    with sqlite3.connect(db_path, timeout=10) as con:
        _init_db(con)
        previous = _previous(con, key)

        con.execute("""
            INSERT INTO question_memory_entries (
                memory_key, scan_id, created_at, updated_at, question,
                verification_state, active_layer, direct_answer, answer_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(memory_key, scan_id) DO UPDATE SET
                updated_at = excluded.updated_at,
                question = excluded.question,
                verification_state = excluded.verification_state,
                active_layer = excluded.active_layer,
                direct_answer = excluded.direct_answer,
                answer_hash = excluded.answer_hash
        """, (
            key, scan_id, timestamp, timestamp, question,
            verification_state, active_layer, direct_answer, answer_hash,
        ))
        con.execute("""
            DELETE FROM question_memory_entries
            WHERE memory_key = ?
              AND id NOT IN (
                  SELECT id
                  FROM question_memory_entries
                  WHERE memory_key = ?
                  ORDER BY scan_id DESC, id DESC
                  LIMIT 50
              )
        """, (key, key))
        con.commit()

    if previous is None:
        return {
            "ok": True,
            "state": "first_observation",
            "previous": None,
            "lines": [],
        }

    same_snapshot = previous["scan_id"] == scan_id
    previous_comparison = _comparison_value(
        key,
        previous["active_layer"],
        previous["direct_answer"],
    )
    unchanged = (
        previous["verification_state"] == verification_state
        and previous["active_layer"] == active_layer
        and previous_comparison == comparison_value
    )

    lines = ["#### Previous answer comparison"]
    lines.append(f"- Matched question memory: `{key}`")

    if same_snapshot:
        lines.append(
            f"- This repeats evidence snapshot #{scan_id}; "
            "no new system scan is being compared."
        )
    else:
        lines.append(
            f"- Previous evidence snapshot: #{previous['scan_id']}; "
            f"current evidence snapshot: #{scan_id}."
        )

    lines.append(
        "- Direct conclusion: "
        + ("unchanged." if unchanged else "changed since the previous answer.")
    )
    lines.append(
        f"- Verification: {previous['verification_state']} → "
        f"{verification_state}."
    )

    if not unchanged:
        lines.append(
            f"- Previous conclusion: {previous_comparison[:600]}"
        )
        lines.append(
            f"- Current conclusion: {comparison_value[:600]}"
        )

    return {
        "ok": True,
        "state": (
            "same_snapshot"
            if same_snapshot
            else "unchanged"
            if unchanged
            else "changed"
        ),
        "previous": previous,
        "lines": lines,
    }


def memory_count(db_path):
    with sqlite3.connect(db_path, timeout=5) as con:
        _init_db(con)
        return con.execute(
            "SELECT COUNT(*) FROM question_memory_entries"
        ).fetchone()[0]
