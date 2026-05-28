import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


PROJECT_ROOT = Path(__file__).parent.parent


class Settings:
    PROJECT_ROOT: Path = PROJECT_ROOT
    LOG_DIR: Path = PROJECT_ROOT / "file"

    API_KEY: Optional[str] = os.getenv("DASHSCOPE_API_KEY")
    API_BASE_URL: Optional[str] = os.getenv("DASHSCOPE_BASE_URL")
    MODEL: str = "qwen-flash-character-2026-02-26"  # os.getenv("DASHSCOPE_MODEL", "qwen-plus")
    TEMPERATURE: float = float(os.getenv("MODEL_TEMPERATURE", "0.1"))
    EMBEDDING_MODEL_PATH: str = os.getenv(
        "EMBEDDING_MODEL_PATH",
        r"D:\llm\Local_model\BAAI\bge-small-zh-v1___5",
    )

    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    TITLE_EXTRACTOR_NODES: int = int(os.getenv("TITLE_EXTRACTOR_NODES", "5"))

    SIMILARITY_TOP_K: int = int(os.getenv("SIMILARITY_TOP_K", "5"))
    RERANK_TOP_K: int = int(os.getenv("RERANK_TOP_K", "3"))
    RERANK_MODEL_PATH: str = os.getenv(
        "RERANK_MODEL_PATH",
        r"D:\llm\Local_model\BAAI\bge-reranker-large",
    )

    CHROMA_PERSIST_DIR: str = str(PROJECT_ROOT / "file/chroma_db")
    BM25_PERSIST_DIR: str = str(PROJECT_ROOT / "file/storage_bm25")
    DOCUMENTS_DIR: str = str(PROJECT_ROOT / "file/documents")
    DEFAULT_PERSIST_DIR: str = str(PROJECT_ROOT / "file/storage")
    PDF_IMAGE_DIR: str = str(PROJECT_ROOT / "file/image")

    HOST: str = os.getenv("RAG_API_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("RAG_API_PORT", "8011"))
