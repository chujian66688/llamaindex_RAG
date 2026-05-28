import os
import pymupdf4llm
from llama_index.core.schema import Document
from config.settings import Settings as AppSettings
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MultimodalPDFProcessor:
    """
    新版 PDF 处理器：PDF -> Markdown -> Document
    """

    def __init__(self, image_output_dir: str = AppSettings.PDF_IMAGE_DIR):
        self.image_output_dir = image_output_dir
        os.makedirs(image_output_dir, exist_ok=True)

    def convert_pdf_to_markdown_doc(self, pdf_path: str) -> Document:
        """
        将 PDF 转换为 Markdown 格式的 Document 对象
        """
        file_name = os.path.basename(pdf_path)
        logger.info(f"开始将 PDF 转换为 Markdown: {file_name}")

        try:
            # 1. 使用 pymupdf4llm 提取 Markdown 和图片
            # write_images=True 会自动提取图片并保存到 image_path
            # image_path 是图片保存的文件夹
            # image_format 也就是在 markdown 里保存时使用的文件格式
            md_text = pymupdf4llm.to_markdown(
                pdf_path,
                write_images=True,
                image_path=self.image_output_dir,
                image_format="png"  # 可选：默认 'png' 或 'jpg'
            )

            # 2. 构造稳定的逻辑 ID (父文档 ID)
            stable_doc_id = f"knowledge_base/{file_name}"

            # 3. 封装成 LlamaIndex Document 对象
            # 注意：我们这里返回的是一个“大文档”，后续交给 Pipeline 的 MarkdownNodeParser 去切分
            doc = Document(
                id_=stable_doc_id,
                text=md_text,
                metadata={
                    "file_name": file_name,
                    "doc_id": stable_doc_id,
                    "file_path": pdf_path,
                    "content_type": "markdown"  # 标记类型，方便后续处理
                }
            )

            logger.info(f"PDF 转 Markdown 成功，长度: {len(md_text)} 字符")
            return doc

        except Exception as e:
            logger.error(f"PDF 转 Markdown 失败: {e}")
            raise e


if __name__ == '__main__':
    m = MultimodalPDFProcessor()
    print(m.convert_pdf_to_markdown_doc("D:\llm\knowledge\斗破苍穹.pdf"))

