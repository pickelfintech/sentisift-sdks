# SDK Overview

Current state of the SentiSift client SDKs in this repository (`pickel-fintech/sentisift-sdks`). The full SentiSift API service lives in a separate, private repository.

**Last updated:** 2026-04-18

## Published versions

| Package | Version | Registry | Status |
|---|---|---|---|
| `sentisift` (Python SDK) | 0.1.3 | https://pypi.org/project/sentisift/ | Live. License: MIT (changed from Proprietary in 0.1.3). 0.1.0 yanked. |
| `@sentisift/client` (Node SDK) | 0.1.3 | https://www.npmjs.com/package/@sentisift/client | Live. License: MIT (changed from custom-restrictive in 0.1.3). 0.1.0 deprecation pending (see RELEASE_RUNBOOK.md section 0.5). |
| `sentisift-mcp` (MCP server) | 0.1.3 | https://pypi.org/project/sentisift-mcp/ | Live. License: MIT (changed from Proprietary in 0.1.3). 0.1.0 yanked. |

## Endpoint coverage matrix

SDK methods and MCP tools that map to API endpoints. When a new endpoint is added to the API, this table and every listed artifact must be updated in the same commit.

| API endpoint | Python method | Node method | MCP tool | Covered |
|---|---|---|---|---|
| `POST /api/v1/analyze` | `client.analyze(...)` | `client.analyze(...)` | `analyze_comments` | Yes |
| `GET /api/v1/usage` | `client.get_usage()` | `client.getUsage()` | `get_balance` | Yes |
| `GET /api/v1/results` | `client.get_results(...)` | `client.getResults(...)` | `get_article_results` | Yes |
| `GET /api/v1/health` | `client.get_health()`, `client.wait_until_ready()` | `client.getHealth()`, `client.waitUntilReady()` | `get_health` | Yes |
| `GET /api/v1/plans` | Not exposed | Not exposed | Not exposed | Deliberately skipped (public, low-traffic, only the pricing page uses it) |
| `POST /api/v1/billing/signup` | Not exposed | Not exposed | Not exposed | Human-only (Cloudflare Turnstile blocks programmatic use) |
| `POST /api/v1/billing/handshake` | Not exposed | Not exposed | Not exposed | Browser-only (Tranzila Hosted Fields required) |
| `POST /api/v1/billing/complete` | Not exposed | Not exposed | Not exposed | Browser-only |
| `POST /api/v1/billing/paypal-subscribe` | Not exposed | Not exposed | Not exposed | Browser-only (PayPal JS SDK required) |

If you add a new customer-facing endpoint to the API, update all three artifacts in the same commit and add a row here. The MCP server is a thin wrapper over the Python SDK: bumping the Python SDK version automatically makes the new method available for the MCP server to expose (you still need to add the `@mcp.tool` decorator explicitly).

## Supported platforms

| Package | Minimum | Tested on |
|---|---|---|
| `sentisift` (Python) | 3.9 | 3.9, 3.10, 3.11, 3.12 |
| `@sentisift/client` (Node) | 18 | 18 (LTS), 20 (LTS) |
| `sentisift-mcp` | Python 3.10 | 3.10, 3.11, 3.12, 3.13 (MCP protocol requires 3.10+) |

## Dependencies

| Package | Runtime dependencies | Rationale |
|---|---|---|
| `sentisift` | `httpx`, `pydantic` | Modern HTTP, typed responses. sync+async in one lib. |
| `@sentisift/client` | (none - built-in `fetch`) | Zero runtime dependencies on Node 18+. |
| `sentisift-mcp` | `fastmcp`, `sentisift` | Thin wrapper. All HTTP and retries delegated to the Python SDK. |

## Known divergences (artifacts vs API)

None as of 0.1.1. All three packages mirror every customer-facing endpoint with consistent semantics. The `HealthResponse.progress` schema mismatch that affected 0.1.0 was fixed in 0.1.1.

## Release history

### 0.1.3 (2026-04-19)

License switch: SDK source code is now MIT-licensed (was custom proprietary in 0.1.2 and earlier). Aligns with industry default for B2B API client libraries (Stripe, OpenAI, Anthropic, Twilio). Removes evaluation friction for corporate procurement filters and improves directory scores (Glama, etc.). The API service itself is unchanged and remains governed by sentisift.com/terms.html.

### 0.1.2 (2026-04-18)

First release from the new public `pickel-fintech/sentisift-sdks` repo (the SDKs were split out of the private monorepo). Only change: package metadata `Repository` URL now points at the public repo so PyPI/npm "Repository" links work for visitors. No functional changes to any of the three packages.

### 0.1.1 (2026-04-18)

Patch release fixing a `HealthResponse.progress` schema mismatch in both Python and Node SDKs. The live API returns `progress` as a structured `{current, total, scorer_name}` object; both SDKs incorrectly modeled it as a single number, causing `get_health()` / `getHealth()` to crash with a validation error. Also added the previously-undeclared `model_name`, `model_version`, `load_time`, and `error` fields as typed first-class fields. MCP server bumped to require the fixed Python SDK (`sentisift>=0.1.1`).

### 0.1.0 (2026-04-18) — yanked

First public release for all three packages. Python and Node SDKs cover the four customer endpoints with retries, typed exceptions, and typed responses. MCP server exposes those same endpoints as four MCP tools (`analyze_comments`, `get_balance`, `get_health`, `get_article_results`). Yanked from PyPI on 2026-04-18 due to the `HealthResponse.progress` schema bug; use 0.1.1.

Per-package changelogs:
- [Python CHANGELOG](./python/CHANGELOG.md)
- [Node CHANGELOG](./node/CHANGELOG.md)
- [MCP CHANGELOG](./mcp/CHANGELOG.md)

## Planned next

- 0.2.0: integration tests against a live test API key (requires a GitLab CI secret).
- 0.3.0: Python async variant (`AsyncSentiSift`) using `httpx.AsyncClient`.
- Eventually 1.0.0: API commits to stability (post-10-customer milestone).
