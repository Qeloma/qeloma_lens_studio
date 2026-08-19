# Qeloma Lens Python Agent Service

This is a lightweight FastAPI service for the agentic AI layer of Qeloma Lens.

It keeps the UI in the existing TypeScript app and adds a low-overhead Python service for:

- document intake
- normalization into a Lens-like document envelope
- field extraction with rule-based confidence checks
- validation and human review routing
- future multi-agent orchestration

## Run locally

This service is pinned to a Python 3.11/3.12-friendly FastAPI/Pydantic stack to avoid the Windows C++ linker issue that occurs on Python 3.14 when compiling `pydantic-core` from source.

```bash
cd python_agent
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /health`
- `POST /v1/process`
- `POST /v1/process-file`

## Containerized deployment

### Docker

```bash
cd python_agent
cp .env.example .env
docker build -t qeloma-agent .
docker run --rm -p 8000:8000 --env-file .env qeloma-agent
```

### Docker Compose

```bash
cd python_agent
cp .env.example .env
docker compose up --build
```

### Azure App Service / Container Apps

```bash
# Build locally
cd python_agent
docker build -t qeloma-agent:latest .

# Example: push to Azure Container Registry, then deploy to Azure Container Apps
az acr create --resource-group qeloma-rg --name qelomaacr --sku Basic
az acr login --name qelomaacr
az acr build --registry qelomaacr --image qeloma-agent:latest .
```

For App Service, use the built image in Azure Container Registry and point the web app at it. For Container Apps, create the app with `--ingress external --target-port 8000`.

## Example

```bash
curl -X POST http://localhost:8000/v1/process \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-demo",
    "document_type": "invoice",
    "file_name": "invoice-1024.pdf",
    "text": "Invoice No.: INV-2024-0105\nDate: 2024-03-15\nVendor: Acme Corp\nTotal Amount: $1,245.67"
  }'
```
