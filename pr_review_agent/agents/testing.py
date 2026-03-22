"""Testing facet agent.

Focuses on: test coverage gaps, missing test cases, test quality,
and test reliability.
"""

from __future__ import annotations

from pr_review_agent.agents.base import (
    BaseAgent,
    FINDING_SCHEMA_INSTRUCTION,
    ReviewContext,
)


class TestingAgent(BaseAgent):
    facet_name = "testing"

    def system_prompt(self, context: ReviewContext) -> str:
        return f"""You are a senior QA engineer reviewing a pull request for test adequacy.
Your job is to identify gaps in test coverage and test quality issues.

Focus areas:
- New code paths that lack corresponding tests
- Missing edge case tests (empty input, boundary values, error paths)
- Tests that are too tightly coupled to implementation details
- Flaky test patterns (timing-dependent, order-dependent)
- Missing assertions or overly broad assertions
- Test data that doesn't cover realistic scenarios
- Integration points that need integration/e2e tests
- Mocked dependencies that might hide real bugs

Use the test output to understand which tests pass/fail and correlate with the diff.

{context.language_context}

{FINDING_SCHEMA_INSTRUCTION}"""

    def user_prompt(self, context: ReviewContext) -> str:
        parts = [
            "## Code Diff\n```\n" + _truncate(context.diff, 30000) + "\n```",
            "## Changed Files\n" + context.changed_files,
        ]
        if context.test:
            parts.append(
                "## Test Output\n```\n"
                + _truncate(context.test, 10000)
                + "\n```"
            )
        return "\n\n".join(parts)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... (truncated, {len(text) - max_chars} chars omitted)"
