import { describe, expect, it, vi } from "vitest";
import {
  SentiSift,
  SentiSiftAuthError,
  SentiSiftRateLimitError,
  SentiSiftServiceLoadingError,
  SentiSiftValidationError,
  SDK_VERSION,
  type BufferedResponse,
  type ProcessedResponse,
} from "../src/index.js";

function sampleProcessed(): ProcessedResponse {
  return {
    status: "processed",
    comments: [
      {
        text: "Great article",
        username: "alice",
        timestamp: "2026-04-18T10:00:00Z",
        sentiment_label: "Positive",
        composite_score: 0.82,
        is_influence: false,
      },
    ],
    moderation: {
      total_analyzed: 1,
      total_approved: 1,
      total_removed: 0,
      removal_breakdown: {
        bot_spam: 0,
        commercial: 0,
        negative_score: 0,
        positive_score: 0,
      },
    },
    comments_used: 1,
    comment_balance: 999,
  };
}

function sampleBuffered(): BufferedResponse {
  return {
    status: "buffered",
    article_url: "https://example.com/article/1",
    buffered_count: 5,
    threshold: 20,
    comments_used: 0,
    comment_balance: 1000,
  };
}

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

function mockFetch(responses: Response[]): typeof fetch {
  const queue = [...responses];
  return (async () => {
    const next = queue.shift();
    if (!next) throw new Error("mockFetch queue empty");
    return next;
  }) as typeof fetch;
}

function mockFetchSpy(responses: Response[]) {
  const calls: { url: string; init: RequestInit }[] = [];
  const queue = [...responses];
  const impl = (async (url: string | URL | Request, init: RequestInit = {}) => {
    calls.push({ url: String(url), init });
    const next = queue.shift();
    if (!next) throw new Error("mockFetch queue empty");
    return next;
  }) as typeof fetch;
  return { impl, calls };
}

// ---------------------------------------------------------------------
// Construction
// ---------------------------------------------------------------------
describe("SentiSift constructor", () => {
  it("reads API key from env", () => {
    const prev = process.env.SENTISIFT_API_KEY;
    process.env.SENTISIFT_API_KEY = "sk_from_env";
    try {
      const client = new SentiSift({ fetch: mockFetch([]) });
      expect(client).toBeInstanceOf(SentiSift);
    } finally {
      if (prev === undefined) delete process.env.SENTISIFT_API_KEY;
      else process.env.SENTISIFT_API_KEY = prev;
    }
  });

  it("throws when no key provided", () => {
    const prev = process.env.SENTISIFT_API_KEY;
    delete process.env.SENTISIFT_API_KEY;
    try {
      expect(() => new SentiSift({ fetch: mockFetch([]) })).toThrow(SentiSiftAuthError);
    } finally {
      if (prev !== undefined) process.env.SENTISIFT_API_KEY = prev;
    }
  });
});

// ---------------------------------------------------------------------
// analyze
// ---------------------------------------------------------------------
describe("analyze", () => {
  it("returns a processed response", async () => {
    const client = new SentiSift({
      apiKey: "sk_test",
      fetch: mockFetch([jsonResponse(200, sampleProcessed())]),
    });
    const result = await client.analyze({
      articleUrl: "https://example.com/a",
      comments: [{ text: "Hi", author: "alice", time: "2026-04-18T10:00:00" }],
    });
    expect(result.status).toBe("processed");
    if (result.status === "processed") {
      expect(result.comments[0].sentiment_label).toBe("Positive");
    }
  });

  it("returns a buffered response", async () => {
    const client = new SentiSift({
      apiKey: "sk_test",
      fetch: mockFetch([jsonResponse(200, sampleBuffered())]),
    });
    const result = await client.analyze({
      articleUrl: "https://example.com/a",
      comments: [{ text: "Hi", author: "alice", time: "2026-04-18T10:00:00" }],
    });
    expect(result.status).toBe("buffered");
    if (result.status === "buffered") {
      expect(result.buffered_count).toBe(5);
    }
  });

  it("sends expected headers and body", async () => {
    const { impl, calls } = mockFetchSpy([jsonResponse(200, sampleBuffered())]);
    const client = new SentiSift({ apiKey: "sk_test", fetch: impl, maxRetries: 0 });
    await client.analyze({
      articleUrl: "https://example.com/a",
      articleText: "Article body",
      title: "My Article",
      comments: [{ text: "Hi", author: "alice", time: "2026-04-18T10:00:00" }],
    });
    expect(calls).toHaveLength(1);
    const headers = calls[0].init.headers as Record<string, string>;
    expect(headers["X-API-Key"]).toBe("sk_test");
    expect(headers["User-Agent"]).toContain(`sentisift-node/${SDK_VERSION}`);
    const body = JSON.parse(calls[0].init.body as string);
    expect(body.metadata.article_url).toBe("https://example.com/a");
    expect(body.metadata.article_text).toBe("Article body");
    expect(body.metadata.title).toBe("My Article");
  });

  it("surfaces validation error with docs_url", async () => {
    const client = new SentiSift({
      apiKey: "sk_test",
      fetch: mockFetch([
        jsonResponse(400, {
          status: "error",
          error: "Comment at index 0 missing required field: 'author'.",
          docs_url: "https://sentisift.com/api-docs.html#request-format-comment-author",
          request_id: "req-xyz",
        }),
      ]),
      maxRetries: 0,
    });
    await expect(
      client.analyze({
        articleUrl: "https://example.com/a",
        comments: [{ text: "Hi", author: "x", time: "2026-04-18T10:00:00" }],
      }),
    ).rejects.toSatisfy((err: unknown) => {
      if (!(err instanceof SentiSiftValidationError)) return false;
      return (
        err.statusCode === 400 &&
        (err.docsUrl ?? "").includes("comment-author") &&
        err.requestId === "req-xyz"
      );
    });
  });

  it("surfaces auth error on 401", async () => {
    const client = new SentiSift({
      apiKey: "sk_test",
      fetch: mockFetch([jsonResponse(401, { status: "error", error: "Invalid key" })]),
      maxRetries: 0,
    });
    await expect(
      client.analyze({
        articleUrl: "https://example.com/a",
        comments: [{ text: "Hi", author: "x", time: "2026-04-18T10:00:00" }],
      }),
    ).rejects.toBeInstanceOf(SentiSiftAuthError);
  });
});

// ---------------------------------------------------------------------
// Retry behavior
// ---------------------------------------------------------------------
describe("retry behavior", () => {
  it("retries 429 then succeeds", async () => {
    vi.useFakeTimers();
    const { impl, calls } = mockFetchSpy([
      jsonResponse(429, { retry_after: 1 }, { "Retry-After": "1" }),
      jsonResponse(200, sampleBuffered()),
    ]);
    const client = new SentiSift({ apiKey: "sk_test", fetch: impl, maxRetries: 3 });
    const promise = client.analyze({
      articleUrl: "https://example.com/a",
      comments: [{ text: "Hi", author: "x", time: "2026-04-18T10:00:00" }],
    });
    // Drain sleep timers.
    await vi.runAllTimersAsync();
    const result = await promise;
    expect(result.status).toBe("buffered");
    expect(calls).toHaveLength(2);
    vi.useRealTimers();
  });

  it("exhausts retries and throws rate-limit error", async () => {
    const client = new SentiSift({
      apiKey: "sk_test",
      fetch: mockFetch([
        jsonResponse(429, { status: "error", error: "Too many", retry_after: 5 }, { "Retry-After": "5" }),
      ]),
      maxRetries: 0,
    });
    await expect(
      client.analyze({
        articleUrl: "https://example.com/a",
        comments: [{ text: "Hi", author: "x", time: "2026-04-18T10:00:00" }],
      }),
    ).rejects.toSatisfy((err: unknown) => {
      return err instanceof SentiSiftRateLimitError && err.retryAfter === 5;
    });
  });

  it("exhausts retries and throws service-loading error", async () => {
    const client = new SentiSift({
      apiKey: "sk_test",
      fetch: mockFetch([jsonResponse(503, { status: "error", error: "Loading" })]),
      maxRetries: 0,
    });
    await expect(
      client.analyze({
        articleUrl: "https://example.com/a",
        comments: [{ text: "Hi", author: "x", time: "2026-04-18T10:00:00" }],
      }),
    ).rejects.toBeInstanceOf(SentiSiftServiceLoadingError);
  });
});

// ---------------------------------------------------------------------
// Other endpoints
// ---------------------------------------------------------------------
describe("other endpoints", () => {
  it("getUsage", async () => {
    const client = new SentiSift({
      apiKey: "sk_test",
      fetch: mockFetch([
        jsonResponse(200, {
          status: "success",
          customer_name: "Acme",
          tier: "free",
          comment_balance: 847,
          comment_grants: [],
        }),
      ]),
    });
    const usage = await client.getUsage();
    expect(usage.customer_name).toBe("Acme");
    expect(usage.comment_balance).toBe(847);
  });

  it("getResults sends article_url query", async () => {
    const { impl, calls } = mockFetchSpy([jsonResponse(200, sampleProcessed())]);
    const client = new SentiSift({ apiKey: "sk_test", fetch: impl });
    const result = await client.getResults({ articleUrl: "https://example.com/a" });
    expect(result.status).toBe("processed");
    expect(calls[0].url).toContain(
      encodeURIComponent("https://example.com/a"),
    );
  });

  it("getHealth ready", async () => {
    const client = new SentiSift({
      apiKey: "sk_test",
      fetch: mockFetch([
        jsonResponse(200, {
          status: "ready",
          model_name: "SentiSift_text_metrics",
          model_version: "1.1",
          load_time: 8.9,
          progress: { current: 17, total: 17, scorer_name: "finalizing" },
          error: null,
        }),
      ]),
    });
    const health = await client.getHealth();
    expect(health.status).toBe("ready");
    expect(health.progress?.current).toBe(17);
    expect(health.progress?.total).toBe(17);
    expect(health.model_name).toBe("SentiSift_text_metrics");
  });

  it("getHealth loading (503 surfaced as-is)", async () => {
    const client = new SentiSift({
      apiKey: "sk_test",
      fetch: mockFetch([
        jsonResponse(503, {
          status: "loading",
          progress: { current: 4, total: 17, scorer_name: "loading_xlmr" },
        }),
      ]),
    });
    const health = await client.getHealth();
    expect(health.status).toBe("loading");
    expect(health.progress?.current).toBe(4);
    expect(health.progress?.total).toBe(17);
    expect(health.progress?.scorer_name).toBe("loading_xlmr");
  });
});
