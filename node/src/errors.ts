/**
 * Typed exception hierarchy for the SentiSift SDK.
 *
 * Every error exposes `docs_url` and `requestId` so callers can follow
 * the deep link to the relevant section of api-docs.html.
 */
import type { ErrorResponse } from "./types.js";

export interface SentiSiftErrorOptions {
  statusCode?: number;
  docsUrl?: string;
  requestId?: string;
  responseBody?: ErrorResponse | Record<string, unknown>;
  cause?: unknown;
}

/** Base class for every SentiSift SDK error. */
export class SentiSiftError extends Error {
  public readonly statusCode?: number;
  public readonly docsUrl?: string;
  public readonly requestId?: string;
  public readonly responseBody?: Record<string, unknown>;

  constructor(message: string, options: SentiSiftErrorOptions = {}) {
    super(message, options.cause !== undefined ? { cause: options.cause } : undefined);
    this.name = "SentiSiftError";
    this.statusCode = options.statusCode;
    this.docsUrl = options.docsUrl;
    this.requestId = options.requestId;
    this.responseBody = options.responseBody as Record<string, unknown> | undefined;
  }
}

/** HTTP 401. API key missing, invalid, or deactivated. */
export class SentiSiftAuthError extends SentiSiftError {
  constructor(message: string, options: SentiSiftErrorOptions = {}) {
    super(message, options);
    this.name = "SentiSiftAuthError";
  }
}

/**
 * HTTP 400. Request payload is malformed. `docsUrl` targets the exact
 * field or row that triggered the failure (e.g.
 * #request-format-comment-author for a missing `author` field).
 */
export class SentiSiftValidationError extends SentiSiftError {
  constructor(message: string, options: SentiSiftErrorOptions = {}) {
    super(message, options);
    this.name = "SentiSiftValidationError";
  }
}

/**
 * HTTP 429. Rate limit exceeded. The SDK retries automatically; you only
 * see this exception after every retry has been exhausted.
 */
export class SentiSiftRateLimitError extends SentiSiftError {
  public readonly retryAfter?: number;

  constructor(
    message: string,
    options: SentiSiftErrorOptions & { retryAfter?: number } = {},
  ) {
    super(message, options);
    this.name = "SentiSiftRateLimitError";
    this.retryAfter = options.retryAfter;
  }
}

/**
 * HTTP 503. Models still loading after a restart. The SDK retries
 * automatically; typical resolution is 10-60 seconds.
 */
export class SentiSiftServiceLoadingError extends SentiSiftError {
  constructor(message: string, options: SentiSiftErrorOptions = {}) {
    super(message, options);
    this.name = "SentiSiftServiceLoadingError";
  }
}

/** HTTP 5xx (except 503). Unexpected server-side failure. */
export class SentiSiftServerError extends SentiSiftError {
  constructor(message: string, options: SentiSiftErrorOptions = {}) {
    super(message, options);
    this.name = "SentiSiftServerError";
  }
}
