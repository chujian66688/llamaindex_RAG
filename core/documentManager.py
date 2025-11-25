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
            # 从ChromaDB获取所有元数据
            results = self.collection.get(include=['metadatas'])

            documents_info = []
            seen_documents = set()  # 用于去重

            if results and results.get('metadatas'):
                for metadata in results['metadatas']:
                    if metadata and 'file_name' in metadata:
                        doc_key = f"{metadata['file_name']}_{metadata.get('doc_id', '')}"

                        # 避免重复
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

            # 按上传时间排序
            documents_info.sort(key=lambda x: x.get('upload_time', ''), reverse=True)
            return documents_info

        except Exception as e:
            logger.error(f"获取文档名称失败: {e}")
            return []

    def get_document_names_only(self) -> List[Dict[str,str]]:
        """只获取文档名称列表"""
        documents = self.get_all_document_names()
        return [{doc['doc_id']: doc['file_name']} for doc in documents]


if __name__ == '__main__':
    print(DocumentManager().get_all_document_names())
