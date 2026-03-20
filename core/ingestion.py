from typing import List, Optional, Tuple
from pathlib import Path
import torch
import os

from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Settings,
    SimpleDirectoryReader,
    load_index_from_storage
)
from llama_index.core.node_parser import SentenceSplitter, MarkdownNodeParser, MarkdownElementNodeParser
from llama_index.core.extractors import TitleExtractor
from llama_index.core.ingestion import IngestionPipeline, IngestionCache, DocstoreStrategy
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.storage.docstore.redis import RedisDocumentStore
from llama_index.storage.index_store.redis import RedisIndexStore
from llama_index.storage.kvstore.redis import RedisKVStore as RedisCache
import chromadb
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.dashscope import DashScope
from config.settings import Settings as AppSettings
from utils.logger import setup_logger
# from core.pdfProcessor import MultimodalPDFProcessor
from core.pdf_parser import MultimodalPDFProcessor

logger = setup_logger(__name__)


class DocumentIngestionPipeline:
    """文档摄取管道"""

    def __init__(self):
        self._setup_models()
        self.index: Optional[VectorStoreIndex] = None
        self.chroma_vector_store: Optional[ChromaVectorStore] = None
        self.text_pipeline: Optional[IngestionPipeline] = None
        self.markdown_pipeline: Optional[IngestionPipeline] = None

        # 1. 初始化存储组件 (Redis & Chroma)
        self._initialize_storage_components()

        # 2. 创建不同类型的 Pipeline
        self._create_pipelines()

        # 3. 初始化 PDF 处理器
        self.pdf_processor = MultimodalPDFProcessor()

        # 创建 StorageContext
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.chroma_vector_store,
            docstore=self.redis_document_store,
            index_store=self.redis_index_store
        )

    def _setup_models(self):
        """设置LLM和嵌入模型"""
        Settings.llm = DashScope(
            api_key=AppSettings.API_KEY,
            api_base=AppSettings.API_BASE_URL,
            model_name=AppSettings.MODEL,
            temperature=AppSettings.TEMPERATURE
        )
        Settings.embed_model = HuggingFaceEmbedding(
            model_name=AppSettings.EMBEDDING_MODEL_PATH,
            device="cuda" if torch.cuda.is_available() else "cpu",
        )

    def _initialize_storage_components(self):
        """初始化存储组件"""
        # 初始化索引存储
        self.redis_index_store = RedisIndexStore.from_host_and_port(
            host="127.0.0.1", port=6379, namespace="redis_index"
        )
        # 初始化文档存储
        self.redis_document_store = RedisDocumentStore.from_host_and_port(
            host="127.0.0.1", port=6379, namespace="redis_docs"
        )
        # 初始化向量存储
        self._create_chroma_db()

    def _create_chroma_db(self):
        """创建Chroma向量存储"""
        chroma_client = chromadb.PersistentClient(AppSettings.CHROMA_PERSIST_DIR)
        chroma_collection = chroma_client.get_or_create_collection("quickstart")
        self.chroma_vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    def _create_pipelines(self):
        """创建不同类型的摄取管道"""
        # 通用配置
        common_config = {
            "vector_store": self.chroma_vector_store,
            "docstore": self.redis_document_store,
            "cache": IngestionCache(
                cache=RedisCache.from_host_and_port("localhost", 6379),
                collection="redis_cache",
            ),
            "docstore_strategy": DocstoreStrategy.UPSERTS_AND_DELETE
        }

        # 1. 普通文本文件的管道 (使用 SentenceSplitter)
        self.text_pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(
                    chunk_size=AppSettings.CHUNK_SIZE,
                    chunk_overlap=AppSettings.CHUNK_OVERLAP
                ),
                TitleExtractor(nodes=AppSettings.TITLE_EXTRACTOR_NODES),
                Settings.embed_model,
            ],
            **common_config
        )

        # 2. Markdown 文件的管道 (使用 MarkdownNodeParser)
        # 对于没有目录层级的文档，优化MarkdownNodeParser配置
        self.markdown_pipeline = IngestionPipeline(
            transformations=[
                MarkdownNodeParser(
                    include_metadata=True,  # 保留文档元数据
                    include_prev_next_rel=True,  # 保留节点之间的关系，有助于上下文理解
                ),
                # 使用更适合Markdown的分块策略，避免在图片标签中间切分
                SentenceSplitter(
                    chunk_size=AppSettings.CHUNK_SIZE,
                    chunk_overlap=AppSettings.CHUNK_OVERLAP,
                    # 使用更安全的分隔符，避免在图片标签中间切分
                    separator="\n\n",
                    # 禁用默认的句子切分，使用段落级别切分
                    paragraph_separator="\n\n"
                ),
                TitleExtractor(nodes=AppSettings.TITLE_EXTRACTOR_NODES),
                Settings.embed_model,
            ],
            **common_config
        )

    def update_model_config(self, model_name: str, temperature: float, max_tokens: int):
        """动态更新 LLM 模型和温度"""
        Settings.llm = DashScope(
            api_key=AppSettings.API_KEY,
            api_base=AppSettings.API_BASE_URL,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        logger.info(f"🔄 模型已更新: model={model_name}, temperature={temperature}")

    def ingest_documents(self, file_paths: List[str]) -> Tuple:
        """摄取文档并创建索引"""
        try:
            documents = []
            # 对上传的多个文件进行解析
            for file_path in file_paths:
                if not Path(file_path).exists():
                    logger.warning(f"文件不存在: {file_path}")
                    continue
                # 判断是否是PDF文件
                if Path(file_path).suffix.lower() == ".pdf":
                    # 保留你的 PDF 处理逻辑
                    document = self.pdf_processor.convert_pdf_to_markdown_doc(file_path)
                    documents.append(document)
                else:
                    # 1. 获取物理路径 (用于读取文件内容)
                    physical_path = file_path

                    # 2. 提取文件名 (作为唯一标识的核心)
                    # 结果: 公司规章制度.txt
                    file_name = os.path.basename(physical_path)

                    # 3. 构造一个固定的“逻辑 ID”
                    # 这一步最关键！不管临时文件夹怎么变，这个字符串永远不变。
                    # 你可以加个前缀，模拟一个虚拟的文件系统
                    stable_id = f"knowledge_base/{file_name}"

                    # 4. 读取数据
                    # 注意：这里 filename_as_id=True 已经不重要了，因为我们马上要手动改掉它
                    reader = SimpleDirectoryReader(input_files=[physical_path])
                    docs = reader.load_data()

                    for doc in docs:
                        # === 核心修复：强制覆盖 ID ===
                        # 将 ID 从 "C:\...\Temp\..." 改为 "knowledge_base/公司规章制度.txt"
                        doc.id_ = stable_id

                        # === 必须操作：清除易变元数据 ===
                        # 临时文件的创建时间肯定是刚生成的，必须删掉，否则 Hash 会变
                        doc.metadata.pop("file_path", None)
                        doc.metadata.pop("last_modified_date", None)

                        # 我们可以把真实的原始文件名存进去方便以后展示
                        doc.metadata["file_name"] = file_name

                        # 如果你想让溯源更清晰，可以把 ID 也存一份在 metadata
                        doc.metadata["doc_id"] = stable_id

                    documents.extend(docs)
                    logger.info(f"已处理文档: {file_name} (ID: {stable_id})")
                logger.info(f"已读取文档: {file_path}")

            if not documents:
                return "error", "没有找到有效的文档"

            # 根据文档类型分别处理
            logger.info("开始处理文档...")
            markdown_docs = []
            text_docs = []

            for doc in documents:
                if doc.metadata.get("content_type") == "markdown":
                    markdown_docs.append(doc)
                else:
                    text_docs.append(doc)

            pipeline_nodes = []

            # 处理 Markdown 文档
            if markdown_docs:
                logger.info(f"处理 {len(markdown_docs)} 个 Markdown 文档...")
                md_nodes = self.markdown_pipeline.run(documents=markdown_docs, show_progress=True)
                pipeline_nodes.extend(md_nodes)
                logger.info(f"Markdown 文档处理完成，生成了 {len(md_nodes)} 个节点")

            # 处理普通文本文档
            if text_docs:
                logger.info(f"处理 {len(text_docs)} 个普通文本文档...")
                txt_nodes = self.text_pipeline.run(documents=text_docs, show_progress=True)
                pipeline_nodes.extend(txt_nodes)
                logger.info(f"普通文本文档处理完成，生成了 {len(txt_nodes)} 个节点")

            logger.info(f"所有文档处理完成，共生成了 {len(pipeline_nodes)} 个节点")

            # 检查是否有新节点生成（如果文档重复，pipeline_nodes将为空）
            if not pipeline_nodes:
                logger.info("所有文档都是重复的，无需更新索引")
                result = "所有文档都是重复的，无需处理"
                return "success", result, pipeline_nodes

            # 把切分好的"小切片"也存进 docstore
            # 注意：虽然方法叫 add_documents，但它其实是用来存 nodes 的
            self.storage_context.docstore.add_documents(pipeline_nodes)

            # 创建向量索引
            logger.info("创建文档对应索引对象")
            if not self.index:
                logger.info("创建文档对应索引对象")
                self.index = VectorStoreIndex(pipeline_nodes, storage_context=self.storage_context,
                                              embed_model=Settings.embed_model)
            else:
                logger.info("获取当前索引，进行添加节点")
                self.index.insert_nodes(pipeline_nodes)

            # 调试信息：创建索引后
            if self.index:
                print(f" 索引后 docstore 文档数: {len(self.index.docstore.docs)}")
                print(f" 索引 ID: {self.index.index_id}")

            result = f"成功摄取了 {len(file_paths)} 个文档，生成了 {len(pipeline_nodes)} 个节点"
            logger.info(result)
            return "success", result, pipeline_nodes

        except Exception as e:
            error_msg = f"文档摄取失败: {str(e)}"
            logger.error(error_msg)
            return "error", error_msg, ""

    def get_documents(self):
        """加载已存在的索引和文档"""
        logger.info("读取已有向量数据库中的文档和索引...")
        try:
            # 尝试获取索引列表
            index_store = self.storage_context.index_store
            index_ids = index_store.list_indexes()

            if not index_ids:
                logger.info("未找到任何已有索引，将创建新索引")
                return None

            # 如果有多个索引，使用第一个（按时间排序，最近的优先）
            if len(index_ids) > 1:
                logger.warning(f"发现 {len(index_ids)} 个索引，将使用第一个: {index_ids[0]}")

            # 使用第一个索引ID加载
            index_id = index_ids[0]
            self.index = load_index_from_storage(
                self.storage_context,
                index_id=index_id
            )
            logger.info(f"成功加载索引: {index_id}")
            print("index:", self.index)
            return self.index

        except Exception as e:
            logger.error(f"加载索引失败: {e}")
            # 降级方案：直接从向量存储加载
            try:
                logger.info("尝试降级方案：从向量存储直接加载...")
                self.index = VectorStoreIndex.from_vector_store(
                    vector_store=self.chroma_vector_store,
                    embed_model=Settings.embed_model,
                    storage_context=self.storage_context
                )
                print("index (fallback):", self.index)
                return self.index
            except Exception as fallback_error:
                logger.error(f"降级加载也失败: {fallback_error}")
                return None
