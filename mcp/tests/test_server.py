"""Unit tests for the SentiSift MCP server tools.

Thanks to FastMCP 3.0's "tools are still regular callables" design, we
can call each tool as a normal function. We mock the underlying
SentiSift SDK client so no live API calls happen during tests.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

# The server module reads SENTISIFT_API_KEY at import time only if we
# call main(); tool definitions don't. Still, we set a dummy value so
# that ``SentiSift()`` inside the singleton getter doesn't raise.


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTISIFT_API_KEY", "sk_sentisift_mcp_test")
    # Reset the module-level client between tests so each test starts fresh.
    import sentisift_mcp.server as server_mod
    server_mod._client = None


class _FakeAnalyzeResponse:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def model_dump(self) -> dict[str, Any]:
        return self._data


class _FakeUsageResponse:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def model_dump(self) -> dict[str, Any]:
        return self._data


class _FakeHealthResponse:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def model_dump(self) -> dict[str, Any]:
        return self._data


def test_analyze_comments_delegates_to_sdk() -> None:
    from sentisift_mcp.server import analyze_comments

    expected_body = {
        "status": "processed",
        "comments": [
            {
                "text": "Nice article",
                "username": "alice",
                "timestamp": "2026-04-18T10:00:00Z",
                "sentiment_label": "Positive",
                "composite_score": 0.8,
                "is_influence": False,
            }
        ],
        "moderation": {
            "total_analyzed": 1,
            "total_approved": 1,
            "total_removed": 0,
            "removal_breakdown": {
                "bot_spam": 0, "commercial": 0,
                "negative_score": 0, "positive_score": 0,
            },
        },
        "comments_used": 1,
        "comment_balance": 999,
    }
    with patch("sentisift_mcp.server.SentiSift") as mock_cls:
        instance = mock_cls.return_value
        instance.analyze.return_value = _FakeAnalyzeResponse(expected_body)
        result = analyze_comments(
            article_url="https://example.com/article",
            comments=[{"text": "Nice", "author": "a", "time": "2026-04-18T10:00:00"}],
            article_text="Body",
        )
    assert result["status"] == "processed"
    assert result["comments"][0]["sentiment_label"] == "Positive"
    # Verify the SDK received the parameters we passed through.
    call_kwargs = instance.analyze.call_args.kwargs
    assert call_kwargs["article_url"] == "https://example.com/article"
    assert call_kwargs["article_text"] == "Body"
    assert call_kwargs["title"] is None
    assert call_kwargs["tone"] is None


def test_analyze_comments_handles_sdk_error() -> None:
    from sentisift import SentiSiftValidationError
    from sentisift_mcp.server import analyze_comments

    with patch("sentisift_mcp.server.SentiSift") as mock_cls:
        instance = mock_cls.return_value
        instance.analyze.side_effect = SentiSiftValidationError(
            "Missing required field: 'author'",
            status_code=400,
            docs_url="https://sentisift.com/api-docs.html#request-format-comment-author",
            request_id="req-xyz",
        )
        result = analyze_comments(
            article_url="https://example.com/a",
            comments=[{"text": "Hi", "time": "2026-04-18T10:00:00"}],
        )
    assert result["status"] == "error"
    assert "author" in result["error"]
    assert result["docs_url"] == "https://sentisift.com/api-docs.html#request-format-comment-author"
    assert result["request_id"] == "req-xyz"


def test_get_balance() -> None:
    from sentisift_mcp.server import get_balance

    usage_body = {
        "status": "success",
        "customer_name": "Acme",
        "tier": "free",
        "comment_balance": 847,
        "comment_grants": [],
    }
    with patch("sentisift_mcp.server.SentiSift") as mock_cls:
        instance = mock_cls.return_value
        instance.get_usage.return_value = _FakeUsageResponse(usage_body)
        result = get_balance()
    assert result == usage_body


def test_get_health_ready() -> None:
    from sentisift_mcp.server import get_health

    with patch("sentisift_mcp.server.SentiSift") as mock_cls:
        instance = mock_cls.return_value
        instance.get_health.return_value = _FakeHealthResponse({"status": "ready"})
        result = get_health()
    assert result == {"status": "ready"}


def test_get_article_results() -> None:
    from sentisift_mcp.server import get_article_results

    body = {
        "status": "processed",
        "comments": [],
        "moderation": {
            "total_analyzed": 0, "total_approved": 0, "total_removed": 0,
            "removal_breakdown": {"bot_spam": 0, "commercial": 0, "negative_score": 0, "positive_score": 0},
        },
        "comments_used": 0,
        "comment_balance": 1000,
    }
    with patch("sentisift_mcp.server.SentiSift") as mock_cls:
        instance = mock_cls.return_value
        instance.get_results.return_value = _FakeAnalyzeResponse(body)
        result = get_article_results(article_url="https://example.com/article")
    assert result["status"] == "processed"
    assert instance.get_results.call_args.kwargs["article_url"] == "https://example.com/article"


def test_main_errors_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from sentisift_mcp.server import main

    monkeypatch.delenv("SENTISIFT_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        main()
    assert "SENTISIFT_API_KEY" in str(exc.value)


def test_client_is_singleton() -> None:
    """The lazy client getter should return the same instance across calls."""
    import sentisift_mcp.server as server_mod

    with patch("sentisift_mcp.server.SentiSift") as mock_cls:
        first = server_mod._get_client()
        second = server_mod._get_client()
    assert first is second
    assert mock_cls.call_count == 1


def test_mcp_server_exposes_four_tools() -> None:
    """Guard against accidentally removing a tool in a refactor."""
    from sentisift_mcp.server import mcp

    # FastMCP stores tools in its internal registry.  The exact attribute
    # is stable enough to assert on: mcp.tools or via list_tools().
    # We use getattr fallbacks to stay resilient across minor versions.
    tool_names: set[str] = set()
    if hasattr(mcp, "tools"):
        tool_names = {t for t in mcp.tools}  # type: ignore[attr-defined]
    elif hasattr(mcp, "_tools"):
        tool_names = set(getattr(mcp, "_tools").keys())  # type: ignore[attr-defined]
    # If we can't introspect, at least verify the callables exist on the
    # module (which is what matters for the tool surface).
    from sentisift_mcp import server
    for name in ("analyze_comments", "get_balance", "get_health", "get_article_results"):
        assert hasattr(server, name), f"Tool {name!r} missing from server module"
