// SentiSift error handling - one example per typed exception.
//
// Demonstrates the typed exception hierarchy and how to read the deep-link
// `docsUrl` and correlation `requestId` for self-service debugging.
//
// Prerequisites:
//   npm install @sentisift/client
//   export SENTISIFT_API_KEY=sk_sentisift_your_key_here
//
// Run:
//   node error_handling.mjs

import {
  SentiSift,
  SentiSiftAuthError,
  SentiSiftError,
  SentiSiftRateLimitError,
  SentiSiftServerError,
  SentiSiftServiceLoadingError,
  SentiSiftValidationError,
} from "@sentisift/client";

async function show(label, fn) {
  console.log(`\n--- ${label} ---`);
  try {
    await fn();
    console.log("(no exception thrown)");
  } catch (err) {
    if (err instanceof SentiSiftValidationError) {
      // Validation errors include a deep-linked docsUrl that targets the
      // exact field row in the HTML docs (e.g. #request-format-comment-author).
      console.log(`validation: ${err.message}`);
      console.log(`  docsUrl:   ${err.docsUrl}`);
      console.log(`  requestId: ${err.requestId}`);
    } else if (err instanceof SentiSiftAuthError) {
      console.log(`auth: ${err.message}  (docsUrl=${err.docsUrl})`);
    } else if (err instanceof SentiSiftRateLimitError) {
      // 429 rate-limit. Exception is only thrown after retries exhaust.
      console.log(`rate-limit: ${err.message}  (retryAfter=${err.retryAfter}s)`);
    } else if (err instanceof SentiSiftServiceLoadingError) {
      // 503 - models loading after a deploy. SDK auto-retries; if you see
      // this, retries exhausted. Wait 30-60s and retry.
      console.log(`service-loading: ${err.message}`);
    } else if (err instanceof SentiSiftServerError) {
      console.log(`server (5xx): ${err.message}  (requestId=${err.requestId})`);
    } else if (err instanceof SentiSiftError) {
      console.log(`unexpected SentiSift error: ${err.message}`);
    } else {
      throw err;
    }
  }
}

const validClient = new SentiSift(); // uses SENTISIFT_API_KEY env var
const badClient = new SentiSift({ apiKey: "sk_sentisift_obviously_invalid_key_for_demo_only" });

// Validation: missing required `author` field on the comment.
await show(
  "Validation - missing comment.author",
  () =>
    validClient.analyze({
      articleUrl: "https://example.com/article/err-demo",
      comments: [{ text: "hi", time: "2026-04-18T10:00:00" }],
    }),
);

// Validation: missing required `metadata.article_url`.
await show(
  "Validation - missing metadata.article_url",
  () =>
    validClient.analyze({
      articleUrl: "",
      comments: [{ text: "hi", author: "x", time: "2026-04-18T10:00:00" }],
    }),
);

// Auth: wrong key.
await show("Auth - invalid key", () => badClient.getUsage());
