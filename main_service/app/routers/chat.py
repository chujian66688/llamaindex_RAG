from typing import List
import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.routers.users import get_current_active_user
from app.schemas import (
    ChatMessage, ChatRequest, ChatResponse, ClearRequest, CommonResponse,
    ConversationCreate, ConversationListResponse, ConversationResponse, ConversationUpdate,
    ResumeRequest, User,
)
from app.services import get_langgraph_service
from app.services.conversation_repository import ConversationRepository
from app.services.langgraph_service import LangGraphService
from db import get_db
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


# ===== 会话管理 API =====

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    req: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """创建新会话。"""
    repo = ConversationRepository(db)
    conversation = repo.create(user_id=current_user.username, title=req.title or "新对话")
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的会话列表。"""
    repo = ConversationRepository(db)
    conversations = repo.list_by_user(current_user.username)
    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=c.id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conversations
        ]
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    req: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """更新会话标题。"""
    repo = ConversationRepository(db)
    conversation = repo.update_title(conversation_id, current_user.username, req.title)
    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.delete("/conversations/{conversation_id}", response_model=CommonResponse)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    svc: LangGraphService = Depends(get_langgraph_service),
):
    """删除会话（同时删除 LangGraph Thread 状态）。"""
    repo = ConversationRepository(db)
    if not repo.delete(conversation_id, current_user.username):
        raise HTTPException(status_code=404, detail="会话不存在")
    # 同时删除 LangGraph Thread 状态
    try:
        await svc.clear_history(thread_id=current_user.username, conversation_id=conversation_id)
    except Exception as e:
        logger.warning(f"删除 LangGraph Thread 失败: {e}")
    return CommonResponse(status="success", message="会话已删除")


# ===== 聊天 API =====


@router.post("/chat", response_model=ChatResponse)
async def chat_query(
    req: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    svc: LangGraphService = Depends(get_langgraph_service),
    db: Session = Depends(get_db),
):
    """
    非流式聊天接口。

    改造后的行为：
    - 不再直接调用原有 RAGService 做对话
    - 而是统一转发到本地部署的 LangGraph 服务

    请求体现在只保留两个核心字段：
    - query
    - model

    用户身份仍由 FastAPI 的 JWT 鉴权负责，
    然后把用户名作为 thread_id 传给 LangGraph，
    用于隔离不同用户的记忆与状态。
    """
    # 如果没有提供 conversation_id，自动创建新会话
    conversation_id = req.conversation_id
    if not conversation_id:
        repo = ConversationRepository(db)
        # 自动生成标题（取前20个字符）
        title = req.query[:20] + "..." if len(req.query) > 20 else req.query
        conversation = repo.create(user_id=current_user.username, title=title)
        conversation_id = conversation.id
    else:
        # 更新会话的最后活跃时间
        repo = ConversationRepository(db)
        repo.touch(conversation_id, current_user.username)

    try:
        result = await svc.chat(
            thread_id=current_user.username,
            conversation_id=conversation_id,
            query=req.query,
            knowledge_bool=req.knowledge_bool,
        )
        
        # 检测是否是 interrupt（人机交互）
        if result.get("is_interrupt"):
            return ChatResponse(
                messages=ChatMessage(
                    role="ai",
                    content=result.get("answer", ""),
                    sources=[],
                ),
                conversation_id=conversation_id,
                is_interrupt=True,
            )
        
        return ChatResponse(
            messages=ChatMessage(
                role="ai",
                content=result.get("answer", ""),
                sources=result.get("sources", []) or [],
            ),
            conversation_id=conversation_id,
            is_interrupt=False,
        )
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_query_stream(
    req: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    svc: LangGraphService = Depends(get_langgraph_service),
    db: Session = Depends(get_db),
):
    """
    流式聊天接口（真正的 token 级流式输出）。

    使用 LangGraph SDK 的 stream 方法，stream_mode=["messages", "updates"]。
    - messages 模式：token 级别的流式输出
    - updates 模式：节点级别的状态更新
    """
    # 如果没有提供 conversation_id，自动创建新会话
    conversation_id = req.conversation_id
    if not conversation_id:
        repo = ConversationRepository(db)
        title = req.query[:20] + "..." if len(req.query) > 20 else req.query
        conversation = repo.create(user_id=current_user.username, title=title)
        conversation_id = conversation.id
    else:
        repo = ConversationRepository(db)
        repo.touch(conversation_id, current_user.username)

    async def event_generator():
        try:
            final_sources = []
            prev_content = ""  # 追踪之前的内容，用于计算增量
            current_node = ""  # 当前执行的节点名
            # 只有这些节点的内容会显示在对话中
            display_nodes = {"format_output", "chat_agent", "knowledge_agent", "fallback_search"}
            # 需要追踪的节点（用于显示加载状态）
            track_nodes = {
                "understand", "ask_clarification", "research", "outline", "draft",
                "review", "revise", "format_output",
                "chat_agent", "knowledge_agent", "fallback_search",
            }
            # 节点中文名称映射
            node_labels = {
                "understand": "正在理解需求...",
                "ask_clarification": "正在准备提问...",
                "research": "正在搜索资料...",
                "outline": "正在生成大纲...",
                "draft": "正在撰写文章...",
                "review": "正在审核内容...",
                "revise": "正在修订内容...",
                "format_output": "正在格式化输出...",
                "chat_agent": "正在思考...",
                "knowledge_agent": "正在检索知识库...",
                "fallback_search": "正在搜索...",
            }
            print("准备进入流式输出")
            async for event in svc.chat_stream(
                thread_id=current_user.username,
                conversation_id=conversation_id,
                query=req.query,
                knowledge_bool=req.knowledge_bool,
            ):
                # 检查客户端是否断开连接
                if await request.is_disconnected():
                    logger.info(f"[CLIENT DISCONNECTED] 用户 {current_user.username} 断开连接，取消正在运行的任务")
                    await svc.cancel_runs(thread_id=current_user.username, conversation_id=conversation_id)
                    break
                
                # v2 格式：{"type": "...", "ns": [...], "data": ...}
                event_type = event.get("type", "")
                event_data = event.get("data", {})
                # 检测 interrupt 事件（人机交互节点）
                if event_type == "updates" and isinstance(event_data, dict):
                    for node_name, node_output in event_data.items():
                        if isinstance(node_output, dict):
                            sources = node_output.get("sources", [])
                            if sources:
                                final_sources = sources
                            
                            # 检查是否有 answer 内容需要发送
                            answer = node_output.get("answer", "")
                            if answer and node_name in display_nodes:
                                # 发送 content 事件
                                yield f"data: {json.dumps({'type': 'content', 'finished': False, 'content': answer, 'is_display': True}, ensure_ascii=False)}\n\n"
                    
                    if "__interrupt__" in event_data:
                        interrupt_data = event_data["__interrupt__"]
                        # 发送会话 ID
                        yield f"data: {json.dumps({'type': 'conversation_id', 'finished': False, 'content': conversation_id}, ensure_ascii=False)}\n\n"
                        yield f"data: {json.dumps({'type': 'interrupt', 'finished': False, 'content': interrupt_data}, ensure_ascii=False)}\n\n"
                        return
                
                # 通过 messages/metadata 事件判断进入哪个节点
                if event_type == "messages/metadata" and isinstance(event_data, dict):
                    for run_id, run_info in event_data.items():
                        if isinstance(run_info, dict):
                            metadata = run_info.get("metadata", {})
                            node_name = metadata.get("langgraph_node", "")
                            if node_name and node_name != current_node:
                                current_node = node_name
                                prev_content = ""  # 重置内容追踪
                                # 发送节点开始事件
                                if node_name in track_nodes:
                                    label = node_labels.get(node_name, f"正在执行 {node_name}...")
                                    is_display = node_name in display_nodes
                                    yield f"data: {json.dumps({'type': 'node_start', 'finished': False, 'node': node_name, 'label': label, 'is_display': is_display}, ensure_ascii=False)}\n\n"
                    continue
                
                # 处理 messages/partial 事件
                if event_type == "messages/partial":
                    # current_node 为空时，不发送 content 事件
                    if not current_node:
                        continue
                    
                    # draft 节点的内容使用 article 事件类型发送
                    if current_node == 'draft':
                        if isinstance(event_data, list):
                            for msg_chunk in event_data:
                                if isinstance(msg_chunk, dict):
                                    content = msg_chunk.get("content", "")
                                    if content and isinstance(content, str):
                                        if prev_content and content.startswith(prev_content):
                                            delta = content[len(prev_content):]
                                        else:
                                            delta = content
                                        
                                        if delta:
                                            yield f"data: {json.dumps({'type': 'article', 'finished': False, 'content': delta, 'node': current_node}, ensure_ascii=False)}\n\n"
                                        prev_content = content
                    # 显示节点的内容使用 content 事件类型发送
                    elif current_node in display_nodes:
                        if isinstance(event_data, list):
                            for msg_chunk in event_data:
                                if isinstance(msg_chunk, dict):
                                    content = msg_chunk.get("content", "")
                                    if content and isinstance(content, str):
                                        if prev_content and content.startswith(prev_content):
                                            delta = content[len(prev_content):]
                                        else:
                                            delta = content
                                        
                                        if delta:
                                            yield f"data: {json.dumps({'type': 'content', 'finished': False, 'content': delta, 'is_display': True}, ensure_ascii=False)}\n\n"
                                        prev_content = content

            # 发送会话 ID
            yield f"data: {json.dumps({'type': 'conversation_id', 'finished': False, 'content': conversation_id}, ensure_ascii=False)}\n\n"

            # 发送最终 sources（如果有）
            if final_sources:
                # 格式化 sources
                formatted_sources = []
                for source in final_sources:
                    if isinstance(source, str):
                        # 尝试解析嵌套的 JSON 字符串
                        try:
                            # 处理可能的嵌套结构
                            if source.startswith("[") or source.startswith("{"):
                                parsed = json.loads(source)
                                if isinstance(parsed, list):
                                    for item in parsed:
                                        if isinstance(item, dict):
                                            text = item.get("text", "")
                                            if text:
                                                # 尝试解析内部的 JSON
                                                try:
                                                    inner = json.loads(text)
                                                    if isinstance(inner, dict):
                                                        inner_answer = inner.get("answer", "")
                                                        inner_sources = inner.get("sources", [])
                                                        for src in inner_sources:
                                                            formatted_sources.append(str(src))
                                                except (json.JSONDecodeError, TypeError):
                                                    formatted_sources.append(text)
                                        else:
                                            formatted_sources.append(str(item))
                                elif isinstance(parsed, dict):
                                    text = parsed.get("text", "")
                                    if text:
                                        formatted_sources.append(text)
                            else:
                                formatted_sources.append(source)
                        except (json.JSONDecodeError, TypeError):
                            formatted_sources.append(source)
                    elif isinstance(source, dict):
                        text = source.get("text", "")
                        if text:
                            formatted_sources.append(text)
                    else:
                        formatted_sources.append(str(source))
                
                yield f"data: {json.dumps({'type': 'sources', 'finished': False, 'content': formatted_sources if formatted_sources else final_sources}, ensure_ascii=False)}\n\n"

            # 发送完成信号
            yield f"data: {json.dumps({'type': 'complete', 'finished': True, 'content': ''}, ensure_ascii=False)}\n\n"

        except asyncio.CancelledError:
            logger.info(f"[STREAM CANCELLED] 用户 {current_user.username} 的流式请求被取消，取消 LangGraph 任务")
            try:
                await asyncio.shield(svc.cancel_runs(thread_id=current_user.username, conversation_id=conversation_id))
            except asyncio.CancelledError:
                logger.info(f"[SHIELD CANCELLED] shield 被取消，但 cancel_runs 应该继续执行")
        except Exception as e:
            logger.error(f"[STREAM ERROR] {str(e)}")
            error_data = {
                "type": "error",
                "content": f"流式传输错误: {str(e)}",
                "finished": True,
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        content=event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

@router.get("/history")
async def get_user_history(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: LangGraphService = Depends(get_langgraph_service),
) -> List[ChatMessage]:
    """
    获取当前用户指定会话的历史消息。

    这里读取的是 LangGraph thread state 里的 messages，
    也就是"短期记忆"部分，而不是你额外存到 PostgreSQL 长期记忆表里的内容。
    """
    try:
        chat_history = await svc.get_history(
            thread_id=current_user.username,
            conversation_id=conversation_id,
        )
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))

    result: list[ChatMessage] = []
    for msg in chat_history:
        role = msg.get("role") or msg.get("type") or "ai"
        content = msg.get("content", "")
        if isinstance(content, list):
            content = "\n".join(str(item) for item in content)
        # 从消息元数据中提取sources，实现消息级别的sources关联
        sources = msg.get("sources", [])
        if not isinstance(sources, list):
            sources = []
        result.append(ChatMessage(role=str(role), content=str(content), sources=sources))
    return result


@router.post("/clear", response_model=CommonResponse)
async def chat_clear(
    req: ClearRequest,
    current_user: User = Depends(get_current_active_user),
    svc: LangGraphService = Depends(get_langgraph_service),
):
    """
    清空指定会话的 LangGraph 短期记忆。

    注意：
    - 当前只清理 LangGraph thread 状态
    - 不删除 PostgreSQL 长期记忆表中的历史沉淀
    """
    try:
        await svc.clear_history(
            thread_id=current_user.username,
            conversation_id=req.conversation_id,
        )
        return CommonResponse(status="success", message="会话已清空")
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear", response_model=CommonResponse)
async def chat_clear(
    _: ClearRequest,
    current_user: User = Depends(get_current_active_user),
    svc: LangGraphService = Depends(get_langgraph_service),
):
    """
    清空当前用户的 LangGraph 短期记忆。

    注意：
    - 当前只清理 LangGraph thread 状态
    - 不删除 PostgreSQL 长期记忆表中的历史沉淀
    """
    try:
        await svc.clear_history(thread_id=current_user.username)
        return CommonResponse(status="success", message="会话已清空")
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/resume/stream")
async def chat_resume_stream(
    req: ResumeRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    svc: LangGraphService = Depends(get_langgraph_service),
):
    """
    流式恢复被 interrupt 暂停的写作流程。
    """
    async def event_generator():
        try:
            final_sources = []
            prev_content = ""
            current_node = ""
            # 只有这些节点的内容会显示在对话中
            display_nodes = {"format_output", "chat_agent", "knowledge_agent", "fallback_search"}
            # 需要追踪的节点
            track_nodes = {
                "understand", "research", "outline", "draft",
                "review", "revise", "format_output",
                "chat_agent", "knowledge_agent", "fallback_search",
            }
            # 节点中文名称映射
            node_labels = {
                "understand": "正在理解需求...",
                "research": "正在搜索资料...",
                "outline": "正在生成大纲...",
                "draft": "正在撰写文章...",
                "review": "正在审核内容...",
                "revise": "正在修订内容...",
                "format_output": "正在格式化输出...",
                "chat_agent": "正在思考...",
                "knowledge_agent": "正在检索知识库...",
                "fallback_search": "正在搜索...",
            }

            async for event in svc.resume_stream(
                thread_id=current_user.username,
                conversation_id=req.conversation_id,
                action=req.action,
                content=req.content,
                answer=req.answer,
            ):
                # 检查客户端是否断开连接
                if await request.is_disconnected():
                    logger.info(f"[CLIENT DISCONNECTED] 用户 {current_user.username} 断开连接，取消正在运行的任务")
                    await svc.cancel_runs(thread_id=current_user.username, conversation_id=req.conversation_id)
                    break
                
                event_type = event.get("type", "")
                event_data = event.get("data", {})
                
                # 检测 interrupt 事件（resume 后可能再次遇到人机交互）
                if event_type == "updates" and isinstance(event_data, dict):
                    for node_name, node_output in event_data.items():
                        if isinstance(node_output, dict):
                            sources = node_output.get("sources", [])
                            if sources:
                                final_sources = sources

                    if "__interrupt__" in event_data:
                        interrupt_data = event_data["__interrupt__"]
                        yield f"data: {json.dumps({'type': 'interrupt', 'finished': False, 'content': interrupt_data}, ensure_ascii=False)}\n\n"
                        return

                # 通过 messages/metadata 事件判断进入哪个节点
                if event_type == "messages/metadata" and isinstance(event_data, dict):
                    for run_id, run_info in event_data.items():
                        if isinstance(run_info, dict):
                            metadata = run_info.get("metadata", {})
                            node_name = metadata.get("langgraph_node", "")
                            if node_name and node_name != current_node:
                                current_node = node_name
                                prev_content = ""
                                if node_name in track_nodes:
                                    label = node_labels.get(node_name, f"正在执行 {node_name}...")
                                    is_display = node_name in display_nodes
                                    yield f"data: {json.dumps({'type': 'node_start', 'finished': False, 'node': node_name, 'label': label, 'is_display': is_display}, ensure_ascii=False)}\n\n"
                    continue

                # 处理 messages/partial 事件
                if event_type == "messages/partial":
                    # current_node 为空时，不发送 content 事件
                    if not current_node:
                        continue
                    
                    # draft 节点的内容使用 article 事件类型发送
                    if current_node == 'draft':
                        if isinstance(event_data, list):
                            for msg_chunk in event_data:
                                if isinstance(msg_chunk, dict):
                                    content = msg_chunk.get("content", "")
                                    if content and isinstance(content, str):
                                        if prev_content and content.startswith(prev_content):
                                            delta = content[len(prev_content):]
                                        else:
                                            delta = content

                                        if delta:
                                            yield f"data: {json.dumps({'type': 'article', 'finished': False, 'content': delta, 'node': current_node}, ensure_ascii=False)}\n\n"
                                        prev_content = content
                    # 显示节点的内容使用 content 事件类型发送
                    elif current_node in display_nodes:
                        if isinstance(event_data, list):
                            for msg_chunk in event_data:
                                if isinstance(msg_chunk, dict):
                                    content = msg_chunk.get("content", "")
                                    if content and isinstance(content, str):
                                        if prev_content and content.startswith(prev_content):
                                            delta = content[len(prev_content):]
                                        else:
                                            delta = content

                                        if delta:
                                            yield f"data: {json.dumps({'type': 'content', 'finished': False, 'content': delta, 'is_display': True}, ensure_ascii=False)}\n\n"
                                        prev_content = content

            if final_sources:
                yield f"data: {json.dumps({'type': 'sources', 'finished': False, 'content': final_sources}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'complete', 'finished': True, 'content': ''}, ensure_ascii=False)}\n\n"

        except asyncio.CancelledError:
            logger.info(f"[STREAM CANCELLED] 用户 {current_user.username} 的流式请求被取消，取消 LangGraph 任务")
            try:
                await asyncio.shield(svc.cancel_runs(thread_id=current_user.username, conversation_id=req.conversation_id))
            except asyncio.CancelledError:
                logger.info(f"[SHIELD CANCELLED] shield 被取消，但 cancel_runs 应该继续执行")
        except Exception as e:
            logger.error(f"[STREAM ERROR] {str(e)}")
            error_data = {
                "type": "error",
                "content": f"流式传输错误: {str(e)}",
                "finished": True,
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        content=event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
