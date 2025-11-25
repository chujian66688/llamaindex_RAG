# app/services/main.py
"""
RAGService：对核心 RAG 逻辑（core.*）的轻量封装。
- 负责处理 HTTP 层传入的数据（如 UploadFile 的二进制）与核心层（文件路径、历史消息结构）的适配。
- 屏蔽临时文件创建/清理等细节，子路由只需要调用业务方法。
"""

from typing import List, Dict, Tuple, Any
from core.application import RAGApplication
from core.documentManager import DocumentManager
import tempfile, os, shutil
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RAGService:
    """
    单例服务对象：
    - self.app: 你的核心 RAG 应用入口（需在 core/application.py 中实现对应方法）
    - self.doc_manager: 文档管理器，用于列出/清理向量库文档等
    """

    def __init__(self):
        self.app = RAGApplication()
        self.doc_manager = DocumentManager()

    def upload_and_process_files(self, files: List[bytes], filenames: List[str]) -> Tuple[str, str, List[str]]:
        """
        将上传的文件内容写入临时目录，再调用核心应用进行摄取与索引构建。
        参数:
            files: 每个文件的二进制内容（来自 UploadFile.read()）
            filenames: 对应的原始文件名，用于产生落盘路径与后续展示
        返回:
            (状态文本, 处理过的文件名列表)
        注意:
            - 使用临时目录进行中转，确保每次请求之间互不干扰。
            - finally 中清理临时目录，避免磁盘泄漏。
        """
        tmpdir = tempfile.mkdtemp(prefix="rag_upload_")
        paths = []
        try:
            # 将内存中的文件写入到临时目录形成可被核心层消费的“文件路径”
            for name, content in zip(filenames, files):
                p = os.path.join(tmpdir, name)
                with open(p, "wb") as f:
                    f.write(content)
                paths.append(p)

            logger.info(f"上传的文档:{paths}")
            # 调用核心层的摄取方法，完成解析、切分、向量化与入库
            status, status_text = self.app.upload_and_process_files(paths)
            return status, status_text, filenames
        finally:
            # 无论成功或异常，都清理临时目录
            shutil.rmtree(tmpdir, ignore_errors=True)

    def get_documents(self) -> List[str]:
        """
        从文档管理器中获取已入库文档名列表。
        要求 core/documentManager.py 提供 get_document_names_only。
        """
        return self.doc_manager.get_document_names_only() or []

    def query(self, session_id: str, query: str, model: str, knowledge_bool: bool, temperature: float,
              max_tokens: int):
        """
        对话查询主流程：
        参数:
            session_id: 会话 ID，用于区分不同用户/窗口的上下文
            query: 用户问题
            knowledge_bool: 是否开启知识库模式
            history: 历史消息列表，元素形如 {"role": "user"/"assistant", "content": "..."}
            top_k: 检索返回的候选条数
        返回:
            (answer, new_history, sources)
            - answer: 生成的答案字符串
            - new_history: 更新后的会话消息列表
            - sources: 引用信息（文档名/分数/片段等），便于前端展示出处
        """
        # 更新对应的模型配置
        self.app.update_model_config(model, temperature, max_tokens)

        return self.app.query_documents(
            session_id=session_id,
            query=query,
            knowledge_bool=knowledge_bool,
        )

    async def query_stream(self, session_id: str, query: str, model: str,
                           knowledge_bool: bool, temperature: float, max_tokens: int):
        """异步生成器版本"""

        # 更新模型配置
        self.app.update_model_config(model, temperature, max_tokens)

        # 使用 async for 遍历底层异步生成器，并逐个 yield
        async for chunk in self.app.query_documents_stream(
                session_id=session_id,
                query=query,
                knowledge_bool=knowledge_bool,
        ):
            yield chunk  # 关键：使用 yield

    def get_session(self, session_id: str):
        """
        清空指定会话的历史记录，释放内存/上下文负担。
        """
        return self.app.get_session_history(session_id)

    def clear_session(self, session_id: str):
        """
        清空指定会话的历史记录，释放内存/上下文负担。
        """
        self.app.clear_session(session_id)

    def reset_system(self):
        """
        系统级重置：
        - 清理会话
        - 清空或重建索引/向量库（由 DocumentManager.clear_all 实现）
        用于开发调试或后台维护操作，生产环境需加鉴权限制。
        """
        self.app.reset()
        if hasattr(self.doc_manager, "clear_all"):
            self.doc_manager.clear_all()
