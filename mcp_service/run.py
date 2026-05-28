from __future__ import annotations

from mcp_server import mcp


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8010,
        path="/mcp",
    )
