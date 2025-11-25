# app/schemas.py
"""
Pydantic 数据模型：
- 定义请求与响应结构，确保接口契约清晰、可被前端与 OpenAPI 文档消费。
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from config.settings import Settings


class UploadResponse(BaseModel):
    """上传/摄取结果"""
    status: str  # "success" | "processing" | "failed"
    message: str  # 友好提示文本
    processed_files: List[str] = []  # 成功处理的文件名列表


class DocsListResponse(BaseModel):
    """文档列表响应"""
    documents: List[str]


class ChatMessage(BaseModel):
    """对话中的一条消息"""
    role: str  # "user" | "assistant" | "system"
    content: str
    sources: List[str]  # 引用来源（文档名/片段/分数等）


class ChatRequest(BaseModel):
    """对话请求体"""
    query: str
    model: Optional[str] = Settings.MODEL  # 要使用的AI模型名称，默认使用配置中的模型
    knowledge_bool: bool = None  # 是否要开启知识库模式
    temperature: Optional[float] = Settings.TEMPERATURE  # 创造性温度值(0-2)，控制回答的随机性
    max_tokens: int = 100


class ChatResponse(BaseModel):
    """对话响应体"""
    messages: ChatMessage  # 返回更新后的完整消息历史


class ClearRequest(BaseModel):
    """清空会话请求"""
    session_id: str


class CommonResponse(BaseModel):
    """通用状态响应"""
    status: str
    message: str


# ----------------------
# 用户数据模型
# ----------------------

class LoginRequest(BaseModel):
    """
        用户登录输入的模型
    """
    username: str
    password: str


class Token(BaseModel):
    """
    访问令牌响应模型
    用于登录成功后返回JWT令牌
    """
    message: str
    access_token: str  # JWT访问令牌
    token_type: str  # 令牌类型，通常是"bearer"
    username: str


class TokenData(BaseModel):
    """
    令牌数据模型
    用于解析JWT令牌中的用户信息
    """
    username: Optional[str] = None  # 用户名（可选）


class User(BaseModel):
    """
    用户基础信息模型
    定义用户的公开信息（不包含密码等敏感信息）
    """
    username: str  # 用户名（必需）
    email: Optional[str] = None  # 邮箱（可选）
    full_name: Optional[str] = None  # 全名（可选）
    disabled: Optional[bool] = None  # 是否禁用（可选）


class UserInDB(User):
    """
    数据库中的用户模型
    继承User模型，添加了密码哈希字段
    """
    hashed_password: str  # 哈希后的密码


class UserCreate(BaseModel):
    """
    用户创建请求模型
    用于用户注册时接收前端传来的数据
    """
    username: str  # 用户名（必需）
    password: str  # 明文密码（必需）
    email: Optional[str] = None  # 邮箱（可选）
    full_name: Optional[str] = None  # 全名（可选）


class UserUpdate(BaseModel):
    """
    用户更新请求模型
    用于更新用户信息时接收前端传来的数据
    """
    email: Optional[str] = None  # 新邮箱（可选）
    full_name: Optional[str] = None  # 新全名（可选）
