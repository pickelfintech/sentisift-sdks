"""Exception hierarchy for the SentiSift SDK.

Every exception exposes the original `docs_url` from the API response
(when available) so callers can programmatically follow deep links to
the relevant section of api-docs.html.
"""
from __future__ import annotations

from typing import Optional


class SentiSiftError(Exception):
    """Base class for all SentiSift SDK errors.

    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code (if the error originated from a response).
        docs_url: Deep link to api-docs.html explaining this error.
        request_id: Correlation ID from the API response, for support.
        response_body: Raw decoded JSON body from the API response (best-effort).
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        docs_url: Optional[str] = None,
        request_id: Optional[str] = None,
        response_body: Optional[dict] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.docs_url = docs_url
        self.request_id = request_id
        self.response_body = response_body

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"(HTTP {self.status_code})")
        if self.docs_url:
            parts.append(f"docs: {self.docs_url}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        return " ".join(parts)


class SentiSiftAuthError(SentiSiftError):
    """Raised on HTTP 401. API key missing, invalid, or deactivated."""


class SentiSiftValidationError(SentiSiftError):
    """Raised on HTTP 400. Request payload is malformed.

    `docs_url` targets the exact field or row that triggered the failure,
    e.g. ``https://sentisift.com/api-docs.html#request-format-comment-author``
    for a missing ``author`` field.
    """


class SentiSiftRateLimitError(SentiSiftError):
    """Raised on HTTP 429. Too many requests in a short window.

    Attributes:
        retry_after: Seconds to wait before retrying (from the API body or
            the ``Retry-After`` header).
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: Optional[int] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.retry_after = retry_after


class SentiSiftServiceLoadingError(SentiSiftError):
    """Raised on HTTP 503. Models are still loading after a restart.

    Typical resolution: retry in 10-60 seconds. The SDK's automatic retry
    logic handles this for you by default; you only see this exception if
    every retry attempt has been exhausted.
    """


class SentiSiftServerError(SentiSiftError):
    """Raised on HTTP 5xx (except 503). Unexpected server-side failure."""
