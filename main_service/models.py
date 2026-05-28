from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class UserModel(Base):
    """
    用户表。

    用于替代原先的内存字典 `fake_users_db`。
    存储内容包括：
    - username: 主键，用户名
    - email/full_name: 用户资料
    - hashed_password: 哈希后的密码
    - disabled: 是否禁用
    - role: 角色（admin/user）
    - created_at/updated_at: 创建与更新时间
    """
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class LongTermMemoryModel(Base):
    """
    长期记忆表。

    这是你要求的 PostgreSQL 长期记忆落点之一。
    当前采用比较简单的“记忆条目”结构：
    - user_id: 归属用户
    - content: 记忆内容
    - created_at: 写入时间

    后续如果你希望更高级一点，可以扩展成：
    - memory_type
    - tags
    - importance_score
    - source
    """
    __tablename__ = "long_term_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ConversationModel(Base):
    """
    会话表。

    每个用户可以有多个会话，每个会话对应一个 LangGraph Thread。
    """
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="新对话", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
