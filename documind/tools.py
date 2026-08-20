from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List

from .models import DocumentSchema, SchemaField


class DocumentParsingTools:
    """A set of deterministic tools that model the workflow of a document parsing agent."""

    def __init__(self) -> None:
        self._schemas = {
            "invoice": DocumentSchema(
                document_type="invoice",
                fields=[
                    SchemaField("invoice_number", "string", description="Invoice identifier", confidence_threshold=0.8),
                    SchemaField("date", "date", description="Invoice date", confidence_threshold=0.8),
                    SchemaField("vendor_name", "string", description="Vendor name", confidence_threshold=0.8),
                    SchemaField("total_amount", "currency", description="Total invoice amount", confidence_threshold=0.8),
                ],
            )
        }
        self._historical = {
            "invoice": [
                {"field": "invoice_number", "value": "INV-2024-0105", "confidence": 0.94},
                {"field": "total_amount", "value": "$1,245.67", "confidence": 0.93},
            ]
        }
        self._extractions: Dict[str, Dict[str, Any]] = {}

    def schema_lookup(self, document_type: str) -> Dict[str, Any]:
        schema = self._schemas.get(document_type)
        if not schema:
            return {"status": "missing", "schema": None}

        return {
            "status": "ok",
            "schema": {
                "document_type": schema.document_type,
                "fields": [
                    {
                        "name": field.name,
                        "kind": field.kind,
                        "required": field.required,
                        "description": field.description,
                        "pattern": field.pattern,
                        "confidence_threshold": field.confidence_threshold,
                    }
                    for field in schema.fields
                ],
            },
        }

    def extract_text(self, file_url: str, language_hint: str = "en") -> Dict[str, Any]:
        sample_text = {
            "invoice": """Invoice No.: INV-2024-0105\nDate: 2024-03-15\nVendor: Acme Corp\nTotal Amount: $1,245.67\nStatus: Paid\n""",
            "receipt": """Receipt # RCP-2301\nMerchant: Corner Cafe\nTotal: $18.40\nDate: 2024-04-02\n""",
        }.get(file_url.split("/")[-1].split(".")[0], "")

        if not sample_text:
            sample_text = "Invoice No.: INV-2024-0105\nDate: 2024-03-15\nVendor: Acme Corp\nTotal Amount: $1,245.67\n"

        return {
            "status": "ok",
            "text_content": sample_text,
            "confidence": 0.96,
            "language_hint": language_hint,
        }

    def parse_structured(self, text_segment: str, field_path: str) -> Dict[str, Any]:
        if field_path == "invoice_number":
            match = re.search(r"Invoice No\.?\s*[:#-]?\s*([A-Z0-9-]+)", text_segment, re.IGNORECASE)
            value = match.group(1) if match else "INV-UNKNOWN"
        elif field_path == "date":
            match = re.search(r"Date\s*[:#-]?\s*(\d{4}-\d{2}-\d{2})", text_segment, re.IGNORECASE)
            value = match.group(1) if match else "2024-01-01"
        elif field_path == "vendor_name":
            match = re.search(r"Vendor\s*[:#-]?\s*([A-Za-z0-9 .&'-]+)", text_segment, re.IGNORECASE)
            value = match.group(1).strip() if match else "Unknown Vendor"
        elif field_path == "total_amount":
            match = re.search(r"Total Amount\s*[:#-]?\s*\$?([0-9,]+\.\d{2})", text_segment, re.IGNORECASE)
            value = f"${match.group(1)}" if match else "$0.00"
        else:
            value = "unknown"

        return {"status": "ok", "field_path": field_path, "extracted_value": value}

    def validate_field(self, field_name: str, value: Any) -> Dict[str, Any]:
        valid = True
        errors: List[str] = []

        if field_name == "invoice_number":
            valid = bool(re.fullmatch(r"[A-Z0-9-]+", str(value)))
            if not valid:
                errors.append("Invoice number contains unsupported characters.")
        elif field_name == "date":
            valid = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)))
            if not valid:
                errors.append("Date must be YYYY-MM-DD.")
        elif field_name == "vendor_name":
            valid = bool(str(value).strip())
            if not valid:
                errors.append("Vendor name is required.")
        elif field_name == "total_amount":
            try:
                amount = float(str(value).replace("$", "").replace(",", ""))
                valid = amount > 0
            except ValueError:
                valid = False
            if not valid:
                errors.append("Amount must be a positive number.")

        return {"status": "ok" if valid else "invalid", "valid": valid, "error_message": "; ".join(errors)}

    def confidence_check(self, field_name: str, value: Any, context: str) -> Dict[str, Any]:
        base = 0.75
        if field_name in {"invoice_number", "date", "total_amount"}:
            base += 0.15
        if value and str(value).strip() != "unknown":
            base += 0.05
        if "low confidence" in context.lower():
            base -= 0.2
        confidence = max(0.0, min(1.0, base))
        return {"status": "ok", "confidence_score": round(confidence, 2)}

    def search_knowledge(self, field_name: str, similar_context: str) -> Dict[str, Any]:
        examples = {
            "invoice_number": ["Invoice # INV-2024-0105 appears at the top right of the invoice", "Document IDs are usually uppercase with a hyphenated year"],
            "total_amount": ["Total amount is the largest monetary value on the page", "Amounts are often formatted as $1,245.67"],
            "date": ["The issue date usually appears near the invoice header", "Dates often follow YYYY-MM-DD format"],
        }
        return {"status": "ok", "examples": examples.get(field_name, [similar_context])}

    def human_review(self, field_name: str, value: Any, context: str) -> Dict[str, Any]:
        return {
            "status": "queued",
            "task_id": f"review-{field_name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "field_name": field_name,
            "value": value,
            "context": context,
            "message": "Low confidence extraction has been queued for human verification.",
        }

    def store_extraction(self, doc_id: str, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        self._extractions[doc_id] = deepcopy(extraction_result)
        return {"status": "ok", "doc_id": doc_id, "stored": True}

    def get_historical(self, doc_fingerprint: str) -> Dict[str, Any]:
        data = self._historical.get(doc_fingerprint, [])
        return {"status": "ok", "doc_fingerprint": doc_fingerprint, "historical_data": data}

    def run_tool(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        fn = getattr(self, tool_name)
        return fn(**kwargs)
