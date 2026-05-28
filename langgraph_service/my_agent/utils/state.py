from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages
from langmem.short_term import RunningSummary


class GraphState(TypedDict, total=False):
    """
    LangGraph 整体状态对象。

    这里采用官方短期记忆摘要模式：
    - `messages` 使用 LangGraph 官方消息追加机制自动维护完整历史
    - `context` 中存放 `RunningSummary`，用于跨轮累积摘要
    - `summarized_messages` 由 `SummarizationNode` 生成，供后续节点直接消费

    这样模型不再依赖手工裁剪消息，而是依赖"历史摘要 + 最近消息"的组合。
    """

    # 官方风格的消息状态字段：自动追加，不手工拼接。
    messages: Annotated[list[Any], add_messages]

    # 短期记忆摘要上下文，由 langmem 维护。
    context: dict[str, RunningSummary]

    # SummarizationNode 生成的消息输入，供下游节点直接使用。
    summarized_messages: list[Any]

    # 下面这些是业务字段，保留多智能体流程需要的上下文信息。
    user_id: str
    intent: str
    answer: str
    sources: list[str]
    search_notes: list[str]
    draft: str
    review: str

    # 前端传入的控制参数
    knowledge_bool: bool

    # 人机交互相关字段
    human_action: str  # 用户操作：approve / edit / rewrite
    human_edited_content: str  # 用户编辑后的内容
