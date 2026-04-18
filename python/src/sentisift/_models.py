"""Pydantic models for SentiSift API request and response shapes.

Field names mirror the OpenAPI schema at
https://sentisift.com/openapi.json. Models use ``extra="allow"`` so that
new fields added by the API do not break older SDK versions (forward
compatibility).
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class _SentiSiftModel(BaseModel):
    """Base model allowing extra fields for forward compatibility."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Comment(_SentiSiftModel):
    """Input comment structure passed to ``analyze``."""

    text: str
    author: str
    time: str
    likes: Optional[int] = None
    dislikes: Optional[int] = None
    is_reply: Optional[bool] = None


class ArticleMetadata(_SentiSiftModel):
    """Input article metadata for ``analyze``."""

    article_url: str
    article_text: Optional[str] = None
    title: Optional[str] = None
    tone: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None


class ProcessedComment(_SentiSiftModel):
    """A single comment in a processed analyze response."""

    text: str
    username: str
    timestamp: str
    sentiment_label: str
    composite_score: float
    sentiment_confidence: Optional[float] = None
    sentiment_polarity: Optional[float] = None
    language: Optional[str] = None
    is_influence: bool = False


class RemovalBreakdown(_SentiSiftModel):
    bot_spam: int = 0
    commercial: int = 0
    negative_score: int = 0
    positive_score: int = 0


class Moderation(_SentiSiftModel):
    total_analyzed: int
    total_approved: int
    total_removed: int
    removal_breakdown: RemovalBreakdown


class SentimentBalance(_SentiSiftModel):
    positive_mass: float
    negative_mass: float


class Intelligence(_SentiSiftModel):
    """Crowd-level analytics. Professional and Enterprise only."""

    discussion_themes: Optional[str] = None
    omega_ratio: Optional[float] = None
    omega_interpretation: Optional[str] = None
    accumulated_comments: Optional[int] = None
    sentiment_balance: Optional[SentimentBalance] = None


class BufferedResponse(_SentiSiftModel):
    """Returned when the per-article buffer has not yet reached the processing
    threshold. No comments are billed. Your data is safe in the buffer and
    will be processed when the threshold is crossed (by a later batch or
    by our background inactivity worker).
    """

    status: Literal["buffered"]
    article_url: str
    buffered_count: int
    threshold: int
    comments_used: int = 0
    comment_balance: int
    processing_time_ms: Optional[int] = None
    message: Optional[str] = None
    request_id: Optional[str] = None


class ProcessedResponse(_SentiSiftModel):
    """Returned when the buffer crosses the threshold and all accumulated
    comments for the article have been analyzed. The ``comments`` array is
    your moderated, ready-to-display set; on paid tiers it may include
    interleaved Influence comments flagged with ``is_influence=True``.
    """

    status: Literal["processed"]
    comments: List[ProcessedComment]
    moderation: Moderation
    comments_used: int
    comment_balance: int
    model: Optional[str] = None
    model_version: Optional[str] = None
    processing_time_ms: Optional[int] = None
    intelligence: Optional[Intelligence] = None
    influence_pending: Optional[bool] = None
    total_comments: Optional[int] = None
    approved_comments: Optional[int] = None
    sentiment_distribution: Optional[Dict[str, int]] = None
    languages: Optional[Dict[str, int]] = None
    request_id: Optional[str] = None


AnalyzeResponse = Union[BufferedResponse, ProcessedResponse]


class CommentGrant(_SentiSiftModel):
    id: int
    source: str
    comments_granted: int
    comments_remaining: int
    granted_at: str
    expires_at: Optional[str] = None


class Subscription(_SentiSiftModel):
    status: str
    plan: Optional[str] = None
    billing_interval: Optional[str] = None
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    cancelled_at: Optional[str] = None


class InfluenceStats(_SentiSiftModel):
    total_comments_generated: int = 0
    articles_influenced: int = 0
    today_comments_generated: int = 0
    last_influence_at: Optional[str] = None
    avg_omega_improvement: Optional[float] = None


class UsageStats(_SentiSiftModel):
    today_requests: int = 0
    month_requests: int = 0
    total_requests: int = 0
    total_comments_analyzed: int = 0
    total_comments_billed: int = 0
    total_comments_purchased: int = 0
    avg_response_ms: Optional[int] = None


class UsageLimits(_SentiSiftModel):
    max_comments_per_request: int


class UsageFeatures(_SentiSiftModel):
    moderate: bool = True
    intelligence: bool = False
    influence: bool = False


class UsageResponse(_SentiSiftModel):
    """Balance, usage history, subscription state, and feature flags.

    Returned by ``client.get_usage()``.
    """

    status: Literal["success"]
    customer_name: str
    tier: str
    comment_balance: int
    usage: Optional[UsageStats] = None
    limits: Optional[UsageLimits] = None
    features: Optional[UsageFeatures] = None
    comment_grants: List[CommentGrant] = Field(default_factory=list)
    subscription: Optional[Subscription] = None
    influence_stats: Optional[InfluenceStats] = None


class Progress(_SentiSiftModel):
    """Model-loading progress reported by the health endpoint.

    Present on every health response (both ``"ready"`` and ``"loading"``).
    During load, ``current`` < ``total``; once ready, ``current == total``
    and ``scorer_name`` is ``"finalizing"``.
    """

    current: int
    total: int
    scorer_name: str


class HealthResponse(_SentiSiftModel):
    """Service readiness probe result.

    ``status`` is ``"ready"`` (HTTP 200) when models are loaded, or
    ``"loading"`` (HTTP 503) during startup. ``progress`` is a structured
    object with ``current``, ``total``, and ``scorer_name`` fields and is
    typically present on every response (use ``current/total`` to compute
    a 0.0-1.0 fraction yourself if needed). ``model_name``,
    ``model_version``, ``load_time``, and ``error`` are also present in
    the live response and are accessible via attribute access thanks to
    the base model's ``extra="allow"`` config.
    """

    status: str
    progress: Optional[Progress] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    load_time: Optional[float] = None
    error: Optional[str] = None


class SignupResponse(_SentiSiftModel):
    """Response from the free-signup endpoint. Exposed for integrators
    building custom signup flows. Normal use is via sentisift.com/pricing.html
    (Cloudflare Turnstile required).
    """

    status: Literal["success"]
    api_key: str
    tier: str
    comment_balance: int
    email_status: Optional[str] = None
    dashboard_url: Optional[str] = None


class ErrorResponse(_SentiSiftModel):
    """Error response shape. Raised as an exception by the SDK; exposed
    for callers who catch exceptions and want to inspect the raw body.
    """

    status: Literal["error"]
    error: str
    docs_url: Optional[str] = None
    request_id: Optional[str] = None
    retry_after: Optional[int] = None


__all__ = [
    "ArticleMetadata",
    "Comment",
    "ProcessedComment",
    "RemovalBreakdown",
    "Moderation",
    "SentimentBalance",
    "Intelligence",
    "BufferedResponse",
    "ProcessedResponse",
    "AnalyzeResponse",
    "CommentGrant",
    "Subscription",
    "InfluenceStats",
    "UsageStats",
    "UsageLimits",
    "UsageFeatures",
    "UsageResponse",
    "Progress",
    "HealthResponse",
    "SignupResponse",
    "ErrorResponse",
]
