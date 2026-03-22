"""Base agent class and LLM provider abstraction.

Provides a unified interface for calling Anthropic, OpenAI, and
OpenAI-compatible providers (e.g. Kimi/Moonshot) so each facet agent
can be configured with a different model/provider.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import anthropic
import openai

from pr_review_agent.config import AgentModelConfig

logger = logging.getLogger(__name__)


@dataclass
class Finding:
    severity: str  # "critical" | "warning" | "info"
    file: str
    line: int | None
    message: str
    suggestion: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class FacetResult:
    facet: str
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""


@dataclass
class ReviewContext:
    diff: str
    changed_files: str
    commit_log: str
    lint: str
    test: str
    type_check: str
    security_scan: str
    language_context: str


@dataclass
class ReviewResult:
    findings: list[Finding]
    body: str  # Final markdown review body


FINDING_SCHEMA_INSTRUCTION = """
Return your analysis as a JSON object with this exact structure:
{
  "summary": "Brief overall assessment of this facet",
  "findings": [
    {
      "severity": "critical|warning|info",
      "file": "path/to/file.py",
      "line": 42,
      "message": "What the issue is",
      "suggestion": "How to fix it"
    }
  ]
}

Rules:
- severity: "critical" for bugs/vulnerabilities, "warning" for improvements, "info" for suggestions
- line: the line number in the diff, or null if not applicable
- Return ONLY valid JSON, no markdown fences, no extra text
- If there are no findings, return {"summary": "...", "findings": []}
"""


PROVIDER_REGISTRY: dict[str, dict[str, str]] = {
    "anthropic": {},
    "openai": {},
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "api_key_env": "KIMI_API_KEY",
    },
}


class LLMProvider:
    """Unified interface for Anthropic, OpenAI, and OpenAI-compatible APIs."""

    def __init__(self) -> None:
        self._anthropic_client: anthropic.Anthropic | None = None
        self._openai_client: openai.OpenAI | None = None
        self._compat_clients: dict[str, openai.OpenAI] = {}

    @property
    def anthropic(self) -> anthropic.Anthropic:
        if self._anthropic_client is None:
            self._anthropic_client = anthropic.Anthropic()
        return self._anthropic_client

    @property
    def openai(self) -> openai.OpenAI:
        if self._openai_client is None:
            self._openai_client = openai.OpenAI()
        return self._openai_client

    def _get_compat_client(self, provider: str) -> openai.OpenAI:
        """Get or create an OpenAI-compatible client for a registered provider."""
        if provider not in self._compat_clients:
            cfg = PROVIDER_REGISTRY[provider]
            api_key = os.environ.get(cfg["api_key_env"], "")
            self._compat_clients[provider] = openai.OpenAI(
                api_key=api_key,
                base_url=cfg["base_url"],
            )
        return self._compat_clients[provider]

    async def chat(
        self,
        config: AgentModelConfig,
        system: str,
        user: str,
        max_tokens: int = 4096,
    ) -> str:
        if config.provider == "anthropic":
            return self._call_anthropic(config.model, system, user, max_tokens)
        elif config.provider == "openai":
            return self._call_openai(config.model, system, user, max_tokens)
        elif config.provider in PROVIDER_REGISTRY:
            return self._call_openai_compat(
                config.provider, config.model, system, user, max_tokens
            )
        else:
            raise ValueError(f"Unknown provider: {config.provider}")

    def _call_anthropic(
        self, model: str, system: str, user: str, max_tokens: int
    ) -> str:
        response = self.anthropic.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text

    def _call_openai(
        self, model: str, system: str, user: str, max_tokens: int
    ) -> str:
        response = self.openai.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""

    def _call_openai_compat(
        self, provider: str, model: str, system: str, user: str, max_tokens: int
    ) -> str:
        client = self._get_compat_client(provider)
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


# Singleton shared across all agents
_llm = LLMProvider()


class BaseAgent(ABC):
    """Base class for all facet review agents."""

    facet_name: str = "base"

    def __init__(self, model_config: AgentModelConfig) -> None:
        self.model_config = model_config
        self.llm = _llm

    @abstractmethod
    def system_prompt(self, context: ReviewContext) -> str:
        """Return the system prompt for this facet agent."""

    @abstractmethod
    def user_prompt(self, context: ReviewContext) -> str:
        """Return the user prompt containing the code context."""

    async def analyze(self, context: ReviewContext) -> FacetResult:
        system = self.system_prompt(context)
        user = self.user_prompt(context)

        logger.info("Running %s agent (model=%s)", self.facet_name, self.model_config.model)
        raw = await self.llm.chat(self.model_config, system, user)

        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> FacetResult:
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse %s response as JSON, using raw text", self.facet_name)
            return FacetResult(facet=self.facet_name, summary=raw)

        findings = [
            Finding(
                severity=f.get("severity", "info"),
                file=f.get("file", ""),
                line=f.get("line"),
                message=f.get("message", ""),
                suggestion=f.get("suggestion", ""),
            )
            for f in data.get("findings", [])
        ]
        return FacetResult(
            facet=self.facet_name,
            findings=findings,
            summary=data.get("summary", ""),
        )
