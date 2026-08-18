from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from dateutil import parser as date_parser

from .models import (
    DocumentEnvelope,
    DocumentProcessRequest,
    ExtractionField,
    ProcessResponse,
    SourceInfo,
)


log = logging.getLogger(__name__)

# Precompile common patterns
_INVOICE_NUM_RE = re.compile(r"Invoice\s*(?:No\.?|#)?\s*[:#-]?\s*([A-Z0-9-]+)", re.IGNORECASE)
_DATE_ISO_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_DATE_SLASH_RE = re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})")
_TOTAL_RE = re.compile(r"Total\s*(?:Amount)?\s*[:#-]?\s*\(?\$?\s*([0-9,]+(?:\.\d{1,2})?)\)?", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_NAME_RE = re.compile(r"^Name\s*[:#-]?\s*(.+)$", re.IGNORECASE | re.MULTILINE)


class AgenticDocumentProcessor:
    """A lightweight, robust document parser for agentic AI workflows.

    Changes vs previous:
    - Use stable UUIDs for `input_id`.
    - Return `None` for missing values instead of sentinel strings.
    - Robust date and amount parsing with normalization.
    - Value normalization before validation.
    - Use `ExtractionField` dicts for review queue to aid serialization.
    """

    def process(self, request: DocumentProcessRequest) -> ProcessResponse:
        text = request.text.strip()
        if not text:
            raise ValueError("document text is required")

        now = datetime.now(timezone.utc)
        input_id = f"inp_{now.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4()}"

        envelope = DocumentEnvelope(
            input_id=input_id,
            tenant_id=request.tenant_id,
            source=SourceInfo(kind="text", name=request.file_name, size_bytes=len(text.encode("utf-8"))),
            text=text,
            meta={
                "document_type": request.document_type,
                "detected_context": self.detect_context(text, request.file_name),
            },
            extraction={"method": "rule-based", "confidence": 0.96, "language": "en"},
            created_at=now.isoformat(),
        )

        extracted = self.extract_fields(envelope.text, request.document_type)
        review_queue: List[Dict[str, Any]] = []
        cleaned: Dict[str, ExtractionField] = {}

        for field_name, raw_value in extracted.items():
            value = self._normalize_value(field_name, raw_value)
            valid, errors = self.validate_field(field_name, value)
            confidence = self.confidence_for(field_name, value)
            item = ExtractionField(
                field_name=field_name,
                value=value,
                confidence=confidence,
                valid=valid,
                errors=errors,
            )
            cleaned[field_name] = item

            if confidence < 0.7 or not valid:
                review_queue.append(item.dict())

        log.info("Processed document %s type=%s fields=%d", envelope.input_id, request.document_type, len(cleaned))

        return ProcessResponse(
            status="ok",
            input_id=envelope.input_id,
            document_type=request.document_type,
            text_preview=text[:220],
            extracted_fields=cleaned,
            review_queue=review_queue,
            created_at=envelope.created_at,
        )

    def detect_context(self, text: str, filename: str) -> str:
        lower = (text + " " + filename).lower()
        if any(k in lower for k in ("invoice", "receipt", "total", "amount")):
            return "invoice-receipt"
        if any(k in lower for k in ("resume", "experience", "education")):
            return "resume-cv"
        if any(k in lower for k in ("contract", "agreement", "terms")):
            return "legal-contract"
        return "general-document"

    def extract_fields(self, text: str, document_type: str) -> Dict[str, Optional[Any]]:
        if document_type == "invoice":
            return {
                "invoice_number": self._first_match(_INVOICE_NUM_RE, text),
                "date": self._first_match(_DATE_ISO_RE, text) or self._first_match(_DATE_SLASH_RE, text),
                "vendor_name": self._first_match(re.compile(r"Vendor\s*[:#-]?\s*(.+)", re.IGNORECASE), text),
                "total_amount": self._first_match(_TOTAL_RE, text),
            }

        if document_type == "resume":
            return {
                "candidate_name": self._first_match(_NAME_RE, text) or self._first_match(re.compile(r"^([A-Z][A-Za-z'`.-]+(?:\s+[A-Z][A-Za-z'`.-]+)+)$", re.MULTILINE), text),
                "email": self._first_match(_EMAIL_RE, text),
                "experience_years": self._first_match(re.compile(r"(\d+)(?:\+)?\s+years?\s+of\s+experience", re.IGNORECASE), text),
            }

        return {
            "doc_title": text.splitlines()[0].strip() if text.splitlines() else None,
            "summary": text[:120],
        }

    def _first_match(self, pattern: re.Pattern, text: str) -> Optional[str]:
        match = pattern.search(text)
        if not match:
            return None
        val = match.group(1).strip() if match.groups() else match.group(0).strip()
        return val

    def _normalize_value(self, field_name: str, value: Optional[Any]) -> Optional[Any]:
        if value is None:
            return None
        val = str(value).strip()

        if field_name == "invoice_number":
            return val.upper()

        if field_name == "date":
            return self._normalize_date(val)

        if field_name == "total_amount":
            return self._normalize_amount(val)

        if field_name == "candidate_name":
            return " ".join(part.capitalize() for part in val.split())

        return val

    def _normalize_date(self, val: str) -> Optional[str]:
        # Try ISO first, then rely on dateutil parser
        m = _DATE_ISO_RE.search(val)
        if m:
            return m.group(1)
        try:
            dt = date_parser.parse(val, dayfirst=False, yearfirst=False)
            return dt.date().isoformat()
        except Exception:
            log.debug("Failed to parse date: %s", val)
            return None

    def _normalize_amount(self, val: str) -> Optional[str]:
        # strip currency-like characters and parentheses
        san = re.sub(r"[()\s$€£,]", "", val)
        try:
            d = Decimal(san)
            return format(d.quantize(Decimal("0.01")), "f")
        except (InvalidOperation, ValueError):
            log.debug("Failed to parse amount: %s", val)
            return None

    def validate_field(self, field_name: str, value: Optional[Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        if value in (None, "", "unknown"):
            return False, ["Field missing or not identifiable."]

        val = str(value).strip()

        if field_name == "invoice_number":
            if not re.fullmatch(r"[A-Z0-9-]+", val):
                errors.append("Invoice number format is invalid.")
        elif field_name == "date":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", val):
                errors.append("Date must be in YYYY-MM-DD format.")
        elif field_name == "total_amount":
            try:
                Decimal(val)
            except Exception:
                errors.append("Amount must be numeric.")
        elif field_name == "email":
            if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", val):
                errors.append("Email format is invalid.")

        return (len(errors) == 0), errors

    def confidence_for(self, field_name: str, value: Optional[Any]) -> float:
        if value in (None, "", "unknown"):
            return 0.1

        base = 0.7
        if field_name in {"invoice_number", "date", "total_amount"}:
            base += 0.15
        if field_name == "email":
            base += 0.05

        # small boost if value looks normalized
        if field_name == "date" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)):
            base += 0.08
        if field_name == "total_amount":
            try:
                Decimal(str(value))
                base += 0.08
            except Exception:
                pass

        return max(0.0, min(1.0, round(base, 2)))
