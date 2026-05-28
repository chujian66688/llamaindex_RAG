"""
写作子工作流节点实现。

本模块包含写作子图的所有处理节点，按执行顺序排列：
1. understand         - 需求理解：分析用户写作需求，判断需求是否清晰
2. ask_clarification  - 澄清提问：需求不清晰时向用户提问，等待用户回答
3. research           - 信息收集：搜索相关资料
4. outline            - 大纲规划：生成文章大纲
5. draft              - 章节写作：按大纲生成完整草稿
6. review             - 审稿检查：对草稿进行质量审核
7. human_review       - 人机交互：暂停执行，等待用户审阅
8. revise             - 修订：根据审核意见修改草稿
9. format_output      - 格式化：对最终内容进行格式优化

执行流程：
  understand → (需求清晰?) ─┬─ 是 → research → outline → draft → review
                            │                              ↑
                            └─ 否 → ask_clarification ─────┘
                                     (等待用户回答)           ↓
                                                 (通过) → human_review → format → output
                                                 (不通过) → revise → review (循环)
"""

import logging
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from config.settings import Settings
from my_agent.writing_subgraph.state import WritingState
from my_agent.utils.tools import web_search

# 子图专用日志器
logger = logging.getLogger("writing_subgraph")


def get_llm() -> ChatOpenAI:
    """
    创建统一的 LLM 实例。

    Returns:
        配置好的 ChatOpenAI 实例
    """
    return ChatOpenAI(
        model=Settings.MODEL,
        api_key=Settings.API_KEY,
        base_url=Settings.API_BASE_URL,
        temperature=Settings.TEMPERATURE,
    )


# ==============================
# 节点实现
# ==============================
def understand(state: WritingState) -> WritingState:
    """
    需求理解节点：分析用户写作需求，提取关键信息，并判断需求是否清晰。

    输入：query（用户原始需求）、user_clarification（用户澄清，如有）
    输出：requirements（结构化需求分析）、need_clarification（是否需要提问）、clarification_question（澄清问题）

    分析维度：
    - 主题：用户要写什么
    - 字数要求：如有指定
    - 写作风格：正式/轻松/学术等
    - 目标读者：文章面向的受众
    - 其他特殊要求

    需求清晰度判断：
    - 如果用户需求过于模糊（如"帮我写篇文章"），则需要向用户提问澄清
    - 如果用户需求包含足够信息（如"帮我写一篇关于AI在医疗领域应用的科普文章，800字左右"），则直接继续
    """
    query = state.get("query", "")
    user_clarification = state.get("user_clarification", "")

    # 如果有用户的澄清回答，将其追加到原始需求中
    if user_clarification:
        full_query = f"{query}\n\n用户补充说明：{user_clarification}"
        logger.info(f"[understand] 收到用户澄清，重新理解需求 | clarification={user_clarification[:50]}...")
    else:
        full_query = query

    logger.info(f"[understand] 开始需求理解 | query={full_query[:50]}...")

    llm = get_llm()

    prompt = f"""你是一个需求分析专家。请分析用户的写作需求，并判断需求是否足够清晰。

## 重要规则

1. **如果用户已经提供了补充说明**，说明用户已经回答了之前的澄清问题，此时应该判断为 CLEAR，不要再提问
2. 只有在完全没有足够信息的情况下才判断为 UNCLEAR
3. 判断 CLEAR 的条件：至少明确了主题（写什么）和大致方向

## 分析任务

第一步：提取以下信息（如果能从需求中获取）：
1. 主题
2. 字数要求（如有）
3. 写作风格（正式/轻松/学术等）
4. 目标读者
5. 其他特殊要求

第二步：判断需求清晰度
- 如果用户提供了补充说明 → 一定是 CLEAR
- 如果需求包含足够的关键信息（至少明确了主题和大致方向）→ CLEAR
- 只有需求极其模糊（如只说"帮我写篇文章"、没有任何具体内容）→ UNCLEAR

## 输出格式

请严格按照以下格式输出：

【需求分析】
（这里输出结构化的需求分析结果）

【清晰度判断】
CLEAR 或 UNCLEAR（必须二选一，不要输出其他内容）

【澄清问题】
（仅当判断为 UNCLEAR 时输出，提出1-3个关键问题帮助理解用户需求）

## 用户需求
{full_query}"""

    result = str(llm.invoke(prompt).content)
    logger.info(f"[understand] LLM 原始输出 | result={result[:200]}...")

    # 解析 LLM 输出
    # 更健壮的判断逻辑：检查清晰度判断部分是否包含 UNCLEAR
    need_clarification = False
    if "【清晰度判断】" in result:
        # 提取清晰度判断部分
        clarity_start = result.index("【清晰度判断】") + len("【清晰度判断】")
        # 找到下一个标记或结尾
        clarity_end = len(result)
        for marker in ["【澄清问题】", "【需求分析】"]:
            if marker in result[clarity_start:]:
                marker_pos = clarity_start + result[clarity_start:].index(marker)
                clarity_end = min(clarity_end, marker_pos)
        clarity_text = result[clarity_start:clarity_end].strip()
        # 关键修复：UNCLEAR 包含 CLEAR 子串，必须用精确匹配
        # 提取第一行并去除空白，只判断第一个单词
        first_word = clarity_text.split()[0].upper() if clarity_text.split() else ""
        need_clarification = first_word == "UNCLEAR"

    # 如果有用户补充说明，强制设置为不需要澄清
    if user_clarification:
        need_clarification = False
        logger.info("[understand] 用户已提供补充说明，跳过澄清判断")

    # 提取需求分析部分
    requirements = ""
    if "【需求分析】" in result:
        req_start = result.index("【需求分析】") + len("【需求分析】")
        req_end = result.index("【清晰度判断】") if "【清晰度判断】" in result else len(result)
        requirements = result[req_start:req_end].strip()

    # 提取澄清问题
    clarification_question = ""
    if need_clarification and "【澄清问题】" in result:
        q_start = result.index("【澄清问题】") + len("【澄清问题】")
        clarification_question = result[q_start:].strip()

    # 如果解析失败，使用整个结果作为需求
    if not requirements:
        requirements = result

    logger.info(f"[understand] 需求理解完成 | need_clarification={need_clarification}")
    if need_clarification:
        logger.info(f"[understand] 需要向用户提问 | question={clarification_question[:100]}...")

    return {
        "requirements": requirements,
        "need_clarification": need_clarification,
        "clarification_question": clarification_question,
    }


def ask_clarification(state: WritingState) -> WritingState:
    """
    澄清提问节点：向用户提问以获取更清晰的需求描述。

    输入：clarification_question（需要向用户提出的问题）
    输出：user_clarification（用户的回答）

    使用 LangGraph 的 interrupt 机制暂停执行，
    将澄清问题发送给用户，等待用户提供更多信息。
    用户回答后会重新进入 understand 节点进行需求理解。

    interrupt 返回值由前端通过 Command(resume=...) 传入。
    """
    clarification_question = state.get("clarification_question", "请提供更多关于您写作需求的详细信息。")
    logger.info(f"[ask_clarification] 向用户提问 | question={clarification_question[:100]}...")

    # 构造发送给用户的消息
    content = f"您的需求描述不够清晰，我需要了解更多信息：\n\n{clarification_question}\n\n请补充说明您的写作需求。"

    # 先把问题写入消息历史
    ask_message = AIMessage(content=content)

    # 使用 interrupt 暂停执行，将问题发送给用户
    # interrupt 的返回值是前端通过 Command(resume=user_answer) 传入的数据
    user_answer = interrupt({
        "type": "clarification",
        "question": clarification_question,
        "message": content,
    })

    # 获取用户的回答
    user_response = user_answer.get("answer", "") if isinstance(user_answer, dict) else str(user_answer)
    logger.info(f"[ask_clarification] 收到用户回答 | answer={user_response[:100]}...")

    # 把用户的回答写入消息历史
    human_message = HumanMessage(content=user_response)

    return {
        "user_clarification": user_response,
        "messages": [ask_message, human_message],
    }


def clarification_router(state: WritingState) -> Literal["research", "ask_clarification"]:
    """
    澄清路由：根据需求清晰度决定下一步。

    路由逻辑：
    - need_clarification=True  → ask_clarification（向用户提问）
    - need_clarification=False → research（继续信息收集）

    这个路由函数实现了 understand-ask_clarification 的循环机制：
    当需求不清晰时，向用户提问，用户回答后重新理解需求。
    """
    need_clarification = state.get("need_clarification", False)
    if need_clarification:
        logger.info("[clarification_router] 需求不清晰 → ask_clarification")
        return "ask_clarification"
    logger.info("[clarification_router] 需求清晰 → research")
    return "research"


def research(state: WritingState) -> WritingState:
    """
    信息收集节点：根据需求搜索相关资料。

    输入：query（用户需求）、requirements（需求分析）
    输出：research_notes（搜索结果摘要）

    使用 web_search 工具搜索相关资料，为后续写作提供素材。
    如果搜索失败，返回提示信息，使用 LLM 已有知识创作。
    """
    query = state.get("query", "")
    requirements = state.get("requirements", "")
    logger.info(f"[research] 开始信息收集 | query={query[:50]}...")

    # 提取关键词进行搜索（限制长度避免过长）
    search_query = query
    try:
        search_result = web_search.invoke(search_query)
        logger.info(f"[research] 搜索完成 | 结果长度={len(str(search_result))}")
    except Exception as e:
        # 搜索失败时的降级处理
        search_result = "搜索暂不可用，请基于已有知识创作。"
        logger.warning(f"[research] 搜索失败，使用降级方案 | error={e}")

    return {"research_notes": str(search_result)}


def outline(state: WritingState) -> WritingState:
    """
    大纲规划节点：根据需求和资料生成文章大纲。

    输入：requirements（需求分析）、research_notes（参考资料）
    输出：outline（结构化大纲）

    大纲格式要求：
    - 层次分明（使用 一、1. (1) 等层级）
    - 每个章节标注大致字数
    - 逻辑连贯，结构完整
    """
    requirements = state.get("requirements", "")
    research_notes = state.get("research_notes", "")
    logger.info(f"[outline] 开始大纲规划 | 需求={requirements[:50]}...，资料长度={len(research_notes)}")
    llm = get_llm()

    prompt = f"""你是一个写作大纲规划专家。请根据以下信息生成一份清晰的文章大纲。

## 需求分析
{requirements}

## 参考资料
{research_notes}

要求：
- 大纲层次分明（使用 一、1. (1) 等层级）
- 每个章节标注大致字数
- 逻辑连贯，结构完整

请输出大纲："""

    result = str(llm.invoke(prompt).content)
    logger.info(f"[outline] 大纲生成完成 | 大纲长度={len(result)}")
    return {"outline": result}


def draft(state: WritingState) -> WritingState:
    """
    章节写作节点：根据大纲生成完整草稿。

    输入：outline（大纲）、requirements（需求）、research_notes（资料）
    输出：draft（完整草稿）

    写作要求：
    - 严格按照大纲结构撰写
    - 语言流畅，逻辑清晰
    - 内容充实，有理有据
    - 使用 Markdown 格式（标题、列表、加粗等）
    """
    outline_text = state.get("outline", "")
    requirements = state.get("requirements", "")
    research_notes = state.get("research_notes", "")
    human_action = state.get("human_action", "")
    logger.info(f"[draft] 开始章节写作 | 大纲长度={len(outline_text)}，human_action={human_action}")
    llm = get_llm()

    prompt = f"""你是一个专业的写作助手。请根据以下大纲和资料，撰写一篇完整的文章。

## 需求分析
{requirements}

## 文章大纲
{outline_text}

## 参考资料
{research_notes}

写作要求：
- 严格按照大纲结构撰写
- 语言流畅，逻辑清晰
- 内容充实，有理有据
- 适当使用 Markdown 格式（标题、列表、加粗等）

请输出完整文章："""

    result = str(llm.invoke(prompt).content)
    logger.info(f"[draft] 草稿生成完成 | 草稿长度={len(result)}")
    return {"draft": result}


def review(state: WritingState) -> WritingState:
    """
    审稿检查节点：对草稿进行质量审核。

    输入：draft（草稿）、requirements（需求）
    输出：review_feedback（审核意见）、review_passed（是否通过）

    审核维度：
    1. 结构完整性：是否符合大纲要求
    2. 内容质量：论点是否充分、逻辑是否清晰
    3. 语言表达：是否流畅、是否有错别字或语法错误
    4. 格式规范：Markdown 格式是否正确

    审核结论：
    - VERDICT: PASS - 质量合格，进入人机交互
    - VERDICT: REVISE - 需要修改，进入修订节点
    """
    draft_text = state.get("draft", "")
    requirements = state.get("requirements", "")
    print(requirements)
    logger.info(f"[review] 开始审稿检查 | 草稿长度={len(draft_text)}")
    llm = get_llm()

    prompt = f"""你是一个专业的文档审核专家。请从以下维度审核文章草稿：

1. **结构完整性**：是否符合大纲要求
2. **内容质量**：论点是否充分、逻辑是否清晰
3. **语言表达**：是否流畅、是否有错别字或语法错误
4. **格式规范**：Markdown 格式是否正确

## 原始需求
{requirements}

## 文章草稿
{draft_text}

请输出审核意见，并在最后给出结论：
- 如果质量合格，输出 "VERDICT: PASS"
- 如果需要修改，输出 "VERDICT: REVISE"
注意：只输出修改意见和"VERDICT: PASS"或者"VERDICT: REVISE"，不要输出其他内容。
"""

    result = str(llm.invoke(prompt).content)
    # 判断审核是否通过
    passed = "VERDICT: PASS" in result.upper()
    logger.info(f"[review] 审稿完成 | passed={passed}")
    if not passed:
        logger.info(f"[review] 审核未通过，将进入修订 | 审核意见前100字={result}")

    return {
        "review_feedback": result,
        "review_passed": passed,
    }


def human_review(state: WritingState) -> WritingState:
    """
    人机交互节点：暂停执行，等待用户审阅草稿。

    输入：draft（草稿）
    输出：human_action（用户操作）、draft/draft（可能被用户修改）

    使用 LangGraph 的 interrupt 机制暂停图执行，
    将草稿内容发送给用户审阅，等待用户选择：
    - approve: 确认通过，进入格式化
    - edit:    修改内容，使用用户提供的新内容
    - rewrite: 重新生成，回到 draft 节点

    interrupt 返回值由前端通过 Command(resume=...) 传入。
    """
    draft_text = state.get("draft", "")
    logger.info(f"[human_review] 进入人机交互 | 草稿长度={len(draft_text)}")
    logger.info(f"[human_review] 草稿前100字: {draft_text}...")
    content = f"请审阅草稿内容：\n\n{draft_text}\n\n您可以选择：确认通过、修改内容、或重新生成"
     # 先把"发给用户的内容"写入消息历史
    review_message = AIMessage(content=content)


    # 使用 interrupt 暂停执行，将草稿发送给用户审阅
    # interrupt 的返回值是前端通过 Command(resume=user_feedback) 传入的数据
    user_feedback = interrupt({
        "type": "human_review",
        "draft": content,
        "message": "请审阅草稿内容，您可以选择：确认通过、修改内容、或重新生成",
    })

    # 根据用户反馈处理
    action = user_feedback.get("action", "approve")
    logger.info(f"[human_review] 用户操作: {action}")
    
     # 把用户的操作也写入消息历史
    

    if action == "approve":
        human_message = HumanMessage(content=f"用户操作：确认通过")
        logger.info("[human_review] 用户确认通过，进入格式化")
        return {"messages": [review_message, human_message],
                "human_action": "approve"}
    elif action == "edit":
        # 用户修改了内容，更新 draft
        edited_content = user_feedback.get("content", draft_text)
        logger.info(f"[human_review] 用户修改内容 | 修改后长度={len(edited_content)}")
        human_message = HumanMessage(content=f"用户操作：修改内容")
        return {
            "messages": [review_message, human_message],
            "human_action": "edit",
            "human_edited_content": edited_content,
        }
    elif action == "rewrite":
        logger.info("[human_review] 用户选择重新生成，回到 draft 节点")
        human_message = HumanMessage(content=f"用户操作：重新生成")
        return {
            "messages": [review_message, human_message], 
            "human_action": "rewrite"
        }
    else:
        logger.warning(f"[human_review] 未知操作: {action}，默认确认通过")
        human_message = HumanMessage(content=f"用户操作：确认通过")
        return {
            "messages": [review_message, human_message],
            "human_action": "approve"
        }


def revise(state: WritingState) -> WritingState:
    """
    修订节点：根据审核意见修改草稿。

    输入：draft（原始草稿）、review_feedback（审核意见）
    输出：draft（修订后的草稿）

    修订要求：
    - 针对审核意见逐条修改
    - 保持文章整体结构
    - 提升内容质量

    修订后会重新进入 review 节点进行审核，形成 revise-review 循环。
    """
    draft_text = state.get("draft", "")
    review_feedback = state.get("review_feedback", "")
    logger.info(f"[revise] 开始修订 | 草稿长度={len(draft_text)}，审核意见长度={len(review_feedback)}")
    llm = get_llm()

    prompt = f"""你是一个专业的写作修订助手。请根据审核意见修改文章草稿。

## 审核意见
{review_feedback}

## 原始草稿
{draft_text}

修改要求：
- 针对审核意见逐条修改
- 保持文章整体结构
- 提升内容质量

请输出修订后的完整文章："""

    result = str(llm.invoke(prompt).content)
    logger.info(f"[revise] 修订完成 | 修订后草稿长度={len(result)}")
    return {"draft": result}


def format_output(state: WritingState) -> WritingState:
    """
    格式化输出节点：对最终内容进行格式优化，并作为子图的最终输出。

    输入：draft（最终草稿）
    输出：answer（最终内容）、sources、messages

    优化内容：
    - 确保 Markdown 格式规范
    - 检查标题层级
    - 优化段落间距
    - 确保列表格式正确

    这是子图的最后一个节点，负责将结果封装成主图期望的格式。
    """
    draft_text = state.get("human_edited_content") or state.get("draft", "")
    logger.info(f"[format_output] 开始格式化并输出 | 草稿长度={len(draft_text)}")
    llm = get_llm()

    prompt = f"""请对以下文章进行最终的格式优化：

1. 确保 Markdown 格式规范
2. 检查标题层级
3. 优化段落间距
4. 确保列表格式正确

## 文章内容
{draft_text}

请输出格式优化后的完整文章（仅输出文章内容，不要添加额外说明）："""

    result = str(llm.invoke(prompt).content)
    logger.info(f"[format_output] 格式化完成 | 输出长度={len(result)}")
    logger.info(f"[format_output] 输出前100字: {result[:100]}...")

    # 作为子图最终输出，封装成主图期望的格式
    return {
        "formatted_content": result,
        "answer": result,
        "sources": [],
        "messages": [AIMessage(content=result)],
    }


# ==============================
# 路由函数
# ==============================


def review_router(state: WritingState) -> Literal["revise", "human_review"]:
    """
    审核结果路由：根据审核结果决定下一步。

    路由逻辑：
    - review_passed=True  → human_review（进入人机交互）
    - review_passed=False → revise（进入修订）

    这个路由函数实现了 review-revise 的自动循环机制：
    当审核不通过时，自动进入修订节点修改草稿，然后重新审核。
    """
    passed = state.get("review_passed", False)
    if passed:
        logger.info("[review_router] 审核通过 → human_review")
        return "human_review"
    logger.info("[review_router] 审核未通过 → revise")
    return "revise"


def human_review_router(state: WritingState) -> Literal["draft", "format_output"]:
    """
    人机交互路由：根据用户操作决定下一步。

    路由逻辑：
    - human_action="rewrite" → draft（重新生成草稿）
    - human_action 其他值    → format_output（进入格式化）

    当用户选择"重新生成"时，会回到 draft 节点重新生成草稿，
    形成 human_review-draft-review 的大循环。
    """
    action = state.get("human_action", "approve")
    if action == "rewrite":
        logger.info("[human_review_router] 用户选择重新生成 → draft")
        return "draft"
    logger.info(f"[human_review_router] 用户操作={action} → format_output")
    return "format_output"

