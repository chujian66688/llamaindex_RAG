# app/main.py
"""
FastAPI 应用入口：
- 配置 CORS（跨域）
- 注册子路由：/api/docs, /api/chat, /api/users
- 提供健康检查接口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat, documents, users
from utils.logger import setup_logger

logger = setup_logger(__name__)

# 创建 FastAPI 应用实例，title/version 会显示在自动生成的文档页面
app = FastAPI(title="RAG API", version="1.0.0")

# CORS 配置：开发阶段允许所有来源；生产环境务必收紧 allow_origins 白名单
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有自定义头
)

# 通过 include_router 挂载子路由，统一加上 /api 前缀与 tags
app.include_router(documents.router, prefix="/api/docs", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(users.router, prefix="/users", tags=["users"])


@app.get("/api/health")
def health():
    """
    健康检查：用于存活探针与基本可用性验证。
    Kubernetes/监控系统可定期调用该接口。
    """
    return {"status": "ok", "message": "healthy"}



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
