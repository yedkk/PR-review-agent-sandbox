"""Tests for configuration loading."""

from pathlib import Path

from pr_review_agent.config import AppConfig


def test_load_config():
    config = AppConfig.load(Path(__file__).parent.parent / "config.yaml")
    assert "security" in config.agents
    assert "summarizer" in config.agents
    assert config.agents["security"].provider == "anthropic"
    assert config.agents["quality"].provider == "openai"


def test_language_profiles():
    config = AppConfig.load(Path(__file__).parent.parent / "config.yaml")
    py = config.get_language_profile("python")
    assert py.template == "python-reviewer"
    assert "ruff" in py.lint_cmd

    base = config.get_language_profile("unknown-lang")
    assert base.template == "base-reviewer"
