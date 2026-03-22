"""Entry point for the PR Review Agent.

Reads PR event context from environment variables (set by GitHub Actions)
and dispatches to the appropriate handler.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from pr_review_agent.agents.orchestrator import orchestrate_review
from pr_review_agent.config import AppConfig, PREvent
from pr_review_agent.github.client import GitHubClient
from pr_review_agent.sandbox.manager import SandboxManager
from pr_review_agent.sandbox.collector import collect_context
from pr_review_agent.sandbox.templates import resolve_language

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pr-review-agent")


async def main() -> None:
    event = PREvent.from_env()
    config = AppConfig.load()
    gh = GitHubClient()
    sandbox_mgr = SandboxManager()

    logger.info(
        "Handling PR #%d action=%s repo=%s",
        event.pr_number,
        event.action,
        event.repo_full_name,
    )

    if event.action == "closed":
        sandbox_mgr.cleanup(event.repo_full_name, event.pr_number)
        logger.info("Sandbox cleaned up for closed PR #%d", event.pr_number)
        return

    language = resolve_language(
        override=event.language_override,
        repo=event.repo_full_name,
        gh=gh,
    )
    profile = config.get_language_profile(language)
    logger.info("Resolved language=%s template=%s", language, profile.template)

    sandbox = sandbox_mgr.get_or_create(
        repo=event.repo_full_name,
        pr_number=event.pr_number,
        template=profile.template,
        head_sha=event.head_sha,
        base_ref=event.base_ref,
    )

    try:
        context = collect_context(sandbox, profile, event.base_ref)
        logger.info("Context collected: %d changed files", len(context.changed_files.splitlines()))

        review = await orchestrate_review(context, config)
        logger.info("Review complete: %d findings", len(review.findings))

        gh.post_review(event.repo_full_name, event.pr_number, review)
        logger.info("Review posted to PR #%d", event.pr_number)
    finally:
        try:
            sandbox_mgr.pause(sandbox)
            logger.info("Sandbox paused")
        except Exception:
            logger.warning("Failed to pause sandbox", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logger.exception("PR Review Agent failed")
        sys.exit(1)
