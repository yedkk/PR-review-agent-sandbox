"""Logic and correctness facet agent.

Focuses on: bugs, edge cases, error handling, race conditions,
and logical flaws.
"""

from __future__ import annotations

from pr_review_agent.agents.base import (
    BaseAgent,
    FINDING_SCHEMA_INSTRUCTION,
    ReviewContext,
)


class LogicAgent(BaseAgent):
    facet_name = "logic"

    def system_prompt(self, context: ReviewContext) -> str:
        return f"""You are a senior software engineer reviewing a pull request for logical correctness.
Your job is to find bugs, edge cases, and logical errors in the code changes.

Focus areas:
- Off-by-one errors and boundary conditions
- Null/None/undefined dereferences
- Unhandled error paths and missing error propagation
- Race conditions in concurrent code
- Incorrect boolean logic or operator precedence
- State mutation side effects
- Infinite loops or unbounded recursion
- Incorrect assumptions about data format or range
- Missing validation before critical operations

Consider the commit log for intent and verify the implementation matches.

{context.language_context}

{FINDING_SCHEMA_INSTRUCTION}"""

    def user_prompt(self, context: ReviewContext) -> str:
        parts = [
            "## Code Diff\n```\n" + _truncate(context.diff, 30000) + "\n```",
            "## Changed Files\n" + context.changed_files,
            "## Commit Log\n" + context.commit_log,
        ]
        return "\n\n".join(parts)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... (truncated, {len(text) - max_chars} chars omitted)"
