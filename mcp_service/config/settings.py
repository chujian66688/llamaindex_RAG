import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    LOG_DIR: Path = PROJECT_ROOT / "file"

    MODEL: str = "qwen-flash-character-2026-02-26"  # os.getenv("DASHSCOPE_MODEL", "qwen-plus")
    TEMPERATURE: float = float(os.getenv("MODEL_TEMPERATURE", "0.1"))

    RAG_API_HOST: str = os.getenv("RAG_API_HOST", "127.0.0.1")
    RAG_API_PORT: int = int(os.getenv("RAG_API_PORT", "8011"))
