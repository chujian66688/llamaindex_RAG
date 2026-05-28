import json
from typing import Any

from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langmem import create_manage_memory_tool, create_search_memory_tool
from mcp import ClientSession

from config.settings import Settings

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except ImportError:
    MultiServerMCPClient = None


from mcp.client.streamable_http import streamable_http_client


async def _call_via_langchain(tool_name: str, arguments: dict[str, Any]) -> Any:
    if MultiServerMCPClient is None:
        raise ImportError("langchain-mcp-adapters is not installed")

    client = MultiServerMCPClient(
        {
            "rag": {
                "transport": "streamable_http",
                "url": Settings.MCP_SERVICE_URL,
            }
        }
    )
    tools = await client.get_tools()
    tool_map = {tool.name: tool for tool in tools}
    if tool_name not in tool_map:
        raise ValueError(f"MCP tool not found: {tool_name}")
    return await tool_map[tool_name].astream(arguments)


async def _call_via_mcp(tool_name: str, arguments: dict[str, Any]) -> Any:
    async with streamable_http_client(Settings.MCP_SERVICE_URL) as (read, write, *_):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if hasattr(result, "structuredContent") and result.structuredContent:
                return result.structuredContent
            if hasattr(result, "content") and result.content:
                first = result.content[0]
                text = getattr(first, "text", str(first))
                try:
                    return json.loads(text)
                except Exception:
                    return text
            return result


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    try:
        return await _call_via_langchain(tool_name, arguments)
    except Exception:
        return await _call_via_mcp(tool_name, arguments)


# 初始化 Tavily 搜索工具
tavily_search = TavilySearch(
    max_results=5,
    topic="general",
)


@tool
def web_search(query: str) -> str:
    """搜索互联网上的公开信息，用于知识库不足时补充事实。"""
    try:
        results = tavily_search.invoke({"query": query})
        # 格式化搜索结果
        if isinstance(results, dict):
            # TavilySearch 返回格式
            search_results = results.get("results", [])
            if search_results:
                formatted = []
                for i, result in enumerate(search_results[:5], 1):
                    title = result.get("title", "")
                    url = result.get("url", "")
                    content = result.get("content", "")
                    formatted.append(f"{i}. {title}\n   链接: {url}\n   摘要: {content}")
                return "\n\n".join(formatted)
            return "未找到相关搜索结果"
        elif isinstance(results, str):
            return results
        else:
            return str(results)
    except Exception as e:
        return f"搜索出错: {str(e)}"


# ==============================
# langmem 长期记忆工具
# ==============================
# 使用官方 langmem 工具实现长期记忆
# namespace 支持按用户隔离：("memories", "{user_id}")
memory_tools = [
    create_manage_memory_tool(namespace=("memories", "{user_id}")),
    create_search_memory_tool(namespace=("memories", "{user_id}")),
]
