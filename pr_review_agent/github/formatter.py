"""Format ReviewResult into markdown for GitHub PR comments."""

from __future__ import annotations

from pr_review_agent.agents.base import Finding, ReviewResult

SEVERITY_EMOJI = {
    "critical": "🔴",
    "warning": "🟡",
    "info": "🔵",
}

HEADER = "## 🤖 PR Review Agent\n\n"
FOOTER = "\n\n---\n*Automated review by [PR Review Agent](https://github.com) — powered by multi-agent analysis*"


def format_review_body(review: ReviewResult) -> str:
    """Format a ReviewResult into a markdown string for GitHub."""
    parts = [HEADER]

    parts.append(review.body)

    # Append a severity summary table if the summarizer didn't include one
    if review.findings and "| Severity" not in review.body:
        parts.append(_severity_table(review.findings))

    parts.append(FOOTER)
    return "\n".join(parts)


def _severity_table(findings: list[Finding]) -> str:
    counts = {"critical": 0, "warning": 0, "info": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    rows = []
    for sev in ("critical", "warning", "info"):
        if counts[sev]:
            emoji = SEVERITY_EMOJI.get(sev, "")
            rows.append(f"| {emoji} {sev.capitalize()} | {counts[sev]} |")

    if not rows:
        return ""

    table = "\n### Summary\n\n| Severity | Count |\n|----------|-------|\n"
    table += "\n".join(rows)
    return table
