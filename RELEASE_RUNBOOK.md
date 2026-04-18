# SDK Release Runbook (AI-Assistant-Driven)

**Audience:** the AI coding assistant in Cursor (you, future-me) when Tom asks for a release.

**Purpose:** Tom is not a release engineer. He asks for a release in plain English; you (the AI) own the procedure end-to-end. This runbook tells you exactly what to do, what to ask Tom for, and how to recover from the failures we already debugged.

For the deeper dev-facing checklist, see `RELEASE_CHECKLIST.md`. This runbook supersedes any guidance in that checklist where they conflict (the checklist was written before we did the first release; this runbook captures lessons learned).

---

## 0. Read this first

Tonight (2026-04-18) we did the first public release. We hit and fixed many issues. The procedure now WORKS, but it's fragile in known places. Treat this runbook as the truth and follow it literally.

---

## 0.5 Pending cleanup tasks from previous releases

These are items that were deferred because they weren't blocking. Handle them as part of the next relevant release so they don't pile up.

| Task | When | How |
|---|---|---|
| Deprecate `@sentisift/client@0.1.0` on npm | At the same time as the next Node SDK release (`node-v0.1.2` or later) | After the new version publishes successfully, while you still have a fresh `NPM_TOKEN` with Bypass-2FA active in CI: have Tom run `npm deprecate "@sentisift/client@0.1.0" "Use 0.1.1+ - this version has a HealthResponse schema bug"` from his laptop using a temporarily-installed Granular Token (procedure: generate token via web UI, write only that token to `~/.npmrc` with full backup-and-restore of the original, run deprecate, restore). Or — cleaner — add a one-shot `npm-deprecate-0.1.0` job to `.gitlab-ci.yml` that runs on the next `node-v*` tag and uses the same `NPM_TOKEN` GitLab variable. After 0.1.0 is deprecated, **remove this row from the table**. |

When you finish a deferred task, delete its row. When you defer a new task, add a row.

---

## 1. Current state of the world

### Published packages

| Package | Registry | Latest | URL |
|---|---|---|---|
| `sentisift` | PyPI | 0.1.1 | https://pypi.org/project/sentisift/ |
| `sentisift-mcp` | PyPI | 0.1.1 | https://pypi.org/project/sentisift-mcp/ |
| `@sentisift/client` | npm | 0.1.1 | https://www.npmjs.com/package/@sentisift/client |

### CI / publish infrastructure

- **GitLab project:** `pickel-fintech/sentisift` on gitlab.com.
- **Pipeline file:** `.gitlab-ci.yml` at the repo root. Tag patterns trigger publishing:
  - `py-vX.Y.Z` -> publishes `sentisift` to PyPI.
  - `mcp-vX.Y.Z` -> publishes `sentisift-mcp` to PyPI.
  - `node-vX.Y.Z` -> publishes `@sentisift/client` to npm.
- **All three tag patterns are `Protected`** in GitLab Settings -> Repository -> Protected tags (Maintainers can create). This is required so the masked `NPM_TOKEN` becomes visible on tag-triggered jobs.
- **PyPI publishing uses Trusted Publishers (OIDC, no token).** Configured at https://pypi.org/manage/project/{sentisift,sentisift-mcp}/settings/publishing/. Critical detail:
  - `sentisift` requires `Environment name: publish-pypi`.
  - `sentisift-mcp` requires `Environment name: publish-pypi-mcp` (DIFFERENT - they MUST differ, otherwise the OIDC mint matches both publishers and may pick the wrong one, causing twine 403).
  - Our CI sets `environment.name: publish-pypi` on `sdk-python-publish` and `environment.name: publish-pypi-mcp` on `sdk-mcp-publish`. Do not change these.
- **npm publishing uses an `NPM_TOKEN` CI variable** (Granular Access Token with `Bypass 2FA when publishing` enabled, `@sentisift` scope read-write). Token expires every 90 days max. Renewal procedure is in section 8 of this runbook AND in Tom's calendar.
- **OIDC mint endpoint pattern (PyPI):** the publish jobs call `https://pypi.org/_/oidc/mint-token` with the `$PYPI_ID_TOKEN` env var as the JWT (NOT `cat`'d as a file - this is a GitLab-vs-GitHub difference). The mint is done in Python via `urllib` because the slim Docker image has no curl. Don't "improve" this with curl.

### Recovery from common first-time pitfalls

These are what we hit tonight. If a publish fails for any of these reasons, the fix is in the listed section:

| Symptom | Cause | Fix |
|---|---|---|
| `cat: [MASKED]: File name too long` | Treating `$PYPI_ID_TOKEN` as a file path | Already fixed in `.gitlab-ci.yml` |
| `curl: command not found` | Slim image has no curl | Already fixed (use Python urllib) |
| `403 Forbidden` from `upload.pypi.org` after successful OIDC mint | Two publishers with overlapping claims | Ensure mcp uses `publish-pypi-mcp` env (already configured) |
| `403 Forbidden ... Two-factor authentication or granular access token` (npm) | Using a Classic Automation token | Use a Granular Access Token with `Bypass 2FA when publishing` |
| `[remote rejected] py-v0.1.X (pre-receive hook declined)` on tag delete | Protected tag, can't delete from CLI | Delete via web UI: `https://gitlab.com/pickel-fintech/sentisift-sdks/-/tags` -> trash icon |
| `pip index versions` shows old version after publish | pip's local index cache | Use `pip index versions <pkg> --no-cache-dir` or `curl https://pypi.org/pypi/<pkg>/json` |

---

## 2. When Tom asks for a release

### Trigger phrases to recognize

Tom will say something like one of these:

- "Release a new version of the SDK with X."
- "Ship 0.2.0 with the new endpoint."
- "Cut a patch release - the Node SDK has a bug."
- "I changed the API; update everything and publish."

When you see this kind of request, this runbook is your roadmap.

### Things to confirm with Tom before starting (one short message)

Always ask these THREE questions in one batch (not one at a time):

1. **What changed?** (so you know which SDKs are affected and what the version bump should be)
2. **What version number?** (default to a semver patch bump if it's a bugfix; minor bump if it's a new endpoint or new optional field; major bump if it's a breaking change. Pre-1.0 follows the same logic but bumps minor for breaking changes. Suggest the version to Tom and have him confirm.)
3. **Should we yank the previous version?** (default no; yes only if the previous version is dangerously broken)

After Tom confirms, do the work. Do not ask for confirmation on every micro-step.

---

## 3. The standard release procedure

### Step 1: Decide scope

For each package, decide: does this release ship a new version of it?

| If you changed... | Bump |
|---|---|
| `python/src/...` or anything that affects `sentisift` | Yes -> bump Python |
| `node/src/...` or anything that affects `@sentisift/client` | Yes -> bump Node |
| `mcp/src/...` OR you bumped `sentisift` and want MCP to use the new one | Yes -> bump MCP |
| Only website docs, OpenAPI, API service code (no SDK code) | No SDK release; just commit + push, then re-upload openapi.json etc. |

### Step 2: Code changes (the surgical edits)

Per package being bumped:

- Update version in **all** of these places (use the search in section 2.5 to confirm you got them):
  - **Python:** `python/pyproject.toml` (`version = "..."`) and `python/src/sentisift/_version.py` (`__version__`).
  - **Node:** `node/package.json` (`"version"`) and `node/src/version.ts` (`SDK_VERSION`). Then **regenerate the lockfile** so it matches: `cd node && npm install --package-lock-only --no-audit --no-fund` (otherwise `package-lock.json` stays at the old version even though it's not in the published tarball - it's still in the repo and confuses contributors).
  - **MCP:** `mcp/pyproject.toml` and `mcp/src/sentisift_mcp/_version.py`. If the MCP server now requires a newer Python SDK, also bump the dependency line in `pyproject.toml`: `"sentisift>=X.Y.Z,<1.0"`.
- Add a CHANGELOG entry to the package's `CHANGELOG.md`. Format:
  ```
  ## [0.X.Y] - YYYY-MM-DD

  ### Added | Changed | Fixed | Removed | Deprecated
  - One-line description of each change.
  ```
- Update README.md examples that include the version (e.g. pin examples like `^0.1.0`).
- Update `OVERVIEW.md`'s "Published versions" table and append a "Release history" entry.
- Update relevant tests (`python/tests/`, `node/tests/`, `mcp/tests/`).

### Step 2.5: Sweep for stale version references - MANDATORY

**Always run this before tagging.** It catches version strings that hide in places no checklist remembers (READMEs, docs, examples, comments, copy on the website). Past releases (0.1.1) hit this exact gap: User-Agent examples on the live website still claimed the SDK was 0.1.0 after we shipped 0.1.1.

```bash
cd "/Users/tomp/Dropbox/Pickel Fintech/projects/sentisift-sdks"
# Replace OLD with the version you're bumping FROM, NEW with the version you're bumping TO.
OLD=0.1.0
NEW=0.1.1

# 1) Find every reference to the old version, excluding lockfiles and changelogs (those legitimately keep history)
rg --no-heading -n "$OLD" \
  --glob '!**/CHANGELOG.md' \
  --glob '!**/package-lock.json' \
  --glob '!**/node_modules/**' \
  --glob '!**/dist/**' \
  --glob '!**/.cursor/**'

# 2) Manually inspect each hit. For each one, decide:
#    (a) Update to $NEW
#    (b) Replace with a version-agnostic placeholder like <version> or X.Y.Z
#    (c) Leave (e.g. historical context, semver examples, yanked-version notes)
```

The default action is (b) for any *example* (pin examples in READMEs, User-Agent demos, recipe code). Hardcoding a version into example text guarantees drift on the next bump. Use placeholders so future bumps don't require touching the doc.

### Step 2.6: Re-grep after the bump - MANDATORY

After all version bumps and the sweep above, grep for the NEW version too. Any package's `pyproject.toml` / `package.json` / `_version.py` / `version.ts` / `package-lock.json` should appear; if anything else *outside that list* mentions the new version when it shouldn't (e.g. a hardcoded reference that was supposed to be a placeholder), fix it now.

```bash
rg --no-heading -n "$NEW" \
  --glob '!**/CHANGELOG.md' \
  --glob '!**/node_modules/**' \
  --glob '!**/dist/**' \
  --glob '!**/.cursor/**'
```

If the API itself changed:

- Update `marketing/website/public/openapi.json`. Validate it parses: `python3 -c "import json; json.load(open('marketing/website/public/openapi.json'))"`.
- Update `marketing/website/public/api-docs.html` (English) AND `api-docs_he.html` (Hebrew) AND `api-docs.md`.
- Update `marketing/website/public/llms.txt` and `AGENTS.md` if the integration story shifted.
- Update `api_service/routes.py` `_DOCS_SECTIONS` and `_REQUEST_DEEP_ANCHORS` if new error paths exist that should deep-link.

### Step 3: Run tests locally before tagging

```bash
# Python
cd "/Users/tomp/Dropbox/Pickel Fintech/projects/sentisift-sdks/python"
/tmp/sentisift-sdk-test/bin/pytest tests/ -q

# MCP (if changed)
cd "/Users/tomp/Dropbox/Pickel Fintech/projects/sentisift-sdks/mcp"
/tmp/sentisift-mcp-test/bin/pytest tests/ -q

# Node (if changed)
cd "/Users/tomp/Dropbox/Pickel Fintech/projects/sentisift-sdks/node"
npx vitest run
```

If those venvs don't exist on a fresh machine, recreate them: `python3 -m venv /tmp/sentisift-sdk-test && /tmp/sentisift-sdk-test/bin/pip install -e "python[dev]"` etc.

If tests fail, fix and re-run. Do NOT proceed to commit until tests pass.

### Step 4: Smoke test against the live API (Python only, fastest path)

This catches schema mismatches like the `progress` bug we hit on 0.1.0. Skip only if Tom explicitly says skip.

```bash
rm -rf /tmp/sentisift-smoke
python3 -m venv /tmp/sentisift-smoke
/tmp/sentisift-smoke/bin/pip install --quiet --no-cache-dir "/Users/tomp/Dropbox/Pickel Fintech/projects/sentisift-sdks/python"
cat > /tmp/sentisift_smoke.py <<'EOF'
from sentisift import SentiSift
c = SentiSift()
print("Health:", c.get_health())
print("Balance:", c.get_usage().comment_balance)
EOF
SENTISIFT_API_KEY=<KEY> /tmp/sentisift-smoke/bin/python3 /tmp/sentisift_smoke.py
```

If the smoke test crashes with a `pydantic.ValidationError`, the SDK's models are out of sync with the live API. Fix and re-run.

Tom must give you a key for the smoke test (or you skip with his explicit consent). Free-tier keys work.

### Step 5: Commit

Stage ONLY the files for this release. Do NOT use `git add -A` blindly because Tom often has unrelated edits in the working tree.

```bash
cd "/Users/tomp/Dropbox/Pickel Fintech/projects/sentisift-sdks"
git add \
  python/CHANGELOG.md python/pyproject.toml \
  python/src/sentisift/_version.py \
  python/src/sentisift/_models.py \
  python/src/sentisift/_client.py \
  python/src/sentisift/__init__.py \
  python/tests/test_client.py \
  python/README.md \
  # ... and the equivalent for node + mcp + openapi.json + api-docs files

git commit -m "release: SDK 0.X.Y - <one-line summary>"
git push origin main
```

### Step 6: Tag

For each bumped package, create and push a tag. You can push all tags at once:

```bash
git tag -a py-v0.X.Y -m "sentisift Python SDK v0.X.Y - <summary>"
git tag -a mcp-v0.X.Y -m "sentisift-mcp v0.X.Y - <summary>"     # if mcp bumped
git tag -a node-v0.X.Y -m "@sentisift/client Node SDK v0.X.Y - <summary>"  # if node bumped
git push origin py-v0.X.Y mcp-v0.X.Y node-v0.X.Y                # only push the tags you actually created
```

### Step 7: Watch CI

Tell Tom to refresh `https://gitlab.com/pickel-fintech/sentisift-sdks/-/pipelines` and report green or red. ~3 min per pipeline; pipelines run in parallel.

If a pipeline fails:
1. Ask Tom to click into the failed pipeline -> failed job -> paste the last 30-50 lines of output.
2. Cross-reference the symptom in the table in section 1 ("Recovery from common pitfalls").
3. If the symptom isn't in the table, debug from first principles and ADD a new row to that table after fixing.

### Step 8: Verify on registries

```bash
# PyPI - definitive source (bypasses pip cache)
curl -s https://pypi.org/pypi/sentisift/json | python3 -c "import json,sys; d=json.load(sys.stdin); print('Latest:', d['info']['version'])"
curl -s https://pypi.org/pypi/sentisift-mcp/json | python3 -c "import json,sys; d=json.load(sys.stdin); print('Latest:', d['info']['version'])"

# npm
npm view @sentisift/client@0.X.Y version
```

### Step 9: Re-upload website files (if changed)

If `openapi.json`, `api-docs.html`, `api-docs.md`, `api-docs_he.html`, `AGENTS.md`, or `llms.txt` changed in this release, Tom must re-upload them to the web server. Per the project's deployment-listing rule, give Tom a list at the end of the release in this format:

```
**`marketing/website/public/`**
- `openapi.json` (updated: <reason>)
- `api-docs.html` (updated: <reason>)
- ...
```

### Step 10: Smoke test the published version

After PyPI confirms the new version, repeat Step 4 but install from PyPI instead of the local path:

```bash
rm -rf /tmp/sentisift-smoke
python3 -m venv /tmp/sentisift-smoke
/tmp/sentisift-smoke/bin/pip install --quiet --no-cache-dir sentisift==0.X.Y
SENTISIFT_API_KEY=<KEY> /tmp/sentisift-smoke/bin/python3 /tmp/sentisift_smoke.py
```

If this succeeds, the release is fully verified.

---

## 4. What you (the AI) need from Tom for a smooth release

Ask these all at once at the start. Do not interrogate him.

1. The change description (what's new/fixed/changed).
2. Confirmation of the version bump (you propose, he confirms).
3. A free-tier API key for the smoke test (or "skip smoke test").
4. Whether to yank the previous version (default no).

Then do the work. Only come back to him for:
- Permission to commit (show the staged file list first).
- Permission to push tags (show what tags you'll push).
- Pipeline failures (with the specific log output you need from him).

---

## 5. Format Tom uses to request a release

Tom should paste something like this. If he doesn't, prompt him with the four questions above.

```
Release request:
- What changed: <short description>
- Affected SDKs: [python] [node] [mcp]
- Suggested version: 0.X.Y
- API key for smoke test: sk_sentisift_...
- Yank previous: no
```

---

## 6. Yanking and deprecating broken versions

### PyPI (yank)

Yanking does NOT delete the version. It just makes `pip install pkg` (without a version pin) avoid the yanked version. Existing pinned installs still work.

Done via web UI:
1. Go to https://pypi.org/manage/project/<project>/release/<version>/.
2. Scroll to "Yank release". Provide a one-line reason.
3. Click Yank.

Per package: do this on `sentisift` 0.X.X-broken and `sentisift-mcp` 0.X.X-broken.

### npm (deprecate)

```bash
npm deprecate @sentisift/client@0.X.Y "Use 0.X.(Y+1) - this version has bug ABC"
```

`npm deprecate` requires Tom to be logged in (`npm whoami` confirms). With 2FA on his account, npm will prompt for an OTP - this is fine for one-off deprecations (different from publishing, where we use the `Bypass 2FA` token).

### npm (unpublish, only within 72 hours of publish)

`npm unpublish @sentisift/client@0.X.Y` works for 72 hours after publish. After that, deprecate is the only option.

---

## 7. CHANGELOG conventions

Each package's `CHANGELOG.md` follows Keep-a-Changelog. New entries go at the top, under the package's existing entries.

Section labels: `Added`, `Changed`, `Fixed`, `Removed`, `Deprecated`, `Security`.

Date format: `YYYY-MM-DD`.

Example:

```markdown
## [0.2.0] - 2026-05-15

### Added
- New `analyze_async` method that returns a future for non-blocking workflows.

### Fixed
- `get_results` raised on empty article history; now returns an empty list.
```

---

## 8. npm token renewal (every 90 days)

The Granular Access Token in GitLab CI (`NPM_TOKEN`) expires every 90 days. Tom has a calendar reminder. When that reminder fires, he'll paste a request to you. Procedure:

1. Tell Tom to go to `https://www.npmjs.com/settings/<his-npm-username>/tokens` and click "Generate New Token" -> Granular Access Token.
2. Settings:
   - Token name: `SentiSift_CI_v<N>` (increment `<N>` from the previous one).
   - Expiration: 90 days.
   - **Bypass 2FA when publishing: enabled** (this is critical).
   - Allowed IP ranges: empty.
   - Packages and scopes: `@sentisift` scope, Read and write.
   - Organizations: `sentisift`, Read and write.
3. Tell Tom to copy the token, then go to `https://gitlab.com/pickel-fintech/sentisift-sdks/-/settings/ci_cd` -> Variables -> edit `NPM_TOKEN` -> paste the new value -> save (keep Type=Variable, Environment=*, Masked=yes, Protected=yes).
4. Verify by triggering a small no-op pipeline (push any small commit to main and check `sdk-node-test` passes).
5. Tell Tom to bump the calendar reminder by 90 days.

---

## 9. Things that are NOT your job (escalate to Tom)

- Anything that requires entering the dashboard at sentisift.com or a production database.
- Generating npm tokens (Tom does this in his account).
- PyPI publisher management UI (Tom clicks through).
- Tag deletion from GitLab web UI (protected; Tom does this).
- Decisions about whether a change is breaking or not (Tom decides; you analyze and recommend).
- Any change to billing, email, subscription, or Stripe code unless explicitly part of the release request.

---

## 10. Self-update

If you discover something this runbook should mention (a new failure mode, a procedural improvement, a dependency change), add it to the relevant section in your same response. Do not let Tom be the one to remember.
