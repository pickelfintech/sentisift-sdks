# Changelog

All notable changes to the `@sentisift/client` Node SDK are documented here.

This project follows [Semantic Versioning](https://semver.org/). Before 1.0.0, minor-version bumps may include breaking changes; patch versions are always backward-compatible.

## [0.1.2] - 2026-04-18

### Changed

- `package.json` `repository.url` now points at the new public repo: https://gitlab.com/pickel-fintech/sentisift-sdks (was: a private repo URL that returned 404 for visitors clicking through from npm). No code changes.

## [0.1.1] - 2026-04-18

### Fixed

- `getHealth()` returned a typed object whose `progress` field was declared as `number` but the live API returns a structured `{current, total, scorer_name}` object. Replaced with a new `Progress` interface and added the previously-undeclared `model_name`, `model_version`, `load_time`, and `error` fields so they are typed first-class on `HealthResponse`. Index signature retained for forward compatibility.

## [0.1.0] - 2026-04-18

### Added

- First public release.
- `SentiSift` client with automatic retries on HTTP 429 (honors `Retry-After`) and 503 (models loading).
- `analyze()`: submit a batch of comments plus article metadata; returns a typed `BufferedResponse | ProcessedResponse` discriminated union.
- `getUsage()`: balance, grants, subscription state, feature flags, influence stats.
- `getResults()`: retrieve already-processed results for an article URL.
- `getHealth()` and `waitUntilReady()` for service readiness probing.
- Typed exception hierarchy (`SentiSiftError`, `SentiSiftAuthError`, `SentiSiftValidationError`, `SentiSiftRateLimitError`, `SentiSiftServiceLoadingError`, `SentiSiftServerError`) with `docsUrl` and `requestId` exposed on every instance.
- Full TypeScript types for request and response shapes with index signatures for forward compatibility.
- Dual-module build (CJS + ESM) via tsup.
- User-Agent header identifies the SDK version for API-side analytics.
- Unit tests via vitest covering success paths, error paths, retries, and header propagation.
