"""Agent orchestrator.

Runs all facet agents in parallel via asyncio.gather,
then feeds results to the summarizer for convergence.
"""

from __future__ import annotations

import asyncio
import logging

from pr_review_agent.agents.base import BaseAgent, ReviewContext, ReviewResult
from pr_review_agent.agents.security import SecurityAgent
from pr_review_agent.agents.quality import QualityAgent
from pr_review_agent.agents.logic import LogicAgent
from pr_review_agent.agents.testing import TestingAgent
from pr_review_agent.agents.performance import PerformanceAgent
from pr_review_agent.agents import summarizer as summarizer_mod
from pr_review_agent.config import AppConfig

logger = logging.getLogger(__name__)

FACET_AGENT_CLASSES: list[type[BaseAgent]] = [
    SecurityAgent,
    QualityAgent,
    LogicAgent,
    TestingAgent,
    PerformanceAgent,
]


async def orchestrate_review(
    context: ReviewContext,
    config: AppConfig,
) -> ReviewResult:
    """Run all facet agents in parallel, then summarize results."""

    agents: list[BaseAgent] = []
    for cls in FACET_AGENT_CLASSES:
        agent_name = cls.facet_name
        model_config = config.agents.get(agent_name)
        if model_config is None:
            logger.warning("No model config for agent %s, skipping", agent_name)
            continue
        agents.append(cls(model_config))

    logger.info("Running %d facet agents in parallel", len(agents))

    facet_results = await asyncio.gather(
        *[agent.analyze(context) for agent in agents],
        return_exceptions=True,
    )

    successful = []
    for agent, result in zip(agents, facet_results):
        if isinstance(result, Exception):
            logger.error("Agent %s failed: %s", agent.facet_name, result)
        else:
            successful.append(result)

    logger.info(
        "%d/%d agents completed successfully", len(successful), len(agents)
    )

    summarizer_config = config.agents.get("summarizer")
    if summarizer_config is None:
        raise RuntimeError("No model config for summarizer agent")

    review = await summarizer_mod.summarize(successful, context, summarizer_config)
    return review
