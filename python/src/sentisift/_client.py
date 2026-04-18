"""Main SentiSift client. Synchronous HTTP via httpx.

Automatic retries on HTTP 429 (rate-limit, honors Retry-After) and HTTP 503
(service loading). Typed responses via Pydantic. User-Agent identifies the
SDK version for our usage analytics.
"""
from __future__ import annotations

import json
import logging
import os
import platform
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Union

import httpx

from sentisift._errors import (
    SentiSiftAuthError,
    SentiSiftError,
    SentiSiftRateLimitError,
    SentiSiftServerError,
    SentiSiftServiceLoadingError,
    SentiSiftValidationError,
)
from sentisift._models import (
    AnalyzeResponse,
    BufferedResponse,
    Comment,
    HealthResponse,
    ProcessedResponse,
    UsageResponse,
)
from sentisift._version import __version__

DEFAULT_BASE_URL = "https://api.sentisift.com"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_SERVICE_LOADING_RETRY_DELAY = 10.0
DEFAULT_USER_AGENT = f"sentisift-python/{__version__} python/{platform.python_version()}"

# Module-level logger. Callers can attach handlers and set the level on the
# `sentisift` logger to see SDK diagnostics (retry attempts, malformed
# responses, etc.). By default the logger emits nothing (no handler); this
# keeps the SDK quiet for customers who don't configure logging.
logger = logging.getLogger("sentisift")


class SentiSift:
    """Synchronous client for the SentiSift API.

    Args:
        api_key: Your API key. If omitted, read from the ``SENTISIFT_API_KEY``
            environment variable. Get one at https://sentisift.com/pricing.html.
        base_url: Override the API base URL. Defaults to the production endpoint.
        timeout: Per-request timeout in seconds. Defaults to 30.
        max_retries: Retries on 429 and 503 responses. Defaults to 3. Set to 0
            to disable retries entirely.
        user_agent: Override the default User-Agent. Prefer extending rather
            than replacing so our SDK version stays identifiable in your logs.

    Example:
        >>> from sentisift import SentiSift
        >>> client = SentiSift()
        >>> result = client.analyze(
        ...     article_url="https://example.com/article/1",
        ...     comments=[
        ...         {"text": "Great piece!", "author": "alice", "time": "2026-04-18T10:00:00"},
        ...     ],
        ... )
        >>> result.status
        'buffered'
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        user_agent: Optional[str] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        resolved_key = api_key or os.environ.get("SENTISIFT_API_KEY", "")
        if not resolved_key:
            raise SentiSiftAuthError(
                "API key not provided. Pass api_key=... to SentiSift() or set "
                "the SENTISIFT_API_KEY environment variable. Get a free key at "
                "https://sentisift.com/pricing.html",
                docs_url="https://sentisift.com/api-docs.html#authentication",
            )
        self._api_key = resolved_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max(0, max_retries)
        self._user_agent = user_agent or DEFAULT_USER_AGENT
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(timeout=timeout)

    def __enter__(self) -> "SentiSift":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client if we created it."""
        if self._owns_client:
            self._http.close()

    # ------------------------------------------------------------------
    # Primary endpoint
    # ------------------------------------------------------------------
    def analyze(
        self,
        *,
        article_url: str,
        comments: Iterable[Union[Comment, Mapping[str, Any]]],
        article_text: Optional[str] = None,
        title: Optional[str] = None,
        tone: Optional[str] = None,
        source: Optional[str] = None,
        category: Optional[str] = None,
    ) -> AnalyzeResponse:
        """Submit a batch of comments for analysis.

        Comments are buffered per article until the processing threshold is
        reached, then all accumulated comments are analyzed together. You are
        billed only when processing occurs.

        Send ``article_text`` on the first batch per article (cached and
        used for contextual analysis); skip it on later batches.

        Args:
            article_url: Full URL of the article. Used to group comments.
            comments: Iterable of ``Comment`` instances or equivalent dicts.
                Each needs ``text``, ``author``, and ``time``.
            article_text: Full article body. Recommended on the first batch.
            title: Article title (stored in article profile).
            tone: Brand voice for Influence comments (e.g. "professional").
            source: Publication or site name.
            category: Article category (e.g. "news", "opinion").

        Returns:
            ``BufferedResponse`` if the buffer has not reached the threshold,
            or ``ProcessedResponse`` with analysis results. Check ``.status``
            to distinguish.

        Raises:
            SentiSiftValidationError: Payload failed server validation (HTTP 400).
            SentiSiftAuthError: API key invalid (HTTP 401).
            SentiSiftRateLimitError: Rate limit exceeded after retries (HTTP 429).
            SentiSiftServiceLoadingError: Models still loading after retries (HTTP 503).
            SentiSiftServerError: Server-side failure (HTTP 5xx).
        """
        metadata: Dict[str, Any] = {"article_url": article_url}
        if article_text is not None:
            metadata["article_text"] = article_text
        if title is not None:
            metadata["title"] = title
        if tone is not None:
            metadata["tone"] = tone
        if source is not None:
            metadata["source"] = source
        if category is not None:
            metadata["category"] = category

        serialized_comments: List[Dict[str, Any]] = []
        for c in comments:
            if isinstance(c, Comment):
                serialized_comments.append(c.model_dump(exclude_none=True))
            else:
                serialized_comments.append(dict(c))

        body = {"metadata": metadata, "comments": serialized_comments}
        data = self._request("POST", "/api/v1/analyze", json_body=body)
        if data.get("status") == "buffered":
            return BufferedResponse.model_validate(data)
        return ProcessedResponse.model_validate(data)

    # ------------------------------------------------------------------
    # Supporting endpoints
    # ------------------------------------------------------------------
    def get_usage(self) -> UsageResponse:
        """Return current balance, usage counters, grants, and subscription state.

        Returns:
            ``UsageResponse`` with all account fields.
        """
        data = self._request("GET", "/api/v1/usage")
        return UsageResponse.model_validate(data)

    def get_results(self, *, article_url: str) -> AnalyzeResponse:
        """Retrieve already-processed results for an article URL.

        Does not trigger new processing. On Free and Starter tiers this
        returns the buffered state only; on Professional and Enterprise
        it returns the accumulated analyzed comments for the article.

        Args:
            article_url: Full URL of the article.

        Returns:
            ``BufferedResponse`` or ``ProcessedResponse``.
        """
        data = self._request(
            "GET",
            "/api/v1/results",
            params={"article_url": article_url},
        )
        if data.get("status") == "buffered":
            return BufferedResponse.model_validate(data)
        return ProcessedResponse.model_validate(data)

    def get_health(self) -> HealthResponse:
        """Return service readiness. ``status`` is ``"ready"`` or ``"loading"``.

        Useful for startup probes. Unlike the other endpoints this does not
        require authentication and does not trigger the SDK's automatic
        service-loading retry (you get the raw 503 as a HealthResponse with
        status="loading").
        """
        # Health intentionally bypasses retry-on-503 so callers can see the
        # current loading state. We still parse the body as HealthResponse.
        url = f"{self._base_url}/api/v1/health"
        response = self._http.get(url, headers={"User-Agent": self._user_agent})
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as parse_err:
            # Fallback: the health probe is an informational endpoint. If the
            # API returns malformed JSON we surface status="unknown" rather
            # than raising, so a customer's startup probe does not crash on
            # a transient proxy error. Logged for visibility.
            logger.warning(
                "sentisift.health: malformed JSON body (HTTP %s, body=%r, err=%s); "
                "returning status='unknown'",
                response.status_code,
                response.text[:200],
                parse_err,
            )
            data = {"status": "unknown"}
        return HealthResponse.model_validate(data)

    def wait_until_ready(self, *, timeout: float = 60.0, poll_interval: float = 2.0) -> None:
        """Block until ``get_health()`` returns ``status="ready"``.

        Useful at application startup after a cold deploy.

        Args:
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between health checks.

        Raises:
            SentiSiftServiceLoadingError: If the service is still loading
                after ``timeout`` seconds.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            health = self.get_health()
            if health.status == "ready":
                return
            time.sleep(poll_interval)
        raise SentiSiftServiceLoadingError(
            f"Service still loading after {timeout}s",
            docs_url="https://sentisift.com/api-docs.html#errors",
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        headers = {
            "X-API-Key": self._api_key,
            "User-Agent": self._user_agent,
            "Accept": "application/json",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        attempt = 0
        while True:
            response = self._http.request(
                method,
                url,
                headers=headers,
                json=json_body,
                params=params,
            )
            # Success path.
            if response.status_code == 200:
                return _safe_json(response)

            # Retryable cases: 429 (rate limit) and 503 (models loading).
            if response.status_code == 429 and attempt < self._max_retries:
                retry_after = _parse_retry_after(response)
                logger.info(
                    "sentisift: HTTP 429 on %s, retrying in %.1fs (attempt %d/%d)",
                    path, retry_after, attempt + 1, self._max_retries,
                )
                time.sleep(max(retry_after, 1.0))
                attempt += 1
                continue
            if response.status_code == 503 and attempt < self._max_retries:
                logger.info(
                    "sentisift: HTTP 503 on %s (models loading), retrying in %.1fs (attempt %d/%d)",
                    path, DEFAULT_SERVICE_LOADING_RETRY_DELAY, attempt + 1, self._max_retries,
                )
                time.sleep(DEFAULT_SERVICE_LOADING_RETRY_DELAY)
                attempt += 1
                continue

            # Terminal error path: map to a typed exception.
            raise _build_exception(response)


def _safe_json(response: httpx.Response) -> Dict[str, Any]:
    try:
        return response.json()  # type: ignore[no-any-return]
    except json.JSONDecodeError as decode_err:
        raise SentiSiftServerError(
            f"Malformed JSON from API (HTTP {response.status_code}): "
            f"{response.text[:200]!r}",
            status_code=response.status_code,
        ) from decode_err


def _parse_retry_after(response: httpx.Response) -> float:
    header_value = response.headers.get("Retry-After")
    if header_value:
        try:
            return float(header_value)
        except ValueError:
            # Fallback: Retry-After can legitimately be an HTTP-date
            # instead of seconds. We do not parse dates here; instead we
            # fall through to the JSON body or the default delay. Logged
            # because a non-integer header from our own API would be a bug.
            logger.warning(
                "sentisift: unparseable Retry-After header value %r; "
                "falling back to body.retry_after or default delay",
                header_value,
            )
    body = _safe_json_or_empty(response)
    retry_after = body.get("retry_after")
    if isinstance(retry_after, (int, float)):
        return float(retry_after)
    return DEFAULT_SERVICE_LOADING_RETRY_DELAY


def _safe_json_or_empty(response: httpx.Response) -> Dict[str, Any]:
    try:
        parsed = response.json()
    except (json.JSONDecodeError, ValueError) as parse_err:
        # Used only when we are already constructing an exception from a
        # non-200 response and want to read the body best-effort. Returning
        # {} is the right answer (the caller uses .get()), but we log at
        # debug level in case this is the tip of a larger issue.
        logger.debug(
            "sentisift: could not decode response body as JSON (HTTP %s, err=%s)",
            response.status_code, parse_err,
        )
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _build_exception(response: httpx.Response) -> SentiSiftError:
    body = _safe_json_or_empty(response)
    message = body.get("error") or f"HTTP {response.status_code}: {response.text[:200]}"
    common: Dict[str, Any] = {
        "status_code": response.status_code,
        "docs_url": body.get("docs_url"),
        "request_id": body.get("request_id"),
        "response_body": body,
    }
    if response.status_code == 400:
        return SentiSiftValidationError(message, **common)
    if response.status_code == 401:
        return SentiSiftAuthError(message, **common)
    if response.status_code == 429:
        return SentiSiftRateLimitError(
            message,
            retry_after=int(_parse_retry_after(response)),
            **common,
        )
    if response.status_code == 503:
        return SentiSiftServiceLoadingError(message, **common)
    return SentiSiftServerError(message, **common)
