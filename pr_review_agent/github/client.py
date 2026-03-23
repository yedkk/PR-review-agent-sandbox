"""GitHub API client for PR review operations.

Uses PyGithub with GITHUB_TOKEN (auto-provided by Actions).
"""

from __future__ import annotations

import logging
import os

from github import Github, Auth

from pr_review_agent.agents.base import ReviewResult
from pr_review_agent.github.formatter import format_review_body

logger = logging.getLogger(__name__)


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        token = token or os.environ.get("GITHUB_TOKEN", "")
        self._gh = Github(auth=Auth.Token(token)) if token else Github()

    def get_repo_language(self, repo_full_name: str) -> str | None:
        """Get the primary language of a repo from the GitHub API."""
        try:
            repo = self._gh.get_repo(repo_full_name)
            return repo.language
        except Exception:
            logger.warning("Failed to detect repo language via API", exc_info=True)
            return None

    def post_review(
        self,
        repo_full_name: str,
        pr_number: int,
        review: ReviewResult,
    ) -> None:
        """Post a review comment on the PR."""
        repo = self._gh.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)

        body = format_review_body(review)

        # Use create_issue_comment for a general PR comment.
        # For inline comments, we'd use create_review with comments,
        # but that requires mapping diff hunks which we can add later.
        pr.create_issue_comment(body)
        logger.info("Posted review comment on %s#%d", repo_full_name, pr_number)

    def post_inline_review(
        self,
        repo_full_name: str,
        pr_number: int,
        review: ReviewResult,
        head_sha: str,
    ) -> None:
        """Post a pull request review with inline comments on specific lines."""
        repo = self._gh.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)

        comments = []
        for finding in review.findings:
            if finding.file and finding.line:
                comments.append({
                    "path": finding.file,
                    "line": finding.line,
                    "body": f"**[{finding.severity.upper()}]** {finding.message}\n\n"
                            f"**Suggestion:** {finding.suggestion}",
                })

        body = format_review_body(review)

        if comments:
            try:
                pr.create_review(
                    commit=repo.get_commit(head_sha),
                    body=body,
                    event="COMMENT",
                    comments=comments,
                )
                logger.info(
                    "Posted review on %s#%d (%d inline comments)",
                    repo_full_name, pr_number, len(comments),
                )
                return
            except Exception:
                logger.warning(
                    "Inline review failed, falling back to issue comment",
                    exc_info=True,
                )

        pr.create_issue_comment(body)
        logger.info("Posted review comment on %s#%d", repo_full_name, pr_number)
