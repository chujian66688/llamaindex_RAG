from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.schemas import TokenData, User, UserInDB
from app.services.user_repository import UserRepository
from config.settings import Settings

# 使用 pwdlib 推荐的密码哈希方案。
# 当前通常会生成 argon2 等更安全的哈希格式。
password_hash = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码是否与数据库中的哈希值匹配。"""
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """对明文密码做哈希，数据库永远不直接存明文密码。"""
    return password_hash.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    创建 JWT 访问令牌。

    常见约定：
    - `sub` 字段存用户唯一标识（这里用 username）
    - `exp` 字段存过期时间
    - `type` 字段区分 access/refresh
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, Settings.JWT_SECRET_KEY, algorithm=Settings.JWT_ALGORITHM)


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    创建 JWT 刷新令牌。

    refresh_token 有效期更长，用于在 access_token 过期后获取新的 access_token。
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, Settings.JWT_SECRET_KEY, algorithm=Settings.JWT_ALGORITHM)


def get_user(db: Session, username: str) -> UserInDB | None:
    """
    从数据库中加载用户，并转换成 `UserInDB` 模型。

    为什么要单独做这一层转换：
    - 路由层、Service 层尽量不要直接暴露 ORM 实体
    - 更方便后续替换数据源或增加字段
    """
    model = UserRepository(db).get_by_username(username)
    if model is None:
        return None
    return UserInDB(
        username=model.username,
        email=model.email,
        full_name=model.full_name,
        disabled=model.disabled,
        role=model.role,
        hashed_password=model.hashed_password,
    )


def authenticate_user(db: Session, username: str, password: str) -> UserInDB | None:
    """
    用户认证。

    流程：
    1. 先查用户
    2. 再校验密码
    3. 成功则返回用户对象，失败返回 None
    """
    user = get_user(db, username)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def decode_token(token: str, expected_type: str = "access") -> TokenData:
    """
    解码 JWT，提取其中的用户名。

    注意：
    - 只负责解码，不负责业务上的"用户是否存在"判断
    - 通过 expected_type 参数区分 access_token 和 refresh_token
    """
    payload = jwt.decode(token, Settings.JWT_SECRET_KEY, algorithms=[Settings.JWT_ALGORITHM])
    token_type = payload.get("type", "access")
    if token_type != expected_type:
        raise jwt.InvalidTokenError(f"Expected token type '{expected_type}', got '{token_type}'")
    username = payload.get("sub")
    return TokenData(username=username)


def to_public_user(user: UserInDB | User) -> User:
    """
    把带敏感字段的用户对象转换成公开用户对象。

    目的是防止 `hashed_password` 这类字段意外暴露到接口返回里。
    """
    if isinstance(user, UserInDB):
        return User(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled,
            role=user.role,
        )
    return user
