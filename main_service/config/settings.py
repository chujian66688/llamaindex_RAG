import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """main_service 配置。"""

    PROJECT_ROOT: Path = Path(__file__).parent.parent
    LOG_DIR: Path = PROJECT_ROOT / "file"

    POSTGRES_URL: str = os.getenv(
        "POSTGRES_URL",
        "postgresql+psycopg://postgres:123456@127.0.0.1:5432/langgraph_agents",
    )
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me-in-env")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    MODEL: str = "qwen-flash-character-2026-02-26"  # os.getenv("DASHSCOPE_MODEL", "qwen-plus")
    LANGGRAPH_API_URL: str = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:2024")
    LANGGRAPH_ASSISTANT_ID: str = os.getenv("LANGGRAPH_ASSISTANT_ID", "multi_agent")
    MCP_SERVICE_URL: str = os.getenv("MCP_SERVICE_URL", "http://127.0.0.1:8010/mcp")
    RAG_API_URL: str = os.getenv("RAG_API_URL", "http://127.0.0.1:8011/api/docs")
