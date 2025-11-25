# app/services/__init__.py
"""
服务层的依赖注入入口。
这里创建并持有一个全局的 RAGService 单例，避免每次请求都重新初始化底层资源
（例如索引、向量库连接、模型客户端等），提升性能与一致性。
"""

from app.services.rag_service import RAGService

# 全局创建一个 RAGService 实例。注意：若你使用多进程部署（如 gunicorn+uvicorn workers），
# 每个进程都会各自拥有一个实例；这通常是可接受的，因为向量库/存储层应是外部持久化。
_rag_service = RAGService()

def get_rag_service() -> RAGService:
    """
    FastAPI 的依赖函数。
    在路由处理函数中通过 Depends 注入，获得同一份服务对象。
    """
    return _rag_service
