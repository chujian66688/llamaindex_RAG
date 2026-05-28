import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """langgraph_service 配置。"""

    PROJECT_ROOT: Path = Path(__file__).parent.parent

    API_KEY: Optional[str] = os.getenv("DASHSCOPE_API_KEY")
    API_BASE_URL: Optional[str] = os.getenv("DASHSCOPE_BASE_URL")
    MODEL: str = "qwen-flash-character-2026-02-26"  # os.getenv("DASHSCOPE_MODEL", "qwen-plus")
    TEMPERATURE: float = float(os.getenv("MODEL_TEMPERATURE", "0.1"))

    POSTGRES_URL: str = os.getenv(
        "POSTGRES_URL",
        "postgresql+psycopg://postgres:123456@127.0.0.1:5432/langgraph_agents",
    )
    LANGGRAPH_POSTGRES_DSN: str = os.getenv(
        "LANGGRAPH_POSTGRES_DSN",
        "postgresql://postgres:123456@127.0.0.1:5432/langgraph_agents?sslmode=disable",
    )
    MCP_SERVICE_URL: str = os.getenv("MCP_SERVICE_URL", "http://127.0.0.1:8010/mcp")
