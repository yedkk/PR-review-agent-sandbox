"""Tests for agent response parsing and structure."""

import json

from pr_review_agent.agents.base import (
    BaseAgent,
    FacetResult,
    Finding,
    ReviewContext,
)
from pr_review_agent.config import AgentModelConfig


def _make_context(**overrides) -> ReviewContext:
    defaults = dict(
        diff="+ added line",
        changed_files="file.py",
        commit_log="abc123 initial commit",
        lint="",
        test="",
        type_check="",
        security_scan="",
        language_context="Python project",
    )
    defaults.update(overrides)
    return ReviewContext(**defaults)


class DummyAgent(BaseAgent):
    facet_name = "dummy"

    def system_prompt(self, context: ReviewContext) -> str:
        return "You are a test agent."

    def user_prompt(self, context: ReviewContext) -> str:
        return context.diff


def test_parse_valid_json():
    agent = DummyAgent(AgentModelConfig(model="test", provider="anthropic"))
    raw = json.dumps({
        "summary": "Looks good",
        "findings": [
            {
                "severity": "warning",
                "file": "main.py",
                "line": 10,
                "message": "Unused variable",
                "suggestion": "Remove it",
            }
        ],
    })
    result = agent._parse_response(raw)
    assert isinstance(result, FacetResult)
    assert result.facet == "dummy"
    assert result.summary == "Looks good"
    assert len(result.findings) == 1
    assert result.findings[0].severity == "warning"
    assert result.findings[0].line == 10


def test_parse_json_with_markdown_fences():
    agent = DummyAgent(AgentModelConfig(model="test", provider="anthropic"))
    raw = '```json\n{"summary": "OK", "findings": []}\n```'
    result = agent._parse_response(raw)
    assert result.summary == "OK"
    assert result.findings == []


def test_parse_invalid_json_fallback():
    agent = DummyAgent(AgentModelConfig(model="test", provider="anthropic"))
    raw = "This is not JSON at all"
    result = agent._parse_response(raw)
    assert result.facet == "dummy"
    assert result.summary == raw
    assert result.findings == []


def test_finding_to_dict():
    f = Finding(
        severity="critical",
        file="app.py",
        line=5,
        message="SQL injection",
        suggestion="Use parameterized queries",
    )
    d = f.to_dict()
    assert d["severity"] == "critical"
    assert d["line"] == 5
