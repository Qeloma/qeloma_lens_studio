from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .agent import AgenticDocumentProcessor
from .models import DocumentProcessRequest

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000").split(",")
    if origin.strip()
]

app = FastAPI(
    title="Qeloma Lens Agent Service",
    version="0.1.0",
    description="Lightweight Python agentic AI service for document classification, extraction, and validation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

processor = AgenticDocumentProcessor()


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "qeloma-lens-agent-service",
        "environment": os.getenv("APP_ENV", "development"),
        "port": int(os.getenv("PORT", "8000")),
    }


@app.post("/v1/process")
def process_document(payload: DocumentProcessRequest) -> Dict[str, Any]:
    try:
        result = processor.process(payload)
        return result.dict()
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"status": "error", "detail": str(exc)})


@app.post("/v1/process-file")
async def process_file(file: UploadFile = File(...), tenant_id: str = "tenant-demo") -> Dict[str, Any]:
    contents = await file.read()
    text = contents.decode("utf-8", errors="ignore")

    request = DocumentProcessRequest(
        tenant_id=tenant_id,
        document_type="general",
        file_name=file.filename or "uploaded_file.txt",
        text=text,
    )
    result = processor.process(request)
    return result.dict()


@app.get("/")
def root() -> Dict[str, str]:
    return {"message": "Qeloma Lens Python agent service is running."}
