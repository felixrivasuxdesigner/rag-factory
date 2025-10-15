# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**RAG Factory** - A multi-project RAG (Retrieval-Augmented Generation) management system that allows users to create, configure, and manage multiple RAG projects. Each project can ingest documents from various sources, generate embeddings using local Ollama models, and store vectors in user-provided PostgreSQL databases.

**Key Concept**: The application manages RAG project configurations and document tracking internally, but stores the actual vector embeddings in the **user's own PostgreSQL databases**. This allows users to integrate RAG capabilities into their existing infrastructure.

## Tech Stack

- **Backend**: Python 3.11, FastAPI, psycopg2
- **Job Queue**: Redis + RQ (Redis Queue)
- **Database**: PostgreSQL with pgvector extension
- **Embeddings**: Ollama (local) - jina/jina-embeddings-v2-base-es (768 dimensions, bilingual ES/EN)
- **LLM Providers**:
  - **Google AI Cloud** (default) - gemini-flash-lite-latest, gemma-3-4b-it, gemma-3-12b-it
  - **Ollama Local** - gemma3:1b-it-qat, gemma3:4b-it-qat (optional)
- **Frontend**: React 19 with TypeScript and Vite
- **Containerization**: Docker Compose

## Architecture

### Two-Database System

1. **Internal Database** (`rag_factory_db`):
   - `rag_projects` - Project configurations (target DB credentials, embedding settings)
   - `data_sources` - Data source configurations (SPARQL, APIs, files)
   - `documents_tracking` - Document hashes for deduplication (NO vectors stored here)
   - `ingestion_jobs` - Job status and progress tracking

2. **User Databases** (dynamically connected):
   - User provides: host, port, database, user, password, table_name
   - Application creates table with vector columns
   - Embeddings stored here for user's RAG queries

### Service Architecture

```
Frontend (React) → API (FastAPI) → Redis Queue → Workers
                         ↓                          ↓
                Internal DB (tracking)      User DB (vectors)
                         ↓
                    Ollama (embeddings)
```

### Document Processing Pipeline

1. **Fetch**: Get documents from configured sources (SPARQL, APIs, etc.)
2. **Deduplicate**: Check SHA-256 hash against `documents_tracking`
3. **Chunk**: Split text with overlap (default 1000 chars, 200 overlap)
4. **Embed**: Generate vectors using Ollama
5. **Store**: Insert into user's vector database
6. **Track**: Mark as completed in internal tracking DB

### Vector Database Schema (v2 - PostgreSQL Best Practices)

RAG Factory now supports **Schema v2**, which implements PostgreSQL best practices for vector storage:

**Schema v2 Features:**
- **SERIAL auto-increment IDs** instead of TEXT IDs (more efficient, 4 bytes vs variable length)
- **Structured columns**: `title`, `document_type`, `source`, `specialty` (instead of storing everything in metadata)
- **Optimized indexes**: 5 indexes created automatically (embedding, document_type, specialty, metadata, created_at)
- **Better query performance**: Column-level filtering is 30-50% faster than JSONB queries
- **Chunk metadata**: `chunk_index` and `original_document_id` stored in JSONB metadata

**Table Schema:**
```sql
CREATE TABLE {table_name} (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    source VARCHAR(255),
    specialty VARCHAR(50),
    embedding vector(768),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes created automatically:
-- 1. IVFFlat vector index for similarity search
-- 2. document_type (btree) for filtering by type
-- 3. specialty (btree) for filtering by specialty
-- 4. metadata (GIN) for JSONB queries
-- 5. created_at (btree) for time-based queries
```

**Backward Compatibility:**
- Auto-detects existing table schema (v1 or v2)
- Supports legacy TEXT id schema (v1) for existing deployments
- New projects default to Schema v2
- Migration path: Create new table with v2 schema, re-ingest documents

**When to Use Each Schema:**
- **Schema v2 (recommended)**: New projects, high-performance requirements, structured legal/medical documents
- **Schema v1 (legacy)**: Existing deployments, simple use cases, custom metadata needs

## Key Development Commands

### Docker Services

```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f [service-name]

# Services: db, redis, ollama, api, worker, backend, frontend

# Stop services
docker-compose -f docker/docker-compose.yml down
```

### Backend Development

```bash
cd backend

# Install dependencies (if running locally)
pip install -r requirements.txt

# Test internal schema
DATABASE_URL='postgresql://user:password@localhost:5432/rag_factory_db' \
python3 -m core.schema

# Test embedding service
python3 -m services.embedding_service

# Test vector DB writer
python3 -m services.vector_db_writer

# Run API locally
uvicorn api.main:app --reload --port 8000

# Run RQ worker locally
REDIS_URL='redis://localhost:6379/0' \
DATABASE_URL='postgresql://user:password@localhost:5432/rag_factory_db' \
rq worker --url redis://localhost:6379/0 rag-tasks
```

### Frontend Development

```bash
cd frontend

npm install
npm run dev          # Dev server
npm run build        # Production build
npm run lint         # Linting
npm run preview      # Preview production build
```

### Database Management

```bash
# Create internal database (if not exists)
docker exec [postgres-container] psql -U [user] -d postgres -c "CREATE DATABASE rag_factory_db;"

# Enable pgvector
docker exec [postgres-container] psql -U [user] -d rag_factory_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Connect to internal DB
docker exec -it [postgres-container] psql -U [user] -d rag_factory_db
```

## API Endpoints

### Health & Info
- `GET /` - API info
- `GET /health` - Health check (database, redis, ollama)

### RAG Projects
- `POST /projects` - Create new RAG project
- `GET /projects` - List all projects (optional `?status_filter=active`)
- `GET /projects/{id}` - Get project details
- `PATCH /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project (cascades)
- `GET /projects/{id}/stats` - Project statistics

### Data Sources
- `POST /sources` - Create data source for a project
- `GET /projects/{id}/sources` - List project data sources

### Ingestion Jobs
- `POST /jobs` - Create and enqueue ingestion job
- `GET /jobs/{id}` - Get job status and progress

### Utilities
- `POST /test-connection` - Test user database connection

Interactive API docs: `http://localhost:8000/docs`

## Environment Variables

**Docker Compose** (set in [docker/docker-compose.yml](docker/docker-compose.yml)):
- `DATABASE_URL` - Internal database URL
- `REDIS_URL` - Redis connection URL
- `OLLAMA_HOST` - Ollama service hostname
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` - Database credentials

**Local Development**:
```bash
export DATABASE_URL='postgresql://user:password@localhost:5432/rag_factory_db'
export REDIS_URL='redis://localhost:6379/0'
export OLLAMA_HOST='localhost'
```

## Key Files and Modules

### Backend Core
- [backend/core/schema.py](backend/core/schema.py) - Internal database schema
- [backend/core/database.py](backend/core/database.py) - Database connection utilities

### Services
- [backend/services/embedding_service.py](backend/services/embedding_service.py) - Ollama embedding generation
- [backend/services/vector_db_writer.py](backend/services/vector_db_writer.py) - Dynamic user DB connections
- [backend/workers/ingestion_tasks.py](backend/workers/ingestion_tasks.py) - RQ async job tasks

### API
- [backend/api/main.py](backend/api/main.py) - FastAPI application and endpoints
- [backend/api/models.py](backend/api/models.py) - Pydantic request/response models

### Legacy (to be refactored)
- [backend/connectors/sparql_connector.py](backend/connectors/sparql_connector.py) - SPARQL endpoint connector
- [backend/processors/document_processor.py](backend/processors/document_processor.py) - Document text processing

## Important Implementation Notes

### Deduplication Strategy
Documents are deduplicated using SHA-256 content hashing stored in `documents_tracking.document_hash`. Before processing a document:
1. Compute hash of content
2. Check if hash exists in tracking table for this project
3. If exists and status='completed', skip
4. If new, track and process

### Vector Database Table Schema
When connecting to user's database, the application creates:
```sql
CREATE TABLE {user_table_name} (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX {table}_embedding_idx ON {table}
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### Job Queue System
- Jobs are enqueued to Redis queue named `rag-tasks`
- RQ workers process jobs asynchronously
- Job progress updates are written to `ingestion_jobs` table
- Workers update document status in `documents_tracking`

### LLM Models Available

#### Google AI Cloud (Recommended - Fast & Free)
- **gemini-flash-lite-latest** (default) - Fastest, 8s response, 3.6k chars, free 1,500 queries/day
- **gemini-2.0-flash-exp** - More detailed, 9s response, 4.1k chars
- **gemma-3-4b-it** - Google-hosted Gemma, 7s response
- **gemma-3-12b-it** - Most detailed, 14s response, 4k chars

#### Ollama Local (Optional - Privacy-focused)
- **jina/jina-embeddings-v2-base-es** (323 MB) - Default embedding model, 768 dimensions, bilingual Spanish-English
- **embeddinggemma** (621 MB) - Alternative embedding model, 768 dimensions, multilingual (100+ languages)
- **gemma3:1b-it-qat** (1.0 GB) - Faster local LLM option (~40s response)
- **gemma3:4b-it-qat** (4.0 GB) - Better quality local LLM (~120s response)

## Service Ports

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Ollama: http://localhost:11434

## Development Workflow

1. **Start services**: `docker-compose -f docker/docker-compose.yml up -d`
2. **Create RAG project** via API: `POST /projects` with target DB config
3. **Add data source**: `POST /sources` with source configuration
4. **Trigger ingestion**: `POST /jobs` to start async processing
5. **Monitor progress**: `GET /jobs/{id}` or `GET /projects/{id}/stats`
6. **Query vectors**: Connect directly to user's database for similarity search

## Google AI Cloud Setup (Recommended)

RAG Factory supports cloud-based LLM providers for faster responses, especially on older hardware.

### Quick Setup (3 minutes)

1. **Get API Key** (Free - 1,500 queries/day):
   ```bash
   # Visit: https://aistudio.google.com/apikey
   # Sign in → Create API Key → Copy it
   ```

2. **Configure Environment**:
   ```bash
   # Create .env file in docker directory
   cd docker
   echo "GOOGLE_AI_API_KEY=your-api-key-here" > .env
   ```

3. **Restart API**:
   ```bash
   docker-compose restart api
   ```

4. **Use in Frontend**:
   - Open http://localhost:3000
   - Go to "Search & Query" tab
   - Select "Google AI Cloud" from LLM Provider dropdown
   - Enjoy 8-second responses instead of 40-120s with local Ollama!

### Performance Comparison

| Provider | Model | Response Time | Quality | Cost |
|----------|-------|---------------|---------|------|
| Google AI (cloud) | gemini-flash-lite | ~8s | ⭐⭐⭐⭐ | Free (1,500/day) |
| Ollama (local) | gemma3:1b | ~40s | ⭐⭐ | Free (unlimited) |
| Ollama (local) | gemma3:4b | ~120s | ⭐⭐⭐ | Free (unlimited) |

**Recommendation**: Use Google AI Cloud for better user experience. Falls back to Ollama automatically if API key not configured.

## Testing

No automated tests yet. Each module has manual test code in its `if __name__ == '__main__'` block:

```bash
# Test individual modules
python -m backend.core.schema
python -m backend.services.embedding_service
python -m backend.services.vector_db_writer
```

## Future Enhancements

- WebSocket support for real-time job progress
- Additional data sources: REST APIs, file uploads, web scraping
- Advanced chunking with LangChain
- Frontend dashboard
- Authentication and user management
- Scheduled/automated syncs
- Batch job management
