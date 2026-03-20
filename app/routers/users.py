from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from app.schemas import LoginRequest, Token, TokenData, User, UserInDB, UserCreate, UserUpdate

# =====================================================
# JWT和安全配置
# =====================================================

# JWT密钥配置 - 生产环境中应该使用环境变量或密钥管理服务
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"  # 警告：生产环境请使用强密钥并通过环境变量管理
ALGORITHM = "HS256"  # JWT签名算法
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token过期时间（分钟）

# 密码加密上下文配置
# 安全哈希算法
password_hash = PasswordHash.recommended()

# OAuth2密码Bearer令牌方案
# tokenUrl: 获取token的端点URL，必须与实际的token端点路径匹配
# 这告诉FastAPI和前端客户端在哪里获取访问令牌
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")

# 创建路由器实例
# 这个路由器将包含所有用户相关的路由
router = APIRouter()

# =====================================================
# 模拟数据库
# =====================================================

# 模拟用户数据库 - 生产环境中应该使用真实的数据库（如PostgreSQL、MySQL等）
# 这里使用字典来模拟数据库存储，包含一个默认管理员账户
fake_users_db = {
    "root": {
        "username": "root",
        "full_name": "Administrator",
        "email": "admin@example.com",
        # 这是"admin123"的bcrypt哈希值
        "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$SCdx9sCe8SSxNynoPXO20g$k25MW0aUhKQrepvriHWmCRJef+p+9GnPfddsyNQVVBQ",
        "disabled": False,
    }
}


# =====================================================
# 工具函数
# =====================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码是否正确

    Args:
        plain_password (str): 用户输入的明文密码
        hashed_password (str): 数据库中存储的密码哈希

    Returns:
        bool: 密码是否匹配
    """
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    生成密码的哈希值

    Args:
        password (str): 明文密码

    Returns:
        str: 密码的bcrypt哈希值
    """
    return password_hash.hash(password)


def get_user(db: dict, username: str) -> Optional[UserInDB]:
    """
    从数据库中获取用户信息

    Args:
        db (dict): 用户数据库
        username (str): 用户名

    Returns:
        Optional[UserInDB]: 用户信息对象，如果用户不存在则返回None
    """
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(fake_db: dict, username: str, password: str) -> Optional[UserInDB]:
    """
    验证用户身份

    Args:
        fake_db (dict): 用户数据库
        username (str): 用户名
        password (str): 明文密码

    Returns:
        Optional[UserInDB]: 验证成功返回用户对象，失败返回False
    """
    # 首先获取用户信息
    user = get_user(fake_db, username)
    if not user:
        return False

    # 验证密码是否正确
    if not verify_password(password, user.hashed_password):
        return False

    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问令牌

    Args:
        data (dict): 要编码到令牌中的数据（通常包含用户标识）
        expires_delta (Optional[timedelta]): 令牌过期时间，如果不提供则使用默认值

    Returns:
        str: 编码后的JWT令牌
    """
    # 复制数据以避免修改原始数据
    to_encode = data.copy()

    # 计算过期时间，没有设置过期时间，就默认设置15分钟
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    # 添加过期时间到令牌数据中
    to_encode.update({"exp": expire})

    # 使用密钥和算法对数据进行编码
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# =====================================================
# 依赖函数（用于路由中的依赖注入）
# =====================================================

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserInDB:
    """
    从JWT令牌中获取当前用户信息

    这是一个依赖函数，会被其他需要用户身份验证的路由使用

    Args:
        token (str): 从请求头中提取的Bearer令牌

    Returns:
        UserInDB: 当前用户信息

    Raises:
        HTTPException: 如果令牌无效或用户不存在
    """
    # 定义认证异常，当令牌验证失败时抛出
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",  # 无法验证凭据
        headers={"WWW-Authenticate": "Bearer"},  # 告诉客户端使用Bearer认证
    )

    try:
        # 解码JWT令牌
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 从令牌中提取用户名（sub是JWT标准字段，表示subject/主题）
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        # 创建令牌数据对象
        token_data = TokenData(username=username)

    except jwt.PyJWTError:
        # JWT解码失败（令牌无效、过期等）
        raise credentials_exception

    # 从数据库中获取用户信息
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
        current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    获取当前活跃用户

    这是另一个依赖函数，确保用户不仅通过了身份验证，而且账户是活跃的

    Args:
        current_user (User): 从get_current_user依赖中获取的当前用户

    Returns:
        User: 活跃的用户信息

    Raises:
        HTTPException: 如果用户账户被禁用
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# =====================================================
# API路由端点
# =====================================================

@router.post("/token", response_model=Token, summary="用户登录", description="使用用户名和密码获取JWT访问令牌")
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends()
) -> Token:
    """
    用户登录端点

    接受用户名和密码，返回JWT访问令牌
    使用OAuth2PasswordRequestForm来接收表单数据（username、password字段）

    Args:
        form_data : 包含用户名和密码的表单数据

    Returns:
        Token: 包含访问令牌和令牌类型的对象

    Raises:
        HTTPException: 如果用户名或密码不正确
    """
    # 验证用户身份
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        # 认证失败，返回401未授权状态码
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",  # 用户名或密码错误
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 设置令牌过期时间
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # 创建访问令牌，将用户名作为subject存储在令牌中
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )

    # 返回令牌和令牌类型
    return {
        "message": "登录成功",
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username
    }


@router.post("/register", response_model=User, summary="用户注册", description="创建新用户账户")
async def register_user(user: UserCreate) -> User:
    """
    用户注册端点

    创建新的用户账户，密码会被自动哈希加密存储

    Args:
        user (UserCreate): 包含用户注册信息的对象

    Returns:
        User: 创建成功的用户信息（不包含密码）

    Raises:
        HTTPException: 如果用户名已存在
    """
    # 检查用户名是否已经存在
    if user.username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"  # 用户名已被注册
        )

    # 对密码进行哈希加密
    hashed_password = get_password_hash(user.password)

    # 创建用户数据字典
    user_dict = {
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "hashed_password": hashed_password,
        "disabled": False  # 新用户默认为启用状态
    }

    # 将用户数据保存到"数据库"
    fake_users_db[user.username] = user_dict

    # 返回用户信息（不包含密码哈希）
    return User(**user_dict)


@router.post("/logout", summary="用户退出", description="用户退出登录")
async def logout(
        current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict:
    """
    用户退出登录端点

    由于JWT是无状态的，服务端不需要做特殊处理
    主要是返回成功消息，让前端清除本地存储的token

    Args:
        current_user (User): 通过依赖注入获取的当前用户信息

    Returns:
        dict: 退出成功的消息
    """
    print(current_user.username)
    return {
        "message": "退出登录成功",
        "username": current_user.username,
        "logout_time": datetime.now(timezone.utc).isoformat()
    }


@router.get("/me", response_model=User, summary="获取用户信息", description="获取当前登录用户的个人信息")
async def read_users_me(
        current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    获取当前用户信息端点

    需要有效的JWT令牌才能访问

    Args:
        current_user (User): 通过依赖注入获取的当前用户信息

    Returns:
        User: 当前用户的信息
    """
    return current_user


@router.put("/me", response_model=User, summary="更新用户信息", description="更新当前登录用户的个人信息")
async def update_user_me(
        user_update: UserUpdate,
        current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    更新当前用户信息端点

    允许用户更新自己的邮箱和全名信息

    Args:
        user_update (UserUpdate): 包含要更新的用户信息
        current_user (User): 通过依赖注入获取的当前用户信息

    Returns:
        User: 更新后的用户信息
    """
    # 只更新非None的字段
    if user_update.email is not None:
        fake_users_db[current_user.username]["email"] = user_update.email
    if user_update.full_name is not None:
        fake_users_db[current_user.username]["full_name"] = user_update.full_name

    # 获取并返回更新后的用户信息
    updated_user = get_user(fake_users_db, current_user.username)
    return User(**updated_user.model_dump())


@router.get("/protected", summary="受保护的路由示例", description="演示需要身份验证才能访问的路由")
async def protected_route(
        current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict:
    """
    受保护的路由示例

    这个端点演示了如何创建需要身份验证的路由
    只有提供有效JWT令牌的用户才能访问

    Args:
        current_user (User): 通过依赖注入获取的当前用户信息

    Returns:
        dict: 包含欢迎消息的字典
    """
    return {
        "message": f"Hello {current_user.username}, this is a protected route!",
        "user_info": {
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name
        },
        "access_time": datetime.now(timezone.utc).isoformat()
    }


@router.get("/all", summary="获取所有用户", description="获取系统中所有用户的列表（需要管理员权限）")
async def get_all_users(
        current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict:
    """
    获取所有用户列表端点

    返回系统中所有用户的信息（不包含密码）
    注意：在实际应用中，这个功能应该有权限控制

    Args:
        current_user (User): 通过依赖注入获取的当前用户信息

    Returns:
        dict: 包含用户列表和总数的字典
    """
    users = []
    for username, user_data in fake_users_db.items():
        # 创建User对象（不包含密码哈希）
        user_info = {k: v for k, v in user_data.items() if k != 'hashed_password'}
        users.append(User(**user_info))

    return {
        "users": users,
        "total": len(users),
        "requested_by": current_user.username
    }


@router.delete("/me", summary="删除用户账户", description="删除当前登录用户的账户")
async def delete_user_account(
        current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict:
    """
    删除当前用户账户端点

    允许用户删除自己的账户
    注意：在实际应用中，可能需要额外的确认步骤

    Args:
        current_user (User): 通过依赖注入获取的当前用户信息

    Returns:
        dict: 删除成功的确认消息

    Raises:
        HTTPException: 如果用户不存在（理论上不会发生）
    """
    if current_user.username in fake_users_db:
        # 从数据库中删除用户
        del fake_users_db[current_user.username]
        return {
            "message": "User account deleted successfully",
            "deleted_user": current_user.username,
            "deleted_at": datetime.now(timezone.utc).isoformat()
        }
    else:
        # 这种情况理论上不会发生，因为用户已经通过了身份验证
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
