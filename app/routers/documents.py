# app/routers/documents.py
"""
文档相关的 API：
- POST /api/docs/upload: 多文件上传与摄取
- GET  /api/docs/list:   返回已入库文档名列表
- POST /api/docs/reset:  系统级重置（会清空索引等，需谨慎）
"""

from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.schemas import UploadResponse, DocsListResponse, CommonResponse
from app.routers.users import get_current_active_user, User
from app.services import get_rag_service
from app.services.rag_service import RAGService
from utils.logger import setup_logger

logger = setup_logger(__name__)

# 创建一个子路由实例，供 main.py 挂载
router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_docs(
        files: List[UploadFile] = File(...),  # 支持多文件，表单字段名为 "files"
        current_user: User = Depends(get_current_active_user),  # ← 鉴权
        svc: RAGService = Depends(get_rag_service)  # 注入全局服务实例
):
    """
    处理多文件上传与摄取：
    - 读取所有 UploadFile 内容到内存
    - 交给服务层落盘至临时目录并调用核心摄取
    - 根据返回文本初步判断状态（成功/处理中/失败）
    # 如果在公司开发的话，上传文档的功能一定是有一个后台管理去进行维护的，普通的用户没有上传文档的权限,是由管理员统一进行文档的管理
    """
    try:
        # 依次将文件内容全部读入内存；如需更省内存，可在服务层流式写入
        contents = [await f.read() for f in files]
        filenames = [f.filename for f in files]

        status, status_text, processed = svc.upload_and_process_files(contents, filenames)

        return UploadResponse(status=status, message=status_text, processed_files=processed)
    except Exception as e:
        # HTTP 500：服务器内部错误。detail 会返回给客户端，注意不要泄漏敏感信息。
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=DocsListResponse)
async def list_docs(current_user: User = Depends(get_current_active_user),  # ← 鉴权
              svc: RAGService = Depends(get_rag_service)):
    """
    返回当前已存在于向量库/索引中的文档名列表。
    前端可用于提供筛选下拉选项。
    """
    return DocsListResponse(documents=svc.get_documents())


@router.post("/reset", response_model=CommonResponse)
async def reset_system(current_user: User = Depends(get_current_active_user),  # ← 鉴权
                 svc: RAGService = Depends(get_rag_service)):
    """
    系统级重置：清空会话与索引。
    强烈建议在生产环境对此接口加上鉴权与二次确认。
    """
    svc.reset_system()
    return CommonResponse(status="success", message="系统已重置")
