# @sentisift/client

Official TypeScript/JavaScript client for the [SentiSift](https://sentisift.com) comment-moderation and intelligence API.

**What SentiSift does.** Send a batch of comments and an article, receive bot/spam flags, sentiment labels, commercial-content flags, and confidence scores. On paid tiers, also get crowd-level Intelligence (discussion themes, Omega Ratio) and interleaved Influence comments when a discussion skews negative.

## Install

```bash
npm install @sentisift/client
# or
pnpm add @sentisift/client
# or
yarn add @sentisift/client
```

Requires Node.js 18 or newer (native `fetch`). Works in TypeScript and plain JavaScript.

## Quick start

```typescript
import { SentiSift } from "@sentisift/client";

const client = new SentiSift();  // reads SENTISIFT_API_KEY from env

const result = await client.analyze({
  articleUrl: "https://example.com/article/1",
  articleText: "The full article body...",  // recommended on the first batch only
  title: "My Article Title",
  comments: [
    { text: "Great article!", author: "alice", time: "2026-04-18T10:00:00" },
    { text: "This is wrong.", author: "bob", time: "2026-04-18T10:05:00" },
  ],
});

if (result.status === "buffered") {
  console.log(`Buffered ${result.buffered_count}/${result.threshold} - not yet analyzed`);
} else if (result.status === "processed") {
  for (const c of result.comments) {
    const tag = c.is_influence ? " (SentiSift)" : "";
    console.log(`${c.sentiment_label.padEnd(12)} ${c.text}${tag}`);
  }
  console.log(`Balance: ${result.comment_balance} comments`);
}
```

Get a free API key (1,000 comments, no credit card) at [sentisift.com/pricing](https://sentisift.com/pricing.html).

## Core concepts

- **Buffered batching.** Small batches are buffered per article until a processing threshold is reached. Below-threshold requests return `status: "buffered"` with no billing. Above-threshold requests return `status: "processed"` with analysis results for *all* accumulated comments for that article.
- **Article text on first batch.** Send `articleText` on the first batch for each article (we cache it and use it for contextual analysis). Skip it on later batches for the same article.
- **URL normalization.** `https://example.com/a` and `https://EXAMPLE.COM/a/` map to the same article.

Full details: [sentisift.com/api-docs.html](https://sentisift.com/api-docs.html).

## Configuration

```typescript
const client = new SentiSift({
  apiKey: "sk_sentisift_...",              // or set SENTISIFT_API_KEY env
  baseUrl: "https://api.sentisift.com",    // override for testing
  timeoutMs: 30000,                        // per-request timeout
  maxRetries: 3,                           // retries on 429 and 503
  userAgent: "my-app/1.0",                 // override default
  fetch: customFetch,                      // inject mocks in tests
});
```

## Handling responses

TypeScript's discriminated union makes response handling type-safe:

```typescript
const result = await client.analyze({ articleUrl, comments });

if (result.status === "buffered") {
  // type: BufferedResponse
  return;  // keep collecting
}

// type: ProcessedResponse
for (const c of result.comments) {
  render(c.text, c.sentiment_label, c.composite_score, c.is_influence);
}

if (result.intelligence) {
  console.log(result.intelligence.discussion_themes);
  console.log(`Mood: ${result.intelligence.omega_interpretation}`);
}
```

## Error handling

Every SDK exception exposes `docsUrl` from the API response, deep-linked to the exact field or section.

```typescript
import {
  SentiSiftError,
  SentiSiftAuthError,
  SentiSiftValidationError,
  SentiSiftRateLimitError,
  SentiSiftServiceLoadingError,
} from "@sentisift/client";

try {
  await client.analyze({ articleUrl, comments });
} catch (err) {
  if (err instanceof SentiSiftValidationError) {
    console.log(`Payload invalid: ${err.message}`);
    console.log(`Docs: ${err.docsUrl}`);       // e.g. ...#request-format-comment-author
    console.log(`Request ID: ${err.requestId}`);
  } else if (err instanceof SentiSiftRateLimitError) {
    console.log(`Rate limited. Retry in ${err.retryAfter}s.`);
  } else if (err instanceof SentiSiftAuthError) {
    console.log("Invalid API key.");
  } else if (err instanceof SentiSiftServiceLoadingError) {
    console.log("Models still loading.");
  } else if (err instanceof SentiSiftError) {
    console.log(`Unexpected error: ${err.message}`);
  } else {
    throw err;
  }
}
```

The SDK automatically retries on HTTP 429 (respecting `Retry-After`) and HTTP 503 (models loading). You only see these exceptions after every retry has been exhausted.

## Other endpoints

```typescript
// Balance, grants, subscription state, influence stats
const usage = await client.getUsage();
console.log(`${usage.comment_balance} comments on ${usage.tier} tier`);

// Retrieve already-processed results for an article
const result = await client.getResults({ articleUrl: "https://example.com/a" });

// Service readiness
const health = await client.getHealth();
if (health.status === "loading") {
  await client.waitUntilReady({ timeoutMs: 60000 });
}
```

## Versioning

Follows [semantic versioning](https://semver.org/). Before `1.0.0`, minor versions may include breaking changes (documented in [CHANGELOG.md](CHANGELOG.md)). Pin a version in production:

```json
"@sentisift/client": "^0.1.1"
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
