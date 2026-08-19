from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SourceInfo(BaseModel):
    kind: Literal["pdf", "docx", "image", "text", "bytes"]
    name: str
    size_bytes: Optional[int] = None


class ExtractionMeta(BaseModel):
    method: str = "rule-based"
    confidence: float = 0.0
    language: str = "en"


class DocumentEnvelope(BaseModel):
    input_id: str
    tenant_id: str
    source: SourceInfo
    text: str
    meta: Dict[str, Any] = Field(default_factory=dict)
    extraction: ExtractionMeta = Field(default_factory=ExtractionMeta)
    created_at: str


class DocumentProcessRequest(BaseModel):
    tenant_id: str = "tenant-demo"
    document_type: str = "general"
    file_name: str = "document.txt"
    text: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractionField(BaseModel):
    field_name: str
    value: Optional[Any] = None
    confidence: float
    valid: bool
    errors: List[str] = Field(default_factory=list)


class ProcessResponse(BaseModel):
    status: str
    input_id: str
    document_type: str
    text_preview: str
    extracted_fields: Dict[str, ExtractionField]
    review_queue: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str
