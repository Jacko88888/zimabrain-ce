#!/usr/bin/env python3
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))

from brain import router

expected_path = ROOT / "tests/public-release/router-quality-expected-v2.csv"
out_path = ROOT / "tests/public-release/router-quality-results-v2.md"

rows = []
passed = 0
failed = 0

with expected_path.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        q = r["question"]
        expected = r["expected_intent"]
        route = router.classify(q)
        actual = route.get("_intent", "unknown")
        confidence = route.get("_confidence", 0)
        candidates = route.get("_candidates", [])
        ok = actual == expected
        if ok:
            passed += 1
            result = "PASS"
        else:
            failed += 1
            result = "FAIL"

        rows.append({
            "id": r["id"],
            "question": q,
            "expected": expected,
            "actual": actual,
            "confidence": confidence,
            "result": result,
            "candidates": candidates,
        })

lines = []
lines.append("# ZimaBrain CE Router Quality Results v2")
lines.append("")
lines.append(f"Total: {passed + failed}")
lines.append(f"Passed: {passed}")
lines.append(f"Failed: {failed}")
lines.append(f"Score: {round((passed / max(passed + failed, 1)) * 100, 2)}%")
lines.append("")
lines.append("| ID | Result | Expected | Actual | Confidence | Question |")
lines.append("|---:|:---:|---|---|---:|---|")

for r in rows:
    lines.append(
        f"| {r['id']} | {r['result']} | {r['expected']} | {r['actual']} | {r['confidence']} | {r['question']} |"
    )

lines.append("")
lines.append("## Failed details")
lines.append("")

for r in rows:
    if r["result"] == "FAIL":
        lines.append(f"### {r['id']}. {r['question']}")
        lines.append(f"- Expected: `{r['expected']}`")
        lines.append(f"- Actual: `{r['actual']}`")
        lines.append(f"- Confidence: `{r['confidence']}`")
        lines.append(f"- Top candidates: `{r['candidates']}`")
        lines.append("")

out_path.write_text("\n".join(lines), encoding="utf-8")
print(out_path)
print(f"PASS={passed} FAIL={failed} SCORE={round((passed / max(passed + failed, 1)) * 100, 2)}%")
