# Local Setup Guide

This guide describes how to install dependencies, configure environment variables, apply database migrations, provision WorkOS credentials, and start the PII Guard application locally.

---

## Prerequisites

- **Python**: 3.12+
- **Node.js**: 20+ (with npm)
- **Git**

---

## Quickstart

### 1. Configure Environment Variables

Copy the example environment file:

```sh
cp .env.example apps/api/.env
```

Edit `apps/api/.env` with your settings:

```ini
APP_ENV=development
DATABASE_URL=sqlite:///./pii-guard.db
PUBLIC_APP_URL=http://localhost:5173
WORKOS_CLIENT_ID=client_01M4DB2GA63J2DSF441YB66NZY
WORKOS_REDIRECT_URI=http://localhost:5173/api/v1/auth/callback
SHOW_DEMO_SAMPLES=true
OPENAI_MODEL=gpt-4o-mini
STORAGE_DIR=./uploads
```

Generate a Fernet cookie encryption key:

```sh
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set `WORKOS_COOKIE_PASSWORD` in `apps/api/.env` to this generated key. Add your `WORKOS_API_KEY` and optional `OPENAI_API_KEY`.

---

### 2. Backend Setup (API & Engine)

From the repository root or `apps/api`:

```sh
cd apps/api
python3 -m venv .venv

# On Linux / macOS:
source .venv/bin/activate
# On Windows (PowerShell):
# .venv\Scripts\Activate.ps1

pip install -e '.[test]'
```

To install the local privacy engine package in editable mode:

```sh
pip install -e ../../packages/engine
```

> **Note on Engine Runtime Tools**:
> The privacy engine requires OCR and NLP runtimes for document processing:
> - OCR runtime: `rapidocr-onnxruntime` / `onnxruntime`
> - Presidio Analyzer & NLP: `presidio-analyzer`, `spacy` with `python -m spacy download en_core_web_sm`

---

### 3. Database Migrations

Apply Alembic database migrations to initialize tables for companies, users, and manager assignments:

```sh
cd apps/api
.venv/bin/alembic upgrade head
```

---

### 4. Seed Fictional Development Data (Optional)

To seed a synthetic demo company, manager, employees, and assignments for local development:

```sh
APP_ENV=development DEMO_ADAPTERS_ENABLED=true scripts/seed-demo.sh
```

---

### 5. Frontend Setup

From `apps/web`:

```sh
cd apps/web
npm ci
npm run dev
```

The frontend will start on [http://localhost:5173](http://localhost:5173). The Vite development server automatically proxies `/api` requests to `http://localhost:8000`.

---

### 6. Start the Backend API

From `apps/api`:

```sh
cd apps/api
.venv/bin/uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- Health check: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- Interactive API Docs: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- OpenAPI Specification: [http://localhost:8000/api/openapi.json](http://localhost:8000/api/openapi.json)

---

## Running Automated Checks

Run backend unit and integration tests:

```sh
cd apps/api
.venv/bin/python -m pytest tests -v
```

Run frontend tests and production build:

```sh
cd apps/web
npm test
npm run build
```

Verify migration schema consistency:

```sh
cd apps/api
.venv/bin/alembic check
```
