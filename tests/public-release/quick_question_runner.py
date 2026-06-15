#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))

from brain import router

questions_path = ROOT / "tests/public-release/questions-to-test.txt"
out_path = ROOT / "tests/public-release/quick-question-results.md"

questions = [
    line.strip()
    for line in questions_path.read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.strip().startswith("#")
]

lines = []
lines.append("# ZimaBrain CE Quick Question Results")
lines.append("")
lines.append("| ID | Intent | Confidence | Question |")
lines.append("|---:|---|---:|---|")

for i, q in enumerate(questions, 1):
    r = router.classify(q)
    lines.append(f"| {i} | {r.get('_intent')} | {r.get('_confidence')} | {q} |")

out_path.write_text("\n".join(lines), encoding="utf-8")

print(out_path)
print(f"Tested {len(questions)} questions")
