import json
from typing import List, Optional, Tuple, Dict, Any, AsyncGenerator
from core.ingestion import DocumentIngestionPipeline
from core.workflow import RAGWorkflow
from utils.logger import setup_logger
from llama_index.core import Settings
from config.settings import Settings as AppSettings
import base64
import copy
from pathlib import Path
import os

logger = setup_logger(__name__)


def image_to_base64(path: str) -> str:
    """将图片文件转为 Base64 字符串，方便前端 <img src='data:...'> 内联展示"""
    try:
        file_name = Path(path).name
        file_path = AppSettings.PDF_IMAGE_DIR + rf"\{file_name}"
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"图片转Base64失败: {e}")
        return ""


class RAGApplication:
    """
    RAG 应用主类
    - 负责：文档摄取（ingestion）、检索与生成（workflow）、多会话管理（session_id）
    - 对外方法：
        * upload_and_process_files(files) -> str
        * query_documents(session_id, query, docs_selects, history, top_k) -> (history, err)
        * clear_session(session_id) -> None
        * clear_chat() -> List  (保留以兼容旧接口，不推荐新用)
        * reset() -> None
    """

    def __init__(self) -> None:
        # 文档摄取流水线（解析/切分/向量化/建索引）
        self.ingestion_pipeline = DocumentIngestionPipeline()
        # 启动时尝试加载已有索引
        self.ingestion_pipeline.get_documents()
        # RAG 工作流，基于索引构建；懒加载
        self.workflow: Optional[RAGWorkflow] = None

        # 结构：{ session_id: [ {"role": "...", "content": "..."}, ... ] }
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}

    def update_model_config(self, model_name: str, temperature: float, max_tokens: int):
        """让外部能直接更新模型"""
        self.ingestion_pipeline.update_model_config(model_name, temperature, max_tokens)

    # -----------------------------
    # 文档摄取与索引
    # -----------------------------
    def upload_and_process_files(self, files) -> Tuple:
        """
        上传并处理文件（构建或更新索引）
        参数:
            files: 文件对象或路径集合；若对象带 .name 则取其路径，否则 str(file)
        返回:
            摄取结果说明字符串
        """
        if not files:
            return "请上传至少一个文件"

        try:
            file_paths: List[str] = []
            for file in files:
                if hasattr(file, "name"):
                    file_paths.append(file.name)
                else:
                    file_paths.append(str(file))

            # 摄取并构建/更新索引
            status, result, pipeline_nodes = self.ingestion_pipeline.ingest_documents(file_paths)
            if status == "error":
                raise RuntimeError(result)

            # 若有可用索引，则初始化构建工作流
            if self.ingestion_pipeline.index:
                self.workflow = RAGWorkflow(self.ingestion_pipeline.index, pipeline_nodes)

            return status, result

        except Exception as e:
            error_msg = f"文件处理失败: {str(e)}"
            logger.error(error_msg)
            return error_msg

    # -----------------------------
    # 工具方法
    # -----------------------------

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        取出某个会话的历史列表；若不存在则初始化为空列表。
        注意：返回的是容器内的引用，可直接 append。
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def get_safe_history(self, session_history: List[Dict[str, Any]],
                         max_history_length: int = 5,
                         max_token_limit: int = 4000) -> List[Dict[str, Any]]:
        """
        获取用于发送给 LLM 的安全历史记录。
        优化点：
        1. 彻底移除 'sources' 字段（包含Base64图片和长文本），模型不需要看旧的检索源。
        2. 增加字符/Token估算限制，防止上下文溢出。

        Args:
            session_history: 原始会话历史
            max_history_length: 保留最近 N 轮对话
            max_token_limit: 估算的最大字符限制 (粗略按 1 token ≈ 2-3 chars 估算，这里设为字符数阈值)

        Returns:
            List[Dict[str, Any]]: 精简后的历史列表
        """
        if not session_history:
            return []

        # 1. 深拷贝，避免修改原始 session 数据（原始数据包含图片用于前端展示）
        # 只取最近的 N 轮 (user + assistant = 2条，所以 * 2)
        slice_index = max(0, len(session_history) - (max_history_length * 2))
        recent_history = copy.deepcopy(session_history[slice_index:])

        clean_history = []
        current_char_count = 0
        # 设定一个字符上限（例如 12000 字符，约 4k-6k tokens，根据你的模型调整）
        CHAR_LIMIT = max_token_limit * 3

        # 2. 倒序处理：优先保留最近的对话
        for msg in reversed(recent_history):
            # --- 核心优化：移除 sources 字段 ---
            # 历史记录中的 sources 包含 Base64 图片和长文档，LLM 上下文不需要它们
            if "sources" in msg:
                del msg["sources"]

            # --- 核心优化：移除可能混入 content 中的 Base64 ---
            # 如果你的 content 字段里也意外混入了 html 标签或 base64，可以在这里清理
            # 这里假设 content 是纯文本，如果不是，可以用正则清理
            content_str = str(msg.get("content", ""))

            # 3. 长度检查
            msg_len = len(content_str)
            if current_char_count + msg_len > CHAR_LIMIT:
                logger.info(f"历史记录触达字符限制，已截断。当前保留字符数: {current_char_count}")
                break

            current_char_count += msg_len
            clean_history.insert(0, msg)  # 插到最前面，恢复顺序

        # 4. 确保第一条是 user (某些模型要求 user 开头)
        if clean_history and clean_history[0]["role"] == "assistant":
            # 如果截断后第一条是 assistant，通常为了上下文连贯性可以选择丢弃，或者保留（视模型鲁棒性而定）
            # 这里选择保留，但打个日志
            pass

        return clean_history

    def _ensure_workflow(self, streaming: bool):
        """
        [状态管理] 确保 Workflow 已初始化，且处于正确的流式/非流式模式。

        背景:
            LlamaIndex 的 ResponseSynthesizer 在初始化时就决定了是 'streaming' 还是 'compact'。
            如果用户上一次请求是非流式，这一次是流式，我们需要重新构建 Workflow 实例，
            否则调用 .run() 时行为会不符合预期。

        Args:
            streaming (bool): 本次请求是否期望流式输出
        """
        # 1. 懒加载：如果索引还没加载，先加载索引
        if not self.ingestion_pipeline.index:
            self.ingestion_pipeline.get_documents()

        # 如果还是没有索引（说明没有文件），抛出错误
        if not self.ingestion_pipeline.index:
            raise RuntimeError("索引未构建，无法创建 Workflow")

        # 2. 状态检查：
        # 条件 A: workflow 还没创建 (None)
        # 条件 B: 当前 workflow 的模式 (self.workflow.streaming) 与 请求模式 (streaming) 不一致
        if (self.workflow is None) or (getattr(self.workflow, 'streaming', None) != streaming):
            logger.info(f"初始化 RAGWorkflow (Streaming={streaming})")
            self.workflow = RAGWorkflow(
                self.ingestion_pipeline.index,
                pipeline_nodes=None,  # 👈 重启模式，无新节点
                streaming=streaming
            )

    # -----------------------------
    # 核心业务方法：非流式查询 (一次性返回)
    # -----------------------------
    async def query_documents(
            self,
            session_id: str,
            query: str,
            knowledge_bool: bool,
    ) -> Tuple[str, str]:
        """
       [主入口] 执行非流式查询，等待所有处理完成后一次性返回结果。
       通常用于 API 接口调用，或者不需要打字机效果的场景。

       Args:
           session_id: 会话ID，用于隔离不同用户的上下文
           query: 用户的问题
           knowledge_bool: 开关，True=走RAG检索，False=纯LLM闲聊

       Returns:
           Tuple[str, str]: (回复文本, 来源信息字符串)
       """

        # --- [Step 1] 上下文准备 ---
        # 获取服务端维护的会话历史 (引用)
        hist_srv = self.get_session_history(session_id)
        # 将用户问题存入历史，作为本次生成的上下文
        hist_srv.append({"role": "user", "content": query})

        try:
            if knowledge_bool:
                # ==================================================
                # 分支 A: RAG 知识库模式 (检索 + 生成)
                # ==================================================

                # 1. [状态管理] 确保 Workflow 为 "非流式(False)" 模式
                #    这一点很重要，因为如果上一次调用是流式的，Workflow 内部状态可能是 streaming=True，
                #    导致 .run() 返回生成器而不是完整对象，这里强制重置为 False。
                self._ensure_workflow(streaming=False)

                # 2. [执行] 运行 Workflow
                #    因为是 streaming=False，这里的 await 会一直阻塞，
                #    直到 检索 -> 重排序 -> LLM生成全部完成。
                result: Dict[str, Any] = await self.workflow.run(
                    query=query,
                    timeout=60.0
                )

                # 3. [解析] 提取结果
                #    非流式模式下，result['response'] 是一个完整的 Response 对象或字符串
                response_text = str(result.get("response", ""))

                #    提取来源节点 (Source Nodes)
                sources = result.get("sources", [])

                # 4. [格式化] 将来源节点转为前端可读的字符串 (含相似度、图片等)
                sources_info_list = self._format_sources(sources)

                # 5. [记录] 更新历史
                #    注意：这里我们将来源信息也存入了历史记录结构中，方便后续追溯
                hist_srv.append({
                    "role": "assistant",
                    "content": response_text,
                    "sources": sources_info_list
                })

                return response_text, sources_info_list

            else:
                # ==================================================
                # 分支 B: 纯 LLM 聊天模式 (无检索)
                # ==================================================

                # 1. [执行] 调用 LLM
                #    使用 acomplete (异步完成) 而不是 complete (同步完成)。
                #    这样在等待 LLM 思考时，不会阻塞 Python 的主线程，允许其他用户的请求被处理。
                # 安全处理历史记录，避免过长导致的问题
                safe_history = self.get_safe_history(hist_srv)
                try:
                    history_json = json.dumps(safe_history, ensure_ascii=False)
                    logger.debug(f"历史记录JSON大小: {len(history_json)} 字符")
                    llm_res = await Settings.llm.acomplete(history_json)
                except Exception as e:
                    logger.error(f"LLM调用失败: {str(e)}")
                    raise

                response_text = llm_res.text

                # 2. [记录] 更新历史
                #    纯聊天模式没有来源，sources_info_list 为空
                hist_srv.append({
                    "role": "assistant",
                    "content": response_text,
                    "sources": []
                })

                return response_text, ""

        except Exception as e:
            # --- [异常处理] ---
            error_msg = f"查询失败: {str(e)}"
            logger.error(error_msg)

            # 记录错误信息到历史，保证对话连贯性 (或者方便用户看到报错)
            hist_srv.append({
                "role": "assistant",
                "content": error_msg,
                "sources": []
            })

            return error_msg, ""

    # =========================================================================
    # 核心业务方法：流式查询 (支持 SSE)
    # =========================================================================
    async def query_documents_stream(
            self,
            session_id: str,
            query: str,
            knowledge_bool: bool,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        [主入口] 执行流式查询，逐步返回来源信息和生成的文本。

        流程:
            1. 预处理：获取历史，追加用户问题。
            2. 分支判断：
               - RAG模式: 检索 -> 返回来源 -> 流式生成文本。
               - 纯LLM模式: 直接流式生成文本。
            3. 后处理：拼接完整回复，存入历史，发送完成信号。

        Yields (Dict):
            每次 yield 返回给前端的数据包，结构如下:
            {
                "type": "sources" | "text" | "complete" | "error",  # 消息类型
                "content": str | List,                              # 实际内容
                "finished": bool                                    # 是否结束
            }
        """
        # --- [Step 1] 上下文准备 ---
        # 获取该会话的历史记录 (引用对象，修改会直接影响 self.sessions)
        hist_srv = self.get_session_history(session_id)
        # 将用户当前的问题加入历史
        hist_srv.append({"role": "user", "content": query})

        # 用于拼接 LLM 生成的所有碎片，最后存入数据库/内存历史
        full_response = ""
        # 用于存储格式化后的来源信息，最后也要存入历史
        sources_info_list = []

        try:
            if knowledge_bool:
                # ==================================================
                # 分支 A: RAG 知识库模式 (检索 + 生成)
                # ==================================================

                # 1. 强制切换到流式模式 (如果之前是非流式)
                self._ensure_workflow(streaming=True)

                # 2. 执行 Workflow
                #    注意: 这里的 await 主要是等待 "检索(Retrieval)" 和 "重排序(Rerank)" 完成。
                #    一旦 LLM 开始生成，它就会返回一个包含 Generator 的结果对象，不会阻塞到文本完全生成结束。
                result = await self.workflow.run(query=query, timeout=60.0)

                # 3. [优先处理] 发送来源信息 (Sources)
                #    我们在文本出来之前先告诉用户参考了哪些文档，提升体验。
                raw_sources = result.get("sources", [])
                if raw_sources:
                    # 格式化来源 (添加相似度、图片预览等)
                    sources_info_list = self._format_sources(raw_sources)

                    # 🚀 Yield 1: 发送来源卡片
                    yield {
                        "type": "sources",
                        "finished": False,
                        "content": sources_info_list,
                    }

                # 4. [核心] 处理文本流 (Token Stream)
                #    result["stream"] 是我们在 Workflow 的 finalize_step 中返回的 response_gen
                stream_gen = result.get("stream")

                if stream_gen:
                    # 实时迭代生成器：LLM 每吐出一个字，这里就循环一次
                    async for token in stream_gen:
                        full_response += token  # 拼接到总结果中

                        # 🚀 Yield 2: 发送文本片段
                        yield {
                            "type": "text",
                            "finished": False,
                            "content": token,  # 注意：这里是增量字符，不是全量
                        }
                else:
                    # [兜底逻辑] 万一 Workflow 没返回流 (比如 fallback 到了非流式)
                    full_response = str(result.get("response", ""))
                    yield {"type": "text", "finished": False, "content": full_response}

            else:
                # ==================================================
                # 分支 B: 纯 LLM 聊天模式 (无检索)
                # ==================================================

                # 使用 Settings.llm.astream_complete 进行异步流式调用
                # 这比 stream_complete 更好，因为它不会阻塞 Python 的事件循环
                # 安全处理历史记录，避免过长导致的问题
                safe_history = self.get_safe_history(hist_srv)
                try:
                    history_json = json.dumps(safe_history, ensure_ascii=False)
                    logger.debug(f"流式历史记录JSON大小: {len(history_json)} 字符")
                    stream_response = await Settings.llm.astream_complete(history_json)
                except Exception as e:
                    logger.error(f"LLM流式调用失败: {str(e)}")
                    raise

                async for chunk in stream_response:
                    # 获取增量文本 (不同 LLM 库可能字段不同，通常是 delta)
                    token = chunk.delta
                    full_response += token

                    # 🚀 Yield 2: 发送文本片段
                    yield {
                        "type": "text",
                        "finished": False,
                        "content": token,
                    }

            # --- [Step 3] 收尾工作 ---

            # 将完整的对话轮次 (Q&A) 写入会话历史，用于下一次对话的上下文
            hist_srv.append({
                "role": "assistant",
                "content": full_response.strip(),
                "sources": sources_info_list  # 只有 RAG 模式这里才有值
            })

            # 🚀 Yield 3: 发送完成信号
            # 前端收到这个信号后，可以停止加载动画，解锁输入框
            yield {
                "type": "complete",
                "finished": True,
                "content": full_response.strip(),  # 可选：发送一次全量文本用于校对
            }

        except Exception as e:
            # --- [异常处理] ---
            error_msg = f"流式查询过程中发生错误: {str(e)}"
            logger.error(error_msg)

            # 也要记录错误到历史，避免上下文中断
            hist_srv.append({"role": "assistant", "content": error_msg, "sources": []})

            # 发送错误信号给前端
            yield {
                "type": "error",
                "content": error_msg,
                "finished": True
            }

    def _extract_images_from_markdown(self, content_preview: str) -> str:
        """
        从Markdown内容中提取图片路径并转换为HTML显示
        
        Args:
            content_preview: Markdown格式的内容预览文本
            
        Returns:
            str: 包含HTML图片标签的字符串
        """
        img_html = ""
        try:
            import re
            # 优化的Markdown图片标签提取正则表达式，支持Windows路径格式
            img_pattern = r'!\[.*?\]\((D:/llm/[^)]+\.png)\)'  # 匹配 ![alt](src) 格式
            matches = re.findall(img_pattern, content_preview)
            
            # 去重集合，避免重复处理同一张图片
            processed_img_names = set()
            
            for img_path in matches:
                # 清理路径中的可能存在的引号
                img_path = img_path.strip('"').strip("'")
                # 对于任何路径格式，提取文件名
                img_name = os.path.basename(img_path)
                
                # 避免重复处理同一张图片
                if img_name not in processed_img_names:
                    processed_img_names.add(img_name)
                    # 尝试从PDF_IMAGE_DIR中查找
                    b64_img = image_to_base64(img_name)
                    if b64_img:
                        img_html += (
                            '<div style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">'
                            '<p style="margin: 0 0 10px 0; font-weight: bold;">文档相关的图片：</p>'
                            f'<img src="data:image/jpeg;base64,{b64_img}" width="300" style="border-radius: 3px; max-width: 100%;"/>'
                            '</div>'
                        )
        except Exception as md_img_e:
            logger.warning(f"从Markdown提取图片失败: {md_img_e}")
        
        return img_html
    
    def _format_single_source(self, source_index: int, source: Dict) -> str:
        """
        格式化单个来源信息
        
        Args:
            source_index: 来源的索引编号
            source: 包含来源信息的字典
            
        Returns:
            str: 格式化后的来源信息字符串
        """
        score = float(source.get("score"))
        content_preview = source.get("content", "")
        metadata = source.get("metadata", {}) or {}
        
        # 获取文档类型和文件名
        content_type = metadata.get("content_type", "text")
        file_name = metadata.get("file_name", "未知文件")

        sources_info = ""

        # 显示相似度和文件信息
        if isinstance(score, (int, float)):
            sources_info += f"{source_index}. 相似度: {score:.3f} | 文件: {file_name}\n"
        else:
            sources_info += f"{source_index}. 相似度: - | 文件: {file_name}\n"

        # 处理内容预览
        sources_info += f"   内容: {content_preview}\n\n"

        # 处理Markdown中的图片
        if content_type == "markdown" and content_preview:
            sources_info += self._extract_images_from_markdown(content_preview)
        
        return sources_info
    
    def _format_sources(self, sources: List[Dict]) -> List[str]:
        """
        格式化多个来源信息，支持Markdown格式文档和图片显示
        
        Args:
            sources: 来源信息列表，每个元素是包含score、content、metadata等键的字典
            
        Returns:
            List[str]: 格式化后的来源信息字符串列表
        """
        sources_info_list = []

        for i, source in enumerate(sources, 1):
            sources_info = self._format_single_source(i, source)
            sources_info_list.append(sources_info)

        return sources_info_list

    async def _run_workflow_safe(self, query: str, timeout: float) -> Dict[str, Any]:
        """
        安全调用 workflow.run：
        - 首选带 top_k 形参
        - 若不支持则降级到不带 top_k 的版本
        """
        if not self.workflow:
            raise RuntimeError("RAG 工作流未初始化")

        try:
            return await self.workflow.run(query=query, timeout=timeout)
        except TypeError:
            logger.warning("RAGWorkflow.run 不支持 top_k 参数，已降级为默认检索数量")
            return await self.workflow.run(query=query, timeout=timeout)

    # -----------------------------
    # 会话管理
    # -----------------------------
    def clear_session(self, session_id: str) -> None:
        """清空指定会话的历史"""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def reset(self) -> None:
        """
        系统级重置：清空所有会话与审计历史。
        如需连同向量库/索引一并清空，请在外层调用 DocumentManager.clear_all。
        """
        self.sessions.clear()
