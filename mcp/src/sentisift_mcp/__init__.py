"""SentiSift MCP server.

Exposes the SentiSift comment-moderation and intelligence API as native
tools for MCP-compatible AI hosts (Claude Desktop, Cursor, VS Code,
Continue, and others).

Entry point:
    sentisift-mcp   (console script, reads SENTISIFT_API_KEY from env)

See README.md for integration instructions for each supported host.
"""
from sentisift_mcp._version import __version__
from sentisift_mcp.server import main, mcp

__all__ = ["__version__", "main", "mcp"]
