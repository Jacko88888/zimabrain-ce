from brain.layers.comprehensive_health import _docker_states


def _security_rows(text):
    rows = []

    for raw in str(text or "").splitlines():
        parts = raw.strip().split("|")
        if not parts or not parts[0]:
            continue

        values = {"name": parts[0].lstrip("/")}

        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                values[key] = value

        rows.append(values)

    return rows


def answer(bundle, question=""):
    evidence = bundle.get("same_report_evidence", {}) or {}
    q = str(question or "").lower()

    configuration_focus = any(
        term in q
        for term in (
            "misconfigured", "misconfiguration", "configuration",
            "configured", "privileged", "docker socket",
            "capability", "capabilities", "security", "risky",
        )
    )

    if configuration_focus:
        rows = _security_rows(
            evidence.get("docker_security", "")
        )

        privileged = [
            row for row in rows
            if row.get("Privileged", "").lower() == "true"
        ]
        docker_socket = [
            row for row in rows
            if row.get("DockerSock", "")
        ]
        host_pid = [
            row for row in rows
            if row.get("PidMode", "").lower() == "host"
        ]
        capabilities = [
            row for row in rows
            if row.get("CapAdd", "") not in ("", "[]", "<nil>")
        ]

        flagged_names = sorted({
            row["name"]
            for group in (
                privileged,
                docker_socket,
                host_pid,
                capabilities,
            )
            for row in group
        })

        lines = [
            "- This is a current container configuration-risk assessment.",
            "- Elevated settings are risk flags, not automatic proof that "
            "a container is incorrectly configured.",
            "",
            "### Container configuration assessment",
            (
                "- Container configuration assessment: "
                f"{len(rows)} running container(s) were inspected; "
                f"{len(flagged_names)} had one or more elevated settings."
            ),
            f"- Privileged containers: {len(privileged)}",
            f"- Docker-socket containers: {len(docker_socket)}",
            f"- Host-PID containers: {len(host_pid)}",
            (
                "- Containers with added capabilities: "
                f"{len(capabilities)}"
            ),
            "",
            "### Flagged containers",
        ]

        if flagged_names:
            by_name = {
                row["name"]: row for row in rows
            }

            for name in flagged_names:
                row = by_name[name]
                flags = []

                if row in privileged:
                    flags.append("privileged")
                if row in docker_socket:
                    flags.append("Docker socket")
                if row in host_pid:
                    flags.append("host PID namespace")
                if row in capabilities:
                    flags.append(
                        f"added capabilities {row.get('CapAdd')}"
                    )

                lines.append(
                    f"- {name}: {', '.join(flags)}"
                )
        else:
            lines.append("- No elevated setting was captured.")

        return {
            "lines": lines,
            "trust_state": "PARTIALLY VERIFIED",
            "trust_title":
                "⚠️ PARTIALLY VERIFIED CONFIGURATION ASSESSMENT",
            "trust_detail": (
                "Current Docker inspect evidence verifies elevated "
                "settings. Whether each setting is necessary depends "
                "on the container's documented purpose."
            ),
            "next_step": (
                "Review each flagged container against its trusted "
                "deployment documentation before removing privileges, "
                "capabilities, host PID access, or Docker-socket access."
            ),
            "forum_summary": (
                f"ZimaBrain inspected {len(rows)} running container(s) "
                f"and flagged {len(flagged_names)} with elevated settings "
                "requiring purpose-specific review."
            ),
        }

    states = _docker_states(
        evidence.get("docker_states", "")
    )

    lines = [
        "- This is a container state question.",
        "- The answer uses current same-report Docker inspect evidence.",
        "",
    ]

    if states:
        running = [
            row for row in states
            if row["state"] == "running"
        ]
        exited = [
            row for row in states
            if row["state"] == "exited"
        ]
        restarting = [
            row for row in states
            if row["state"] == "restarting"
        ]
        unhealthy = [
            row for row in states
            if row["state"] == "running"
            and row["health"] == "unhealthy"
        ]

        lines.extend([
            "Current Docker state summary:",
            f"- Total containers inspected: {len(states)}",
            f"- Running containers: {len(running)}",
            f"- Exited containers: {len(exited)}",
            f"- Restarting containers: {len(restarting)}",
            f"- Unhealthy running containers: {len(unhealthy)}",
            "",
            "Restarting containers:",
        ])

        if restarting:
            for row in restarting:
                lines.append(
                    f"- {row['name']} ({row['image']}) — "
                    f"restart count {row['restart_count']}"
                )
        else:
            lines.append("- None detected.")

        lines.extend([
            "",
            "Unhealthy running containers:",
        ])

        if unhealthy:
            for row in unhealthy:
                lines.append(
                    f"- {row['name']} ({row['image']})"
                )
        else:
            lines.append("- None detected.")

        lines.extend([
            "",
            "Exited containers:",
        ])

        if exited:
            for row in exited:
                lines.append(
                    f"- {row['name']} ({row['image']})"
                )
        else:
            lines.append("- None detected.")

        next_step = (
            "Inspect the restarting or unhealthy container first. "
            "Confirm whether exited containers are intentionally stopped "
            "before changing configuration."
        )
        forum_summary = (
            f"Current Docker evidence shows {len(running)} running, "
            f"{len(exited)} exited, {len(restarting)} restarting, and "
            f"{len(unhealthy)} unhealthy running container(s)."
        )
    else:
        exited = bundle.get("exited", []) or []

        lines.append(
            "- Current Docker inspect evidence was unavailable; "
            "dashboard-parsed exited rows are the only available fallback."
        )

        if exited:
            lines.append("Dashboard-parsed exited containers:")

            for item in exited:
                lines.append(
                    f"- {item.get('name', 'unknown')} "
                    f"({item.get('image', 'unknown')})"
                )
        else:
            lines.append(
                "- No named exited containers were captured."
            )

        next_step = (
            "Collect current Docker state before classifying stopped, "
            "restarting, or unhealthy containers."
        )
        forum_summary = (
            "Current Docker inspect evidence was unavailable, so "
            "container state requires fresh verification."
        )

    return {
        "lines": lines,
        "next_step": next_step,
        "forum_summary": forum_summary,
    }
