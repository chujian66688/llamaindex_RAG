from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config.settings import Settings

# SQLAlchemy Engine：
# - 负责和 PostgreSQL 建立底层连接
# - pool_pre_ping=True 可以在连接失效时做预检查，减少长连接报错
engine = create_engine(Settings.POSTGRES_URL, future=True, pool_pre_ping=True)

# Session 工厂：
# 后续每次请求、每次数据库操作，都从这里创建一个 Session 实例。
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# 所有 ORM 模型的基类。
Base = declarative_base()


def get_db():
    """
    FastAPI 数据库依赖。

    典型用法：
    `db: Session = Depends(get_db)`

    行为：
    - 进入请求时创建 Session
    - 请求结束后自动关闭 Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
