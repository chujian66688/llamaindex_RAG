import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """应用配置类"""

    # OpenAI配置
    API_KEY: Optional[str] = os.getenv("DASHSCOPE_API_KEY")
    API_BASE_URL = os.getenv("DASHSCOPE_BASE_URL")
    MODEL: str = "qwen-plus-2025-07-14"
    TEMPERATURE: float = 0.1
    EMBEDDING_MODEL_PATH: str = r"D:\llm\Local_model\BAAI\bge-small-zh-v1___5"

    # 文档处理配置
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    TITLE_EXTRACTOR_NODES: int = 5

    # 检索配置
    SIMILARITY_TOP_K: int = 5
    RERANK_TOP_K: int = 3
    SIMILARITY_CUTOFF: float = 0.5
    RERANK_MODEL_PATH: str = r"D:\llm\Local_model\BAAI\bge-reranker-large"

    # 存储配置
    PROJECT_ROOT: Path = Path(__file__).parent.parent  # 项目根目录
    CHROMA_PERSIST_DIR: str = str(PROJECT_ROOT / "file/chroma_db")
    BM25_PERSIST_DIR: str = str(PROJECT_ROOT / "file/storage_bm25")
    DOCUMENTS_DIR: str = str(PROJECT_ROOT / "file/documents")
    DEFAULT_PERSIST_DIR: str = str(PROJECT_ROOT / "file/storage")
    PDF_IMAGE_DIR: str = str(PROJECT_ROOT / "file/image")
    LOG_DIR: str = str(PROJECT_ROOT / "file")

    # 支持的文件类型
    SUPPORTED_FILE_TYPES: list = [".txt", ".pdf", ".docx", ".md"]

    @classmethod
    def validate_api_key(cls) -> bool:
        """验证API密钥是否存在"""
        return cls.API_KEY is not None and len(cls.API_KEY.strip()) > 0
