from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class WritingState(TypedDict, total=False):
    """
    写作子工作流状态定义。

    设计说明：
    - 子图与主图共享的字段（如 query）通过 LangGraph 的 input/output 映射自动传递
    - 子图内部使用的字段（如 outline、draft）仅在子图执行期间有效，不会泄露到主图
    - total=False 表示所有字段都是可选的，节点只需返回需要更新的字段

    字段分组：
    1. 输入字段 - 从主图传入，用于初始化子图上下文
    2. 中间状态 - 子图各节点之间传递的中间结果
    3. 输出字段 - 子图执行完成后返回给主图的结果
    """

    # ===== 从主图传入的字段 =====
    # 这些字段由主图的 intent_router 节点设置，子图直接使用
    query: str          # 用户原始写作需求，如"帮我写一篇关于AI的文章"

    # ===== 子图内部状态 =====
    # understand 节点输出：需求分析结果
    # 包含主题、字数要求、写作风格、目标读者等结构化信息
    requirements: str

    # understand 节点输出：是否需要向用户提问澄清
    # True = 需求描述不清晰，需要向用户提问
    # False = 需求足够清晰，可以继续后续流程
    need_clarification: bool

    # understand 节点输出：向用户提出的澄清问题
    # 当 need_clarification=True 时，此字段包含具体的问题内容
    clarification_question: str

    # ask_clarification 节点输出：用户的澄清回答
    # 用户对澄清问题的回答内容，会被追加到 query 中供 understand 重新理解
    user_clarification: str

    # research 节点输出：搜索到的参考资料
    # 通过 web_search 工具获取的相关资料摘要
    research_notes: str

    # outline 节点输出：文章大纲
    # 层次分明的结构化大纲（一、1. (1) 等层级）
    outline: str

    # draft 节点输出：文章草稿
    # 根据大纲生成的完整文章内容（Markdown 格式）
    draft: str

    # review 节点输出：审核结果
    # review_feedback - 审核意见（包含 PASS/REVISE 结论）
    # review_passed - 审核是否通过（True=通过，False=需要修订）
    review_feedback: str
    review_passed: bool

    # revise 节点输出：修订后的草稿
    # 根据审核意见修改后的文章内容
    revised_draft: str

    # format_output 节点输出：格式化后的内容
    # 经过最终格式优化的文章（确保 Markdown 格式规范）
    formatted_content: str

    # human_review 节点使用：人机交互状态
    # human_action - 用户操作类型：
    #   "approve" = 确认通过，进入格式化
    #   "edit"    = 修改内容，使用 human_edited_content
    #   "rewrite" = 重新生成，回到 draft 节点
    # human_edited_content - 用户手动编辑后的内容
    human_action: str
    human_edited_content: str

    # ===== 输出给主图的字段 =====
    # 子图执行完成后，这些字段会被传递回主图
    # 主图的 finalize 节点会读取这些字段并返回给前端
    answer: str                              # 最终输出内容
    sources: list[str]                       # 来源信息（写作场景暂为空列表）
    messages: Annotated[list[Any], add_messages]  # 消息列表（用于历史记录）

