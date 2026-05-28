from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import Settings
from rest_api import router as rest_router

app = FastAPI(title="RAG API Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router, prefix="/api/docs")

if __name__ == "__main__":
    uvicorn.run(
        "run:app",
        host=Settings.HOST,
        port=Settings.PORT,
        reload=False,
    )
