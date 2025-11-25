from typing import List, Dict, Tuple, Optional
from pathlib import Path
import json
import os
import math
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Image, Text, Title, NarrativeText, Table
from llama_index.core.schema import Document, TextNode
from config.settings import Settings as AppSettings
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MultimodalPDFProcessor:
    """多模态PDF处理器 - 支持提取图片、文本和表格"""

    def __init__(self, image_output_dir: str = AppSettings.PDF_IMAGE_DIR):
        self.image_output_dir = image_output_dir
        os.makedirs(image_output_dir, exist_ok=True)

    def extract_images_and_text(self, pdf_path: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """从PDF中提取图片和对应的文档内容"""
        logger.info(f"开始解析PDF文件: {pdf_path}")

        # 解析PDF，优势：能够很精准的识别图片、文本、表格，弊端：速度比较慢
        raw_pdf_elements = partition_pdf(
            filename=pdf_path,  # 指定要解析的 PDF 文件路径
            extract_images_in_pdf=True,  # 是否提取 PDF 中的图片（将其作为 ImageBlock 返回）
            infer_table_structure=False,  # 是否尝试识别并解析表格结构（会输出结构化的 Table 类型元素）
            strategy='hi_res',  # 提取策略：使用高分辨率模式（hi_res）+ OCR，可处理图像型或复杂布局 PDF
            extract_image_block_output_dir=self.image_output_dir  # 图片输出目录，提取出的图片会保存到这个路径
        )

        images = []
        texts = []
        tables = []

        logger.info(f"总共解析到 {len(raw_pdf_elements)} 个元素")

        # 遍历所有元素
        for i, element in enumerate(raw_pdf_elements):
            # 创建每个元素的内容
            element_info = {
                # 元素类型
                'type': type(element).__name__,
                # 元素页码
                'page': getattr(element.metadata, 'page_number', None) if hasattr(element, 'metadata') else None,
                # 获取坐标-整个元素的坐标点是从左上逆时针开始计算的
                'bbox': getattr(element.metadata, 'coordinates', None) if hasattr(element, 'metadata') else None,
                # 获取坐标系
                'content': str(element),
                'element_id': f"{Path(pdf_path).stem}_{i}"
            }

            # 处理图片元素
            if isinstance(element, Image):
                # 处理图片元素
                image_info = self._process_image_element(element, element_info, pdf_path)
                if image_info:
                    images.append(image_info)

            # 处理表格元素
            elif isinstance(element, Table):
                tables.append(element_info)  # 需要特殊处理的，我后续会更新上

            # 处理文本元素
            elif isinstance(element, (Text, Title, NarrativeText)):
                texts.append(element_info)

        logger.info(f"提取完成 - 图片: {len(images)}, 文本: {len(texts)}, 表格: {len(tables)}")
        return images, texts, tables

    def _process_image_element(self, element: Image, element_info: Dict, pdf_path: str) -> Optional[Dict]:
        """处理图片元素"""
        # 拷贝元素的内容
        image_info = element_info.copy()

        # 获取图片的base64数据
        if hasattr(element.metadata, 'image_base64') and element.metadata.image_base64:
            # 获取图片的bs4的内容
            image_info['image_data'] = element.metadata.image_base64
            # 图片类型
            image_info['image_format'] = getattr(element.metadata, 'image_mime_type', 'image/png')

        # 获取图片路径
        elif hasattr(element.metadata, 'image_path') and element.metadata.image_path:
            image_info['image_path'] = element.metadata.image_path

        # 检查其他可能的图片数据属性
        elif hasattr(element.metadata, 'image_data') and element.metadata.image_data:
            image_info['image_data'] = element.metadata.image_data
        # 如果 image_info 字典中包含 'image_data' 或 'image_path' 这两个键中任意一个，就返回 image_info 本身；否则返回 None。
        return image_info if any(key in image_info for key in ['image_data', 'image_path']) else None

    def euclidean_distance(self, p1: float, p2: float) -> float:
        """计算欧几里得距离"""
        return math.sqrt((p1 - p2) ** 2)

    def get_context_around_image(self, images: List[Dict], texts: List[Dict]) -> List[Dict]:
        """获取图片周围的文本内容作为上下文"""

        # 第一部分：建立图片-文本关联
        for image in images:
            image_page = image.get('page')  # 获取图片的页面
            image_bbox = image.get('bbox')  # 获取图片的坐标
            image_path = image.get('image_path')  # 获取图片的路径

            # 数据有效性检查
            if not all([image_page, image_bbox, image_path]):
                continue

            # 找到同一页最近的文本
            closest_text = None  # 就等于文本对象，存储当前图片和那个文档最接近
            min_dist = float("inf")  # 创建一个无穷大的浮点数

            # 计算图片和哪个文档最接近
            for text in texts:
                text_page = text.get('page')  # 获取文档的页码
                text_bbox = text.get('bbox')  # 获取文档的坐标
                text_content = text.get('content')  # 获取文档的内容

                # 检查数据有效性和是否在相同页面， 当一个页面中只有图片没有文字的时候，这个图片会失效
                if not all([text_page, text_bbox, text_content]) or text_page != image_page:
                    continue

                try:
                    # 图片和文字的四个角的坐标- 从左上坐标开始逆时针直到右上角坐标
                    # 图片的上下坐标  (  [左上[X，Y]], [左下[X，Y]], [右下[X，Y]], [右上[X，Y]]        )
                    image_top = int(image_bbox.points[0][1])  # 图片的左上Y坐标
                    image_bottom = int(image_bbox.points[1][1])  # 图片的左下Y坐标

                    # 文本的上下坐标
                    text_top = int(text_bbox.points[0][1])  # 文本的左上Y坐标
                    text_bottom = int(text_bbox.points[1][1])  # 文本的左下Y坐标

                    # 计算距离
                    if image_top > text_bottom:  # 文字在图片上面
                        dist = self.euclidean_distance(image_top, text_bottom)
                    elif text_top > image_bottom:  # 文字在图片下面
                        dist = self.euclidean_distance(text_top, image_bottom)
                    else:  # 文字与图片有重叠
                        dist = 0  # 重叠时距离最小
                    # 但计算的距离小于上次计算的内容，那么就代表当前文档和图片更接近
                    if dist < min_dist:
                        min_dist = dist
                        closest_text = text

                except (IndexError, ValueError, AttributeError) as e:
                    logger.warning(f"处理坐标时出错: {e}")
                    continue

            # 创建图片-文本关联
            if closest_text:
                # 支持多图片关联
                if 'image_paths' not in closest_text:
                    closest_text['image_paths'] = []
                closest_text['image_paths'].append(image_path)

        # 第二部分：文本分块处理
        results = []
        text_chunk = {}  # 文档大小
        text_chunk_overlap = ""  # 文档重叠数
        text_length = 0  # 文档长度

        for text in texts:
            content = text.get('content', '')  # 使用 get 避免 KeyError
            if not content:  # 跳过空内容
                continue

            # 如果文本长度为0，创建一个新的文本块
            if text_length == 0:
                # 初始化文档快内容
                text_chunk = {
                    'content': text_chunk_overlap + content,
                    'image_paths': json.dumps(text.get('image_paths', []).copy() if 'image_paths' in text else [])
                }
                # 统计文档长度
                text_length = len(text_chunk['content'])
            else:
                # 添加到当前文本块
                text_chunk['content'] += content
                text_length += len(content)

                # 处理图片内容
                if 'image_paths' in text:
                    # 合并图片路径列表，避免重复
                    existing_paths = set(text_chunk['image_paths'])
                    # 从当前 text（新加入的文本）中筛选出还没出现在 text_chunk 里的新路径
                    new_paths = [path for path in text['image_paths'] if path not in existing_paths]
                    # 转换json字符串
                    new_paths_json = json.dumps(
                        json.loads(text_chunk['image_paths']) + new_paths) if new_paths else None
                    text_chunk['image_paths'] = new_paths_json

            # 检查是否达到分块大小
            if text_length >= AppSettings.CHUNK_SIZE:

                results.append(text_chunk)

                # 清理数据并添加到结果
                if not text_chunk['image_paths']:
                    text_chunk.pop('image_paths', None)  # 移除空的图片路径列表
                # 准备下一个块
                text_chunk_overlap = text_chunk['content'][-AppSettings.CHUNK_OVERLAP:] if len(
                    text_chunk['content']) > AppSettings.CHUNK_OVERLAP else ""
                text_chunk = {}
                text_length = 0

        # 处理最后一个文本块
        if text_chunk and text_chunk.get('content'):
            if not text_chunk.get('image_paths'):
                text_chunk.pop('image_paths', None)
            results.append(text_chunk)

        return results

    def create_multimodal_nodes(self, pdf_path: str) -> List[TextNode]:
        """创建多模态文档"""

        # 1. 获取文件名 (这是唯一标识的基准)
        file_name = os.path.basename(pdf_path)

        # 2. 构造稳定的逻辑 ID 前缀
        # 类似于我们处理 TXT 时做的，忽略 temp 目录，只认文件名
        # 格式示例: "knowledge_base/公司手册.pdf"
        stable_doc_id = f"knowledge_base/{file_name}"

        # 从pdf中获取图片、文字、表格内容
        images, texts, tables = self.extract_images_and_text(pdf_path)
        # 处理图片和文字之间的关联关系,处理图片和那个文字最接近
        texts = self.get_context_around_image(images, texts)

        # 解析完pdf后读取的节点对象列表
        text_nodes = []

        # 3. 遍历切块后的文本，生成确定性的 Node ID
        for i, text_chunk in enumerate(texts):
            # 构造当前分块的唯一 ID
            # 格式示例: "knowledge_base/公司手册.pdf#chunk_0", "...#chunk_1"
            # 只要文件内容和分块逻辑不变，这个 ID 永远不变！
            chunk_id = f"{stable_doc_id}#chunk_{i}"

            doc = TextNode(
                # === 核心修复 1: 显式指定 id_ ===
                # 告诉 LlamaIndex/Redis：这个节点的 ID 是固定的，不要随机生成
                id_=chunk_id,

                text=text_chunk['content'],

                metadata={
                    # === 核心修复 2: 路径清洗 ===
                    # 绝对不要把 pdf_path (带 temp 路径) 放进 metadata
                    # 否则 Hash 计算会变，导致重新 Embedding
                    "file_name": file_name,

                    # 这里的 doc_id 仅作展示用，真正的 ID 是上面的 id_
                    "doc_id": stable_doc_id,

                    # 图片路径处理
                    "image_paths": text_chunk.get('image_paths', None),

                    # 记录这是第几个分块，方便调试
                    "chunk_index": i
                }
            )

            # ⚠️ 注意：如果 image_paths 里包含 temp 路径，
            # 可能会导致 Hash 变动。建议在 extract_images_and_text 里
            # 确保 image_output_dir 是一个固定的静态目录，而不是临时目录。

            text_nodes.append(doc)

        return text_nodes

