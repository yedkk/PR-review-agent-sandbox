"""Security facet agent.

Focuses on: secret leaks, injection vulnerabilities, dependency risks,
permission issues, and insecure patterns.
"""

from __future__ import annotations

from pr_review_agent.agents.base import (
    BaseAgent,
    FINDING_SCHEMA_INSTRUCTION,
    ReviewContext,
)


class SecurityAgent(BaseAgent):
    facet_name = "security"

    def system_prompt(self, context: ReviewContext) -> str:
        return f"""You are a senior security engineer reviewing a pull request.
Your job is to identify security vulnerabilities and risks in the code changes.

Focus areas:
- Hardcoded secrets, API keys, tokens, or credentials
- SQL injection, XSS, command injection, path traversal
- Insecure deserialization or unsafe eval/exec usage
- Missing input validation or sanitization
- Insecure cryptographic practices (weak hashing, no salt)
- Overly permissive file/network permissions
- Dependency vulnerabilities (if security scan data is provided)
- Authentication/authorization bypass risks

{context.language_context}

{FINDING_SCHEMA_INSTRUCTION}"""

    def user_prompt(self, context: ReviewContext) -> str:
        parts = [
            "## Code Diff\n```\n" + _truncate(context.diff, 30000) + "\n```",
            "## Changed Files\n" + context.changed_files,
        ]
        if context.security_scan:
            parts.append(
                "## Security Scanner Output\n```\n"
                + _truncate(context.security_scan, 10000)
                + "\n```"
            )
        return "\n\n".join(parts)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... (truncated, {len(text) - max_chars} chars omitted)"
