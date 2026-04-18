"""Official Python client for the SentiSift comment-moderation and intelligence API.

SentiSift analyzes comment sections: filters bots, spam, and commercial content;
scores sentiment; reveals crowd-level themes; and on paid tiers adds constructive
Influence comments when a discussion skews negative.

Quick start:

    from sentisift import SentiSift

    client = SentiSift()  # reads SENTISIFT_API_KEY from env
    result = client.analyze(
        article_url="https://example.com/article",
        comments=[
            {"text": "Great article!", "author": "reader1", "time": "2026-03-28T10:00:00"},
        ],
    )
    if result.status == "buffered":
        print(f"Buffered {result.buffered_count} comments")
    elif result.status == "processed":
        for comment in result.comments:
            print(comment.sentiment_label, comment.text)

Full documentation: https://sentisift.com/api-docs.html
"""
from sentisift._client import SentiSift
from sentisift._errors import (
    SentiSiftError,
    SentiSiftAuthError,
    SentiSiftRateLimitError,
    SentiSiftServiceLoadingError,
    SentiSiftServerError,
    SentiSiftValidationError,
)
from sentisift._models import (
    AnalyzeResponse,
    BufferedResponse,
    CommentGrant,
    HealthResponse,
    InfluenceStats,
    Intelligence,
    Moderation,
    ProcessedComment,
    ProcessedResponse,
    Progress,
    Subscription,
    UsageResponse,
)
from sentisift._version import __version__

__all__ = [
    "SentiSift",
    "SentiSiftError",
    "SentiSiftAuthError",
    "SentiSiftRateLimitError",
    "SentiSiftServiceLoadingError",
    "SentiSiftServerError",
    "SentiSiftValidationError",
    "AnalyzeResponse",
    "BufferedResponse",
    "ProcessedResponse",
    "ProcessedComment",
    "Moderation",
    "Intelligence",
    "UsageResponse",
    "CommentGrant",
    "Subscription",
    "InfluenceStats",
    "HealthResponse",
    "Progress",
    "__version__",
]
