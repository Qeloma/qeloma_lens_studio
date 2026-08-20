from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SchemaField:
    name: str
    kind: str
    required: bool = True
    description: str = ""
    pattern: Optional[str] = None
    confidence_threshold: float = 0.7


@dataclass
class DocumentSchema:
    document_type: str
    fields: List[SchemaField] = field(default_factory=list)

    def get_field(self, name: str) -> Optional[SchemaField]:
        for field in self.fields:
            if field.name == name:
                return field
        return None


@dataclass
class DocumentInput:
    doc_id: str
    document_type: str
    file_url: str
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    field_name: str
    value: Any
    confidence: float
    source: str = "structured_parser"
    validated: bool = True
    errors: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source,
            "validated": self.validated,
            "errors": self.errors,
        }
