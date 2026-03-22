"""Performance facet agent.

Focuses on: algorithmic complexity, resource usage, N+1 queries,
memory leaks, and unnecessary computation.
"""

from __future__ import annotations

from pr_review_agent.agents.base import (
    BaseAgent,
    FINDING_SCHEMA_INSTRUCTION,
    ReviewContext,
)


class PerformanceAgent(BaseAgent):
    facet_name = "performance"

    def system_prompt(self, context: ReviewContext) -> str:
        return f"""You are a senior performance engineer reviewing a pull request.
Your job is to identify performance issues and optimization opportunities.

Focus areas:
- Algorithmic complexity regressions (O(n^2) loops, unnecessary sorting)
- N+1 query patterns in database access
- Missing caching for expensive or repeated operations
- Memory leaks (unclosed resources, growing collections)
- Unnecessary data copying or serialization
- Blocking I/O in async/concurrent contexts
- Large allocations in hot paths
- Missing pagination for unbounded result sets
- Inefficient string concatenation in loops

Only flag issues with meaningful performance impact.
Do NOT suggest micro-optimizations that sacrifice readability.

{context.language_context}

{FINDING_SCHEMA_INSTRUCTION}"""

    def user_prompt(self, context: ReviewContext) -> str:
        parts = [
            "## Code Diff\n```\n" + _truncate(context.diff, 30000) + "\n```",
            "## Changed Files\n" + context.changed_files,
        ]
        return "\n\n".join(parts)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... (truncated, {len(text) - max_chars} chars omitted)"
