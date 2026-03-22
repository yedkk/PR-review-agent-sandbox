"""Language detection and template selection.

Priority: workflow_dispatch override > .pr-review.yaml > GitHub API > base fallback.
"""

from __future__ import annotations

import logging

import yaml

from pr_review_agent.github.client import GitHubClient

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {"python", "javascript", "go"}


def resolve_language(
    override: str,
    repo: str,
    gh: GitHubClient,
) -> str:
    """Determine which language profile to use for this review."""
    if override and override != "auto":
        logger.info("Language override from workflow input: %s", override)
        return override

    repo_lang = _read_repo_config(repo)
    if repo_lang:
        logger.info("Language from .pr-review.yaml: %s", repo_lang)
        return repo_lang

    api_lang = gh.get_repo_language(repo)
    if api_lang and api_lang.lower() in SUPPORTED_LANGUAGES:
        logger.info("Language from GitHub API: %s", api_lang.lower())
        return api_lang.lower()

    logger.info("Falling back to base language profile")
    return "base"


def _read_repo_config(repo: str) -> str | None:  # noqa: ARG001
    """Read .pr-review.yaml from the checked-out repo (runs inside Actions)."""
    try:
        with open(".pr-review.yaml") as f:
            cfg = yaml.safe_load(f)
        lang = cfg.get("language", "auto") if cfg else "auto"
        if lang and lang != "auto" and lang in SUPPORTED_LANGUAGES:
            return lang
    except FileNotFoundError:
        pass
    return None
