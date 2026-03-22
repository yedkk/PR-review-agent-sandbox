"""E2B Sandbox lifecycle management.

Handles create/find/resume/pause/kill using E2B metadata as the registry
so no external database is needed.
"""

from __future__ import annotations

import logging

from e2b import Sandbox, SandboxQuery, SandboxState

logger = logging.getLogger(__name__)


class SandboxManager:
    """Manages E2B sandbox lifecycle tied to PR events."""

    def _metadata(self, repo: str, pr_number: int) -> dict[str, str]:
        return {"repo": repo, "pr_number": str(pr_number)}

    def find_paused(self, repo: str, pr_number: int) -> str | None:
        """Find a paused sandbox for the given PR via E2B metadata query."""
        paginator = Sandbox.list(
            query=SandboxQuery(
                state=[SandboxState.PAUSED],
                metadata=self._metadata(repo, pr_number),
            )
        )
        sandboxes = paginator.next_items()
        if sandboxes:
            logger.info(
                "Found paused sandbox %s for %s#%d",
                sandboxes[0].sandbox_id,
                repo,
                pr_number,
            )
            return sandboxes[0].sandbox_id
        return None

    def create(
        self,
        repo: str,
        pr_number: int,
        template: str,
    ) -> Sandbox:
        """Create a new sandbox tagged with repo/PR metadata."""
        logger.info(
            "Creating sandbox template=%s for %s#%d", template, repo, pr_number
        )
        sandbox = Sandbox.create(
            template=template,
            metadata=self._metadata(repo, pr_number),
        )
        return sandbox

    def resume(self, sandbox_id: str) -> Sandbox:
        """Resume a previously paused sandbox."""
        logger.info("Resuming sandbox %s", sandbox_id)
        return Sandbox.resume(sandbox_id)

    def pause(self, sandbox: Sandbox) -> None:
        """Pause a sandbox, preserving filesystem and memory state."""
        logger.info("Pausing sandbox %s", sandbox.sandbox_id)
        sandbox.pause()

    def kill(self, sandbox_id: str) -> None:
        """Kill and delete a sandbox."""
        logger.info("Killing sandbox %s", sandbox_id)
        Sandbox.kill(sandbox_id)

    def get_or_create(
        self,
        repo: str,
        pr_number: int,
        template: str,
        head_sha: str,
        base_ref: str,
    ) -> Sandbox:
        """Resume an existing paused sandbox or create a new one.

        On resume, syncs the repo to the latest commit.
        On create, clones the repo and checks out the PR branch.
        """
        sandbox_id = self.find_paused(repo, pr_number)

        if sandbox_id:
            try:
                sandbox = self.resume(sandbox_id)
                sandbox.commands.run(
                    f"cd /workspace && git fetch origin && git checkout {head_sha}",
                    timeout=120,
                )
                logger.info("Resumed and synced sandbox to %s", head_sha)
                return sandbox
            except Exception:
                logger.warning(
                    "Failed to resume sandbox %s, creating new one",
                    sandbox_id,
                    exc_info=True,
                )

        sandbox = self.create(repo, pr_number, template)
        clone_url = f"https://github.com/{repo}.git"
        sandbox.commands.run(
            f"rm -rf /workspace && git clone {clone_url} /workspace && cd /workspace && git checkout {head_sha}",
            timeout=300,
        )
        logger.info("Cloned %s at %s into new sandbox", repo, head_sha)
        return sandbox

    def cleanup(self, repo: str, pr_number: int) -> None:
        """Kill all sandboxes associated with a PR (called on PR close)."""
        paginator = Sandbox.list(
            query=SandboxQuery(
                state=[SandboxState.PAUSED, SandboxState.RUNNING],
                metadata=self._metadata(repo, pr_number),
            )
        )
        for sb in paginator.next_items():
            try:
                self.kill(sb.sandbox_id)
            except Exception:
                logger.warning(
                    "Failed to kill sandbox %s during cleanup",
                    sb.sandbox_id,
                    exc_info=True,
                )
