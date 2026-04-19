# Changelog

All notable changes to the `sentisift` Python SDK are documented here.

This project follows [Semantic Versioning](https://semver.org/). Before 1.0.0, minor-version bumps may include breaking changes; patch versions are always backward-compatible.

## [0.1.3] - 2026-04-19

### Changed

- Switched the SDK license from a custom proprietary license to standard **MIT** (matches industry default for B2B API client libraries: Stripe, OpenAI, Anthropic, Twilio, etc.). The SentiSift API service itself is unchanged and remains governed by https://sentisift.com/terms.html. No code changes in this release.

## [0.1.2] - 2026-04-18

### Changed

- Package metadata `Repository` URL now points at the new public repo: https://gitlab.com/pickel-fintech/sentisift-sdks (was: a private repo URL that returned 404 for visitors clicking through from PyPI). No code changes.

## [0.1.1] - 2026-04-18

### Fixed

- `get_health()` raised `pydantic.ValidationError` against the live API because `progress` was modeled as `Optional[float]` but the service actually returns a structured `{current, total, scorer_name}` object. Replaced with a new `Progress` model. Also added the previously-undeclared fields (`model_name`, `model_version`, `load_time`, `error`) so they are typed first-class on `HealthResponse`.

## [0.1.0] - 2026-04-18

### Added

- First public release.
- `SentiSift` client with automatic retries on HTTP 429 (honors `Retry-After`) and 503 (models loading).
- `analyze()`: submit a batch of comments plus article metadata; returns a typed `BufferedResponse` or `ProcessedResponse`.
- `get_usage()`: balance, grants, subscription state, feature flags, influence stats.
- `get_results()`: retrieve already-processed results for an article URL.
- `get_health()` and `wait_until_ready()` for service readiness probing.
- Typed exception hierarchy (`SentiSiftError`, `SentiSiftAuthError`, `SentiSiftValidationError`, `SentiSiftRateLimitError`, `SentiSiftServiceLoadingError`, `SentiSiftServerError`) with `docs_url` and `request_id` exposed on every instance.
- Pydantic v2 response models with `extra="allow"` for forward compatibility.
- User-Agent header identifies the SDK version for API-side analytics.
- Unit tests via pytest + respx covering success paths, error paths, retries, and header propagation.
