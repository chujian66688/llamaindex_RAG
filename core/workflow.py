from llama_index.core import VectorStoreIndex
from llama_index.core.workflow import Context, Workflow, step, StopEvent, StartEvent
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.postprocessor import SentenceTransformerRerank, PrevNextNodePostprocessor
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import QueryFusionRetriever
from config.settings import Settings as AppSettings
from core.events import RAGEvents
from utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class RAGWorkflow(Workflow):
    """RAG工作流：负责混合检索 (Vector + BM25) 和 答案生成"""

    def __init__(
            self,
            index: VectorStoreIndex,
            pipeline_nodes: list = None,  # 接收新摄取的节点
            streaming: bool = False,
            **kwargs
    ):
        super().__init__(**kwargs, timeout=None)
        self.index = index
        self.nodes = pipeline_nodes
        self.streaming = streaming
        self._setup_components()

    def _setup_components(self):
        """设置工作流组件"""

        # 1. 准备 BM25 检索器 (构建 或 加载)
        self.bm25_retriever = self._initialize_bm25()

        # 2. 准备 向量 检索器
        self.vector_retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=AppSettings.SIMILARITY_TOP_K
        )

        # 3. 配置 混合检索器 (Fusion)
        if self.bm25_retriever:
            logger.info("启用混合检索: Vector + BM25")
            self.retriever = QueryFusionRetriever(
                retrievers=[self.vector_retriever, self.bm25_retriever],
                similarity_top_k=AppSettings.SIMILARITY_TOP_K,
                num_queries=1,  # 保持原Query，不做扩展，大于1的话就去生成相似的问题去检索文档
                mode="reciprocal_rerank",  # RRF 算法，在检索的时候去进行重排
                use_async=True,
                verbose=True
            )
        else:
            logger.warning("BM25 不可用，降级为纯向量检索")
            self.retriever = self.vector_retriever

        # 4. 配置 Reranker (重排序)
        # 混合检索召回量大，必须重排以保证质量
        self.reranker = SentenceTransformerRerank(
            model=AppSettings.RERANK_MODEL_PATH,
            top_n=AppSettings.RERANK_TOP_K
        )

        # 5. 配置合成器
        self.synthesizer = get_response_synthesizer(
            streaming=self.streaming
        )

    def _initialize_bm25(self):
        """
        初始化 BM25 逻辑：
        1. 如果有新 nodes -> 构建新索引并保存
        2. 如果无 nodes -> 尝试从磁盘加载
        """
        try:
            # 情况 A: 有新数据传入 (刚刚 Upload 完)
            if self.nodes and len(self.nodes) > 0:
                logger.info(f"使用 {len(self.nodes)} 个新节点构建 BM25 索引...")
                bm25 = BM25Retriever.from_defaults(
                    nodes=self.nodes,
                    similarity_top_k=AppSettings.SIMILARITY_TOP_K,
                    language="zh"  # 优化中文分词
                )
                # 持久化到磁盘
                if not os.path.exists(AppSettings.BM25_PERSIST_DIR):
                    os.makedirs(AppSettings.BM25_PERSIST_DIR)
                bm25.persist(AppSettings.BM25_PERSIST_DIR)
                logger.info("BM25 索引已保存")
                return bm25

            # 情况 B: 无新数据 (服务重启/直接对话)，尝试加载本地缓存
            elif os.path.exists(AppSettings.BM25_PERSIST_DIR):
                logger.info("从磁盘加载现有的 BM25 索引...")
                return BM25Retriever.from_persist_dir(AppSettings.BM25_PERSIST_DIR)

            # 情况 C: 既无新数据也无缓存
            else:
                logger.warning("没有可用的节点来构建 BM25，也未找到本地缓存。")
                return None

        except Exception as e:
            logger.error(f"BM25 初始化失败: {e}")
            return None

    @step
    async def retrieve_step(
            self,
            ctx: Context,
            ev: StartEvent
    ) -> RAGEvents.RetrievalEvent:
        """检索步骤"""
        logger.info(f"开始检索查询: {ev.query}")

        """执行检索(单个chroma检索)"""
        # nodes = self.retriever.retrieve(ev.query)

        """使用混合检索"""
        retrieve_nodes = await self.retriever.aretrieve(ev.query)

        logger.info(f"检索获得 {len(retrieve_nodes)} 个节点")

        return RAGEvents.RetrievalEvent(query=ev.query, nodes=retrieve_nodes)

    @step
    async def rerank_step(
            self,
            ctx: Context,
            ev: RAGEvents.RetrievalEvent
    ) -> RAGEvents.RerankEvent:
        """重排序步骤"""
        logger.info("开始重排序")

        # 应用重排序
        rerank_nodes = self.reranker.postprocess_nodes(ev.nodes, query_str=ev.query)

        logger.info(f"重排序后保留 {len(rerank_nodes)} 个节点")

        return RAGEvents.RerankEvent(query=ev.query, nodes=rerank_nodes)

    @step
    async def generate_step(
            self,
            ctx: Context,
            ev: RAGEvents.RerankEvent
    ) -> RAGEvents.ResponseEvent:
        """生成回答步骤"""
        logger.info("开始生成回答")

        # 直接使用检索到的节点生成回答，不再重复检索
        response = await self.synthesizer.asynthesize(
            query=ev.query,
            nodes=ev.nodes
        )

        # 如果是流式，response 是 StreamingResponse 对象，不能直接 str()
        # 如果是非流式，response 是 Response 对象，str() 获取文本
        response_payload = response if self.streaming else str(response)

        logger.info("回答生成对象创建完成")

        return RAGEvents.ResponseEvent(
            query=ev.query,
            nodes=ev.nodes,
            response=response_payload  # 这里传递对象或字符串
        )

    @step
    async def finalize_step(
            self,
            ctx: Context,
            ev: RAGEvents.ResponseEvent
    ) -> StopEvent:
        """最终化步骤"""
        # 文档的来源信息
        source_info = [
            {
                "content": node.node.text,
                "score": node.score,
                "metadata": node.node.metadata
            }
            for node in ev.nodes
        ]

        if self.streaming:
            # 修改点：流式返回结构
            # ev.response 是一个 StreamingResponse 对象
            # 我们通常返回它的 response_gen (生成器) 或者整个对象供前端迭代
            result = {
                "query": ev.query,
                "stream": ev.response.response_gen,  # 这是一个生成器
                "sources": source_info,
                "is_streaming": True
            }
        else:
            # 修改点：非流式返回结构（保持原有逻辑）
            result = {
                "query": ev.query,
                "response": ev.response,  # 这是一个字符串
                "sources": source_info,
                "is_streaming": False
            }

        return StopEvent(result=result)
