from __future__ import annotations

from sqlalchemy.orm import Session

from models import UserModel


class UserRepository:
    """
    用户数据访问层。

    这里把对 `users` 表的常见操作集中起来，避免路由层直接写 ORM 细节。
    这样后续如果表结构变化，或者你要增加额外校验，维护成本会更低。
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> UserModel | None:
        """按用户名查询用户。"""
        return self.db.get(UserModel, username)

    def create_user(
        self,
        *,
        username: str,
        hashed_password: str,
        email: str | None = None,
        full_name: str | None = None,
        role: str = "user",
    ) -> UserModel:
        """
        创建一个新用户。

        注意这里传入的是 `hashed_password`，
        说明密码哈希动作应该在 service 层完成，而不是 repository 层处理。
        """
        user = UserModel(
            username=username,
            hashed_password=hashed_password,
            email=email,
            full_name=full_name,
            disabled=False,
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(
        self,
        username: str,
        *,
        email: str | None = None,
        full_name: str | None = None,
        role: str | None = None,
    ) -> UserModel:
        """更新用户公开资料。"""
        user = self.db.get(UserModel, username)
        if email is not None:
            user.email = email
        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        self.db.commit()
        self.db.refresh(user)
        return user

    def admin_update_user(
        self,
        username: str,
        *,
        email: str | None = None,
        full_name: str | None = None,
        role: str | None = None,
        disabled: bool | None = None,
        hashed_password: str | None = None,
    ) -> UserModel:
        """管理员更新用户（包括禁用、角色、密码等）。"""
        user = self.db.get(UserModel, username)
        if email is not None:
            user.email = email
        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        if disabled is not None:
            user.disabled = disabled
        if hashed_password is not None:
            user.hashed_password = hashed_password
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, username: str) -> None:
        """删除用户。"""
        user = self.db.get(UserModel, username)
        if user is not None:
            self.db.delete(user)
            self.db.commit()

    def list_users(self) -> list[UserModel]:
        """按创建时间倒序列出所有用户。"""
        return list(self.db.query(UserModel).order_by(UserModel.created_at.desc()).all())
