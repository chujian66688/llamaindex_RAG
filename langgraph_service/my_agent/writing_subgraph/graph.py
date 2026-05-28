"""
写作子工作流图定义。

本模块定义写作子图的执行流程和节点连接关系。

执行流程：
  START → understand → (需求清晰?) ─┬─ 是 → research → outline → draft → review
                                     │                              ↑
                                     └─ 否 → ask_clarification ─────┘
                                              (等待用户回答)           ↓
                                                          (通过) → human_review → format_output → END
                                                          (不通过) → revise → review (循环)

循环机制：
1. understand-ask_clarification 循环：需求不清晰时向用户提问，用户回答后重新理解需求
2. review-revise 循环：审核不通过时自动修订，然后重新审核
3. human_review-draft 循环：用户选择"重新生成"时回到 draft 节点
"""

from langgraph.graph import END, START, StateGraph

from my_agent.writing_subgraph.state import WritingState
from my_agent.writing_subgraph.nodes import (
    ask_clarification,
    clarification_router,
    draft,
    format_output,
    human_review,
    human_review_router,
    outline,
    research,
    review,
    review_router,
    revise,
    understand,
)


# ==============================
# 构建写作子工作流图
# ==============================

# 创建状态图实例，使用 WritingState 作为状态类型
builder = StateGraph(WritingState)

# ----- 添加所有节点 -----
# understand:        需求理解 - 分析用户写作需求，判断需求是否清晰
# ask_clarification: 澄清提问 - 需求不清晰时向用户提问
# research:          信息收集 - 搜索相关资料
# outline:           大纲规划 - 生成文章大纲
# draft:             章节写作 - 按大纲生成完整草稿
# review:            审稿检查 - 对草稿进行质量审核
# revise:            修订 - 根据审核意见修改草稿
# human_review:      人机交互 - 暂停执行，等待用户审阅
# format_output:     格式化输出 - 对最终内容进行格式优化，并作为子图最终输出
builder.add_node("understand", understand)
builder.add_node("ask_clarification", ask_clarification)
builder.add_node("research", research)
builder.add_node("outline", outline)
builder.add_node("draft", draft)
builder.add_node("review", review)
builder.add_node("revise", revise)
builder.add_node("human_review", human_review)
builder.add_node("format_output", format_output)

# ----- 定义边（节点连接关系） -----
# 入口：START → understand
builder.add_edge(START, "understand")

# 条件路由：understand → (research | ask_clarification)
# 根据需求清晰度决定下一步：
# - need_clarification=False → research（需求清晰，继续信息收集）
# - need_clarification=True  → ask_clarification（需求不清晰，向用户提问）
builder.add_conditional_edges(
    "understand",
    clarification_router,
    {
        "research": "research",
        "ask_clarification": "ask_clarification",
    },
)

# 循环边：ask_clarification → understand
# 用户回答后重新进入 understand 节点，形成 understand-ask_clarification 循环
builder.add_edge("ask_clarification", "understand")

# 线性流程：research → outline → draft → review
builder.add_edge("research", "outline")
builder.add_edge("outline", "draft")
builder.add_edge("draft", "review")

# 条件路由：review → (revise | human_review)
# 根据审核结果决定下一步：
# - review_passed=True  → human_review（进入人机交互）
# - review_passed=False → revise（进入修订）
builder.add_conditional_edges(
    "review",
    review_router,
    {
        "revise": "revise",
        "human_review": "human_review",
    },
)

# 循环边：revise → review
# 修订完成后重新进入审核节点，形成 revise-review 循环
builder.add_edge("revise", "review")

# 条件路由：human_review → (draft | format_output)
# 根据用户操作决定下一步：
# - human_action="rewrite" → draft（重新生成草稿）
# - human_action 其他值    → format_output（进入格式化输出）
builder.add_conditional_edges(
    "human_review",
    human_review_router,
    {
        "draft": "draft",
        "format_output": "format_output",
    },
)

# format_output 是子图的最终节点，直接连接到 END
builder.add_edge("format_output", END)

# ----- 编译子图 -----
# 编译后的子图可以作为节点添加到主图中
# LangGraph 会自动处理子图与主图之间的状态映射
writing_subgraph = builder.compile()

