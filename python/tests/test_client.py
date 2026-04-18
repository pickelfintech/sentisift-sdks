"""Unit tests for the SentiSift client. Uses respx to mock httpx."""
from __future__ import annotations

import os
from typing import Any, Dict

import httpx
import pytest
import respx

from sentisift import (
    BufferedResponse,
    ProcessedResponse,
    SentiSift,
    SentiSiftAuthError,
    SentiSiftRateLimitError,
    SentiSiftServiceLoadingError,
    SentiSiftValidationError,
    __version__,
)

BASE_URL = "https://api.sentisift.com"


def _sample_processed_body() -> Dict[str, Any]:
    return {
        "status": "processed",
        "comments": [
            {
                "text": "Great article",
                "username": "alice",
                "timestamp": "2026-04-18T10:00:00Z",
                "sentiment_label": "Positive",
                "composite_score": 0.82,
                "is_influence": False,
            }
        ],
        "moderation": {
            "total_analyzed": 1,
            "total_approved": 1,
            "total_removed": 0,
            "removal_breakdown": {
                "bot_spam": 0,
                "commercial": 0,
                "negative_score": 0,
                "positive_score": 0,
            },
        },
        "comments_used": 1,
        "comment_balance": 999,
    }


def _sample_buffered_body() -> Dict[str, Any]:
    return {
        "status": "buffered",
        "article_url": "https://example.com/article/1",
        "buffered_count": 5,
        "threshold": 20,
        "comments_used": 0,
        "comment_balance": 1000,
    }


# -----------------------------------------------------------------------
# Client construction
# -----------------------------------------------------------------------
def test_client_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTISIFT_API_KEY", "sk_from_env")
    client = SentiSift()
    assert client._api_key == "sk_from_env"


def test_client_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTISIFT_API_KEY", raising=False)
    with pytest.raises(SentiSiftAuthError) as exc:
        SentiSift()
    assert "https://sentisift.com/pricing.html" in str(exc.value)


def test_user_agent_contains_sdk_version(client: SentiSift) -> None:
    assert f"sentisift-python/{__version__}" in client._user_agent


# -----------------------------------------------------------------------
# analyze
# -----------------------------------------------------------------------
@respx.mock
def test_analyze_returns_processed_response(client: SentiSift) -> None:
    respx.post(f"{BASE_URL}/api/v1/analyze").mock(
        return_value=httpx.Response(200, json=_sample_processed_body())
    )
    result = client.analyze(
        article_url="https://example.com/article/1",
        comments=[{"text": "Great", "author": "alice", "time": "2026-04-18T10:00:00"}],
    )
    assert isinstance(result, ProcessedResponse)
    assert result.status == "processed"
    assert result.comments[0].sentiment_label == "Positive"


@respx.mock
def test_analyze_returns_buffered_response(client: SentiSift) -> None:
    respx.post(f"{BASE_URL}/api/v1/analyze").mock(
        return_value=httpx.Response(200, json=_sample_buffered_body())
    )
    result = client.analyze(
        article_url="https://example.com/article/1",
        comments=[{"text": "Hi", "author": "alice", "time": "2026-04-18T10:00:00"}],
    )
    assert isinstance(result, BufferedResponse)
    assert result.buffered_count == 5


@respx.mock
def test_analyze_sends_expected_headers_and_body(client: SentiSift) -> None:
    route = respx.post(f"{BASE_URL}/api/v1/analyze").mock(
        return_value=httpx.Response(200, json=_sample_buffered_body())
    )
    client.analyze(
        article_url="https://example.com/article",
        comments=[{"text": "Hi", "author": "alice", "time": "2026-04-18T10:00:00"}],
        article_text="Article body",
        title="My Article",
    )
    assert route.called
    request = route.calls.last.request
    assert request.headers["X-API-Key"] == "sk_sentisift_test_fixture"
    assert "sentisift-python/" in request.headers["User-Agent"]
    import json as _json
    body = _json.loads(request.content)
    assert body["metadata"]["article_url"] == "https://example.com/article"
    assert body["metadata"]["article_text"] == "Article body"
    assert body["metadata"]["title"] == "My Article"


# -----------------------------------------------------------------------
# Error mapping
# -----------------------------------------------------------------------
@respx.mock
def test_analyze_validation_error_exposes_docs_url(client: SentiSift) -> None:
    respx.post(f"{BASE_URL}/api/v1/analyze").mock(
        return_value=httpx.Response(
            400,
            json={
                "status": "error",
                "error": "Comment at index 0 missing required field: 'author'.",
                "docs_url": "https://sentisift.com/api-docs.html#request-format-comment-author",
                "request_id": "req-123",
            },
        )
    )
    with pytest.raises(SentiSiftValidationError) as exc:
        client.analyze(
            article_url="https://example.com/a",
            comments=[{"text": "Hi", "time": "2026-04-18T10:00:00"}],
        )
    assert exc.value.status_code == 400
    assert "comment-author" in (exc.value.docs_url or "")
    assert exc.value.request_id == "req-123"


@respx.mock
def test_analyze_auth_error(client: SentiSift) -> None:
    respx.post(f"{BASE_URL}/api/v1/analyze").mock(
        return_value=httpx.Response(
            401,
            json={"status": "error", "error": "Invalid API key"},
        )
    )
    with pytest.raises(SentiSiftAuthError) as exc:
        client.analyze(
            article_url="https://example.com/a",
            comments=[{"text": "Hi", "author": "a", "time": "2026-04-18T10:00:00"}],
        )
    assert exc.value.status_code == 401


# -----------------------------------------------------------------------
# Retry behavior
# -----------------------------------------------------------------------
@respx.mock
def test_rate_limit_retries_then_succeeds(client_with_retries: SentiSift) -> None:
    route = respx.post(f"{BASE_URL}/api/v1/analyze").mock(
        side_effect=[
            httpx.Response(429, json={"retry_after": 1}, headers={"Retry-After": "1"}),
            httpx.Response(200, json=_sample_buffered_body()),
        ]
    )
    result = client_with_retries.analyze(
        article_url="https://example.com/a",
        comments=[{"text": "Hi", "author": "a", "time": "2026-04-18T10:00:00"}],
    )
    assert isinstance(result, BufferedResponse)
    assert route.call_count == 2


@respx.mock
def test_rate_limit_exhausts_retries(client: SentiSift) -> None:
    # client fixture has max_retries=0
    respx.post(f"{BASE_URL}/api/v1/analyze").mock(
        return_value=httpx.Response(
            429,
            json={"status": "error", "error": "Too many requests", "retry_after": 5},
            headers={"Retry-After": "5"},
        )
    )
    with pytest.raises(SentiSiftRateLimitError) as exc:
        client.analyze(
            article_url="https://example.com/a",
            comments=[{"text": "Hi", "author": "a", "time": "2026-04-18T10:00:00"}],
        )
    assert exc.value.retry_after == 5


@respx.mock
def test_service_loading_retries(client_with_retries: SentiSift) -> None:
    route = respx.post(f"{BASE_URL}/api/v1/analyze").mock(
        side_effect=[
            httpx.Response(503, json={"status": "error", "error": "Loading"}),
            httpx.Response(200, json=_sample_buffered_body()),
        ]
    )
    # Use a client with a tiny retry delay for fast tests
    result = client_with_retries.analyze(
        article_url="https://example.com/a",
        comments=[{"text": "Hi", "author": "a", "time": "2026-04-18T10:00:00"}],
    )
    assert isinstance(result, BufferedResponse)
    assert route.call_count == 2


@respx.mock
def test_service_loading_exhausts_retries(client: SentiSift) -> None:
    respx.post(f"{BASE_URL}/api/v1/analyze").mock(
        return_value=httpx.Response(503, json={"status": "error", "error": "Loading"})
    )
    with pytest.raises(SentiSiftServiceLoadingError):
        client.analyze(
            article_url="https://example.com/a",
            comments=[{"text": "Hi", "author": "a", "time": "2026-04-18T10:00:00"}],
        )


# -----------------------------------------------------------------------
# get_usage, get_results, get_health
# -----------------------------------------------------------------------
@respx.mock
def test_get_usage(client: SentiSift) -> None:
    respx.get(f"{BASE_URL}/api/v1/usage").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "success",
                "customer_name": "Acme",
                "tier": "free",
                "comment_balance": 847,
            },
        )
    )
    usage = client.get_usage()
    assert usage.customer_name == "Acme"
    assert usage.comment_balance == 847


@respx.mock
def test_get_results(client: SentiSift) -> None:
    route = respx.get(f"{BASE_URL}/api/v1/results").mock(
        return_value=httpx.Response(200, json=_sample_processed_body())
    )
    result = client.get_results(article_url="https://example.com/a")
    assert isinstance(result, ProcessedResponse)
    assert route.called
    assert route.calls.last.request.url.params["article_url"] == "https://example.com/a"


@respx.mock
def test_get_health_ready(client: SentiSift) -> None:
    respx.get(f"{BASE_URL}/api/v1/health").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "ready",
                "model_name": "SentiSift_text_metrics",
                "model_version": "1.1",
                "load_time": 8.9,
                "progress": {"current": 17, "total": 17, "scorer_name": "finalizing"},
                "error": None,
            },
        )
    )
    health = client.get_health()
    assert health.status == "ready"
    assert health.progress is not None
    assert health.progress.current == 17
    assert health.progress.total == 17
    assert health.model_name == "SentiSift_text_metrics"


@respx.mock
def test_get_health_loading(client: SentiSift) -> None:
    respx.get(f"{BASE_URL}/api/v1/health").mock(
        return_value=httpx.Response(
            503,
            json={
                "status": "loading",
                "progress": {"current": 4, "total": 17, "scorer_name": "loading_xlmr"},
            },
        )
    )
    health = client.get_health()
    assert health.status == "loading"
    assert health.progress is not None
    assert health.progress.current == 4
    assert health.progress.total == 17
    assert health.progress.scorer_name == "loading_xlmr"


# -----------------------------------------------------------------------
# Context manager
# -----------------------------------------------------------------------
def test_client_is_context_manager() -> None:
    with SentiSift(api_key="sk_test") as client:
        assert isinstance(client, SentiSift)
