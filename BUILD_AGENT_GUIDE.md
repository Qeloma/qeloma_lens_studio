# Qeloma Lens Build Agent Guide

This guide documents the complete local build agent setup for the current Qeloma Lens project. It focuses on the architecture, repo layout, local development workflow, and the Python/FastAPI agent service that sits alongside the TypeScript app.

This is a development-stage guide. Production deployment and hosting are intentionally left for a later phase.

## 1. Purpose and architecture

The project follows a hybrid architecture intentionally chosen for agentic AI work:

- TypeScript UI and app layer for the user-facing experience
- Python/FastAPI service for the agentic document processing layer
- Reuse of the existing Qeloma Lens ingestion and normalization concepts from the main TypeScript project

This separation keeps the frontend lightweight and maintainable while allowing the agentic logic to live in a Python runtime optimized for service orchestration, validation, extraction, and future multi-step AI workflows.

### High-level design

```text
Browser / UI (TypeScript)
    │
    ▼
Qeloma Lens app
    │
    ├── Existing ingestion pipeline (PDF/DOCX/image/text normalization)
    │
    └── Agent service (Python + FastAPI)
            │
            ├── /health
            ├── /v1/process
            ├── /v1/process-file
            │
            └── document detection + extraction + validation + review routing
```

### Why Python + FastAPI here

This approach is best for an agentic workflow because:

- the Python ecosystem is strong for document processing and orchestration
- FastAPI is lightweight and fast to run locally
- it avoids the heavier operational cost of Django for a service that is focused on processing and orchestration rather than full-stack app logic
- it lets the existing TypeScript app remain the front end without overloading the UI layer with backend orchestration concerns

## 2. Current repo layout

```text
qeloma_lens/
├── src/                                # TypeScript app / existing Lens functionality
│   ├── ingestion/                      # existing document normalization and ingestion logic
│   ├── ai/                             # AI capability logic
│   ├── capabilities/                   # capability plugins
│   ├── gateway/                        # API routing
│   └── ...
├── python_agent/                       # Python agent service
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI app + routes
│   │   ├── agent.py                    # extraction and validation logic
│   │   └── models.py                   # request/response models
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── .env.example
│   ├── .dockerignore
│   └── README.md
├── ARCHITECTURE.md                     # architecture overview
├── DEPLOYMENT.md                       # deployment guide for the main app
├── README.md                           # project overview
├── .env.example                        # project environment config
├── package.json                        # TypeScript project
└── ...
```

## 3. What the Python agent does today

The current Python service is intentionally lightweight and acts as a document processing layer. It is designed for:

- document intake
- text normalization and canonical document envelope patterns
- document-type detection
- field extraction for invoice/resume/general content
- confidence scoring
- validation and review routing for weak or missing fields
- future extension toward multi-agent orchestration

### Example supported flow

1. User submits text or file content.
2. FastAPI receives the request.
3. `AgenticDocumentProcessor.process()` creates a canonical request envelope.
4. Document context is detected from the text and file name.
5. Relevant fields are extracted using regex rules.
6. Values are validated and scored.
7. Review queue is created for low confidence or invalid outputs.

## 4. Local prerequisites

Use the following tools locally:

- Node.js 20+
- Python 3.12 (recommended)
- pip and venv support
- Docker (optional, for containerized local/production setups)

Important note:

The project originally hit a Windows Python 3.14 issue when installing `pydantic-core` from source. That environment failed because the MSVC linker was unavailable. The working path is Python 3.12, which is stable for FastAPI + Pydantic in this environment.

## 5. Local setup

### 5.1 TypeScript app setup

From the repo root:

```bash
npm install
cp .env.example .env
npm run dev
```

This runs the main app locally for UI and backend behavior.

### 5.2 Python agent setup

From the project root:

```bash
cd python_agent
python -m venv .venv312
. .venv312\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Or, with the default Python 3.12 path explicitly:

```bash
cd python_agent
C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv312
. .venv312\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5.3 Dockerized local run

```bash
cd python_agent
cp .env.example .env
docker build -t qeloma-agent .
docker run --rm -p 8000:8000 --env-file .env qeloma-agent
```

Or with Compose:

```bash
cd python_agent
docker compose up --build
```

## 6. Runtime behavior and API surface

The app exposes these routes:

### GET /health

Returns app health info.

Example:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "qeloma-lens-agent-service",
  "environment": "development",
  "port": 8000
}
```

### POST /v1/process

Accepts a document-processing payload and extracts fields.

Example body:

```json
{
  "tenant_id": "tenant-demo",
  "document_type": "invoice",
  "file_name": "invoice-1024.pdf",
  "text": "Invoice No.: INV-2024-0105\nDate: 2024-03-15\nVendor: Acme Corp\nTotal Amount: $1,245.67"
}
```

Request:

```bash
curl -X POST http://127.0.0.1:8000/v1/process \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-demo",
    "document_type": "invoice",
    "file_name": "invoice-1024.pdf",
    "text": "Invoice No.: INV-2024-0105\nDate: 2024-03-15\nVendor: Acme Corp\nTotal Amount: $1,245.67"
  }'
```

The response includes:

- status
- input_id
- document_type
- extracted_fields
- review_queue
- created_at

### POST /v1/process-file

Uploads a file and processes its text content.

```bash
curl -X POST http://127.0.0.1:8000/v1/process-file \
  -F "file=@sample.txt" \
  -F "tenant_id=tenant-demo"
```

## 7. Example success output

This is a sample response from the local service:

```json
{
  "status": "ok",
  "input_id": "inp_20260817111630_9432",
  "document_type": "invoice",
  "text_preview": "Invoice No.: INV-2024-0105\nDate: 2024-03-15\nVendor: Acme Corp\nTotal Amount: $1,245.67",
  "extracted_fields": {
    "invoice_number": {
      "field_name": "invoice_number",
      "value": "INV-2024-0105",
      "confidence": 0.95,
      "valid": true,
      "errors": []
    },
    "date": {
      "field_name": "date",
      "value": "2024-03-15",
      "confidence": 0.95,
      "valid": true,
      "errors": []
    },
    "vendor_name": {
      "field_name": "vendor_name",
      "value": "Acme Corp",
      "confidence": 0.85,
      "valid": true,
      "errors": []
    },
    "total_amount": {
      "field_name": "total_amount",
      "value": "1,245.67",
      "confidence": 0.95,
      "valid": true,
      "errors": []
    }
  },
  "review_queue": [],
  "created_at": "2026-08-17T11:16:30.947656+00:00"
}
```

## 8. Document extraction logic

The current processing layer includes:

- invoice detection via keywords like `invoice`, `receipt`, `total`, `amount`
- resume/cv detection via `resume`, `experience`, `education`
- contract detection via `contract`, `agreement`, `terms`
- regex extraction for field names such as:
  - invoice number
  - date
  - vendor name
  - total amount
  - candidate name
  - email
  - experience years

The logic intentionally has a simple, deterministic rule-based foundation so it always works for local development even without LLM access.

## 9. Environment configuration

The Python service already supports environment variables for local or containerized deployment. Relevant values:

- `APP_ENV` — environment name
- `PORT` — service port, default 8000
- `CORS_ORIGINS` — allowed frontend origins
- `TENANT_ID` — default tenant id

Example file:

```env
APP_ENV=development
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000
TENANT_ID=tenant-demo
```

These values are defined in `python_agent/.env.example` and are intended for future Azure and hosting configuration.

## 10. Troubleshooting

### FastAPI import fails on Python 3.14

Symptoms:

- `pydantic-core` build fails
- `link.exe` not found
- native wheel compilation fails on Windows

Fix:

- use Python 3.12 instead of 3.14
- recreate the venv under Python 3.12
- reinstall dependencies

### Local service not starting

Check:

```bash
python --version
pip --version
uvicorn --version
```

Then verify the venv is activated and dependencies are installed from `requirements.txt`.

### CORS issues in browser calls

Ensure the frontend origin is included in `CORS_ORIGINS`, for example:

```env
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## 11. Production path (planned next stage)

This project is currently documented and validated for local development. Production work still belongs to the next phase:

- deploy the Python agent as a standalone service
- connect frontend to the deployed API URL
- set secrets and env variables in cloud hosting
- add auth and/or API-key protection
- add persistent storage and review workflows
- add logging/monitoring and health checks
- move from local dev to Azure or another production host

Recommended target for the agent service:

- Azure Container Apps for lightweight scaling and low operational weight
- TypeScript app remains on Vercel or another frontend host

## 12. Current status

The system is in a good local development state:

- the FastAPI service works locally
- routes respond successfully
- invoice extraction and validation pass
- Docker and deployment scaffolding are present
- production rollout is intentionally deferred to a later phase

This means the project is ready for iteration and extension without yet being production-hardened.
