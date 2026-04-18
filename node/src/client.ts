/**
 * Main SentiSift client (TypeScript).
 *
 * Uses global fetch (Node 18+). Automatic retries on HTTP 429 (honors
 * Retry-After) and 503 (service loading). Typed responses.
 */
import { SDK_VERSION } from "./version.js";
import {
  SentiSiftAuthError,
  SentiSiftError,
  SentiSiftRateLimitError,
  SentiSiftServerError,
  SentiSiftServiceLoadingError,
  SentiSiftValidationError,
} from "./errors.js";
import type {
  AnalyzeInput,
  AnalyzeResponse,
  ErrorResponse,
  HealthResponse,
  SentiSiftOptions,
  UsageResponse,
} from "./types.js";

const DEFAULT_BASE_URL = "https://api.sentisift.com";
const DEFAULT_TIMEOUT_MS = 30000;
const DEFAULT_MAX_RETRIES = 3;
const DEFAULT_SERVICE_LOADING_RETRY_MS = 10000;

function defaultUserAgent(): string {
  const nodePart = typeof process !== "undefined" && process.versions?.node
    ? ` node/${process.versions.node}`
    : "";
  return `sentisift-node/${SDK_VERSION}${nodePart}`;
}

/**
 * Synchronous (Promise-returning) client for the SentiSift API.
 *
 * Usage:
 *
 *     import { SentiSift } from "@sentisift/client";
 *
 *     const client = new SentiSift();  // reads SENTISIFT_API_KEY from env
 *     const result = await client.analyze({
 *       articleUrl: "https://example.com/article",
 *       comments: [{ text: "Nice!", author: "alice", time: "2026-04-18T10:00:00" }],
 *     });
 *     if (result.status === "processed") {
 *       for (const c of result.comments) console.log(c.sentiment_label, c.text);
 *     }
 */
export class SentiSift {
  private readonly apiKey: string;
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly maxRetries: number;
  private readonly userAgent: string;
  private readonly fetchImpl: typeof fetch;

  constructor(options: SentiSiftOptions = {}) {
    const resolvedKey =
      options.apiKey ??
      (typeof process !== "undefined" ? process.env?.SENTISIFT_API_KEY : undefined) ??
      "";
    if (!resolvedKey) {
      throw new SentiSiftAuthError(
        "API key not provided. Pass { apiKey } to new SentiSift() or set the " +
          "SENTISIFT_API_KEY environment variable. Get a free key at " +
          "https://sentisift.com/pricing.html",
        { docsUrl: "https://sentisift.com/api-docs.html#authentication" },
      );
    }
    this.apiKey = resolvedKey;
    this.baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/$/, "");
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.maxRetries = Math.max(0, options.maxRetries ?? DEFAULT_MAX_RETRIES);
    this.userAgent = options.userAgent ?? defaultUserAgent();
    const fetchCandidate = options.fetch ?? (globalThis as { fetch?: typeof fetch }).fetch;
    if (!fetchCandidate) {
      throw new SentiSiftError(
        "No fetch implementation available. Run on Node 18+ or pass { fetch } in options.",
      );
    }
    this.fetchImpl = fetchCandidate;
  }

  /**
   * Submit a batch of comments for analysis.
   *
   * Comments are buffered per article until the processing threshold is
   * reached, then all accumulated comments are analyzed together. You are
   * billed only when processing occurs.
   *
   * Send `articleText` on the first batch per article (cached and used
   * for contextual analysis); skip it on later batches.
   */
  async analyze(input: AnalyzeInput): Promise<AnalyzeResponse> {
    const metadata: Record<string, unknown> = { article_url: input.articleUrl };
    if (input.articleText !== undefined) metadata.article_text = input.articleText;
    if (input.title !== undefined) metadata.title = input.title;
    if (input.tone !== undefined) metadata.tone = input.tone;
    if (input.source !== undefined) metadata.source = input.source;
    if (input.category !== undefined) metadata.category = input.category;

    const body = { metadata, comments: input.comments };
    const data = await this.request<AnalyzeResponse>("POST", "/api/v1/analyze", { body });
    return data;
  }

  /** Return current balance, usage counters, grants, and subscription state. */
  async getUsage(): Promise<UsageResponse> {
    return this.request<UsageResponse>("GET", "/api/v1/usage");
  }

  /**
   * Retrieve already-processed results for an article URL. Does not
   * trigger new processing.
   */
  async getResults(input: { articleUrl: string }): Promise<AnalyzeResponse> {
    return this.request<AnalyzeResponse>("GET", "/api/v1/results", {
      query: { article_url: input.articleUrl },
    });
  }

  /**
   * Return service readiness. `status` is "ready" or "loading".
   *
   * Unlike other methods, `getHealth()` does not retry on 503 - it
   * surfaces the current loading state so the caller can decide when
   * to proceed.
   */
  async getHealth(): Promise<HealthResponse> {
    const url = `${this.baseUrl}/api/v1/health`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetchImpl(url, {
        method: "GET",
        headers: { "User-Agent": this.userAgent },
        signal: controller.signal,
      });
      const data = (await safeJson(response)) ?? { status: "unknown" };
      return data as HealthResponse;
    } finally {
      clearTimeout(timeout);
    }
  }

  /**
   * Poll `getHealth()` until it returns `status === "ready"`. Useful at
   * application startup after a cold deploy.
   */
  async waitUntilReady(
    options: { timeoutMs?: number; pollIntervalMs?: number } = {},
  ): Promise<void> {
    const timeoutMs = options.timeoutMs ?? 60000;
    const pollMs = options.pollIntervalMs ?? 2000;
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const health = await this.getHealth();
      if (health.status === "ready") return;
      await sleep(pollMs);
    }
    throw new SentiSiftServiceLoadingError(
      `Service still loading after ${timeoutMs}ms`,
      { docsUrl: "https://sentisift.com/api-docs.html#errors" },
    );
  }

  // ------------------------------------------------------------------
  // Internal
  // ------------------------------------------------------------------
  private async request<T>(
    method: string,
    path: string,
    opts: { body?: unknown; query?: Record<string, string> } = {},
  ): Promise<T> {
    let url = `${this.baseUrl}${path}`;
    if (opts.query) {
      const qs = new URLSearchParams(opts.query).toString();
      if (qs) url += `?${qs}`;
    }
    const headers: Record<string, string> = {
      "X-API-Key": this.apiKey,
      "User-Agent": this.userAgent,
      Accept: "application/json",
    };
    const init: RequestInit = { method, headers };
    if (opts.body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
    }

    let attempt = 0;
    while (true) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
      let response: Response;
      try {
        response = await this.fetchImpl(url, { ...init, signal: controller.signal });
      } finally {
        clearTimeout(timeout);
      }

      if (response.status === 200) {
        const data = await safeJson(response);
        if (data === undefined) {
          throw new SentiSiftServerError(
            `Malformed JSON from API (HTTP 200)`,
            { statusCode: 200 },
          );
        }
        return data as T;
      }

      if (response.status === 429 && attempt < this.maxRetries) {
        const retryMs = await parseRetryAfter(response);
        await sleep(retryMs);
        attempt++;
        continue;
      }

      if (response.status === 503 && attempt < this.maxRetries) {
        await sleep(DEFAULT_SERVICE_LOADING_RETRY_MS);
        attempt++;
        continue;
      }

      throw await buildException(response);
    }
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function safeJson(response: Response): Promise<unknown | undefined> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

async function parseRetryAfter(response: Response): Promise<number> {
  const header = response.headers.get("Retry-After");
  if (header) {
    const seconds = Number.parseFloat(header);
    if (!Number.isNaN(seconds)) return Math.max(seconds * 1000, 1000);
  }
  const body = (await safeJson(response)) as { retry_after?: number } | undefined;
  if (body && typeof body.retry_after === "number") {
    return Math.max(body.retry_after * 1000, 1000);
  }
  return DEFAULT_SERVICE_LOADING_RETRY_MS;
}

async function buildException(response: Response): Promise<SentiSiftError> {
  const body = ((await safeJson(response)) as ErrorResponse | undefined) ?? {
    status: "error",
    error: `HTTP ${response.status}`,
  };
  const message = body.error || `HTTP ${response.status}`;
  const common = {
    statusCode: response.status,
    docsUrl: body.docs_url,
    requestId: body.request_id,
    responseBody: body,
  };
  switch (response.status) {
    case 400:
      return new SentiSiftValidationError(message, common);
    case 401:
      return new SentiSiftAuthError(message, common);
    case 429: {
      const retryMs = await parseRetryAfter(response);
      return new SentiSiftRateLimitError(message, {
        ...common,
        retryAfter: Math.round(retryMs / 1000),
      });
    }
    case 503:
      return new SentiSiftServiceLoadingError(message, common);
    default:
      return new SentiSiftServerError(message, common);
  }
}
