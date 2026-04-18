# Changelog

All notable changes to the `sentisift-mcp` package are documented here.

This project follows [Semantic Versioning](https://semver.org/). Before 1.0.0, minor-version bumps may include breaking changes; patch versions are always backward-compatible.

## [0.1.2] - 2026-04-18

### Changed

- Package metadata `Repository` URL now points at the new public repo: https://gitlab.com/pickel-fintech/sentisift-sdks (was: a private repo URL that returned 404 for visitors clicking through from PyPI). No code changes; `sentisift` dependency pin remains `>=0.1.1,<1.0` (also accepts the new 0.1.2).

## [0.1.1] - 2026-04-18

### Fixed

- Bumped `sentisift` dependency to `>=0.1.1,<1.0` so the MCP server picks up the `get_health` schema fix. The `get_health` tool exposed via MCP previously crashed with a `pydantic.ValidationError` because the SDK modeled `progress` as a float when the API returns a structured object. Custom `User-Agent` updated to `sentisift-mcp/0.1.1`.

## [0.1.0] - 2026-04-18

### Added

- First public release.
- Model Context Protocol (MCP) server exposing the SentiSift API to Claude Desktop, Cursor, VS Code, Continue, and other MCP-compatible hosts.
- Four tools:
  - `analyze_comments` - submit a batch of comments and article metadata, receive moderated results (buffered or processed).
  - `get_balance` - current balance, tier, grants, subscription, influence stats.
  - `get_health` - service readiness probe (ready vs loading).
  - `get_article_results` - historical scored comments for an article URL.
- Thin wrapper over the `sentisift` Python SDK (all HTTP, retry, and typed-response logic delegates to the SDK; this package just maps tools to client methods).
- Custom `User-Agent` header (`sentisift-mcp/0.1.0`) so MCP traffic can be distinguished from direct SDK traffic in server-side usage logs.
- Pre-flight check: server exits with a clear message if `SENTISIFT_API_KEY` is not set, so the host surfaces the error in its UI immediately.
- Unit tests covering each tool, error surfacing, and the client singleton behavior.
