# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a document ingestion pipeline that fetches legal documents (Chilean laws) from a SPARQL endpoint, processes them, and stores them in a PostgreSQL database with pgvector support for future vector search capabilities.

**Tech Stack:**
- Backend: Python with FastAPI, SPARQLWrapper, psycopg2
- Database: PostgreSQL with pgvector extension
- LLM: Ollama (local)
- Frontend: React 19 with TypeScript and Vite
- Containerization: Docker Compose

## Architecture

The system follows a three-stage pipeline pattern:

1. **Data Acquisition (Connectors)**: [backend/connectors/sparql_connector.py](backend/connectors/sparql_connector.py) handles fetching raw data from SPARQL endpoints. Uses custom User-Agent headers to avoid being blocked.

2. **Data Processing (Processors)**: [backend/processors/document_processor.py](backend/processors/document_processor.py) cleans and transforms raw SPARQL results into structured document objects.

3. **Data Persistence (Core)**: [backend/core/database.py](backend/core/database.py) manages PostgreSQL connections and document storage with upsert logic (ON CONFLICT DO NOTHING).

The main orchestration is in [backend/core/main.py](backend/core/main.py) which runs the complete pipeline: fetch → process → store.

## Key Development Commands

### Docker Services
```bash
# Start all services (database, ollama, backend, api, frontend)
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Stop services
docker-compose -f docker/docker-compose.yml down
```

### Backend Development
```bash
# Install dependencies
cd backend && pip install -r requirements.txt

# Run the ingestion pipeline manually
python -m core.main

# Run the FastAPI server locally (dev mode)
cd backend && uvicorn api.main:app --reload --port 8000

# Test individual modules
python -m connectors.sparql_connector
python -m processors.document_processor
python -m core.database
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Lint
npm run lint

# Preview production build
npm run preview
```

## Environment Configuration

The backend uses environment variables with fallback defaults:

- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql://user:password@localhost:5432/vector_db`)
- `SPARQL_ENDPOINT`: SPARQL endpoint URL (default: `https://datos.bcn.cl/es/endpoint-sparql`)
- `DOCUMENT_LIMIT`: Max documents to fetch per run (default: 25)
- `OLLAMA_HOST`: Ollama service hostname (default set in docker-compose)

In Docker, these are configured in [docker/docker-compose.yml](docker/docker-compose.yml).

## Important Notes

- **BCN Endpoint Reliability**: The Chilean BCN SPARQL endpoint (`https://datos.bcn.cl/es/endpoint-sparql`) has been unreliable during development. The code includes error handling and logging for when the endpoint is down or blocks requests.

- **Database Schema**: The `documents` table stores processed documents before vectorization. It uses the SPARQL URI as the primary key (`id TEXT PRIMARY KEY`) to prevent duplicates.

- **Module Execution**: Backend modules can be run standalone for testing (see `if __name__ == '__main__'` blocks in each file). The Docker backend service uses `python -m core.main` to ensure correct package resolution.

- **No Tests Yet**: There are no automated tests. Each module has manual test code in its `__main__` block.

## Service Ports

- Frontend: http://localhost:3000
- API: http://localhost:8000
- PostgreSQL: localhost:5432
- Ollama: http://localhost:11434
