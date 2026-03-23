"""Context collection from within an E2B sandbox.

Runs git, linter, test, and security commands based on the language profile,
then packages results into a ReviewContext for the agents.
"""

from __future__ import annotations

import logging

from e2b import Sandbox
from e2b.sandbox_sync.commands.command_handle import CommandExitException

from pr_review_agent.agents.base import ReviewContext
from pr_review_agent.config import LanguageProfile

logger = logging.getLogger(__name__)

WORKDIR = "/workspace"
CMD_TIMEOUT = 120  # seconds


def _run(sandbox: Sandbox, cmd: str, timeout: int = CMD_TIMEOUT) -> str:
    """Run a command in the sandbox and return stdout. Non-zero exits are tolerated
    (linters/tests often exit non-zero when they find issues)."""
    if not cmd:
        return ""
    logger.info("sandbox exec: %s", cmd)
    try:
        result = sandbox.commands.run(cmd, timeout=timeout, cwd=WORKDIR)
        output = result.stdout or ""
        if result.stderr:
            output += "\n" + result.stderr
    except CommandExitException as exc:
        logger.info("Command exited with code %d: %s", exc.exit_code, cmd)
        output = (exc.stdout or "") + "\n" + (exc.stderr or "")
    return output.strip()


def collect_context(
    sandbox: Sandbox,
    profile: LanguageProfile,
    base_ref: str,
) -> ReviewContext:
    """Collect all review context by executing commands inside the sandbox."""

    diff = _run(sandbox, f"git diff origin/{base_ref}...HEAD")
    changed_files = _run(sandbox, f"git diff --name-only origin/{base_ref}...HEAD")
    commit_log = _run(sandbox, f"git log --oneline origin/{base_ref}...HEAD")

    lint = _run(sandbox, profile.lint_cmd) if profile.lint_cmd else ""
    test = _run(sandbox, profile.test_cmd) if profile.test_cmd else ""
    type_check = _run(sandbox, profile.type_check_cmd) if profile.type_check_cmd else ""
    security_scan = _run(sandbox, profile.security_cmd) if profile.security_cmd else ""

    logger.info(
        "Context collected: diff=%d chars, lint=%d chars, test=%d chars",
        len(diff),
        len(lint),
        len(test),
    )

    return ReviewContext(
        diff=diff,
        changed_files=changed_files,
        commit_log=commit_log,
        lint=lint,
        test=test,
        type_check=type_check,
        security_scan=security_scan,
        language_context=profile.prompt_context,
    )
