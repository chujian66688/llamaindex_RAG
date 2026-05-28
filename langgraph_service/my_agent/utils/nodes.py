from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.messages.utils import count_tokens_approximately
from langchain_openai import ChatOpenAI
from langmem.short_term import SummarizationNode
import json
from config.settings import Settings
from my_agent.utils.state import GraphState
from my_agent.utils.tools import call_mcp_tool, web_search


# 用于正常回答的大模型。
def get_llm() -> ChatOpenAI:
    """创建统一的 LLM 实例，供图中各节点复用。"""
    return ChatOpenAI(
        model=Settings.MODEL,
        api_key=Settings.API_KEY,
        base_url=Settings.API_BASE_URL,
        temperature=Settings.TEMPERATURE,
    )


# 用于短期记忆摘要的模型。
# 这里绑定更小的 max_tokens，避免摘要本身过长。
summarization_model = get_llm().bind(max_tokens=128)

# 官方风格的短期记忆摘要节点：
# - 当历史消息过长时，自动把旧消息压缩成 running summary
# - 生成 `summarized_messages` 给后续节点使用
summarization_node = SummarizationNode(
    token_counter=count_tokens_approximately,
    model=summarization_model,
    max_tokens=4096,
    max_tokens_before_summary=2048,
    max_summary_tokens=512,
)


def get_latest_user_query(state: GraphState) -> str:
    """从 messages 中提取最近一条用户消息，作为当前轮的 query。"""
    messages = state.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            content = message.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "\n".join(str(item) for item in content)
            return str(content)
    return ""


def get_model_messages(state: GraphState) -> list:
    """
    获取供节点调用模型时使用的消息。

    优先使用 `summarized_messages`：
    - 这是一份"摘要后的短期记忆 + 最近原始消息"组合
    - 更适合多轮长对话

    如果摘要节点暂时没有提供输出，则退回原始 messages。
    """
    summarized_messages = state.get("summarized_messages")
    print("summarized_messages:", summarized_messages)
    if summarized_messages:
        return list(summarized_messages)
    return list(state.get("messages", []))


def intent_router(state: GraphState) -> GraphState:
    """主智能体：识别当前请求应路由到知识库、写作还是闲聊。"""
    # 如果前端显式指定了 knowledge_bool，直接按用户意图路由
    knowledge_bool = state.get("knowledge_bool")
    if knowledge_bool is True:
        return {"intent": "knowledge"}
    if knowledge_bool is False:
        # 用户关闭知识库，只在 writing 和 chat 之间选择
        query = get_latest_user_query(state)
        llm = get_llm()
        prompt = f"""### 角色设定
            你是一个高精准度的意图识别专家。将用户输入归类到以下两个模块之一。

            ### 模块定义
            1. **writing (创作文案)**：涉及文本生成、润色、翻译、代码编写或创意写作请求。
               - 关键特征：用户明确要求"写"、"创作"、"生成"、"撰写"某些内容
               - 示例："帮我写一篇文章"、"写一个故事"、"生成一份报告"、"帮我写代码"、"创作一首诗"
            2. **chat (闲聊互动)**：涉及情感咨询、日常问候、主观观点交流或无明确任务指向的交谈。
               - 关键特征：用户在聊天、问问题、寻求建议，而不是要求创作内容
               - 示例："你好"、"今天心情不好"、"你觉得怎么样"、"给我讲个笑话"

            ### 强制约束
            - 只输出 [writing, chat] 中的一个，严禁包含任何解释。
            - 如果用户明确要求"写"某些内容，必须输出 writing。

            ### 待处理输入
            用户问题：{query}

            ### 最终指令
            输出意图标签："""
        result = str(llm.invoke(prompt).content).strip().lower()
        if "writing" in result or "写作" in result:
            intent = "writing"
        else:
            intent = "chat"
        return {"intent": intent}

    # knowledge_bool 未设置，走原有 LLM 意图识别
    query = get_latest_user_query(state)
    llm = get_llm()
    prompt = f"""### 角色设定
你是一个高精准度的意图识别主控专家。你的任务是分析用户的输入，并将其归类到指定的三个功能模块之一。

### 模块定义
1. **knowledge (知识检索)**：
   - 涉及事实性问题、百科知识、学术定义或需要查阅外部资料的情况。
   - 示例："量子纠缠是什么？"、"帮我查一下去年的GDP数据"。
2. **writing (创作文案)**：
   - 涉及文本生成、润色、翻译、代码编写或创意写作请求。
   - 关键特征：用户明确要求"写"、"创作"、"生成"、"撰写"某些内容
   - 示例："帮我写一封辞职信"、"把这段话翻译成英文"、"写一个Python爬虫"、"帮我写一篇文章"、"创作一首诗"、"生成一份报告"
3. **chat (闲聊互动)**：
   - 涉及情感咨询、日常问候、主观观点交流或无明确任务指向的交谈。
   - 关键特征：用户在聊天、问问题、寻求建议，而不是要求创作内容
   - 示例："你好呀"、"你今天心情怎么样？"、"你觉得人工智能会取代人类吗？"、"给我讲个笑话"

### 强制约束
- **唯一输出**：只能输出单词 [knowledge, writing, chat] 中的一个，严禁包含任何解释、标点或引言。
- **写作优先**：如果用户明确要求"写"某些内容，必须输出 writing。
- **缺省处理**：如果意图模糊，请优先选择最接近的分类；若完全无法判断，默认输出 chat。

### 待处理输入
用户问题：{query}

### 最终指令
输出意图标签："""
    result = str(llm.invoke(prompt).content).strip().lower()
    if "writing" in result or "写作" in result:
        intent = "writing"
    elif "knowledge" in result or "知识" in result or "检索" in result:
        intent = "knowledge"
    else:
        intent = "chat"
    return {"intent": intent}


def _extract_sources(raw_sources: Any) -> list[str]:
    """递归提取 sources 列表中的文本内容。"""
    if not raw_sources:
        return []
    if isinstance(raw_sources, str):
        try:
            parsed = json.loads(raw_sources)
            return _extract_sources(parsed)
        except (json.JSONDecodeError, TypeError):
            return [raw_sources]
    if isinstance(raw_sources, dict):
        text = raw_sources.get("text", "")
        if text:
            try:
                inner = json.loads(text)
                return _extract_sources(inner)
            except (json.JSONDecodeError, TypeError):
                return [text]
        return []
    if isinstance(raw_sources, list):
        result = []
        for item in raw_sources:
            result.extend(_extract_sources(item))
        return result
    return [str(raw_sources)]


def _parse_rag_response(response: dict) -> tuple[str, list[str]]:
    """解析 RAG 响应，提取 answer 和 sources。"""
    answer = str(response.get("answer", ""))
    raw_sources = response.get("sources", [])

    # 尝试从 sources 中提取嵌套的 answer
    if isinstance(raw_sources, list):
        for item in raw_sources:
            if isinstance(item, str) and (item.startswith("[") or item.startswith("{")):
                try:
                    parsed = json.loads(item)
                    if isinstance(parsed, dict) and parsed.get("answer"):
                        answer = parsed["answer"]
                except (json.JSONDecodeError, TypeError):
                    pass

    formatted_sources = _extract_sources(raw_sources)
    return answer, formatted_sources or (raw_sources if isinstance(raw_sources, list) else [])


async def knowledge_agent(state: GraphState) -> GraphState:
    """知识库子智能体：通过 MCP 调用现有 RAG。"""
    query = get_latest_user_query(state)
    tool_args: dict = {
        "query": query,
    }
    response = await call_mcp_tool("query_rag", tool_args)
    print("knowledge_agent response:", response)

    if isinstance(response, dict):
        answer, sources = _parse_rag_response(response)
        # 将sources存储到AIMessage的元数据中，实现消息级别的sources关联
        ai_message = AIMessage(
            content=answer,
            additional_kwargs={"sources": sources}
        )
        return {
            "answer": answer,
            "messages": [ai_message],
        }

    answer = str(response)
    return {
        "answer": answer,
        "messages": [AIMessage(content=answer)],
    }


def knowledge_guard(state: GraphState) -> Literal["fallback_search", "finalize"]:
    """知识库结果守卫：知识库答不好时，切换到搜索兜底。"""
    answer = (state.get("answer") or "").strip()
    if (not answer) or ("查询失败" in answer) or ("不知道" in answer):
        return "fallback_search"
    return "finalize"


def fallback_search_agent(state: GraphState) -> GraphState:
    """搜索兜底节点。"""
    query = get_latest_user_query(state)
    note = web_search.invoke(query)
    return {
        "answer": note,
        "sources": [],
        "search_notes": [note],
        "messages": [AIMessage(content=note)],
    }


def chat_agent(state: GraphState) -> GraphState:
    """
    普通聊天节点。

    现在不再手工 trim 历史消息，
    而是直接使用 `SummarizationNode` 产出的 `summarized_messages`。

    即：
    - 历史完整消息由 `messages + checkpointer` 自动维护
    - 长对话压缩由 `SummarizationNode` 自动维护
    - 当前节点只消费摘要结果并返回新的 AI 消息
    """
    
    llm = get_llm()
    prompt_messages = [
        SystemMessage(content="你是普通对话子智能体，直接自然回答用户。"),
        *get_model_messages(state),
    ]
    print(f"[DEBUG] chat_agent: {prompt_messages}")
    answer = str(llm.invoke(prompt_messages).content)
    return {
        "answer": answer,
        "sources": [],
        "messages": [AIMessage(content=answer)],
    }


def finalize(state: GraphState) -> GraphState:
    """收尾节点：返回业务字段。"""
    # 从最后一条AI消息中提取sources（统一从AIMessage中获取）
    sources = []
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "additional_kwargs") and isinstance(msg.additional_kwargs, dict):
            sources = msg.additional_kwargs.get("sources", []) or []
            break
        elif isinstance(msg, dict):
            additional_kwargs = msg.get("additional_kwargs", {})
            if isinstance(additional_kwargs, dict):
                sources = additional_kwargs.get("sources", []) or []
                break
    
    return {
        "answer": state.get("answer", ""),
        "sources": sources,
        "intent": state.get("intent", "chat"),
    }


# ==============================
# 写作子图包装函数
# ==============================
# 由于父图 (GraphState) 和子图 (WritingState) 的状态结构不同，
# 不能直接把子图作为节点添加到父图。
# 需要通过包装函数手动调用子图，并进行状态转换。


def call_writing_subgraph(state: GraphState) -> dict:
    """
    写作子图包装函数：调用写作子工作流。

    状态转换说明：
    - 父图 → 子图：将 GraphState 中的字段映射为 WritingState 需要的字段
      - query (用户消息) → query

    - 子图 → 父图：将 WritingState 的输出映射回 GraphState
      - answer → answer
      - sources → sources
      - messages → messages

    Args:
        state: 父图状态 (GraphState)

    Returns:
        更新父图状态的字典
    """
    from my_agent.writing_subgraph import writing_subgraph

    # 从父图状态中提取用户消息作为 query
    query = get_latest_user_query(state)
    print(f"[writing_workflow] 调用写作子图 | query={query[:50]}...")

    # 构造子图输入状态
    subgraph_input = {
        "query": query,
    }

    # 调用子图
    subgraph_output = writing_subgraph.invoke(subgraph_input)

    # 将子图输出映射回父图状态
    print(f"[writing_workflow] 子图执行完成 | answer长度={len(subgraph_output.get('answer', ''))}")

    return {
        "answer": subgraph_output.get("answer", ""),
        "sources": subgraph_output.get("sources", []),
        "messages": subgraph_output.get("messages", []),
    }
