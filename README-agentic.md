# DocuMind AI

DocuMind AI is a lightweight, TypeScript-inspired Python prototype for an agentic document parsing platform. It implements the key architecture described in the uploaded design brief: provider-agnostic gateway abstraction, tool-based ReAct agent loop, deterministic validation, confidence thresholds, and a simple historical-learning layer.

## Core components

- `documind/gateway.py` — provider-agnostic LLM gateway abstraction plus a deterministic mock implementation for offline demos.
- `documind/tools.py` — tool suite for schema lookup, OCR/text extraction, structured parsing, validation, confidence scoring, knowledge lookups, review queues, and persistence.
- `documind/agent.py` — ReAct runner and pipeline for processing a document end-to-end.
- `documind/eval.py` — lightweight evaluation utility for measuring field-level extraction accuracy.
- `main.py` — demo entry point that processes a sample invoice.

## Running the demo

```bash
python main.py
```

## Design alignment

The system follows the specification goals:

- Provider-agnostic gateway layer
- Tool-based ReAct loop
- High-confidence validation and human review fallback
- Historical and knowledge retrieval for similar fields
- Observability through structured outputs and review queues
- Deterministic local behavior for tests and demos

## Notes

This is a prototype rather than a production-ready multi-tenant SaaS implementation. The code intentionally stays self-contained and dependency-light so it can run in a local environment with no external AI providers configured.
