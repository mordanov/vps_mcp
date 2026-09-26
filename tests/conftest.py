"""Shared test helpers."""

import os

# Must be set before any module that imports config.py is loaded.
os.environ.setdefault("VPS_HOST", "test-host")
os.environ.setdefault("VPS_USER", "test-user")
os.environ.setdefault("VPS_SSH_KEY", "~/.ssh/test_id_rsa")
os.environ.setdefault("GITHUB_REPO", "")  # most tests override per-call

from unittest.mock import AsyncMock


class FakeMCP:
    """Captures tools registered via @mcp.tool() without starting a real MCP server."""

    def __init__(self) -> None:
        self.tools: dict = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


def make_runner(result: str = "ok") -> AsyncMock:
    """Return an AsyncMock runner that records the last call."""
    return AsyncMock(return_value=result)
