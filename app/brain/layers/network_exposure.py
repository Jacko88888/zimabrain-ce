def _parse_docker_access(bundle):
    text = bundle.get("same_report_evidence", {}).get("docker_access", "")
    rows = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line or "|" not in line:
            continue

        parts = line.split("|", 2)
        if len(parts) != 3:
            continue

        name = parts[0].lstrip("/")
        mounts = parts[1]
        ports = parts[2]

        rows.append({
            "name": name,
            "mounts": mounts,
            "ports": ports,
        })

    return rows


def _parse_docker_ps(bundle):
    text = bundle.get("same_report_evidence", {}).get("docker_ps", "")
    rows = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line or "|" not in line:
            continue

        parts = line.split("|", 3)
        if len(parts) != 4:
            continue

        rows.append({
            "name": parts[0].strip(),
            "image": parts[1].strip(),
            "status": parts[2].strip(),
            "ports": parts[3].strip(),
        })

    return rows


def _has_published_ports(ports):
    if not ports:
        return False

    low = ports.lower().strip()
    if low in ("{}", "null", "none", "<nil>"):
        return False

    return (
        "hostport" in low
        or "0.0.0.0:" in low
        or ":::" in low
        or "->" in low
        or "=>" in low
    )


def _is_remote_access_name(name):
    low = name.lower()
    return any(x in low for x in [
        "cloudflare",
        "cloudflared",
        "tailscale",
        "wireguard",
        "zerotier",
        "nginx",
        "traefik",
        "caddy",
        "proxy",
        "tunnel",
    ])


def answer(bundle):
    lines = []

    evidence = bundle.get("same_report_evidence", {})
    docker_user = evidence.get("docker_user", "") or evidence.get("zfw_chains", "")
    zfw_status = evidence.get("zfw_status", "")
    zfw_files = evidence.get("zfw_files", "")
    zfw_chains = evidence.get("zfw_chains", "")
    self_docker_security = evidence.get("self_docker_security", "")
    docker_rows = _parse_docker_access(bundle)
    docker_ps_rows = _parse_docker_ps(bundle)

    lines.append("- This is a network exposure / firewall verification question.")
    lines.append("- The answer comes from the Network Exposure / Firewall Layer using same-report Docker and firewall evidence.")
    lines.append("")

    published = []
    data_rw_published = []
    remote_access = []
    docker_ps_ports = []

    for row in docker_rows:
        name = row["name"]
        mounts = row["mounts"]
        ports = row["ports"]

        if _has_published_ports(ports):
            published.append(f"{name}: {ports}")

        if "/DATA->" in mounts and ":true" in mounts and _has_published_ports(ports):
            data_rw_published.append(f"{name}: /DATA rw with published ports: {ports}")

        if _is_remote_access_name(name):
            remote_access.append(f"{name}: {ports or 'no parsed published port'}")

    for row in docker_ps_rows:
        if row["ports"]:
            docker_ps_ports.append(f"{row['name']}: {row['ports']}")
        if _is_remote_access_name(row["name"]):
            remote_access.append(f"{row['name']}: {row['ports'] or row['status']}")

    lines.append("### Published Docker ports")
    if published:
        for item in published[:30]:
            lines.append(f"- {item}")
    elif docker_ps_ports:
        for item in docker_ps_ports[:30]:
            lines.append(f"- {item}")
    else:
        lines.append("- No published Docker ports were parsed from the current report.")

    lines.append("")
    lines.append("### High-risk exposure checks")
    if data_rw_published:
        lines.append("- Containers with full `/DATA` read-write access and published ports:")
        for item in data_rw_published[:20]:
            lines.append(f"  - {item}")
    else:
        lines.append("- No container with full `/DATA` read-write access and published ports was detected in this report.")

    lines.append("")
    lines.append("### Remote access / tunnel indicators")
    if remote_access:
        seen = set()
        for item in remote_access:
            if item in seen:
                continue
            seen.add(item)
            lines.append(f"- {item}")
    else:
        lines.append("- No Cloudflare, Tailscale, proxy, tunnel, or similar remote-access container names were detected from parsed evidence.")

    lines.append("")
    lines.append("### ZimaBrain CE self audit")
    if self_docker_security.strip():
        lines.append("- ZimaBrain CE inspected its own container security settings.")
        lines.append(f"- {self_docker_security.strip()}")
        low_self = self_docker_security.lower()
        if "privileged=true" in low_self or "pidmode=host" in low_self or "dockersock=" in low_self:
            lines.append("- Self-audit warning: this container has elevated host visibility/access for evidence collection.")
            lines.append("- This is useful for local verification, but should not be exposed without access control.")
    else:
        lines.append("- No self-audit Docker security evidence was collected for ZimaBrain CE.")

    lines.append("")
    lines.append("### ZFW firewall status")
    zfw_installed = bool(zfw_files.strip()) or "zfw-ui.service" in zfw_status or "zfw.raw" in zfw_files
    zfw_active = zfw_status.strip() == "active"
    zfw_applied = "ZFW-IN" in zfw_chains or "ZFW-IN6" in zfw_chains or "ZFW-DOCK-DROP" in zfw_chains

    if zfw_installed:
        lines.append("- ZFW appears installed from host evidence.")
        lines.append(f"- zfw-ui.service: {zfw_status.strip() or 'unknown'}")
        if zfw_applied:
            lines.append("- ZFW firewall chains/rules appear applied.")
        else:
            lines.append("- ZFW is installed/active, but firewall rules do not appear applied yet.")
            lines.append("- Current evidence suggests DOCKER-USER may still be pass-through until Safe-Apply/Commit is used.")
    else:
        lines.append("- ZFW was not detected from host service, module, or rules evidence.")

    lines.append("")
    lines.append("### DOCKER-USER firewall chain")
    if docker_user.strip():
        lines.append("- DOCKER-USER evidence was collected.")
        if "-A DOCKER-USER -j RETURN" in docker_user or docker_user.strip() == "-N DOCKER-USER":
            lines.append("- The DOCKER-USER chain appears open or mostly pass-through from the parsed evidence.")
        else:
            lines.append("- The DOCKER-USER chain contains rules. Review them before assuming Docker ports are blocked.")
    else:
        lines.append("- No DOCKER-USER firewall evidence was parsed from the current report.")

    lines.append("")
    lines.append("### How to interpret this")
    lines.append("- A published Docker port only proves Docker has mapped the port; LAN reachability still depends on host firewall, ZFW, router, VLAN, and bind rules.")
    lines.append("- A tunnel container can expose services externally even when router port-forwarding is not used.")
    lines.append("- A container with `/DATA` write access and a published port deserves extra attention.")
    lines.append("- Do not change firewall rules until the service, port, and access path are confirmed.")

    return {
        "lines": lines,
        "next_step": "Review the listed published ports and any tunnel/proxy containers, then confirm authentication and firewall restrictions before exposing services further.",
        "forum_summary": "Network exposure should be verified from Docker published ports, tunnel/proxy containers, and DOCKER-USER firewall evidence. Do not assume a service is safe just because it is local. Confirm the exact port, service, authentication, and firewall path before exposing it.",
    }
