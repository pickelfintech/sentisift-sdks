"""SentiSift MCP server implementation.

Thin wrapper over the ``sentisift`` Python SDK. Each MCP tool corresponds
to a client method; the SDK handles retries, auth, and response parsing.

This is the ONLY file that defines tools. When a new endpoint appears in
the API (and therefore the Python SDK), add a matching tool here with a
one-paragraph docstring. Tools follow FastMCP 3.x conventions: the
function name becomes the tool name, the docstring becomes the tool
description visible to the LLM, and type hints drive the JSON schema.
"""
from __future__ import annotations

import logging
import os
import traceback
from typing import Annotated, Any

from fastmcp import FastMCP

from sentisift import SentiSift, SentiSiftError
from sentisift_mcp._version import __version__

# Module-level logger. MCP hosts usually capture stderr from the server
# process and surface it in their own logs, so anything we log here is
# visible to the end user for debugging.
logger = logging.getLogger("sentisift_mcp")
if not logger.handlers:
    # Default handler logs to stderr so MCP hosts can surface SDK errors
    # without the customer configuring logging themselves. Level defaults
    # to INFO; customers can override by setting SENTISIFT_MCP_LOG_LEVEL.
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s sentisift-mcp %(levelname)s %(message)s")
    )
    logger.addHandler(_handler)
    logger.setLevel(os.environ.get("SENTISIFT_MCP_LOG_LEVEL", "INFO").upper())

# Custom User-Agent identifies MCP traffic separately from direct SDK
# traffic in our usage_logs. This is how we measure MCP adoption.
_MCP_USER_AGENT = (
    f"sentisift-mcp/{__version__} "
    f"(fastmcp; delegates to sentisift-python)"
)

mcp: FastMCP = FastMCP(
    name="SentiSift",
    instructions=(
        "SentiSift analyzes comment sections: filters bots, spam, and "
        "commercial content; scores sentiment; reveals crowd-level "
        "themes; and on paid tiers adds interleaved Influence comments "
        "when a discussion skews negative.\n\n"
        "Primary tool: analyze_comments. Supporting tools: get_balance, "
        "get_health, get_article_results.\n\n"
        "The user must have a SentiSift API key set as the "
        "SENTISIFT_API_KEY environment variable before launching this "
        "MCP server. Free keys available at https://sentisift.com/pricing.html."
    ),
)

_client: SentiSift | None = None


def _get_client() -> SentiSift:
    """Return a lazily-constructed SentiSift client (singleton per process).

    Constructing once avoids repeated env-var lookups and lets the
    underlying httpx connection pool be reused across tool calls.
    """
    global _client
    if _client is None:
        _client = SentiSift(user_agent=_MCP_USER_AGENT)
    return _client


def _serialize(obj: Any) -> Any:
    """Convert Pydantic models / dataclasses to plain dicts.

    FastMCP can serialize dicts and primitives directly; Pydantic v2
    models have a model_dump() method that produces a JSON-safe dict.
    """
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_serialize(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


# ----------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------
@mcp.tool
def analyze_comments(
    article_url: Annotated[
        str,
        "Full URL of the article the comments belong to (e.g. 'https://example.com/article/42'). "
        "Used to group comments and accumulate Intelligence. URLs are normalized server-side.",
    ],
    comments: Annotated[
        list[dict],
        "Array of comment objects. Each must have 'text' (str), 'author' (str), and 'time' (ISO 8601 str). "
        "Optional fields: 'likes' (int), 'dislikes' (int), 'is_reply' (bool). "
        "If real author/time are unknown, synthesize stable placeholders "
        "(e.g. author='anonymous-1', time='2026-04-18T10:00:00').",
    ],
    article_text: Annotated[
        str | None,
        "Full article body. STRONGLY RECOMMENDED on the first call for each article (we cache it "
        "and use it for contextual analysis and Influence generation). Skip on later calls for the "
        "same article URL.",
    ] = None,
    title: Annotated[str | None, "Article title, for the article profile."] = None,
    tone: Annotated[
        str | None,
        "Brand voice for Influence comments when applicable (e.g. 'professional and measured', "
        "'warm and community-oriented'). Pro/Enterprise tiers only.",
    ] = None,
) -> dict:
    """Submit a batch of comments to SentiSift for moderation and analysis.

    Returns a response with status='buffered' (accepted, not yet analyzed,
    nothing charged) or status='processed' (full analysis returned).

    Processed responses include per-comment sentiment labels (Toxic,
    Negative, Neutral, Positive, Saccharine), bot/spam flags (the
    response 'comments' array has those removed), composite scores, and
    on Professional/Enterprise tiers, crowd-level 'intelligence'
    (discussion_themes, omega_ratio, sentiment_balance) plus interleaved
    Influence comments marked with is_influence=true.

    Comments are buffered per article until a processing threshold is
    reached, then all accumulated comments are analyzed together. You
    are billed only when processing occurs.

    Batch size caps: 50 comments per call on the Free tier, 2000 on
    paid tiers.
    """
    try:
        result = _get_client().analyze(
            article_url=article_url,
            comments=comments,
            article_text=article_text,
            title=title,
            tone=tone,
        )
        return _serialize(result)
    except SentiSiftError as err:
        # Log full traceback so the customer (via their MCP host's stderr
        # capture) can see what went wrong. Still return an error dict so
        # the LLM can read the error message and respond intelligently
        # rather than surfacing a protocol-level failure.
        logger.error(
            "analyze_comments failed: %s\n%s", err, traceback.format_exc(),
        )
        return {
            "status": "error",
            "error": str(err.message) if hasattr(err, "message") else str(err),
            "docs_url": err.docs_url,
            "request_id": err.request_id,
        }


@mcp.tool
def get_balance() -> dict:
    """Return the current SentiSift balance, tier, usage counters, and subscription state.

    Fields of interest:
      - comment_balance: remaining comments across all active grants (FIFO consumed)
      - tier: 'free', 'starter', 'professional', or 'enterprise'
      - features: which capabilities the current key unlocks (moderate,
        intelligence, influence)
      - comment_grants: active allocations with expiry dates
      - subscription: billing state ('active', 'cancelled', 'past_due')
        or null for free-tier keys
      - influence_stats: Influence generation history (if feature enabled)

    Call this when the user asks about their balance, upcoming renewals,
    or whether a feature is available on their tier.
    """
    try:
        return _serialize(_get_client().get_usage())
    except SentiSiftError as err:
        logger.error("get_balance failed: %s\n%s", err, traceback.format_exc())
        return {
            "status": "error",
            "error": str(err.message) if hasattr(err, "message") else str(err),
            "docs_url": err.docs_url,
        }


@mcp.tool
def get_health() -> dict:
    """Check if the SentiSift service is ready to handle requests.

    Returns {'status': 'ready'} when models are loaded and requests
    will be served normally, or {'status': 'loading', 'progress': 0.4}
    during a cold start (usually 10-60 seconds after a restart).

    Call this before a large batch analysis if response latency matters,
    or when diagnosing 'service appears slow' complaints. The
    analyze_comments tool handles transient loading states automatically
    with retries, so this is typically informational.
    """
    try:
        return _serialize(_get_client().get_health())
    except SentiSiftError as err:
        logger.error("get_health failed: %s\n%s", err, traceback.format_exc())
        return {
            "status": "error",
            "error": str(err.message) if hasattr(err, "message") else str(err),
            "docs_url": err.docs_url,
        }


@mcp.tool
def get_article_results(
    article_url: Annotated[
        str,
        "Full URL of the article to retrieve processed results for.",
    ],
) -> dict:
    """Fetch already-processed, scored comments for an article URL.

    Does NOT trigger new processing and does NOT generate Influence
    comments (Influence only appears in analyze_comments responses).

    Tier behavior:
      - Free/Starter: returns the buffered state only (processed
        comments are delivered inline via analyze_comments).
      - Professional/Enterprise: returns the full scored history
        accumulated across batches.

    Use this when the user asks for historical sentiment of an article
    already submitted previously, or to check how a discussion has
    evolved since the last analyze_comments call.
    """
    try:
        return _serialize(_get_client().get_results(article_url=article_url))
    except SentiSiftError as err:
        logger.error(
            "get_article_results failed: %s\n%s", err, traceback.format_exc(),
        )
        return {
            "status": "error",
            "error": str(err.message) if hasattr(err, "message") else str(err),
            "docs_url": err.docs_url,
            "request_id": err.request_id,
        }


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
def main() -> None:
    """Run the MCP server on stdio transport.

    Entry point for the `sentisift-mcp` console script. MCP-compatible
    AI hosts (Claude Desktop, Cursor, VS Code) launch this process and
    communicate with it over stdin/stdout using the MCP protocol.

    The SENTISIFT_API_KEY environment variable must be set before launch.
    The SDK's default exception message covers that case if the key is
    missing, which the host surfaces in its UI.
    """
    # Pre-flight: fail fast if the API key is missing so the host can
    # surface a clear message instead of letting every tool call fail
    # individually at request time.
    if not os.environ.get("SENTISIFT_API_KEY"):
        raise SystemExit(
            "SENTISIFT_API_KEY environment variable is not set. "
            "Get a free key at https://sentisift.com/pricing.html and add it to "
            "your MCP host's env config (see sentisift-mcp README)."
        )
    mcp.run()


if __name__ == "__main__":
    main()
