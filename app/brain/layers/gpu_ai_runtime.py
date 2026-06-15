def _lines(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


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

        rows.append({
            "name": parts[0].lstrip("/"),
            "mounts": parts[1],
            "ports": parts[2],
        })

    return rows


def _is_ai_container(name):
    low = name.lower()
    return any(x in low for x in [
        "ollama",
        "open-webui",
        "openwebui",
        "pdf-ai",
        "stable-diffusion",
        "comfyui",
        "invokeai",
        "text-generation-webui",
        "llama",
    ])


def _nvidia_bad(nvidia_text):
    low = (nvidia_text or "").lower()
    return (
        not nvidia_text.strip()
        or "failed" in low
        or "not found" in low
        or "couldn't communicate" in low
        or "no devices were found" in low
        or "error" in low
    )


def answer(bundle):
    lines = []

    evidence = bundle.get("same_report_evidence", {})
    nvidia = evidence.get("nvidia", "")
    docker_ps_rows = _parse_docker_ps(bundle)
    docker_access_rows = _parse_docker_access(bundle)

    ai_containers = [r for r in docker_ps_rows if _is_ai_container(r["name"]) or _is_ai_container(r["image"])]
    ai_mounts = [r for r in docker_access_rows if _is_ai_container(r["name"])]
    nvidia_lines = _lines(nvidia)
    gpu_bad = _nvidia_bad(nvidia)

    lines.append("- This is a GPU / AI runtime verification question.")
    lines.append("- The answer comes from the GPU / AI Runtime Layer using same-report NVIDIA and Docker evidence.")
    lines.append("")

    lines.append("### Host NVIDIA evidence")
    if nvidia_lines:
        for item in nvidia_lines[:12]:
            lines.append(f"- {item}")
    else:
        lines.append("- No `nvidia-smi` output was parsed from the current report.")

    lines.append("")
    lines.append("### AI containers detected")
    if ai_containers:
        for c in ai_containers[:20]:
            lines.append(f"- {c['name']}: image={c['image']}, status={c['status']}, ports={c['ports']}")
    else:
        lines.append("- No Ollama, Open WebUI, PDF-AI, or similar AI containers were detected from parsed Docker evidence.")

    lines.append("")
    lines.append("### AI storage / port clues")
    if ai_mounts:
        for c in ai_mounts[:20]:
            lines.append(f"- {c['name']}: mounts={c['mounts'][:220]}, ports={c['ports']}")
    else:
        lines.append("- No AI container mount evidence was parsed.")

    lines.append("")
    lines.append("### GPU runtime verdict")
    if ai_containers and gpu_bad:
        lines.append("- AI containers appear to be running, but host NVIDIA evidence is not usable.")
        lines.append("- This means the AI stack may be CPU-only or GPU runtime may not be connected.")
    elif ai_containers and not gpu_bad:
        lines.append("- AI containers are running and host NVIDIA evidence is present.")
        lines.append("- This is a good sign, but it does not prove the containers themselves are using the GPU.")
    elif not ai_containers and not gpu_bad:
        lines.append("- Host NVIDIA evidence is present, but no AI containers were detected.")
    else:
        lines.append("- No usable host NVIDIA evidence and no AI containers were detected.")

    lines.append("")
    lines.append("### How to interpret this")
    lines.append("- `nvidia-smi` working on the host only proves the host can see the GPU.")
    lines.append("- It does not prove Ollama or Open WebUI is using the GPU inside the container.")
    lines.append("- Ollama on port `11434` can still run CPU-only if the GPU runtime is not passed through.")
    lines.append("- Do not assume GPU acceleration until host NVIDIA, Docker runtime, and container-level GPU access are all verified.")

    return {
        "lines": lines,
        "next_step": "Verify host nvidia-smi first, then verify GPU visibility inside the intended AI container before assuming Ollama/Open WebUI is GPU accelerated.",
        "forum_summary": "GPU acceleration should be verified in layers: host NVIDIA visibility, Docker GPU runtime, then GPU visibility inside the AI container. Ollama or Open WebUI can be running while still using CPU-only if the GPU is not passed through.",
    }
