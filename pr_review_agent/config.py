from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class AgentModelConfig:
    model: str
    provider: str  # "anthropic" | "openai"


@dataclass(frozen=True)
class LanguageProfile:
    template: str
    lint_cmd: str
    test_cmd: str
    type_check_cmd: str
    security_cmd: str
    prompt_context: str


@dataclass(frozen=True)
class PREvent:
    action: str
    pr_number: int
    repo_full_name: str
    head_sha: str
    base_ref: str
    language_override: str

    @classmethod
    def from_env(cls) -> PREvent:
        return cls(
            action=os.environ["PR_ACTION"],
            pr_number=int(os.environ["PR_NUMBER"]),
            repo_full_name=os.environ["REPO_FULL_NAME"],
            head_sha=os.environ["PR_HEAD_SHA"],
            base_ref=os.environ["PR_BASE_REF"],
            language_override=os.environ.get("LANGUAGE_OVERRIDE", ""),
        )


@dataclass
class AppConfig:
    agents: dict[str, AgentModelConfig] = field(default_factory=dict)
    languages: dict[str, LanguageProfile] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> AppConfig:
        if path is None:
            path = Path(__file__).resolve().parent.parent / "config.yaml"

        with open(path) as f:
            raw = yaml.safe_load(f)

        agents = {
            name: AgentModelConfig(**cfg)
            for name, cfg in raw.get("agents", {}).items()
        }
        languages = {
            name: LanguageProfile(**cfg)
            for name, cfg in raw.get("languages", {}).items()
        }
        return cls(agents=agents, languages=languages)

    def get_language_profile(self, language: str) -> LanguageProfile:
        return self.languages.get(language, self.languages["base"])
