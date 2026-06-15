#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))

from brain.layers.manual_knowledge import _load_index, _score_page

tests = [
    ("How do I enable SSH in ZimaOS?", "ssh"),
    ("How do I find my Network ID?", "network"),
    ("How do I create a bootable USB for ZimaOS?", "install"),
    ("How do I install ZimaOS?", "install"),
    ("How do I migrate my data to another drive?", "migration"),
    ("How do I use 3-2-1 backup on ZimaOS?", "backup"),
    ("How do I access ZimaOS remotely?", "remote"),
    ("How do I setup SMB shares?", "smb"),
    ("How do I troubleshoot slow transfer speed?", "transfer"),
    ("How do I rebuild RAID after reinstall?", "rebuild"),
]

pages = _load_index()
out_path = ROOT / "tests/public-release/manual-relevance-results.md"

def ok(expected, title, url, score):
    blob = f"{title} {url}".lower()

    if expected == "no_strong_match":
        return score < 35

    return expected in blob and score >= 35

lines = []
passed = 0

lines.append("# ZimaBrain CE Manual Relevance Results")
lines.append("")
lines.append("| ID | Result | Expected | Score | Top Manual Page | URL | Question |")
lines.append("|---:|---|---|---:|---|---|---|")

for i, (q, expected) in enumerate(tests, 1):
    ranked = sorted(
        [(_score_page(q, p), p) for p in pages],
        key=lambda x: x[0],
        reverse=True
    )

    score, page = ranked[0]
    title = page.get("title") or ""
    url = page.get("url") or ""

    result = "PASS" if ok(expected, title, url, score) else "FAIL"
    if result == "PASS":
        passed += 1

    lines.append(f"| {i} | {result} | {expected} | {score} | {title} | {url} | {q} |")

total = len(tests)
score_pct = round((passed / total) * 100, 2)

lines.insert(2, f"Total: {total}")
lines.insert(3, f"Passed: {passed}")
lines.insert(4, f"Failed: {total - passed}")
lines.insert(5, f"Score: {score_pct}%")
lines.insert(6, "")

out_path.write_text("\n".join(lines), encoding="utf-8")

print(out_path)
print(f"PASS={passed} FAIL={total-passed} SCORE={score_pct}%")
