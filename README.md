# SentiSift SDKs

Official client libraries for the [SentiSift](https://sentisift.com) comment-moderation and intelligence API. Three published packages, all open source for the integration code so developers can read, audit, and contribute.

| Package | Source | Registry | Install |
|---|---|---|---|
| `sentisift` (Python) | [`python/`](python/) | [PyPI](https://pypi.org/project/sentisift/) | `pip install sentisift` |
| `@sentisift/client` (Node/TypeScript) | [`node/`](node/) | [npm](https://www.npmjs.com/package/@sentisift/client) | `npm install @sentisift/client` |
| `sentisift-mcp` (MCP server) | [`mcp/`](mcp/) | [PyPI](https://pypi.org/project/sentisift-mcp/) | `uvx sentisift-mcp` |

## What is SentiSift?

SentiSift filters bots, spam, and noise out of comment sections without silencing real voices. It scores each comment on five independent axes (sentiment, eloquence, length, behavioral patterns, commercial signals) and returns moderation decisions plus crowd-level analytics. On paid tiers, it also contributes constructive perspectives when a discussion skews one-sided ("Influence").

Get a free API key (1,000 comments, no credit card) at [sentisift.com/pricing](https://sentisift.com/pricing.html). Full API reference: [sentisift.com/api-docs.html](https://sentisift.com/api-docs.html).

## Quick start

### Python

```bash
pip install sentisift
```

```python
from sentisift import SentiSift

client = SentiSift()  # reads SENTISIFT_API_KEY from env
result = client.analyze(
    article_url="https://example.com/article/1",
    comments=[
        {"text": "Great article!", "author": "alice", "time": "2026-04-18T10:00:00"},
    ],
)
```

### Node / TypeScript

```bash
npm install @sentisift/client
```

```typescript
import { SentiSift } from "@sentisift/client";

const client = new SentiSift();
const result = await client.analyze({
  articleUrl: "https://example.com/article/1",
  comments: [{ text: "Great article!", author: "alice", time: "2026-04-18T10:00:00" }],
});
```

### MCP (Claude Desktop, Cursor, VS Code, Continue)

```bash
uvx sentisift-mcp     # one-shot run via uv
# or
pip install sentisift-mcp     # then add to your MCP host's config
```

Then add the SentiSift entry to your host's MCP config (Claude Desktop's `claude_desktop_config.json`, Cursor's `~/.cursor/mcp.json`, VS Code's `settings.json`, etc.). See [`mcp/README.md`](mcp/README.md) for host-specific snippets.

## Repository layout

```
.
├── python/                Python SDK (sentisift on PyPI)
├── node/                  Node SDK (@sentisift/client on npm)
├── mcp/                   MCP server (sentisift-mcp on PyPI)
├── OVERVIEW.md            Endpoint coverage matrix, supported platforms, release history
├── RELEASE_RUNBOOK.md     AI-driven release procedure (read this for any version bump)
├── RELEASE_CHECKLIST.md   Engineering line-by-line checklist
└── .gitlab-ci.yml         CI: tests on every push; publishes on tag push
```

## Versioning

All three packages follow [Semantic Versioning](https://semver.org/). Pre-1.0 minor versions may include breaking changes. Per-package CHANGELOG.md files document every release.

## Contributing

Bug reports and feature requests welcome via [issues](https://gitlab.com/pickel-fintech/sentisift-sdks/-/issues). For pull requests, please open an issue first to discuss the change.

## Architecture

The full SentiSift API service (auth, billing, scoring pipeline, scrapers) lives in a separate private repository. This public repository contains only the client-facing packages and their integration code, OpenAPI-derived models, and tests.

Documentation is hosted on [sentisift.com](https://sentisift.com):
- HTML reference: [api-docs.html](https://sentisift.com/api-docs.html)
- LLM-friendly Markdown mirror: [api-docs.md](https://sentisift.com/api-docs.md)
- OpenAPI 3.1 spec: [openapi.json](https://sentisift.com/openapi.json)
- AI-agent integration guide: [AGENTS.md](https://sentisift.com/AGENTS.md)
- llmstxt.org index: [llms.txt](https://sentisift.com/llms.txt)

## License

The published SDK packages are MIT-equivalent for usage (see each package's `package.json` / `pyproject.toml` `license` field). Repository code is owned by Pickel Fintech; see [LICENSE](LICENSE) for the full text and [sentisift.com/terms.html](https://sentisift.com/terms.html) for the API terms of service.

## Contact

- General: [tom@sentisift.com](mailto:tom@sentisift.com)
- Customer support: [support@sentisift.com](mailto:support@sentisift.com)
- Issues: [GitLab issues](https://gitlab.com/pickel-fintech/sentisift-sdks/-/issues)
