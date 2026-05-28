from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel


class UploadResponse(BaseModel):
    status: str
    message: str
    processed_files: List[str] = []


class DocsListResponse(BaseModel):
    documents: List[Any]


class DocChunkItem(BaseModel):
    chunk_id: str
    text: str
    metadata: Dict[str, Any]


class DocChunksResponse(BaseModel):
    chunks: List[DocChunkItem]
    total: int
    page: int
    page_size: int


class ChunkConfigResponse(BaseModel):
    chunk_size: int
    chunk_overlap: int


class ChunkConfigUpdateRequest(BaseModel):
    chunk_size: int
    chunk_overlap: int


class ChatMessage(BaseModel):
    role: str
    content: str
    sources: List[str]


class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None  # 会话 ID，为空时自动创建新会话
    knowledge_bool: Optional[bool] = False


class ChatResponse(BaseModel):
    messages: ChatMessage
    conversation_id: str  # 返回会话 ID
    is_interrupt: bool = False


class ResumeRequest(BaseModel):
    conversation_id: str  # 会话 ID
    action: str  # approve / edit / rewrite / clarify
    content: Optional[str] = None  # 用户编辑后的内容（仅 action=edit 时需要）
    answer: Optional[str] = None  # 用户对澄清问题的回答（仅 action=clarify 时需要）


class ClearRequest(BaseModel):
    conversation_id: Optional[str] = None


# ===== 会话相关 Schema =====

class ConversationCreate(BaseModel):
    title: Optional[str] = "新对话"


class ConversationUpdate(BaseModel):
    title: str


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]


class CommonResponse(BaseModel):
    status: str
    message: str


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    message: str
    access_token: str
    refresh_token: str
    token_type: str
    username: str


class TokenData(BaseModel):
    username: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    role: Optional[str] = "user"


class UserInDB(User):
    hashed_password: str


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = "user"


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None


class UserAdminUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    disabled: Optional[bool] = None
    password: Optional[str] = None
