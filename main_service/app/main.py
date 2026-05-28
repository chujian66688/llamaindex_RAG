"""
FastAPI 应用入口。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.routers import chat, documents, users
from db import Base, engine, SessionLocal
from models import UserModel
from app.services.auth_service import get_password_hash
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _ensure_role_column():
    """如果 users 表缺少 role 列，则自动添加。"""
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='role'"
        ))
        if result.fetchone() is None:
            logger.info("users 表缺少 role 列，正在添加...")
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'user'"
            ))
            conn.commit()
            logger.info("role 列添加成功")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 先确保数据库表结构完整（包括 role 列）
    _ensure_role_column()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        root_user = db.get(UserModel, "root")
        if root_user is None:
            db.add(
                UserModel(
                    username="root",
                    full_name="Administrator",
                    email="admin@example.com",
                    hashed_password=get_password_hash("admin123"),
                    disabled=False,
                    role="admin",
                )
            )
            db.commit()
        else:
            # 确保 root 用户是 admin 角色
            if root_user.role != "admin":
                root_user.role = "admin"
                db.commit()
    finally:
        db.close()
    yield


app = FastAPI(title="Agent API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api/docs", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(users.router, prefix="/users", tags=["users"])


@app.get("/api/health")
def health():
    return {"status": "ok", "message": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
