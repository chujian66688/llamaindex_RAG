# app/routers/documents.py
"""
文档相关的 API：
- POST /api/docs/upload: 多文件上传与摄取（支持自定义分块参数）
- GET  /api/docs/list:   返回已入库文档列表（含元数据）
- GET  /api/docs/chunks/{doc_id}: 获取指定文档的分块（分页）
- DELETE /api/docs/documents/{doc_id}: 删除单个文档
- GET  /api/docs/config/chunk: 获取分块配置
- PUT  /api/docs/config/chunk: 更新分块配置
- POST /api/docs/reset:  系统级重置（会清空索引等，需谨慎）
"""

from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query

from app.schemas import (
    UploadResponse, DocsListResponse, CommonResponse,
    DocChunksResponse, ChunkConfigResponse, ChunkConfigUpdateRequest,
)
from app.routers.users import get_current_active_user, User
from app.services import get_rag_api_service
from app.services.rag_api_service import RAGApiService
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_docs(
    files: List[UploadFile] = File(...),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    current_user: User = Depends(get_current_active_user),
    svc: RAGApiService = Depends(get_rag_api_service),
):
    try:
        payload = [(file.filename or "unnamed", await file.read()) for file in files]
        result = await svc.upload_files(payload, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        return UploadResponse(
            status=str(result.get("status", "success")),
            message=str(result.get("message", "")),
            processed_files=[str(item) for item in result.get("processed_files", [])],
        )
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=DocsListResponse)
async def list_docs(
    current_user: User = Depends(get_current_active_user),
    svc: RAGApiService = Depends(get_rag_api_service),
):
    try:
        documents = await svc.list_documents()
        return DocsListResponse(documents=documents)
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chunks/{doc_id:path}", response_model=DocChunksResponse)
async def get_document_chunks(
    doc_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    svc: RAGApiService = Depends(get_rag_api_service),
):
    try:
        result = await svc.get_document_chunks(doc_id, page=page, page_size=page_size)
        return DocChunksResponse(**result)
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id:path}", response_model=CommonResponse)
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: RAGApiService = Depends(get_rag_api_service),
):
    try:
        result = await svc.delete_document(doc_id)
        return CommonResponse(
            status=str(result.get("status", "error")),
            message=str(result.get("message", "")),
        )
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/chunk", response_model=ChunkConfigResponse)
async def get_chunk_config(
    current_user: User = Depends(get_current_active_user),
    svc: RAGApiService = Depends(get_rag_api_service),
):
    try:
        return await svc.get_chunk_config()
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/chunk", response_model=ChunkConfigResponse)
async def update_chunk_config(
    req: ChunkConfigUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    svc: RAGApiService = Depends(get_rag_api_service),
):
    try:
        return await svc.update_chunk_config(req.chunk_size, req.chunk_overlap)
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset", response_model=CommonResponse)
async def reset_system(
    current_user: User = Depends(get_current_active_user),
    svc: RAGApiService = Depends(get_rag_api_service),
):
    try:
        result = await svc.reset_system()
        return CommonResponse(
            status=str(result.get("status", "success")),
            message=str(result.get("message", "系统已重置")),
        )
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))
