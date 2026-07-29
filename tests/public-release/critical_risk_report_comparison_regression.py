#!/usr/bin/env python3
import sys

sys.path.insert(0, "/app")

from brain import intent_policy
from brain import router
from brain.layers import comprehensive_health
from brain.layers import report_comparison
from brain.layers import trend_history


failures = []


def require(condition, message):
    if not condition:
        failures.append(message)


critical_question = "Are there any critical risks?"
critical_policy = intent_policy.classify(critical_question)
critical_route = router.classify(critical_question)

require(
    critical_policy["handler"] == "comprehensive_health",
    "critical-risk policy did not select comprehensive health",
)
require(
    critical_route["_intent"] == "comprehensive_health",
    f"critical-risk route was {critical_route['_intent']!r}",
)

original_timeline = comprehensive_health._timeline
comprehensive_health._timeline = lambda: (
    None, [], [], [], {}, {}
)
try:
    critical_answer = comprehensive_health.answer(
        {
            "same_report_evidence": {},
            "critical_findings": [],
            "normalized": {"info_only": ["context"]},
        },
        critical_question,
    )
finally:
    comprehensive_health._timeline = original_timeline

critical_text = "\n".join(critical_answer["lines"])
require(
    "#### Critical risk assessment" in critical_text,
    "critical-risk assessment section was not rendered",
)
require(
    "No critical risks were verified." in critical_text,
    "no-critical-risk conclusion was not rendered",
)

comparison_question = "What has changed since the previous scan?"
comparison_policy = intent_policy.classify(comparison_question)
comparison_route = router.classify(comparison_question)

require(
    comparison_policy["handler"] == "trend_history",
    "prepared comparison question did not select trend history",
)
require(
    comparison_route["_intent"] == "trend_history",
    f"prepared comparison route was {comparison_route['_intent']!r}",
)
require(
    trend_history.is_trend_question(comparison_question),
    "prepared comparison question was not recognised by trend history",
)

structured_value = {
    "state": "running",
    "details": {
        "ports": [8601, 8717],
        "empty": "",
    },
}
require(
    report_comparison._count_lines(structured_value) == 3,
    "structured line count was not normalised safely",
)

comparison_answer = report_comparison.answer({
    "report": "current report",
    "normalized": {},
    "same_report_evidence": {
        "structured": structured_value,
        "plain": "one\n\ntwo",
    },
    "critical_findings": [{
        "title": "Structured finding",
        "detail": {"state": "attention", "count": 1},
    }],
    "disks": [],
    "exited": [],
})
comparison_text = "\n".join(comparison_answer["lines"])
require(
    "- structured: 3 non-empty lines" in comparison_text,
    "structured evidence coverage was not rendered",
)
require(
    "- plain: 2 non-empty lines" in comparison_text,
    "plain-text evidence coverage changed unexpectedly",
)
require(
    "Structured finding:" in comparison_text
    and '"state": "attention"' in comparison_text,
    "structured finding detail was not rendered safely",
)

if failures:
    print(f"RESULT: FAIL ({len(failures)} failure(s))")
    for failure in failures:
        print(f"- {failure}")
    sys.exit(1)

print(
    "RESULT: PASS "
    "(critical-risk routing and structured report comparison)"
)
