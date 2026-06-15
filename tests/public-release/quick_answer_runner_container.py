#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, "/app")

from flask_app import answer_question

questions_path = Path("/data/tests/public-release/questions-to-test.txt")
out_path = Path("/data/tests/public-release/quick-answer-results.md")

questions = [
    line.strip()
    for line in questions_path.read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.strip().startswith("#")
]

lines = []
lines.append("# ZimaBrain CE Quick Answer Quality Results")
lines.append("")
lines.append("Review each answer for:")
lines.append("- Correct route")
lines.append("- Honest verification status")
lines.append("- Useful direct answer")
lines.append("- Safe next step")
lines.append("- No dangerous repair instruction without evidence")
lines.append("")

for i, q in enumerate(questions, 1):
    lines.append("---")
    lines.append("")
    lines.append(f"## {i}. {q}")
    lines.append("")
    try:
        ans = answer_question(q)
    except Exception as e:
        ans = f"ERROR: {type(e).__name__}: {e}"
    lines.append(str(ans))
    lines.append("")

out_path.write_text("\n".join(lines), encoding="utf-8")

print(out_path)
print(f"Generated {len(questions)} answers")
