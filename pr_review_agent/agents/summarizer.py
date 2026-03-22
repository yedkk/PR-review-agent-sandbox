"""Summarizer agent.

Aggregates all facet results into a unified, well-formatted review comment.
This is the final convergence step before posting to GitHub.
"""

from __future__ import annotations

import logging

from pr_review_agent.agents.base import (
    FacetResult,
    Finding,
    ReviewContext,
    ReviewResult,
    LLMProvider,
)
from pr_review_agent.config import AgentModelConfig

logger = logging.getLogger(__name__)

_llm = LLMProvider()

SUMMARIZER_SYSTEM = """You are a senior tech lead writing a final PR review summary.
You receive analysis from 5 specialist reviewers (security, quality, logic, testing, performance).
Your job is to synthesize their findings into a single, well-organized review comment.

Guidelines:
- Start with a brief overall assessment (1-2 sentences)
- Group findings by severity: Critical > Warning > Info
- De-duplicate overlapping findings from different facets
- For each finding, preserve the file path, line number, and actionable suggestion
- End with a summary table: counts by severity
- Use clear markdown formatting
- Be constructive and professional
- If there are no significant findings, acknowledge the PR looks good

Output format: Return ONLY the markdown text for the review comment (no JSON wrapper).
"""


async def summarize(
    facet_results: list[FacetResult],
    context: ReviewContext,
    model_config: AgentModelConfig,
) -> ReviewResult:
    """Combine all facet results into a single ReviewResult."""

    all_findings: list[Finding] = []
    for fr in facet_results:
        all_findings.extend(fr.findings)

    facet_summaries = _build_facet_summaries(facet_results)

    user_prompt = f"""## Facet Analysis Results

{facet_summaries}

## PR Context
- Changed files: {context.changed_files}
- Commits: {context.commit_log}
- Total findings across all facets: {len(all_findings)}

Please synthesize these into a final review comment."""

    logger.info("Summarizing %d findings from %d facets", len(all_findings), len(facet_results))
    body = await _llm.chat(model_config, SUMMARIZER_SYSTEM, user_prompt)

    return ReviewResult(findings=all_findings, body=body)


def _build_facet_summaries(results: list[FacetResult]) -> str:
    parts: list[str] = []
    for fr in results:
        section = f"### {fr.facet.upper()}\n"
        section += f"Summary: {fr.summary}\n"
        if fr.findings:
            section += f"Findings ({len(fr.findings)}):\n"
            for f in fr.findings:
                loc = f"{f.file}"
                if f.line:
                    loc += f":{f.line}"
                section += f"- [{f.severity}] {loc}: {f.message}\n"
                if f.suggestion:
                    section += f"  Suggestion: {f.suggestion}\n"
        else:
            section += "No findings.\n"
        parts.append(section)
    return "\n".join(parts)
