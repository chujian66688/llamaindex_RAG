from typing import List, Dict, Any, Optional
import chromadb
from config.settings import Settings as AppSettings
from utils.logger import setup_logger

logger = setup_logger(__name__)


class DocumentManager:
    """文档管理器 - 专门用于管理和查询文档信息"""

    def __init__(self, collection_name: str = "quickstart"):
        self.collection_name = collection_name
        self.chroma_client = chromadb.PersistentClient(AppSettings.CHROMA_PERSIST_DIR)
        self.collection = self.chroma_client.get_or_create_collection(collection_name)

    def get_all_document_names(self) -> List[Dict[str, Any]]:
        """获取所有文档名称和基本信息"""
        try:
            results = self.collection.get(include=['metadatas'])

            documents_info = []
            seen_documents = set()

            if results and results.get('metadatas'):
                for metadata in results['metadatas']:
                    if metadata and 'file_name' in metadata:
                        doc_key = f"{metadata['file_name']}_{metadata.get('doc_id', '')}"

                        if doc_key not in seen_documents:
                            seen_documents.add(doc_key)

                            doc_info = {
                                'file_name': metadata.get('file_name', 'Unknown'),
                                'doc_id': metadata.get('doc_id', ''),
                                'file_path': metadata.get('file_path', ''),
                                'upload_time': metadata.get('upload_time', ''),
                                'file_type': metadata.get('file_type', ''),
                                'file_size': metadata.get('file_size', 0)
                            }
                            documents_info.append(doc_info)

            documents_info.sort(key=lambda x: x.get('upload_time', ''), reverse=True)
            return documents_info

        except Exception as e:
            logger.error(f"获取文档名称失败: {e}")
            return []

    def get_document_names_only(self) -> List[Dict[str, str]]:
        """只获取文档名称列表"""
        documents = self.get_all_document_names()
        return [{doc['doc_id']: doc['file_name']} for doc in documents]

    def get_document_chunks(self, doc_id: str, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """获取指定文档的所有分块，支持分页"""
        try:
            results = self.collection.get(
                include=['documents', 'metadatas']
            )

            if not results or not results.get('ids'):
                return {"chunks": [], "total": 0, "page": page, "page_size": page_size}

            # 按 doc_id 过滤分块
            chunks = []
            for i, metadata in enumerate(results['metadatas']):
                if metadata and metadata.get('doc_id') == doc_id:
                    chunk_text = results['documents'][i] if results.get('documents') else ""
                    chunk_meta = metadata or {}
                    chunks.append({
                        "chunk_id": results['ids'][i],
                        "text": chunk_text,
                        "metadata": {
                            "file_name": chunk_meta.get('file_name', ''),
                            "doc_id": chunk_meta.get('doc_id', ''),
                            "upload_time": chunk_meta.get('upload_time', ''),
                            "file_type": chunk_meta.get('file_type', ''),
                            "content_type": chunk_meta.get('content_type', ''),
                            "chunk_size": chunk_meta.get('chunk_size', len(chunk_text)),
                        }
                    })

            total = len(chunks)
            start = (page - 1) * page_size
            end = start + page_size
            paginated_chunks = chunks[start:end]

            return {
                "chunks": paginated_chunks,
                "total": total,
                "page": page,
                "page_size": page_size
            }

        except Exception as e:
            logger.error(f"获取文档分块失败: {e}")
            return {"chunks": [], "total": 0, "page": page, "page_size": page_size}

    def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """删除指定文档的所有分块"""
        try:
            # 获取该文档的所有分块 ID
            results = self.collection.get(
                include=['metadatas']
            )

            if not results or not results.get('ids'):
                return {"status": "error", "message": "未找到任何文档"}

            ids_to_delete = []
            for i, metadata in enumerate(results['metadatas']):
                if metadata and metadata.get('doc_id') == doc_id:
                    ids_to_delete.append(results['ids'][i])

            if not ids_to_delete:
                return {"status": "error", "message": f"未找到文档: {doc_id}"}

            self.collection.delete(ids=ids_to_delete)
            logger.info(f"已删除文档 {doc_id} 的 {len(ids_to_delete)} 个分块")

            return {
                "status": "success",
                "message": f"已删除文档 {doc_id}，共 {len(ids_to_delete)} 个分块"
            }

        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return {"status": "error", "message": str(e)}


if __name__ == '__main__':
    print(DocumentManager().get_all_document_names())
