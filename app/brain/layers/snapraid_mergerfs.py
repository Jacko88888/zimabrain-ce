def answer(bundle):
    lines = []
    lines.append("- This is a SnapRAID / mergerfs protection question.")
    lines.append("- The answer comes from the SnapRAID / mergerfs Layer using same-report verifier evidence.")
    lines.append("")
    lines.append("From the current same-report verifier:")
    lines.append("- No failed snapraid-sync.service protection failure was detected in this report.")
    lines.append("- No SnapRAID data/parity-on-same-physical-disk issue was detected in this report.")
    lines.append("- No full host /DATA mounted back as /DATA with published ports was detected in this report.")
    lines.append("")
    lines.append("Important limitation:")
    lines.append("- This does not prove SnapRAID is fully configured or fully healthy.")
    lines.append("- It only means the current critical rules did not detect Holger’s red protection failures in this report.")
    lines.append("")
    lines.append("What still needs verification before trusting protection:")
    lines.append("- SnapRAID config file")
    lines.append("- data disk list")
    lines.append("- parity disk identity")
    lines.append("- last sync result")
    lines.append("- scrub status")
    lines.append("- whether parity is on a separate physical disk")

    return {
        "lines": lines,
        "next_step": "If you rely on SnapRAID/mergerfs protection, verify config, parity disk, last sync, and scrub status before treating the pool as protected.",
        "forum_summary": "Based on the verified report, no failed snapraid-sync.service or same-disk SnapRAID parity issue was detected. However, this does not prove protection is fully healthy. Verify SnapRAID config, parity disk identity, last sync, and scrub status before treating the pool as protected.",
    }
