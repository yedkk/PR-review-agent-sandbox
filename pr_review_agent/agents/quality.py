"""Code quality facet agent.

Focuses on: code style, naming conventions, complexity, duplication,
and linter findings.
"""

from __future__ import annotations

from pr_review_agent.agents.base import (
    BaseAgent,
    FINDING_SCHEMA_INSTRUCTION,
    ReviewContext,
)


class QualityAgent(BaseAgent):
    facet_name = "quality"

    def system_prompt(self, context: ReviewContext) -> str:
        return f"""You are a senior software engineer reviewing a pull request for code quality.
Your job is to identify maintainability and readability issues.

Focus areas:
- Naming conventions (variables, functions, classes)
- Function/method length and cyclomatic complexity
- Code duplication and DRY violations
- Dead code or unreachable branches
- Inconsistent code style within the changeset
- Missing or misleading documentation/docstrings
- Overly complex expressions that could be simplified
- Proper use of language idioms and best practices

Use the linter output to correlate your findings with automated checks.
Do NOT repeat linter findings verbatim; instead, focus on higher-level quality issues
that linters cannot catch.

{context.language_context}

{FINDING_SCHEMA_INSTRUCTION}"""

    def user_prompt(self, context: ReviewContext) -> str:
        parts = [
            "## Code Diff\n```\n" + _truncate(context.diff, 30000) + "\n```",
            "## Changed Files\n" + context.changed_files,
        ]
        if context.lint:
            parts.append(
                "## Linter Output\n```\n"
                + _truncate(context.lint, 10000)
                + "\n```"
            )
        if context.type_check:
            parts.append(
                "## Type Checker Output\n```\n"
                + _truncate(context.type_check, 5000)
                + "\n```"
            )
        return "\n\n".join(parts)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... (truncated, {len(text) - max_chars} chars omitted)"
