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
    """RAG 应用主类，仅保留知识库摄取与无状态查询能力。"""

    def __init__(self) -> None:
        self.ingestion_pipeline = DocumentIngestionPipeline()
        self.ingestion_pipeline.get_documents()
        self.workflow: Optional[RAGWorkflow] = None

    def upload_and_process_files(self, files, chunk_size=None, chunk_overlap=None) -> Tuple:
        if not files:
            return "请上传至少一个文件"

        try:
            file_paths: List[str] = []
            for file in files:
                if hasattr(file, "name"):
                    file_paths.append(file.name)
                else:
                    file_paths.append(str(file))

            status, result, pipeline_nodes = self.ingestion_pipeline.ingest_documents(
                file_paths, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
            if status == "error":
                raise RuntimeError(result)

            if self.ingestion_pipeline.index:
                self.workflow = RAGWorkflow(self.ingestion_pipeline.index, pipeline_nodes)

            return status, result

        except Exception as e:
            error_msg = f"文件处理失败: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _ensure_workflow(self, streaming: bool):
        if not self.ingestion_pipeline.index:
            self.ingestion_pipeline.get_documents()

        if not self.ingestion_pipeline.index:
            raise RuntimeError("索引未构建，无法创建 Workflow")

        if (self.workflow is None) or (getattr(self.workflow, 'streaming', None) != streaming):
            logger.info(f"初始化 RAGWorkflow (Streaming={streaming})")
            self.workflow = RAGWorkflow(
                self.ingestion_pipeline.index,
                pipeline_nodes=None,
                streaming=streaming
            )

    async def query_documents(self, query: str, knowledge_bool: bool) -> Tuple[str, list[str]]:
        try:
            if knowledge_bool:
                self._ensure_workflow(streaming=False)
                result: Dict[str, Any] = await self.workflow.run(query=query, timeout=60.0)
                response_text = str(result.get("response", ""))
                sources = result.get("sources", [])
                sources_info_list = self._format_sources(sources)
                return response_text, sources_info_list

            llm_res = await Settings.llm.acomplete(query)
            return llm_res.text, []

        except Exception as e:
            error_msg = f"查询失败: {str(e)}"
            logger.error(error_msg)
            return error_msg, []

    async def query_documents_stream(self, query: str, knowledge_bool: bool) -> AsyncGenerator[Dict[str, Any], None]:
        full_response = ""
        sources_info_list = []

        try:
            if knowledge_bool:
                self._ensure_workflow(streaming=True)
                result = await self.workflow.run(query=query, timeout=60.0)
                raw_sources = result.get("sources", [])
                if raw_sources:
                    sources_info_list = self._format_sources(raw_sources)
                    yield {
                        "type": "sources",
                        "finished": False,
                        "content": sources_info_list,
                    }

                stream_gen = result.get("stream")
                if stream_gen:
                    async for token in stream_gen:
                        full_response += token
                        yield {
                            "type": "text",
                            "finished": False,
                            "content": token,
                        }
                else:
                    full_response = str(result.get("response", ""))
                    yield {"type": "text", "finished": False, "content": full_response}
            else:
                stream_response = await Settings.llm.astream_complete(query)
                async for chunk in stream_response:
                    token = chunk.delta
                    full_response += token
                    yield {
                        "type": "text",
                        "finished": False,
                        "content": token,
                    }

            yield {
                "type": "complete",
                "finished": True,
                "content": full_response.strip(),
            }

        except Exception as e:
            error_msg = f"流式查询过程中发生错误: {str(e)}"
            logger.error(error_msg)
            yield {
                "type": "error",
                "content": error_msg,
                "finished": True
            }

    def _extract_images_from_markdown(self, content_preview: str) -> str:
        img_html = ""
        try:
            import re
            img_pattern = r'!\[.*?\]\((D:/llm/[^)]+\.png)\)'
            matches = re.findall(img_pattern, content_preview)
            processed_img_names = set()

            for img_path in matches:
                img_path = img_path.strip('"').strip("'")
                img_name = os.path.basename(img_path)
                if img_name not in processed_img_names:
                    processed_img_names.add(img_name)
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
        score = float(source.get("score"))
        content_preview = source.get("content", "")
        metadata = source.get("metadata", {}) or {}
        content_type = metadata.get("content_type", "text")
        file_name = metadata.get("file_name", "未知文件")

        # 使用简洁的Markdown格式
        if isinstance(score, (int, float)):
            score_percent = f"{score * 100:.1f}%"
            sources_info = f"📄 **{file_name}** (相似度: {score_percent})\n\n"
        else:
            sources_info = f"📄 **{file_name}**\n\n"
        
        # 使用引用块展示内容，更美观
        sources_info += f"> {content_preview}\n"

        if content_type == "markdown" and content_preview:
            sources_info += self._extract_images_from_markdown(content_preview)

        return sources_info

    def _format_sources(self, sources: List[Dict]) -> List[str]:
        sources_info_list = []
        for i, source in enumerate(sources, 1):
            sources_info = self._format_single_source(i, source)
            sources_info_list.append(sources_info)
        return sources_info_list

    def delete_document_from_redis(self, doc_id: str) -> None:
        """从Redis中删除文档存储和索引存储"""
        try:
            # 获取Redis文档存储
            redis_docstore = self.ingestion_pipeline.redis_document_store
           
            # 删除文档存储中的数据
            redis_docstore.delete_document(doc_id)
            logger.info(f"从Redis删除文档: {doc_id}")
            
            # 由于LlamaIndex的Redis存储没有提供按doc_id删除的接口，
            # 我们只能删除整个命名空间，然后重新构建
            # 这是一个限制，但确保数据一致性
            
        except Exception as e:
            logger.error(f"从Redis删除文档失败: {e}")
            raise

    def rebuild_bm25_index(self) -> None:
        """重新构建BM25索引"""
        try:
            # 1. 从 RedisDocumentStore 获取剩余节点
            redis_docstore = self.ingestion_pipeline.redis_document_store
            all_docs = redis_docstore.docs  # 此时已经是删除后的数据

            # 2. 清空旧索引
            if os.path.exists(AppSettings.BM25_PERSIST_DIR):
                import shutil
                shutil.rmtree(AppSettings.BM25_PERSIST_DIR)

            if not all_docs:
                logger.info("无剩余文档，BM25索引已清空")
                # 降级为纯向量检索
                self.rag_workflow.retriever = self.rag_workflow.vector_retriever
                return

            # 3. docs 转 nodes
            from llama_index.core.schema import TextNode
            remaining_nodes = [
                TextNode(text=doc.text, metadata=doc.metadata)
                for doc in all_docs.values()
            ]

            # 4. 重建并持久化
            from llama_index.retrievers.bm25 import BM25Retriever
            from llama_index.core.retrievers import QueryFusionRetriever
            
            new_bm25 = BM25Retriever.from_defaults(
                nodes=remaining_nodes,
                similarity_top_k=AppSettings.SIMILARITY_TOP_K,
                language="zh"
            )
            new_bm25.persist(AppSettings.BM25_PERSIST_DIR)
            logger.info(f"BM25索引重建完成，共 {len(remaining_nodes)} 个节点")

            # 5. 热更新内存中的检索器（关键步骤）
            self.rag_workflow.bm25_retriever = new_bm25
            self.rag_workflow.retriever = QueryFusionRetriever(
                retrievers=[
                    self.rag_workflow.vector_retriever,
                    new_bm25
                ],
                similarity_top_k=AppSettings.SIMILARITY_TOP_K,
                num_queries=1,
                mode="reciprocal_rerank",
                use_async=True
            )

        except Exception as e:
            logger.error(f"重建BM25索引失败: {e}")
            raise

    def reset(self) -> None:
        return None
