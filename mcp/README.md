# SentiSift MCP Server

Official [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server for [SentiSift](https://sentisift.com). Lets MCP-compatible AI hosts (Claude Desktop, Cursor, VS Code, Continue, and others) call the SentiSift comment-moderation and intelligence API as a native tool.

## What this unlocks

Once installed, your AI assistant can:

- Analyze comments directly in conversation: **"Run these 50 comments through SentiSift and show me the bots and the sentiment distribution."**
- Check your account state: **"What's my SentiSift balance and when does my subscription renew?"**
- Retrieve historical results: **"Show me the sentiment history for yesterday's article on example.com/breaking-news."**
- Self-diagnose service status: **"Is the SentiSift API ready, or are models still loading?"**

No code required. The assistant calls the tools through MCP and reports back.

## Tools exposed

| Tool | Description |
|---|---|
| `analyze_comments` | Submit a batch of comments plus an article URL, receive bot/spam flags, sentiment labels, commercial-content flags, moderation summary, and (on Pro/Enterprise) Intelligence + interleaved Influence comments. |
| `get_balance` | Current comment balance, tier, feature flags, active grants, subscription state, Influence stats. |
| `get_health` | Whether the SentiSift API is ready or still loading models. |
| `get_article_results` | Historical scored comments for an article URL (Pro/Enterprise retain full history; Free/Starter return buffer state only). |

## Install

You need Python 3.10+ and a SentiSift API key. Free keys (1,000 comments, no credit card) at [sentisift.com/pricing](https://sentisift.com/pricing.html).

### Recommended: `uvx` (zero install, always latest)

[uv](https://docs.astral.sh/uv/) runs published Python apps without persistent install. This is the install-free path.

```bash
# One-time: install uv (mac/linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify it works (Ctrl-C after a few seconds; the server is meant to be
# launched by your AI host, not run in a terminal).
SENTISIFT_API_KEY=sk_sentisift_... uvx sentisift-mcp
```

### Alternative: `pip install`

```bash
pip install sentisift-mcp
sentisift-mcp   # run manually to verify
```

## Host configuration

Each AI host has its own config file. Pick yours:

### Claude Desktop

Edit the config file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add the SentiSift entry to `mcpServers`:

```json
{
  "mcpServers": {
    "sentisift": {
      "command": "uvx",
      "args": ["sentisift-mcp"],
      "env": {
        "SENTISIFT_API_KEY": "sk_sentisift_your_key_here"
      }
    }
  }
}
```

Restart Claude Desktop. You should see a new tool indicator in the bottom-left corner of a new chat. Try: "Use SentiSift to check my balance."

### Cursor

Cursor supports MCP via the **Settings** → **MCP Servers** panel. Add:

- **Name:** `sentisift`
- **Command:** `uvx`
- **Arguments:** `sentisift-mcp`
- **Environment variables:** `SENTISIFT_API_KEY=sk_sentisift_your_key_here`

Or edit `~/.cursor/mcp.json` directly with the same structure as the Claude Desktop example above.

### VS Code (with the MCP extension)

Edit your user or workspace `settings.json`:

```json
{
  "mcp.servers": {
    "sentisift": {
      "command": "uvx",
      "args": ["sentisift-mcp"],
      "env": {
        "SENTISIFT_API_KEY": "sk_sentisift_your_key_here"
      }
    }
  }
}
```

### Continue.dev

In `~/.continue/config.json`:

```json
{
  "mcpServers": [
    {
      "name": "sentisift",
      "command": "uvx",
      "args": ["sentisift-mcp"],
      "env": {
        "SENTISIFT_API_KEY": "sk_sentisift_your_key_here"
      }
    }
  ]
}
```

### Any other MCP-compatible host

The server speaks MCP over stdio. Point your host at `uvx sentisift-mcp` (or `sentisift-mcp` if installed via pip) and set `SENTISIFT_API_KEY` in its environment.

## How to talk to the assistant

Once configured, natural-language prompts work. Some examples:

> "Check my SentiSift balance."

> "Run these 20 comments through SentiSift for the article at https://example.com/breaking-story. Here are the comments:" (paste them)

> "Is the SentiSift API ready right now, or is it still loading?"

> "Fetch the processed comments for https://example.com/article-42 from SentiSift."

The assistant chooses the right tool, passes the right arguments, and summarizes the results. If a call fails, the error response includes a deep link to the relevant docs section so the assistant can self-correct.

## Privacy

- The server sends a `User-Agent` header identifying it as `sentisift-mcp/<version>` so we can distinguish MCP traffic from direct SDK traffic in our usage logs. No other telemetry.
- The server runs locally on your machine. It only calls out to `api.sentisift.com`.
- Your API key stays on your machine (in the host's env config). It is never logged to disk by this server.

## Source

Source and issue tracker: [gitlab.com/pickel-fintech/sentisift-sdks](https://gitlab.com/pickel-fintech/sentisift-sdks/-/tree/main/mcp).

## Links

- [SentiSift API docs](https://sentisift.com/api-docs.html)
- [OpenAPI spec](https://sentisift.com/openapi.json)
- [Python SDK](https://pypi.org/project/sentisift/) (this MCP server wraps it)
- [Node SDK](https://www.npmjs.com/package/@sentisift/client)
- [Changelog](CHANGELOG.md)
- [Support](mailto:tom@sentisift.com)

## License

MIT — see [LICENSE](LICENSE). The SentiSift API service that this client
calls is governed separately by [sentisift.com/terms.html](https://sentisift.com/terms.html);
use of the API requires an API key from [sentisift.com/pricing](https://sentisift.com/pricing).
