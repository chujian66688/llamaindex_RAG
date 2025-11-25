# app/routers/chat.py
"""
聊天/检索生成相关的 API：
- POST /api/chat/query: 发送问题，返回回答、更新后的消息历史与引用信息
- POST /api/chat/clear: 清空指定 session 的消息历史
"""

from fastapi import APIRouter, Depends, HTTPException
from app.schemas import ChatRequest, ChatResponse, ClearRequest, CommonResponse, ChatMessage, User
from fastapi.responses import StreamingResponse
from app.routers.users import get_current_active_user
from app.services import get_rag_service
from app.services.rag_service import RAGService
from utils.logger import setup_logger
import json
from typing import List

logger = setup_logger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_query(req: ChatRequest,
                     current_user: User = Depends(get_current_active_user),  # ← 鉴权
                     svc: RAGService = Depends(get_rag_service)):
    """
    聊天对话接口 - 需要登录认证

    这是核心的聊天接口，支持流式和非流式两种模式：
    - 非流式: 等待AI完整回答后一次性返回
    - 流式: 实时返回AI生成的内容片段

    安全特性:
    - 需要有效的JWT令牌
    - 自动配额检查和限制
    - 用户数据隔离

    Args:
        req (ChatRequest): 聊天请求数据
        current_user (User): 通过JWT认证获取的当前用户信息
        svc (RAGService): RAG 应用主类

    Returns:
        ChatResponse: 非流式模式的完整响应
        StreamingResponse: 流式模式的SSE响应

    Raises:
        HTTPException:
            - 429: 配额已用完
            - 500: AI模型调用失败或其他服务器错误
    """
    try:
        # 从认证信息中获取用户名，确保数据安全
        username = current_user.username

        answer, sources = await svc.query(
            session_id=username,
            query=req.query,
            model=req.model,
            knowledge_bool=req.knowledge_bool or False,
            temperature=req.temperature,
            max_tokens=req.max_tokens
        )
        print(sources)
        return ChatResponse(
            messages=ChatMessage(role="assistant", content=answer, sources=sources or [])
        )
    except Exception as e:
        # 捕获未预期异常，返回 500
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_query_stream(req: ChatRequest,
                            current_user: User = Depends(get_current_active_user),  # ← 鉴权
                            svc: RAGService = Depends(get_rag_service)):
    """
    聊天对话接口 - 需要登录认证

    这是核心的聊天接口，支持流式和非流式两种模式：
    - 非流式: 等待AI完整回答后一次性返回
    - 流式: 实时返回AI生成的内容片段

    安全特性:
    - 需要有效的JWT令牌
    - 自动配额检查和限制
    - 用户数据隔离

    Args:
        req (ChatRequest): 聊天请求数据
        current_user (User): 通过JWT认证获取的当前用户信息
        svc (RAGService): RAG 应用主类

    Returns:
        ChatResponse: 非流式模式的完整响应
        StreamingResponse: 流式模式的SSE响应

    Raises:
        HTTPException:
            - 429: 配额已用完
            - 500: AI模型调用失败或其他服务器错误
    """

    # 从认证信息中获取用户名，确保数据安全
    username = current_user.username

    """流式聊天接口（SSE）"""

    async def event_generator():
        """SSE 事件生成器"""
        try:
            async for chunk in svc.query_stream(
                    session_id=username,
                    query=req.query,
                    model=req.model,
                    knowledge_bool=req.knowledge_bool or [],
                    temperature=req.temperature,
                    max_tokens=req.max_tokens
            ):
                # 将数据转换为 SSE 格式
                data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"

        except Exception as e:
            error_data = {
                "type": "error",
                "content": f"流式传输错误: {str(e)}",
                "done": True
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        content=event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",  # 禁用缓存
            "Connection": "keep-alive",  # 保持连接
        })


@router.get("/history")
async def get_user_history(
        current_user: User = Depends(get_current_active_user),  # ← 鉴权
        svc: RAGService = Depends(get_rag_service)
) -> List[ChatMessage]:
    """
       获取当前用户的聊天历史 - 安全版本

       只返回当前认证用户的聊天历史，确保数据隐私

       Args:
           current_user (User): 通过JWT认证获取的当前用户信息
           svc (RAGService):

       Returns:
           List[ChatMessage]: 用户的历史消息列表

       Security:
           用户只能访问自己的聊天历史，无法访问他人数据
       """
    username = current_user.username
    if username is None:
        return []

    chat_history = svc.get_session(username)
    if not chat_history:
        return []
    # 返回用户的完整聊天历史
    # 创建新的ChatMessage对象确保数据一致性

    return [

        ChatMessage(
            role=msg["role"],
            content=msg["content"],
            sources=(msg["sources"] if msg.get("sources") else [])
        ) for msg in chat_history
    ]


@router.post("/clear", response_model=CommonResponse)
async def chat_clear(req: ClearRequest,
                     current_user: User = Depends(get_current_active_user),  # ← 鉴权
                     svc: RAGService = Depends(get_rag_service)):
    """
    清空指定会话的历史记录。
    注意：只影响内存或会话存储，不会清空向量库中的文档。
    """
    svc.clear_session(current_user.username)
    return CommonResponse(status="success", message="会话已清空")
