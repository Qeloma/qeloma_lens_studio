from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional


class LLMGateway(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def stream(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        raise NotImplementedError


class MockGateway(LLMGateway):
    """A deterministic mock gateway used for local demos and tests."""

    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        last_user = messages[-1].get("content", "") if messages else ""
        if "extract" in last_user.lower() or "parse" in last_user.lower():
            return {
                "role": "assistant",
                "content": "I will inspect the document, extract the required fields, and record any low-confidence values for human review.",
                "tool_calls": [
                    {"name": "parse_structured", "arguments": {"field_path": "invoice_number"}},
                    {"name": "validate_field", "arguments": {"field_name": "invoice_number", "value": "INV-2024-0105"}},
                ],
            }
        return {
            "role": "assistant",
            "content": "No further tool calls required.",
            "tool_calls": [],
        }

    def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "field_name": "invoice_number",
            "value": "INV-2024-0105",
            "confidence": 0.94,
            "source": "mock_gateway",
        }

    async def stream(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "thought", "content": "Reviewing document and preparing extraction plan."}
        yield {"type": "tool", "content": "schema_lookup"}
