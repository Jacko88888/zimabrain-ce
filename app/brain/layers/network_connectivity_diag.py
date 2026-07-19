import re


def _lines(value):
    return [
        line.strip()
        for line in str(value or "").splitlines()
        if line.strip()
    ]


def _interfaces(text):
    rows = []
    for line in _lines(text):
        parts = line.split()
        if len(parts) < 3:
            continue
        name = parts[0]
        state = parts[1]
        addresses = [
            part for part in parts[2:]
            if "/" in part and part[0].isdigit()
        ]
        if addresses:
            rows.append({
                "name": name,
                "state": state,
                "addresses": addresses,
            })
    return rows


def _route_sections(text):
    routes = []
    rules = []
    route_get = []
    section = "routes"

    for line in _lines(text):
        if line == "---RULES---":
            section = "rules"
            continue
        if line == "---ROUTE_GET---":
            section = "route_get"
            continue

        if section == "routes":
            routes.append(line)
        elif section == "rules":
            rules.append(line)
        else:
            route_get.append(line)

    return routes, rules, route_get


def _resolver_summary(text):
    nameservers = []
    lookup_rows = []
    section = "config"

    for line in _lines(text):
        if line == "---DNS_LOOKUP---":
            section = "lookup"
            continue

        if section == "config":
            if line.startswith("nameserver "):
                nameservers.append(line.split(None, 1)[1])
        elif line[0].isdigit():
            lookup_rows.append(line)

    return nameservers, lookup_rows


def _tailscale_assessment(text):
    rows = _lines(text)
    if not rows:
        return (
            "Tailscale status evidence was not captured.",
            False,
        )

    low = "\n".join(rows).lower()
    negative = any(
        marker in low
        for marker in (
            "tailscale is stopped",
            "backend state: stopped",
            "needs login",
            "logged out",
            "not logged in",
            "inactive (dead)",
            "failed",
        )
    )
    positive = bool(
        re.search(r"\b100(?:\.\d{1,3}){3}\b", low)
        or "tailscale0" in low
        or "active (running)" in low
        or "service_state=active" in low
        or "container_state=running" in low
        or "backend state: running" in low
    )

    if negative and not positive:
        return (
            "Captured Tailscale evidence indicates a stopped, failed, or "
            "logged-out state.",
            True,
        )
    if positive:
        return (
            "Captured Tailscale evidence indicates that the local tunnel is "
            "up. This confirms the local snapshot, not reachability to every peer.",
            True,
        )
    return (
        "Tailscale evidence was captured, but it does not establish a clear "
        "running or stopped state.",
        False,
    )


def answer(bundle, question):
    evidence = bundle.get("same_report_evidence", {}) or {}
    report = bundle.get("report", "") or ""

    network_keys = [
        "ip_addr", "ip_route", "resolv", "ping",
        "tailscale", "cloudflared", "docker_ps",
    ]
    found = [key for key in network_keys if evidence.get(key)]

    interfaces = _interfaces(evidence.get("ip_addr", ""))
    routes, rules, route_get = _route_sections(
        evidence.get("ip_route", "")
    )
    default_routes = [
        line for line in routes if line.startswith("default ")
    ]
    active_default_routes = [
        line for line in default_routes if "linkdown" not in line.split()
    ]
    inactive_default_routes = [
        line for line in default_routes if "linkdown" in line.split()
    ]
    nameservers, lookup_rows = _resolver_summary(
        evidence.get("resolv", "")
    )

    q = str(question or "").lower()
    multi_interface_question = (
        ("interface" in q or "interfaces" in q or " nic" in q)
        and ("routing" in q or "route" in q or "gateway" in q)
    )
    tailscale_question = "tailscale" in q
    listener_question = (
        any(
            term in q
            for term in (
                "listening", "listener", "listeners",
                "open port", "open ports",
            )
        )
        and any(
            term in q
            for term in (
                "service", "services", "process",
                "application", "app", "network",
            )
        )
    )

    if listener_question:
        raw = str(evidence.get("port_reachability", "") or "")
        endpoints = []
        lan_ip = "unknown"

        for raw_line in raw.splitlines():
            line = raw_line.strip()

            if line.startswith("HOST_LAN_IP="):
                lan_ip = line.split("=", 1)[1]
                continue

            parts = line.split("|")
            if len(parts) < 5:
                continue

            endpoints.append({
                "name": parts[0],
                "port": parts[1],
                "localhost": parts[2].split("=", 1)[-1],
                "lan": parts[3].split("=", 1)[-1],
            })

        local_open = [
            item for item in endpoints
            if item["localhost"] == "open"
        ]
        lan_open = [
            item for item in endpoints
            if item["lan"] == "open"
        ]
        localhost_only = [
            item for item in endpoints
            if item["localhost"] == "open"
            and item["lan"] == "closed"
        ]

        lines = [
            "- This is a current network-listener question.",
            "",
            "### Listening-service assessment",
            (
                "- Listening-service assessment: "
                f"{len(local_open)} published service endpoint(s) answered "
                f"locally; {len(lan_open)} answered on the LAN address; "
                f"{len(localhost_only)} were localhost-only."
            ),
            f"- Tested LAN address: {lan_ip}",
            "",
            "### Verified service endpoints",
        ]

        if endpoints:
            for item in endpoints[:30]:
                lines.append(
                    f"- {item['name']} port {item['port']}: "
                    f"localhost={item['localhost']}; "
                    f"LAN={item['lan']}"
                )
        else:
            lines.append(
                "- No published Docker service endpoint was captured."
            )

        return {
            "lines": lines,
            "trust_state": (
                "VERIFIED" if raw.strip() else "PARTIALLY VERIFIED"
            ),
            "trust_title": (
                "✅ VERIFIED FROM CURRENT NETWORK SNAPSHOT"
                if raw.strip()
                else "⚠️ PARTIALLY VERIFIED"
            ),
            "trust_detail": (
                "The current snapshot tested published Docker endpoints "
                "against localhost and the host LAN address."
                if raw.strip()
                else
                "Current endpoint reachability evidence was not captured."
            ),
            "next_step": (
                "For an unexpected LAN-open endpoint, confirm its Docker "
                "port publication and intended exposure before changing "
                "firewall rules."
            ),
            "forum_summary": (
                f"Current endpoint tests found {len(local_open)} locally "
                f"reachable and {len(lan_open)} LAN-reachable published "
                "service endpoint(s)."
            ),
        }

    if tailscale_question:
        tailscale_text = evidence.get("tailscale", "")
        assessment, state_known = _tailscale_assessment(tailscale_text)
        return {
            "lines": [
                "- This is a Tailscale connectivity status question.",
                "",
                "### Current Tailscale evidence",
                (
                    "- Tailscale evidence captured: "
                    f"{'yes' if str(tailscale_text).strip() else 'no'}"
                ),
                f"- Tailscale assessment: {assessment}",
            ],
            "trust_state": (
                "VERIFIED" if state_known else "PARTIALLY VERIFIED"
            ),
            "trust_title": (
                "✅ VERIFIED FROM CURRENT NETWORK SNAPSHOT"
                if state_known
                else "⚠️ PARTIALLY VERIFIED"
            ),
            "trust_detail": (
                "The answer reports the local Tailscale state captured in the "
                "current network snapshot."
                if state_known
                else "The captured Tailscale output does not establish a "
                "definite local tunnel state."
            ),
            "next_step": (
                "If a particular peer remains unreachable, test that peer "
                "directly and compare its Tailscale status, route, and ACL path."
            ),
            "forum_summary": (
                "ZimaBrain assessed the current local Tailscale status "
                "separately from general DNS and default-route health."
            ),
        }

    lines = []
    lines.append("- This is a network connectivity diagnostic question.")
    lines.append(
        "- The layer separates interface, default-route, DNS, "
        "gateway, tunnel/proxy, and container exposure evidence."
    )
    lines.append("")

    lines.append("### Same-report evidence")
    lines.append(
        f"- Network evidence keys found: "
        f"{', '.join(found) if found else 'none'}"
    )
    lines.append(
        f"- General report evidence present: "
        f"{'yes' if report.strip() else 'no'}"
    )
    lines.append(
        f"- Interfaces with IPv4 addresses: {len(interfaces)}"
    )
    for row in interfaces[:12]:
        lines.append(
            f"- Interface {row['name']}: state={row['state']}; "
            f"addresses={', '.join(row['addresses'])}"
        )

    lines.append(f"- Default routes detected: {len(default_routes)}")
    lines.append(
        f"- Active default routes detected: {len(active_default_routes)}"
    )
    for route in active_default_routes[:8]:
        lines.append(f"- Active default route: {route}")
    for route in inactive_default_routes[:8]:
        lines.append(f"- Inactive linkdown default route: {route}")

    lines.append(f"- IPv4 routing rules captured: {len(rules)}")
    if route_get:
        lines.append(f"- Route selection test: {route_get[0]}")

    lines.append(f"- Configured DNS nameservers: {len(nameservers)}")
    if nameservers:
        lines.append(f"- Nameservers: {', '.join(nameservers)}")
    lines.append(f"- DNS IPv4 lookup rows captured: {len(lookup_rows)}")
    if lookup_rows:
        lines.append(f"- DNS lookup evidence: {lookup_rows[0]}")

    lines.append("")
    lines.append("### DNS/routing assessment")

    if not default_routes:
        dns_routing = (
            "A routing problem is indicated because no IPv4 default route "
            "was captured."
        )
    elif not nameservers:
        dns_routing = (
            "Routing evidence exists, but DNS configuration is incomplete "
            "because no nameserver was captured."
        )
    elif not lookup_rows:
        dns_routing = (
            "A default route and resolver configuration were captured, but "
            "the test hostname did not produce a verified IPv4 lookup result."
        )
    else:
        dns_routing = (
            "No missing-default-route or DNS-resolution failure is indicated "
            "by the captured evidence."
        )

    lines.append(f"- DNS/routing assessment: {dns_routing}")

    if len(active_default_routes) > 1:
        routing_conflict = (
            "Multiple active IPv4 default routes were captured. Compare their "
            "interfaces, gateways, and metrics before changing routes."
        )
    elif len(active_default_routes) == 1 and route_get:
        routing_conflict = (
            "No active default-route conflict is indicated. One active default "
            "route was captured and the route-selection test chose a valid path."
        )
    elif len(active_default_routes) == 1:
        routing_conflict = (
            "One active default route was captured, but route selection was not "
            "verified."
        )
    else:
        routing_conflict = (
            "No active default route was captured, so route selection cannot "
            "be verified."
        )

    lines.append(
        f"- Routing-conflict assessment: {routing_conflict}"
    )

    if multi_interface_question and len(interfaces) > 1:
        lines.append(
            "- Multiple addressed interfaces are present, but multiple "
            "interfaces alone do not prove incorrect routing."
        )

    snapshot_verified = bool(
        len(active_default_routes) == 1
        and route_get
        and nameservers
        and lookup_rows
    )

    return {
        "lines": lines,
        "trust_state": (
            "VERIFIED" if snapshot_verified else "PARTIALLY VERIFIED"
        ),
        "trust_title": (
            "✅ VERIFIED FROM CURRENT NETWORK SNAPSHOT"
            if snapshot_verified
            else "⚠️ PARTIALLY VERIFIED"
        ),
        "trust_detail": (
            "Current evidence confirms DNS resolution, resolver configuration, "
            "route selection, and exactly one active default route. This does "
            "not rule out intermittent or destination-specific failures."
            if snapshot_verified
            else "One or more required DNS or active-route checks remain incomplete."
        ),
        "next_step": (
            "If connectivity still fails, compare the affected destination "
            "against the captured route selection, DNS result, interface, "
            "gateway, and route metric before changing firewall or Docker."
        ),
        "forum_summary": (
            f"ZimaBrain captured {len(interfaces)} addressed interface(s), "
            f"{len(default_routes)} IPv4 default route(s), "
            f"{len(nameservers)} resolver(s), and "
            f"{len(lookup_rows)} DNS lookup row(s). "
            "Multiple interfaces are not classified as a routing conflict "
            "unless the route evidence supports that conclusion."
        ),
    }
