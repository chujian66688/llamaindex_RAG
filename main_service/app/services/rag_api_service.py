from __future__ import annotations

from typing import Any, Optional

import httpx

from config.settings import Settings


class RAGApiService:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or Settings.RAG_API_URL).rstrip("/")

    async def upload_files(self, files: list[tuple[str, bytes]],
                           chunk_size: Optional[int] = None,
                           chunk_overlap: Optional[int] = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=300.0) as client:
            multipart = [
                ("files", (name, content, "application/octet-stream"))
                for name, content in files
            ]
            data = {}
            if chunk_size is not None:
                data["chunk_size"] = str(chunk_size)
            if chunk_overlap is not None:
                data["chunk_overlap"] = str(chunk_overlap)
            resp = await client.post(f"{self.base_url}/upload", files=multipart, data=data)
            resp.raise_for_status()
            return resp.json()

    async def list_documents(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/documents")
            resp.raise_for_status()
            data = resp.json()
            return data.get("documents", [])

    async def get_document_chunks(self, doc_id: str, page: int = 1, page_size: int = 10) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/chunks/{doc_id}",
                params={"page": page, "page_size": page_size}
            )
            resp.raise_for_status()
            return resp.json()

    async def delete_document(self, doc_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(f"{self.base_url}/documents/{doc_id}")
            resp.raise_for_status()
            return resp.json()

    async def get_chunk_config(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/config/chunk")
            resp.raise_for_status()
            return resp.json()

    async def update_chunk_config(self, chunk_size: int, chunk_overlap: int) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(
                f"{self.base_url}/config/chunk",
                json={"chunk_size": chunk_size, "chunk_overlap": chunk_overlap}
            )
            resp.raise_for_status()
            return resp.json()

    async def reset_system(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/reset")
            resp.raise_for_status()
            return resp.json()
