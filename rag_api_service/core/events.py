from typing import List, Any
from llama_index.core.workflow import Event
from llama_index.core.schema import NodeWithScore


class RAGEvents:
    """定义RAG工作流中的事件"""

    class RetrievalEvent(Event):
        """检索事件"""
        query: str
        nodes: List[NodeWithScore]

    class RerankEvent(Event):
        """重排事件"""
        query: str
        nodes: List[NodeWithScore]

    class ResponseEvent(Event):
        """响应事件"""
        query: str
        nodes: List[NodeWithScore]
        response: Any
