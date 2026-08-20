from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .gateway import LLMGateway, MockGateway
from .models import DocumentInput, ExtractionResult
from .tools import DocumentParsingTools

SYSTEM_PROMPT = """
You are a document extraction agent. Your task is to extract structured data from documents.

Process:
1. Determine the document type and retrieve the schema.
2. Extract the required fields from the document text.
3. Validate each field against business rules.
4. Escalate any field with confidence under 0.7 to human review.
5. Persist only validated values.
"""


class ReActAgent:
    def __init__(self, gateway: Optional[LLMGateway] = None, tools: Optional[DocumentParsingTools] = None) -> None:
        self.gateway = gateway or MockGateway()
        self.tools = tools or DocumentParsingTools()

    def _tool_defs(self) -> List[Dict[str, Any]]:
        return [
            {"name": "schema_lookup", "description": "Return the extraction schema for a given document type."},
            {"name": "extract_text", "description": "Extract the raw text from a document or image."},
            {"name": "parse_structured", "description": "Parse a field from extracted text using a field path."},
            {"name": "validate_field", "description": "Validate a field against business rules."},
            {"name": "confidence_check", "description": "Score extraction confidence."},
            {"name": "search_knowledge", "description": "Look up similar past extraction examples."},
            {"name": "human_review", "description": "Queue a field for manual validation when confidence is low."},
            {"name": "store_extraction", "description": "Persist a validated extraction."},
            {"name": "get_historical", "description": "Retrieve historical extraction examples for similarity matching."},
        ]

    def run(self, document: DocumentInput, max_turns: int = 8) -> Dict[str, Any]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": json.dumps({"document_type": document.document_type, "doc_id": document.doc_id, "file_url": document.file_url, "text": document.text})}]
        extracted: Dict[str, Any] = {}
        review_queue: List[Dict[str, Any]] = []

        for _ in range(max_turns):
            response = self.gateway.chat(messages, tools=self._tool_defs())
            messages.append({"role": "assistant", "content": response.get("content", "")})

            for tool_call in response.get("tool_calls", []):
                name = tool_call.get("name")
                arguments = tool_call.get("arguments", {})
                result = self.tools.run_tool(name, **arguments)
                messages.append({"role": "tool", "content": json.dumps({"name": name, "result": result})})

                if name == "parse_structured":
                    field_name = arguments.get("field_path")
                    if field_name:
                        extracted[field_name] = result.get("extracted_value")
                if name == "validate_field":
                    valid = result.get("valid", False)
                    if not valid:
                        review_queue.append({"field_name": arguments.get("field_name"), "value": arguments.get("value"), "error": result.get("error_message")})
                if name == "confidence_check":
                    score = result.get("confidence_score", 0.0)
                    if score < 0.7:
                        review_queue.append({"field_name": arguments.get("field_name", "unknown"), "value": arguments.get("value"), "score": score})

            if not response.get("tool_calls"):
                break

        return {
            "status": "ok",
            "document_type": document.document_type,
            "doc_id": document.doc_id,
            "extracted_fields": extracted,
            "review_queue": review_queue,
            "summary": "Extraction complete with low-confidence values routed for human review when required.",
        }


class DocumentProcessingPipeline:
    def __init__(self, gateway: Optional[LLMGateway] = None, tools: Optional[DocumentParsingTools] = None) -> None:
        self.agent = ReActAgent(gateway=gateway, tools=tools)

    def process(self, doc_input: DocumentInput) -> Dict[str, Any]:
        schema_result = self.agent.tools.schema_lookup(doc_input.document_type)
        text_result = self.agent.tools.extract_text(doc_input.file_url, language_hint="en")
        extracted: Dict[str, Any] = {}
        review_queue: List[Dict[str, Any]] = []

        if schema_result.get("status") == "ok":
            for field in schema_result["schema"]["fields"]:
                parsed = self.agent.tools.parse_structured(text_result["text_content"], field["name"])
                value = parsed.get("extracted_value")
                validation = self.agent.tools.validate_field(field["name"], value)
                confidence = self.agent.tools.confidence_check(field["name"], value, text_result["text_content"])

                extraction = ExtractionResult(
                    field_name=field["name"],
                    value=value,
                    confidence=confidence.get("confidence_score", 0.0),
                    validated=validation.get("valid", False),
                    errors=[] if validation.get("valid") else [validation.get("error_message", "Invalid field")],
                )
                extracted[field["name"]] = extraction.as_dict()

                if confidence.get("confidence_score", 0.0) < field["confidence_threshold"]:
                    review_queue.append({
                        "field_name": field["name"],
                        "value": value,
                        "required_threshold": field["confidence_threshold"],
                        "actual_confidence": confidence.get("confidence_score", 0.0),
                    })

        return {
            "status": "ok",
            "document_type": doc_input.document_type,
            "doc_id": doc_input.doc_id,
            "schema": schema_result.get("schema"),
            "extracted_fields": extracted,
            "review_queue": review_queue,
            "historical_context": self.agent.tools.get_historical(doc_input.document_type),
        }
