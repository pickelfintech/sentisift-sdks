# SDK Release Checklist (Engineering Detail)

This is the dev-facing line-by-line checklist. Tom does not run this by hand; the AI assistant in Cursor follows the higher-level `RELEASE_RUNBOOK.md` and uses this file as the detailed reference for what each step covers.

If they conflict, **the runbook wins** (it captures lessons learned from the first release; this checklist was written before then).

**The invariant:** OpenAPI, HTML docs, and both SDKs must all say the same thing. One source of truth (OpenAPI), three derived artifacts (HTML/MD docs, Python SDK, Node SDK).

## When to follow this checklist

| Change | Action |
|---|---|
| Bugfix in an SDK that does not touch the API | Patch bump (`0.1.0 → 0.1.1`). Skip API / docs steps. |
| New optional field in a response | Minor bump (`0.1.0 → 0.2.0` pre-1.0, `1.2.0 → 1.3.0` post-1.0). Update OpenAPI and docs. SDKs usually already forward-compatible. |
| New endpoint | Minor bump. Update OpenAPI, docs, and both SDKs. |
| New required field, removed field, changed response shape | Major bump (`0.1.0 → 0.2.0` pre-1.0, `1.x → 2.0.0` post-1.0). Update everything. Flag in CHANGELOG. |

## Checklist

Pre-flight:
- [ ] Work on a branch, not on `main`.
- [ ] Pick the new version number now. Semver only.

API (if touching the API itself):
- [ ] Update the route in `api_service/routes.py` (or wherever).
- [ ] Update `api_service/routes.py` `_DOCS_SECTIONS` or `_REQUEST_DEEP_ANCHORS` if new error paths were added.

OpenAPI spec (single source of truth):
- [ ] Update `marketing/website/public/openapi.json` to match the new API surface exactly.
- [ ] Validate JSON: `python3 -c "import json; json.load(open('marketing/website/public/openapi.json'))"`
- [ ] Update the example values and descriptions.

HTML and Markdown docs (narrative source of truth):
- [ ] Update `marketing/website/public/api-docs.html` (English).
- [ ] Update `marketing/website/public/api-docs_he.html` (Hebrew mirror).
- [ ] Update `marketing/website/public/api-docs.md` (machine-friendly mirror).
- [ ] Update `marketing/website/public/llms.txt` if the change affects agent guidance.
- [ ] Update `marketing/website/public/AGENTS.md` if integration conventions change.

Python SDK:
- [ ] Update `python/src/sentisift/_models.py` for new or changed response fields.
- [ ] Update `python/src/sentisift/_client.py` for new or changed methods.
- [ ] Update `python/src/sentisift/__init__.py` exports if new types are public.
- [ ] Update `python/src/sentisift/_version.py` to the new version.
- [ ] Update `python/pyproject.toml` `version` to the new version (must match `_version.py`).
- [ ] Update `python/CHANGELOG.md` with a new entry describing the change.
- [ ] Update `python/README.md` examples if the public API changed.
- [ ] Add or update tests in `python/tests/`. Cover the happy path, at least one error path, and anything breaking.
- [ ] Run: `cd python && pytest tests/ -v`
- [ ] Run: `cd python && ruff check src tests`

Node SDK:
- [ ] Update `node/src/types.ts` for new or changed response shapes.
- [ ] Update `node/src/client.ts` for new or changed methods.
- [ ] Update `node/src/index.ts` exports if new types are public.
- [ ] Update `node/src/version.ts` to the new version.
- [ ] Update `node/package.json` `version` to the new version (must match `version.ts`).
- [ ] Update `node/CHANGELOG.md` with a new entry.
- [ ] Update `node/README.md` examples if the public API changed.
- [ ] Add or update tests in `node/tests/`.
- [ ] Run: `cd node && npx tsc --noEmit && npx vitest run`
- [ ] Run: `cd node && npx tsup src/index.ts --format cjs,esm --dts --clean` (build must succeed)

MCP server (only if the API change is customer-facing, i.e. added/changed an endpoint the MCP server exposes):
- [ ] Update the Python SDK first (above). The MCP server depends on it.
- [ ] Add/update the `@mcp.tool` function in `mcp/src/sentisift_mcp/server.py` if a new endpoint is being exposed. Follow the existing pattern: docstring (shown to the LLM), Annotated[] parameter descriptions.
- [ ] Update `mcp/src/sentisift_mcp/_version.py` to the new MCP version.
- [ ] Update `mcp/pyproject.toml` `version` (must match `_version.py`).
- [ ] If the new feature needs a higher Python SDK version, bump the dependency pin in `pyproject.toml`: `sentisift>=0.X,<1.0`.
- [ ] Update `mcp/CHANGELOG.md` with a new entry.
- [ ] Update `mcp/README.md` "Tools exposed" table and example prompts if a new tool was added.
- [ ] Add or update tests in `mcp/tests/`. At minimum: verify the new tool delegates correctly and surfaces errors.
- [ ] Run: `cd mcp && pytest tests/ -v`

Cross-cutting:
- [ ] Update `OVERVIEW.md` endpoint coverage matrix if you added an endpoint.
- [ ] Update `OVERVIEW.md` "Published versions" line after publish.

Dashboard and emails (if SDK install paths changed):
- [ ] `api_service/templates/dashboard/account.html` shows install commands; update if the package name or install syntax changed.
- [ ] `api_service/payment_routes.py` welcome email mentions the SDKs in the Next Steps list.

Commit:
- [ ] Commit all the above in ONE commit with a message like `release: API + SDKs v0.2.0 - add foo endpoint`.
- [ ] Push to your branch and open an MR. Let CI run.
- [ ] Merge to `main` after review.

Tag and publish (CI does the rest):
- [ ] On `main`, create the tags:
  ```bash
  git tag py-v0.2.0
  git tag node-v0.2.0
  git tag mcp-v0.2.0   # only if MCP server also changed
  git push --tags
  ```
- [ ] Watch GitLab CI pipelines. `sdk-python-publish`, `sdk-node-publish`, and `sdk-mcp-publish` (if tagged) should go green.
- [ ] Verify on PyPI: https://pypi.org/project/sentisift/
- [ ] Verify on PyPI: https://pypi.org/project/sentisift-mcp/ (if released)
- [ ] Verify on npm: https://www.npmjs.com/package/@sentisift/client

Post-flight:
- [ ] Announce the release in CHANGELOG.md at the repo root (if we have one) or in team chat.
- [ ] If this was a breaking change, email existing customers using the SDK (we can find them via User-Agent logs in `usage_logs`).

## Accounts and one-time setup (already done as of 2026-04-18)

This section is historical. All of the below was completed during the first release. If you ever rebuild this from scratch, follow the procedure in `RELEASE_RUNBOOK.md` section 1 (Current state of the world), which has the corrected, learned-the-hard-way version.

Key corrections vs. original guidance:

- npm token MUST be a **Granular Access Token with `Bypass 2FA when publishing` enabled**, not a Classic Automation token. Classic tokens stopped bypassing 2FA in late 2024.
- PyPI Trusted Publishers MUST have **distinct environment names per project** (we use `publish-pypi` for `sentisift` and `publish-pypi-mcp` for `sentisift-mcp`). Blank or shared environments cause the OIDC mint to match the wrong publisher and twine fails with 403.
- The release tag patterns (`py-v*`, `mcp-v*`, `node-v*`) MUST be added as **Protected tags** in GitLab (Settings -> Repository -> Protected tags). Without this, the masked `NPM_TOKEN` is invisible on tag-triggered jobs and `npm publish` fails with 401.

## Emergency rollback

If a published SDK version breaks customers in the wild:

Python (PyPI):
- PyPI does not allow deleting versions that have been downloaded. Instead, **publish a patch** that reverts the problematic change, e.g. `0.2.1` that behaves like `0.1.9`.
- Optionally yank the bad version (makes it un-resolvable by `pip install sentisift` without a pin) via the PyPI UI or `twine yank sentisift==0.2.0 --reason "...`.

npm:
- Deprecate the bad version: `npm deprecate @sentisift/client@0.2.0 "Use 0.2.1+, this version has bug X"`.
- Or unpublish within 72 hours: `npm unpublish @sentisift/client@0.2.0`. Rarely used.
- Publish a patch fix.

Both:
- Update CHANGELOG with a "Yanked" or "Deprecated" note.
- Email affected customers (find them via User-Agent logs).
