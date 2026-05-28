from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class UserModel(Base):
    """
    用户表。

    用于替代原先的内存字典 `fake_users_db`。
    存储内容包括：
    - username: 主键，用户名
    - email/full_name: 用户资料
    - hashed_password: 哈希后的密码
    - disabled: 是否禁用
    - created_at/updated_at: 创建与更新时间
    """
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.time, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.time, onupdate=datetime.time, nullable=False)
