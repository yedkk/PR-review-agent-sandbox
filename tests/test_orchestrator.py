"""Tests for the orchestrator and summarizer integration."""

from pr_review_agent.agents.base import FacetResult, Finding, ReviewContext, ReviewResult
from pr_review_agent.github.formatter import format_review_body


def test_format_review_body_with_findings():
    review = ReviewResult(
        findings=[
            Finding("critical", "main.py", 10, "SQL injection", "Use params"),
            Finding("warning", "utils.py", 20, "Unused import", "Remove it"),
            Finding("info", "config.py", None, "Could add docstring", "Add docs"),
        ],
        body="## Overall\nThis PR has some issues.\n",
    )
    body = format_review_body(review)
    assert "PR Review Agent" in body
    assert "This PR has some issues" in body
    assert "Critical" in body
    assert "Warning" in body


def test_format_review_body_no_findings():
    review = ReviewResult(findings=[], body="Looks great!")
    body = format_review_body(review)
    assert "Looks great!" in body
    assert "| Severity" not in body
