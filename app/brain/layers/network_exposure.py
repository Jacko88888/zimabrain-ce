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




def _published_bind_map(rows):
    bind_map = {}

    for row in rows:
        name = row.get("name", "")
        ports = row.get("ports", "")

        for item in ports.split(";"):
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

                if not host_port.isdigit():
                    continue

                bind_map.setdefault((name, host_port), set()).add(host_ip)

    return bind_map


def _bind_label(bind_ips):
    if not bind_ips:
        return "unknown"

    ordered = sorted(bind_ips)
    return ",".join(ordered)


def _is_localhost_only_bind(bind_ips):
    if not bind_ips:
        return False

    return all(ip in {"127.0.0.1", "::1", "localhost"} for ip in bind_ips)

def _parse_port_reachability(bundle):
    text = bundle.get("same_report_evidence", {}).get("port_reachability", "")
    rows = []
    host_ip = ""

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        if line.startswith("HOST_LAN_IP="):
            host_ip = line.split("=", 1)[1].strip()
            continue

        parts = line.split("|")
        if len(parts) < 5:
            continue

        name = parts[0].strip()
        port = parts[1].strip()
        local = ""
        lan = ""
        lan_ip = host_ip

        for part in parts[2:]:
            if part.startswith("localhost="):
                local = part.split("=", 1)[1].strip()
            elif part.startswith("lan="):
                lan = part.split("=", 1)[1].strip()
            elif part.startswith("lan_ip="):
                lan_ip = part.split("=", 1)[1].strip()

        rows.append({
            "name": name,
            "port": port,
            "localhost": local,
            "lan": lan,
            "lan_ip": lan_ip,
        })

    return host_ip, rows


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
    reachability_host_ip, reachability_rows = _parse_port_reachability(bundle)
    bind_map = _published_bind_map(docker_rows)

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

    remote_by_name = {}
    for item in remote_access:
        name = item.split(":", 1)[0].strip()
        current = remote_by_name.get(name)
        if current is None:
            remote_by_name[name] = item
            continue
        if "no parsed published port" in current and "no parsed published port" not in item:
            remote_by_name[name] = item

    remote_access = list(remote_by_name.values())

    lines.append("### Top exposure risks first")

    top_risks = []

    if data_rw_published:
        top_risks.append(f"{len(data_rw_published)} container(s) have full `/DATA` read-write access and published ports.")

    if remote_access:
        top_risks.append(f"{len(set(remote_access))} remote-access / tunnel / proxy indicator(s) were detected.")

    if self_docker_security.strip():
        low_self = self_docker_security.lower()
        if "privileged=true" in low_self or "pidmode=host" in low_self or "dockersock=" in low_self:
            top_risks.append("ZimaBrain CE has elevated host visibility/access for evidence collection.")

    if zfw_status.strip() == "active" and not ("ZFW-IN" in zfw_chains or "ZFW-IN6" in zfw_chains or "ZFW-DOCK-DROP" in zfw_chains):
        top_risks.append("ZFW service appears active, but parsed firewall chains do not show rules applied yet.")

    if docker_user.strip() and ("-A DOCKER-USER -j RETURN" in docker_user or docker_user.strip() == "-N DOCKER-USER"):
        top_risks.append("DOCKER-USER appears open or mostly pass-through from parsed evidence.")

    blocked_reachable = []
    localhost_only_reachable = []

    for r in reachability_rows:
        if r.get("localhost") == "open" and r.get("lan") == "closed":
            bind_ips = bind_map.get((r.get("name", ""), r.get("port", "")), set())
            if _is_localhost_only_bind(bind_ips):
                localhost_only_reachable.append(r)
            else:
                blocked_reachable.append(r)

    if blocked_reachable:
        top_risks.append(f"{len(blocked_reachable)} published port(s) answer locally but not on the host LAN IP; firewall, ZFW, VLAN, router path, or bind behaviour may be blocking access.")

    if localhost_only_reachable:
        top_risks.append(f"{len(localhost_only_reachable)} published port(s) appear intentionally localhost-only and are not reachable on the host LAN IP.")

    if top_risks:
        for item in top_risks:
            lines.append(f"- {item}")
    else:
        lines.append("- No top exposure risk was detected from the parsed evidence.")

    lines.append("")
    lines.append("### Published Docker ports")
    port_source = published if published else docker_ps_ports
    if port_source:
        lines.append(f"- Parsed published-port entries: {len(port_source)}")
        for item in port_source[:15]:
            lines.append(f"- {item}")
        if len(port_source) > 15:
            lines.append(f"- Additional published-port entries hidden from summary: {len(port_source) - 15}")
    else:
        lines.append("- No published Docker ports were parsed from the current report.")

    lines.append("")
    lines.append("### Port reachability self-check")
    if reachability_rows:
        lines.append(f"- Host LAN IP used for reachability probe: `{reachability_host_ip or 'unknown'}`")
        lines.append("- Localhost open + LAN closed can mean either an intentional localhost-only bind or a firewall/ZFW/VLAN/router/bind issue. The bind field helps separate those cases.")

        lan_reachable = []
        localhost_only = []
        possible_blocked = []
        other_reachability = []

        for r in reachability_rows:
            bind_ips = bind_map.get((r.get("name", ""), r.get("port", "")), set())
            item = {
                "row": r,
                "bind_ips": bind_ips,
                "bind": _bind_label(bind_ips),
            }

            if r.get("lan") == "open":
                lan_reachable.append(item)
            elif r.get("localhost") == "open" and r.get("lan") == "closed" and _is_localhost_only_bind(bind_ips):
                localhost_only.append(item)
            elif r.get("localhost") == "open" and r.get("lan") == "closed":
                possible_blocked.append(item)
            else:
                other_reachability.append(item)

        lines.append("")
        lines.append("#### Reachability summary")
        lines.append(f"- LAN reachable: {len(lan_reachable)}")
        lines.append(f"- Intentional localhost-only: {len(localhost_only)}")
        lines.append(f"- Possible firewall / ZFW / VLAN / bind block: {len(possible_blocked)}")
        if other_reachability:
            lines.append(f"- Other / unknown reachability: {len(other_reachability)}")

        def emit_group(title, items, limit=12):
            lines.append("")
            lines.append(f"#### {title}")
            if not items:
                lines.append("- None detected.")
                return

            for item in items[:limit]:
                r = item["row"]
                note = ""
                if title.startswith("Intentional"):
                    note = " expected-localhost-only"
                elif title.startswith("Possible"):
                    note = " possible-firewall-or-bind-block"

                lines.append(
                    f"- {r['name']}:{r['port']} bind={item['bind']} "
                    f"localhost={r['localhost']} lan={r['lan']} lan_ip={r['lan_ip']}{note}"
                )

            if len(items) > limit:
                lines.append(f"- Additional entries hidden from this group: {len(items) - limit}")

        emit_group("LAN reachable", lan_reachable, limit=18)
        emit_group("Intentional localhost-only", localhost_only, limit=18)
        emit_group("Possible firewall / ZFW / VLAN / bind block", possible_blocked, limit=18)

        if other_reachability:
            emit_group("Other / unknown reachability", other_reachability, limit=18)
    else:
        lines.append("- No live port reachability probe evidence was collected.")

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
    lines.append("- A published Docker port only proves Docker has mapped the port; LAN reachability still depends on host firewall, ZFW, router, VLAN, bind rules, and whether the service answers on the host LAN IP.")
    lines.append("- A tunnel container can expose services externally even when router port-forwarding is not used.")
    lines.append("- A container with `/DATA` write access and a published port deserves extra attention.")
    lines.append("- Do not change firewall rules until the service, port, and access path are confirmed.")

    return {
        "lines": lines,
        "next_step": "Review published ports, reachability results, tunnel/proxy containers, authentication, and firewall restrictions before exposing services further.",
        "forum_summary": "Network exposure should be verified from Docker published ports, live localhost/LAN reachability, tunnel/proxy containers, and DOCKER-USER firewall evidence. Do not assume a service is safe just because Docker published a port. Confirm the exact port, service, authentication, bind address, and firewall path before exposing it.",
    }
