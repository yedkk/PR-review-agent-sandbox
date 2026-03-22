"""Tests for sandbox manager metadata logic (unit tests with mocks)."""

from unittest.mock import MagicMock, patch

from pr_review_agent.sandbox.manager import SandboxManager


def test_metadata_format():
    mgr = SandboxManager()
    meta = mgr._metadata("owner/repo", 42)
    assert meta == {"repo": "owner/repo", "pr_number": "42"}


@patch("pr_review_agent.sandbox.manager.Sandbox")
def test_find_paused_returns_none_when_empty(mock_sandbox):
    paginator = MagicMock()
    paginator.next_items.return_value = []
    mock_sandbox.list.return_value = paginator

    mgr = SandboxManager()
    result = mgr.find_paused("owner/repo", 99)
    assert result is None


@patch("pr_review_agent.sandbox.manager.Sandbox")
def test_find_paused_returns_sandbox_id(mock_sandbox):
    sb = MagicMock()
    sb.sandbox_id = "sbx_abc123"
    paginator = MagicMock()
    paginator.next_items.return_value = [sb]
    mock_sandbox.list.return_value = paginator

    mgr = SandboxManager()
    result = mgr.find_paused("owner/repo", 42)
    assert result == "sbx_abc123"


@patch("pr_review_agent.sandbox.manager.Sandbox")
def test_cleanup_kills_all_matching(mock_sandbox):
    sb1 = MagicMock()
    sb1.sandbox_id = "sbx_1"
    sb2 = MagicMock()
    sb2.sandbox_id = "sbx_2"
    paginator = MagicMock()
    paginator.next_items.return_value = [sb1, sb2]
    mock_sandbox.list.return_value = paginator

    mgr = SandboxManager()
    mgr.cleanup("owner/repo", 42)

    assert mock_sandbox.kill.call_count == 2
    mock_sandbox.kill.assert_any_call("sbx_1")
    mock_sandbox.kill.assert_any_call("sbx_2")
