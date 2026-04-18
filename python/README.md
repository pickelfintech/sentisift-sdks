# SentiSift Python SDK

Official Python client for the [SentiSift](https://sentisift.com) comment-moderation and intelligence API.

**What SentiSift does.** Send a batch of comments and an article, receive bot/spam flags, sentiment labels, commercial-content flags, and confidence scores. On paid tiers, also get crowd-level Intelligence (discussion themes, Omega Ratio) and interleaved Influence comments when a discussion skews negative.

## Install

```bash
pip install sentisift
```

Requires Python 3.9 or newer.

## Quick start

```python
from sentisift import SentiSift

client = SentiSift()  # reads SENTISIFT_API_KEY from env
result = client.analyze(
    article_url="https://example.com/article/1",
    comments=[
        {"text": "Great article, very informative!", "author": "alice", "time": "2026-04-18T10:00:00"},
        {"text": "This is wrong on so many levels.", "author": "bob", "time": "2026-04-18T10:05:00"},
    ],
    article_text="The full article body goes here...",  # recommended on the first batch only
    title="My Article Title",
)

if result.status == "buffered":
    print(f"Buffered {result.buffered_count}/{result.threshold} comments - not yet analyzed")
elif result.status == "processed":
    for comment in result.comments:
        tag = " (SentiSift)" if comment.is_influence else ""
        print(f"{comment.sentiment_label:<12} {comment.text}{tag}")
    print(f"Balance: {result.comment_balance} comments remaining")
```

Get a free API key (1,000 comments, no credit card) at [sentisift.com/pricing](https://sentisift.com/pricing.html).

## Core concepts

- **Buffered batching.** Small batches are buffered per article until a processing threshold is reached. Below-threshold requests return `status="buffered"` with no billing. Above-threshold requests return `status="processed"` with analysis results for *all* accumulated comments for that article.
- **Article text on first batch.** Send `article_text` on the first batch for each article (we cache it and use it for contextual analysis). Skip it on later batches for the same article.
- **URL normalization.** `https://example.com/a` and `https://EXAMPLE.COM/a/` map to the same article.
- **Deduplication.** Comments are deduplicated by `(author, text, time)`, so overlapping batches are safe.

Full details: [sentisift.com/api-docs.html](https://sentisift.com/api-docs.html).

## Configuration

```python
client = SentiSift(
    api_key="sk_sentisift_...",            # or set SENTISIFT_API_KEY env var
    base_url="https://api.sentisift.com",  # override for testing
    timeout=30.0,                          # per-request timeout in seconds
    max_retries=3,                         # retries on 429 and 503
    user_agent="my-app/1.0",               # override default (keep version visible)
)
```

## Handling responses

```python
from sentisift import BufferedResponse, ProcessedResponse

result = client.analyze(article_url=..., comments=...)

if isinstance(result, BufferedResponse):
    # Nothing to render yet. Keep collecting.
    ...
elif isinstance(result, ProcessedResponse):
    # Render every entry in result.comments in order.
    # Influence comments (on Pro/Enterprise) are flagged with is_influence=True.
    for c in result.comments:
        render(c.text, c.sentiment_label, c.composite_score, is_influence=c.is_influence)

    # Intelligence is only populated on Professional and Enterprise.
    if result.intelligence:
        print(result.intelligence.discussion_themes)
        print(f"Mood: {result.intelligence.omega_interpretation} ({result.intelligence.omega_ratio:+.2f})")
```

## Error handling

Every SDK exception exposes the `docs_url` from the API response for self-service debugging.

```python
from sentisift import (
    SentiSiftError,
    SentiSiftAuthError,
    SentiSiftValidationError,
    SentiSiftRateLimitError,
    SentiSiftServiceLoadingError,
    SentiSiftServerError,
)

try:
    client.analyze(...)
except SentiSiftValidationError as err:
    print(f"Payload invalid: {err.message}")
    print(f"Docs: {err.docs_url}")      # deep link to the exact field row
    print(f"Request ID: {err.request_id}")
except SentiSiftRateLimitError as err:
    print(f"Rate limited. Retry in {err.retry_after}s.")
except SentiSiftAuthError:
    print("Invalid API key.")
except SentiSiftServiceLoadingError:
    print("Models still loading; try again shortly.")
except SentiSiftError as err:
    print(f"Unexpected error: {err}")
```

The SDK automatically retries on HTTP 429 (respecting `Retry-After`) and HTTP 503 (models loading). You only see these exceptions if every retry attempt has been exhausted.

## Other endpoints

```python
# Balance, grants, subscription state, influence stats
usage = client.get_usage()
print(f"{usage.comment_balance} comments remaining on {usage.tier} tier")
for grant in usage.comment_grants:
    print(f"  {grant.comments_remaining}/{grant.comments_granted} expires {grant.expires_at}")

# Retrieve already-processed results for an article
result = client.get_results(article_url="https://example.com/article")

# Service readiness
health = client.get_health()
if health.status == "loading":
    client.wait_until_ready(timeout=60)
```

## Testing

```python
# In your tests, inject an httpx.Client for mocking
import httpx
import respx
from sentisift import SentiSift

@respx.mock
def test_my_integration():
    respx.post("https://api.sentisift.com/api/v1/analyze").mock(
        return_value=httpx.Response(200, json={...})
    )
    client = SentiSift(api_key="sk_test")
    result = client.analyze(...)
```

## Versioning

This SDK follows [semantic versioning](https://semver.org/). Before `1.0.0`, minor versions may include breaking changes (documented in [CHANGELOG.md](CHANGELOG.md)). Pin a version in production:

```
sentisift>=0.1,<0.2
```

## Links

- [API documentation (HTML)](https://sentisift.com/api-docs.html)
- [API documentation (Markdown)](https://sentisift.com/api-docs.md)
- [OpenAPI 3.1 spec](https://sentisift.com/openapi.json)
- [Pricing and signup](https://sentisift.com/pricing.html)
- [Dashboard](https://dashboard.sentisift.com)
- [Changelog](CHANGELOG.md)
- [Support](mailto:tom@sentisift.com)

## License

Proprietary. See project terms at [sentisift.com/terms.html](https://sentisift.com/terms.html).
