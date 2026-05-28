"""
服务层依赖注入入口。
"""

from app.services.langgraph_service import LangGraphService
from app.services.rag_api_service import RAGApiService

_rag_api_service = RAGApiService()
_langgraph_service = LangGraphService()


def get_rag_api_service() -> RAGApiService:
    return _rag_api_service


def get_langgraph_service() -> LangGraphService:
    return _langgraph_service
