from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.schemas import (
    RefreshRequest, Token, TokenData, User, UserCreate, UserUpdate, UserAdminUpdate, CommonResponse
)
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    get_user,
    to_public_user,
)
from app.services.user_repository import UserRepository
from config.settings import Settings
from db import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")
router = APIRouter()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_data: TokenData = decode_token(token)
        if token_data.username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = get_user(db, token_data.username)
    if user is None:
        raise credentials_exception
    return to_public_user(user)


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


@router.post("/token", response_model=Token, summary="用户登录")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=Settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires,
    )
    refresh_token_expires = timedelta(days=Settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={"sub": user.username},
        expires_delta=refresh_token_expires,
    )
    return Token(
        message="登录成功",
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        username=user.username,
    )


@router.post("/register", response_model=User, summary="用户注册")
async def register_user(user: UserCreate, db: Session = Depends(get_db)) -> User:
    repo = UserRepository(db)
    if repo.get_by_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    created = repo.create_user(
        username=user.username,
        hashed_password=get_password_hash(user.password),
        email=user.email,
        full_name=user.full_name,
        role=user.role or "user",
    )
    return User(
        username=created.username,
        email=created.email,
        full_name=created.full_name,
        disabled=created.disabled,
        role=created.role,
    )


@router.post("/token/refresh", response_model=Token, summary="刷新访问令牌")
async def refresh_access_token(
    req: RefreshRequest,
    db: Session = Depends(get_db),
) -> Token:
    """
    使用 refresh_token 获取新的 access_token。

    流程：
    1. 验证 refresh_token 的签名和有效期
    2. 检查用户是否存在
    3. 返回新的 access_token 和 refresh_token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_data: TokenData = decode_token(req.refresh_token, expected_type="refresh")
        if token_data.username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = get_user(db, token_data.username)
    if user is None:
        raise credentials_exception

    # 生成新的 access_token
    access_token_expires = timedelta(minutes=Settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires,
    )
    # 生成新的 refresh_token（轮转，提高安全性）
    refresh_token_expires = timedelta(days=Settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={"sub": user.username},
        expires_delta=refresh_token_expires,
    )

    return Token(
        message="Token 刷新成功",
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        username=user.username,
    )


@router.post("/logout", summary="用户退出")
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict:
    return {
        "message": "退出登录成功",
        "username": current_user.username,
        "logout_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/me", response_model=User, summary="获取用户信息")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    return current_user


@router.put("/me", response_model=User, summary="更新用户信息")
async def update_user_me(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
) -> User:
    repo = UserRepository(db)
    updated = repo.update_user(
        current_user.username,
        email=user_update.email,
        full_name=user_update.full_name,
    )
    return User(
        username=updated.username,
        email=updated.email,
        full_name=updated.full_name,
        disabled=updated.disabled,
        role=updated.role,
    )


@router.get("/protected", summary="受保护的路由示例")
async def protected_route(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict:
    return {
        "message": f"Hello {current_user.username}, this is a protected route!",
        "user_info": {
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
        },
        "access_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/all", summary="获取所有用户")
async def get_all_users(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
) -> dict:
    users = [
        User(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled,
            role=user.role,
        )
        for user in UserRepository(db).list_users()
    ]
    return {
        "users": users,
        "total": len(users),
        "requested_by": current_user.username,
    }


@router.delete("/me", summary="删除用户账户")
async def delete_user_account(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
) -> dict:
    repo = UserRepository(db)
    if repo.get_by_username(current_user.username) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    repo.delete_user(current_user.username)
    return {
        "message": "User account deleted successfully",
        "deleted_user": current_user.username,
        "deleted_at": datetime.now(timezone.utc).isoformat(),
    }


# ===== 管理员专用 API =====

@router.get("/admin/users", summary="管理员获取所有用户列表")
async def admin_list_users(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Session = Depends(get_db),
) -> dict:
    repo = UserRepository(db)
    users = [
        {
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "disabled": user.disabled,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }
        for user in repo.list_users()
    ]
    return {"users": users, "total": len(users)}


@router.post("/admin/users", response_model=User, summary="管理员创建用户")
async def admin_create_user(
    user: UserCreate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Session = Depends(get_db),
) -> User:
    repo = UserRepository(db)
    if repo.get_by_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )
    created = repo.create_user(
        username=user.username,
        hashed_password=get_password_hash(user.password),
        email=user.email,
        full_name=user.full_name,
        role=user.role or "user",
    )
    return User(
        username=created.username,
        email=created.email,
        full_name=created.full_name,
        disabled=created.disabled,
        role=created.role,
    )


@router.put("/admin/users/{username}", response_model=User, summary="管理员更新用户")
async def admin_update_user(
    username: str,
    user_update: UserAdminUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Session = Depends(get_db),
) -> User:
    repo = UserRepository(db)
    user = repo.get_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    hashed_password = None
    if user_update.password:
        hashed_password = get_password_hash(user_update.password)

    updated = repo.admin_update_user(
        username,
        email=user_update.email,
        full_name=user_update.full_name,
        role=user_update.role,
        disabled=user_update.disabled,
        hashed_password=hashed_password,
    )
    return User(
        username=updated.username,
        email=updated.email,
        full_name=updated.full_name,
        disabled=updated.disabled,
        role=updated.role,
    )


@router.delete("/admin/users/{username}", response_model=CommonResponse, summary="管理员删除用户")
async def admin_delete_user(
    username: str,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Session = Depends(get_db),
) -> CommonResponse:
    if username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账号",
        )
    repo = UserRepository(db)
    if not repo.get_by_username(username):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    repo.delete_user(username)
    return CommonResponse(status="success", message=f"用户 {username} 已删除")
