/**
 * Type definitions for SentiSift API request and response shapes.
 *
 * Mirrors the OpenAPI schema at https://sentisift.com/openapi.json.
 * Response objects are intentionally permissive (index signatures /
 * optional fields) so new server fields do not break older SDK builds.
 */

export interface Comment {
  text: string;
  author: string;
  time: string;
  likes?: number;
  dislikes?: number;
  is_reply?: boolean;
}

export interface ArticleMetadata {
  article_url: string;
  article_text?: string;
  title?: string;
  tone?: string;
  source?: string;
  category?: string;
}

export interface ProcessedComment {
  text: string;
  username: string;
  timestamp: string;
  sentiment_label: "Toxic" | "Negative" | "Neutral" | "Positive" | "Saccharine" | string;
  composite_score: number;
  sentiment_confidence?: number;
  sentiment_polarity?: number;
  language?: string;
  is_influence: boolean;
  [key: string]: unknown;
}

export interface RemovalBreakdown {
  bot_spam: number;
  commercial: number;
  negative_score: number;
  positive_score: number;
  [key: string]: number;
}

export interface Moderation {
  total_analyzed: number;
  total_approved: number;
  total_removed: number;
  removal_breakdown: RemovalBreakdown;
}

export interface SentimentBalance {
  positive_mass: number;
  negative_mass: number;
}

export interface Intelligence {
  discussion_themes?: string;
  omega_ratio?: number;
  omega_interpretation?: string;
  accumulated_comments?: number;
  sentiment_balance?: SentimentBalance;
  [key: string]: unknown;
}

export interface BufferedResponse {
  status: "buffered";
  article_url: string;
  buffered_count: number;
  threshold: number;
  comments_used: number;
  comment_balance: number;
  processing_time_ms?: number;
  message?: string;
  request_id?: string;
  [key: string]: unknown;
}

export interface ProcessedResponse {
  status: "processed";
  comments: ProcessedComment[];
  moderation: Moderation;
  comments_used: number;
  comment_balance: number;
  model?: string;
  model_version?: string;
  processing_time_ms?: number;
  intelligence?: Intelligence;
  influence_pending?: boolean;
  total_comments?: number;
  approved_comments?: number;
  sentiment_distribution?: Record<string, number>;
  languages?: Record<string, number>;
  request_id?: string;
  [key: string]: unknown;
}

export type AnalyzeResponse = BufferedResponse | ProcessedResponse;

export interface CommentGrant {
  id: number;
  source: string;
  comments_granted: number;
  comments_remaining: number;
  granted_at: string;
  expires_at?: string;
}

export interface Subscription {
  status: "active" | "cancelled" | "past_due" | string;
  plan?: string;
  billing_interval?: "monthly" | "yearly" | string;
  current_period_start?: string;
  current_period_end?: string;
  cancelled_at?: string | null;
}

export interface InfluenceStats {
  total_comments_generated: number;
  articles_influenced: number;
  today_comments_generated: number;
  last_influence_at?: string;
  avg_omega_improvement?: number;
}

export interface UsageStats {
  today_requests: number;
  month_requests: number;
  total_requests: number;
  total_comments_analyzed: number;
  total_comments_billed: number;
  total_comments_purchased: number;
  avg_response_ms?: number;
}

export interface UsageLimits {
  max_comments_per_request: number;
}

export interface UsageFeatures {
  moderate: boolean;
  intelligence: boolean;
  influence: boolean;
}

export interface UsageResponse {
  status: "success";
  customer_name: string;
  tier: "free" | "starter" | "professional" | "enterprise" | string;
  comment_balance: number;
  usage?: UsageStats;
  limits?: UsageLimits;
  features?: UsageFeatures;
  comment_grants: CommentGrant[];
  subscription?: Subscription | null;
  influence_stats?: InfluenceStats;
  [key: string]: unknown;
}

/** Model-loading progress reported by the health endpoint.
 *  Present on every health response (both `"ready"` and `"loading"`).
 *  During load, `current` < `total`; once ready, `current === total`
 *  and `scorer_name === "finalizing"`. */
export interface Progress {
  current: number;
  total: number;
  scorer_name: string;
}

export interface HealthResponse {
  status: "ready" | "loading" | string;
  /** Structured load progress. Compute a 0.0-1.0 fraction with
   *  `progress.current / progress.total` if you need one. */
  progress?: Progress;
  model_name?: string;
  model_version?: string;
  load_time?: number;
  error?: string | null;
  [key: string]: unknown;
}

export interface ErrorResponse {
  status: "error";
  error: string;
  docs_url?: string;
  request_id?: string;
  retry_after?: number;
  [key: string]: unknown;
}

/**
 * Input shape for client.analyze().
 */
export interface AnalyzeInput {
  articleUrl: string;
  comments: Comment[];
  articleText?: string;
  title?: string;
  tone?: string;
  source?: string;
  category?: string;
}

/**
 * SDK configuration.
 */
export interface SentiSiftOptions {
  /**
   * API key. Falls back to `process.env.SENTISIFT_API_KEY` when omitted.
   * Get a free key at https://sentisift.com/pricing.html.
   */
  apiKey?: string;
  /** Override the API base URL. Defaults to https://api.sentisift.com. */
  baseUrl?: string;
  /** Per-request timeout in milliseconds. Defaults to 30000. */
  timeoutMs?: number;
  /** Retries on HTTP 429 and 503. Defaults to 3. Set to 0 to disable. */
  maxRetries?: number;
  /** Override the default User-Agent. Prefer extending rather than replacing. */
  userAgent?: string;
  /**
   * Custom fetch implementation. Defaults to globalThis.fetch (Node 18+).
   * Override to inject mocks in tests.
   */
  fetch?: typeof fetch;
}
