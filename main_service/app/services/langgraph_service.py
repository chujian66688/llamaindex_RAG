from __future__ import annotations

import json
from typing import Any, AsyncIterator
from uuid import NAMESPACE_URL, uuid5

from langgraph_sdk import get_client
from langgraph_sdk.schema import Command

from config.settings import Settings


class LangGraphService:
    """
    FastAPI -> LangGraph 的调用适配层。

    这个类的职责非常单一：
    - FastAPI 路由不直接理解 LangGraph 的 HTTP 协议
    - 统一在这里封装对 LangGraph Server 的请求方式

    这样做的好处：
    1. 路由层更干净
    2. 后续如果 LangGraph API 路径变了，只改这里
    3. 可以集中处理超时、错误与返回结构转换
    """

    def __init__(self, base_url: str | None = None, assistant_id: str | None = None):
        self.base_url = (base_url or Settings.LANGGRAPH_API_URL).rstrip("/")
        self.assistant_id = assistant_id or Settings.LANGGRAPH_ASSISTANT_ID
        self.client = get_client(url=self.base_url)

    def _thread_uuid(self, thread_id: str, conversation_id: str | None = None) -> str:
        """
        把业务侧 thread_id 稳定映射成 LangGraph 需要的 UUID。

        当提供 conversation_id 时，每个会话对应独立的 LangGraph Thread。
        否则使用 thread_id 作为唯一标识（兼容旧逻辑）。
        """
        if conversation_id:
            return str(uuid5(NAMESPACE_URL, f"langgraph-thread:{thread_id}:{conversation_id}"))
        return str(uuid5(NAMESPACE_URL, f"langgraph-thread:{thread_id}"))

    async def _ensure_thread(self, thread_id: str) -> None:
        """确保 LangGraph thread 已存在；已存在则忽略。"""
        try:
            await self.client.threads.get(thread_id)
            return
        except Exception:
            pass

        try:
            await self.client.threads.create(thread_id=thread_id)
        except Exception as exc:
            message = str(exc).lower()
            if "already exists" in message or "409" in message:
                return
            raise

    def _extract_text(self, content: Any) -> str:
        """把 LangGraph / LangChain message content 统一转成文本。"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content") or ""
                    if text:
                        parts.append(str(text))
                else:
                    parts.append(str(item))
            return "\n".join(part for part in parts if part)
        if content is None:
            return ""
        return str(content)

    def _extract_answer(self, payload: dict[str, Any]) -> tuple[str, list[Any], str]:
        """兼容不同 LangGraph 返回结构，提取 answer / sources / intent。"""
        # 检测 interrupt 事件（人机交互）
        interrupt_data = payload.get("__interrupt__")
        if interrupt_data:
            # 返回特殊标记，让调用方知道这是 interrupt
            return "__INTERRUPT__", [], "interrupt"

        output = payload.get("output") if isinstance(payload, dict) else None
        if isinstance(output, dict):
            answer = self._extract_text(output.get("answer", ""))
            sources = output.get("sources", []) or []
            intent = str(output.get("intent", "") or "")
            if answer:
                return answer, sources, intent

        values = payload.get("values", {}) if isinstance(payload, dict) else {}
        if not isinstance(values, dict):
            values = {}

        answer = self._extract_text(values.get("answer", ""))
        intent = str(values.get("intent", "") or "")
        
        # 从最后一条AI消息中提取sources（统一从AIMessage中获取）
        messages = values.get("messages", []) or payload.get("messages", []) or []
        sources = []
        if isinstance(messages, list):
            for msg in reversed(messages):
                if not isinstance(msg, dict):
                    continue
                msg_type = str(msg.get("type") or msg.get("role") or "").lower()
                if msg_type in {"ai", "assistant"}:
                    # 从additional_kwargs中提取sources
                    additional_kwargs = msg.get("additional_kwargs", {})
                    if isinstance(additional_kwargs, dict):
                        sources = additional_kwargs.get("sources", []) or []
                    # 如果answer为空，从消息中提取
                    if not answer:
                        answer = self._extract_text(msg.get("content", ""))
                    return answer, sources, intent

        return answer, sources, intent

    async def chat(
        self,
        *,
        thread_id: str,
        conversation_id: str | None = None,
        query: str,
        knowledge_bool: bool | None = None,
    ) -> dict[str, Any]:
        """
        发起一次 LangGraph 对话调用。

        这里切到官方 `langgraph-sdk` 调用方式：
        - 使用 `client.runs.wait(...)` 发起一次等待完成的 run
        - 当前轮输入直接作为 `messages` 传入
        - 同一个 `thread_id` 下，历史消息由 checkpointer 自动恢复
        """
        graph_thread_id = self._thread_uuid(thread_id, conversation_id)
        await self._ensure_thread(graph_thread_id)

        input_payload: dict[str, Any] = {
            "messages": [
                {"type": "human", "content": query}
            ],
            "user_id": thread_id,
        }
        if knowledge_bool is not None:
            input_payload["knowledge_bool"] = knowledge_bool

        payload = await self.client.runs.wait(
            graph_thread_id,
            self.assistant_id,
            input=input_payload,
            multitask_strategy="interrupt",
            config={
                "configurable": {
                    "thread_id": graph_thread_id,
                    "user_id": thread_id,
                }
            },
        )
        # 提取 answer / sources / intent 数据
        answer, sources, intent = self._extract_answer(payload if isinstance(payload, dict) else {})
        
        # 检测是否是 interrupt（人机交互）
        is_interrupt = answer == "__INTERRUPT__"
        if is_interrupt:
            # 提取 interrupt 中的内容
            interrupt_data = (payload if isinstance(payload, dict) else {}).get("__interrupt__", [])
            draft = ""
            interrupt_type = "human_review"  # 默认为草稿审阅
            clarification_question = ""
            # 兼容 interrupt 数据结构
            if interrupt_data and isinstance(interrupt_data, list) and len(interrupt_data) > 0:
                value = interrupt_data[0].get("value", {})
                interrupt_type = value.get("type", "human_review")
                if interrupt_type == "clarification":
                    # 澄清提问类型
                    clarification_question = value.get("question", "")
                    draft = value.get("message", "")
                else:
                    # 草稿审阅类型
                    draft = value.get("draft", "")
            return {
                "answer": draft,
                "sources": [],
                "intent": "interrupt",
                "thread_id": thread_id,
                "raw": payload,
                "is_interrupt": True,
                "interrupt_type": interrupt_type,
                "clarification_question": clarification_question,
            }
        
        return {
            "answer": answer,
            "sources": sources,
            "intent": intent,
            "thread_id": thread_id,
            "raw": payload,
            "is_interrupt": False,
        }

    async def chat_stream(
        self,
        *,
        thread_id: str,
        conversation_id: str | None = None,
        query: str,
        knowledge_bool: bool | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        流式聊天：使用 LangGraph SDK 的 stream 方法逐步返回事件。
        
        使用 v2 格式 + stream_mode=["messages", "updates"]：
        - v2 格式：统一的 StreamPart 输出格式
        - messages 模式：token 级别的流式输出
        - updates 模式：节点级别的状态更新
        """
        graph_thread_id = self._thread_uuid(thread_id, conversation_id)
        print(f"[LangGraph] chat_stream: {graph_thread_id}")
        await self._ensure_thread(graph_thread_id)

        input_payload: dict[str, Any] = {
            "messages": [
                {"type": "human", "content": query}
            ],
            "user_id": thread_id,
        }
        if knowledge_bool is not None:
            input_payload["knowledge_bool"] = knowledge_bool
        async for event in self.client.runs.stream(
            graph_thread_id,
            self.assistant_id,
            input=input_payload,
            stream_mode=["messages", "updates"],
            stream_subgraphs=True,
            multitask_strategy="interrupt", 
            version="v2",
            config={
                "configurable": {
                    "thread_id": graph_thread_id,
                    "user_id": thread_id,
                }
            },
        ):
            # v2 格式下 event 已经是 dict：{"type": ..., "ns": ..., "data": ...}
            yield event

    async def get_history(self, *, thread_id: str, conversation_id: str | None = None) -> list[dict[str, Any]]:
        """获取指定 thread 的 LangGraph 状态中的 messages 历史。"""
        graph_thread_id = self._thread_uuid(thread_id, conversation_id)
        await self._ensure_thread(graph_thread_id)
        payload = await self.client.threads.get_state(graph_thread_id)
        values = payload.get("values", {}) if isinstance(payload, dict) else {}
        messages = values.get("messages", []) or []
        
        # 提取消息元数据中的sources，实现消息级别的sources关联
        result = []
        for msg in messages:
            if isinstance(msg, dict):
                # 从additional_kwargs中提取sources
                additional_kwargs = msg.get("additional_kwargs", {})
                sources = additional_kwargs.get("sources", []) if isinstance(additional_kwargs, dict) else []
                # 将sources添加到消息字典中
                msg_with_sources = {**msg, "sources": sources}
                result.append(msg_with_sources)
            else:
                result.append(msg)
        
        return result

    async def clear_history(self, *, thread_id: str, conversation_id: str | None = None) -> None:
        """删除指定 thread 的 LangGraph 状态。"""
        await self.client.threads.delete(self._thread_uuid(thread_id, conversation_id))

    async def cancel_runs(
        self,
        *,
        thread_id: str,
        conversation_id: str | None = None,
        action: str = "interrupt",
    ) -> None:
        """
        取消指定 thread 上正在运行的任务。

        Args:
            thread_id: 业务侧 thread_id
            conversation_id: 会话 ID
            action: 取消动作，"interrupt" 或 "rollback"
        """
        graph_thread_id = self._thread_uuid(thread_id, conversation_id)
        print("取消 thread:", graph_thread_id)
        try:
            runs = await self.client.runs.list(thread_id=graph_thread_id)
            print("运行中的任务：", runs)
            if not runs:
                print("没有可取消的 run")
                return
            first_run = runs[0]
            await self.client.runs.cancel(
                thread_id=graph_thread_id,
                run_id=first_run["run_id"],
                action=action,
            )

            print("已取消第一个 run:", first_run["run_id"])
        except Exception as e:
            # 如果没有找到运行中的任务，忽略错误
            if "not found" in str(e).lower() or "404" in str(e):
                return
            raise


    async def resume_stream(
        self,
        *,
        thread_id: str,
        conversation_id: str | None = None,
        action: str,
        content: str | None = None,
        answer: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        流式恢复被 interrupt 暂停的图执行。
        """
        graph_thread_id = self._thread_uuid(thread_id, conversation_id)

        # 构造 resume 数据
        if action == "clarify":
            # 澄清回答：使用 {"answer": "..."} 格式
            resume_data = {"answer": answer or content or ""}
        else:
            # 草稿审阅：使用 {"action": "...", "content": "..."} 格式
            resume_data = {"action": action}
            if action == "edit" and content is not None:
                resume_data["content"] = content

        # 使用 Command(resume=...) 恢复执行
        async for event in self.client.runs.stream(
            graph_thread_id,
            self.assistant_id,
            stream_mode=["messages", "updates"],
            stream_subgraphs=True,
            version="v2",
            multitask_strategy="interrupt",
            command=Command(resume=resume_data),
            config={
                "configurable": {
                    "thread_id": graph_thread_id,
                    "user_id": thread_id,
                }
            },
        ):
            yield event
