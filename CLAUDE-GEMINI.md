# CLAUDE.md - Gemini File Search Edition

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**RAG Factory - Gemini File Search Edition** - A simplified RAG (Retrieval-Augmented Generation) management system powered by Google's Gemini File Search API. This variant eliminates the complexity of managing embeddings, vector databases, and search infrastructure by delegating all RAG operations to Google's fully managed service.

**Key Concept**: Instead of generating embeddings locally and storing vectors in PostgreSQL, documents are uploaded directly to Google Gemini File Search Stores. Gemini handles chunking, embedding generation, indexing, and semantic search automatically.

## Tech Stack

- **Backend**: Python 3.11, FastAPI, psycopg2
- **Job Queue**: Redis + RQ (Redis Queue)
- **Database**: PostgreSQL (internal tracking only - NO pgvector needed)
- **RAG Engine**: Google Gemini File Search API
- **LLM**: Gemini models (gemini-2.0-flash-exp, gemini-flash-lite-latest)
- **Frontend**: React 19 with TypeScript and Vite
- **Containerization**: Docker Compose

## Architecture Differences from Traditional RAG Factory

### What's REMOVED
- ❌ Ollama (no local embedding generation)
- ❌ User PostgreSQL databases with pgvector
- ❌ Embedding service (embedding_service.py)
- ❌ Vector DB writer (vector_db_writer.py)
- ❌ Search service (search_service.py)
- ❌ Chunking strategies (adaptive_chunker.py)
- ❌ Local LLM service (llm_service.py)

### What's ADDED
- ✅ Gemini File Search service (gemini_file_search_service.py)
- ✅ Direct API integration with Google AI

### Simplified Architecture

```
Frontend (React) → API (FastAPI) → Redis Queue → Workers
                         ↓                          ↓
                Internal DB (tracking)      Gemini File Search
                                                    ↓
                                            Google Cloud (embeddings + vectors + search)
```

### Document Processing Pipeline

**Traditional RAG Factory:**
1. Fetch → Deduplicate → Chunk → Generate Embeddings → Store in User DB

**Gemini File Search Edition:**
1. Fetch → Deduplicate → Upload to Gemini (Gemini handles chunking, embeddings, indexing)

## Key Changes in Database Schema

### Internal Database (`rag_factory_db`)

**rag_projects table** - SIMPLIFIED:
```sql
CREATE TABLE rag_projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,

    -- Gemini File Search Store configuration
    gemini_file_search_store_id VARCHAR(500),      -- e.g., "file_search_stores/abc123"
    gemini_file_search_store_name VARCHAR(255),    -- Display name in Gemini

    -- Metadata
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**What's REMOVED from schema:**
- `target_db_host`, `target_db_port`, `target_db_name`, `target_db_user`, `target_db_password`, `target_table_name`
- `embedding_model`, `embedding_dimension`, `chunk_size`, `chunk_overlap`

Other tables remain the same:
- `data_sources` - Still tracks where documents come from
- `documents_tracking` - Still tracks document hashes for deduplication
- `ingestion_jobs` - Still tracks job progress
- `documents_content_cache` - Still caches downloaded content

## Development Workflow

### Setup

1. **Get Google AI API Key** (Free tier: 1,500 queries/day):
   ```bash
   # Visit: https://aistudio.google.com/apikey
   # Sign in → Create API Key → Copy it
   ```

2. **Configure Environment**:
   ```bash
   cd docker
   echo "GOOGLE_AI_API_KEY=your-api-key-here" > .env
   ```

3. **Start Services**:
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

### Key Development Commands

#### Docker Services

```bash
# Start services (NO Ollama needed!)
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f [service-name]

# Services: db, redis, api, worker, frontend

# Stop services
docker-compose -f docker/docker-compose.yml down
```

#### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Test internal schema
DATABASE_URL='postgresql://user:password@localhost:5432/rag_factory_db' \
python3 -m core.schema

# Test Gemini File Search service
GOOGLE_AI_API_KEY='your-key' \
python3 -m services.gemini_file_search_service

# Run API locally
GOOGLE_AI_API_KEY='your-key' \
DATABASE_URL='postgresql://user:password@localhost:5432/rag_factory_db' \
REDIS_URL='redis://localhost:6379/0' \
uvicorn api.main:app --reload --port 8000

# Run RQ worker locally
GOOGLE_AI_API_KEY='your-key' \
REDIS_URL='redis://localhost:6379/0' \
DATABASE_URL='postgresql://user:password@localhost:5432/rag_factory_db' \
rq worker --url redis://localhost:6379/0 rag-tasks
```

## API Endpoints

### Health & Info
- `GET /` - API info
- `GET /health` - Health check (database, redis, **gemini_file_search**)

### RAG Projects (SIMPLIFIED)
- `POST /projects` - Create new RAG project (auto-creates Gemini File Search Store)
  - **Request**: `{ "name": "My Project", "description": "..." }`
  - **NO target_db or embedding config needed!**
- `GET /projects` - List all projects
- `GET /projects/{id}` - Get project details
- `PATCH /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project (cascades, deletes Gemini Store)
- `GET /projects/{id}/stats` - Project statistics

### Data Sources (UNCHANGED)
- `POST /sources` - Create data source for a project
- `GET /projects/{id}/sources` - List project data sources

### Ingestion Jobs (SIMPLIFIED)
- `POST /jobs` - Create and enqueue ingestion job
  - **Automatically uploads to Gemini File Search Store**
- `GET /jobs/{id}` - Get job status and progress

### Queries (POWERED BY GEMINI)
- `POST /query` - RAG query using Gemini File Search
  - **Request**: `{ "project_id": 1, "question": "...", "model": "gemini-2.0-flash-exp" }`
  - **Gemini handles both retrieval AND generation in one call**

### Utilities
- ~~`POST /test-connection`~~ - **REMOVED** (no user databases)

Interactive API docs: `http://localhost:8000/docs`

## Environment Variables

**Docker Compose** (set in `.env` file):
```bash
GOOGLE_AI_API_KEY=your-api-key-here
```

**Local Development**:
```bash
export GOOGLE_AI_API_KEY='your-api-key-here'
export DATABASE_URL='postgresql://user:password@localhost:5432/rag_factory_db'
export REDIS_URL='redis://localhost:6379/0'
```

## Key Files and Modules

### Backend Core
- [backend/core/schema.py](backend/core/schema.py) - Internal database schema (simplified)
- [backend/core/database.py](backend/core/database.py) - Database connection utilities

### Services
- [backend/services/gemini_file_search_service.py](backend/services/gemini_file_search_service.py) - **NEW** Gemini File Search integration
- ~~backend/services/embedding_service.py~~ - **REMOVED**
- ~~backend/services/vector_db_writer.py~~ - **REMOVED**

### Workers
- [backend/workers/ingestion_tasks.py](backend/workers/ingestion_tasks.py) - **SIMPLIFIED** RQ async job tasks (uploads to Gemini)

### API
- [backend/api/main.py](backend/api/main.py) - FastAPI application and endpoints
- [backend/api/models.py](backend/api/models.py) - Pydantic request/response models

### Connectors (UNCHANGED)
- [backend/connectors/sparql_connector.py](backend/connectors/sparql_connector.py) - SPARQL endpoint connector
- [backend/processors/document_processor.py](backend/processors/document_processor.py) - Document text processing

## Gemini File Search Features

### Supported File Types
- Documents: PDF, DOC, DOCX, TXT, MD, HTML
- Data: CSV, XLSX, XLS
- Code: Python, JavaScript, Java, C++, etc.
- Max file size: 100 MB per document

### Storage Limits
- **Free tier**: 1 GB total storage
- **Paid tiers**: Up to 1 TB
- Storage cost: **FREE** (only pay for initial indexing at $0.15 per 1M tokens)

### Models Available
- **gemini-2.0-flash-exp** (recommended) - Fast, high-quality responses
- **gemini-flash-lite-latest** - Ultra-fast, lower cost

### Automatic Processing
Gemini File Search automatically:
- Chunks documents intelligently
- Generates embeddings (768-dimension)
- Indexes for fast semantic search
- Retrieves relevant context
- Generates grounded answers with citations

## Service Ports

- Frontend: http://localhost:3001
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL (Internal DB): localhost:5433
- Redis: localhost:6380
- ~~Ollama~~: **REMOVED**

## Advantages of Gemini File Search Edition

1. **Simplified Infrastructure**
   - No Ollama to manage
   - No user vector databases to configure
   - No embedding dimension tuning

2. **Lower Operational Costs**
   - No GPU needed for embeddings
   - No vector DB storage costs
   - Pay only for what you use ($0.15 per 1M tokens for indexing)

3. **Better Performance**
   - Google's optimized infrastructure
   - Fast semantic search at scale
   - Automatic scaling

4. **Easier Maintenance**
   - Fewer moving parts
   - Managed by Google
   - Automatic updates to embedding models

5. **Built-in Features**
   - Citation tracking
   - Grounding metadata
   - Multi-format support
   - Intelligent chunking

## Limitations vs Traditional RAG Factory

1. **Vendor Lock-in**: Dependent on Google AI API
2. **API Rate Limits**: Free tier limited to 1,500 queries/day
3. **Storage Limits**: 1 GB free tier (vs unlimited self-hosted)
4. **Network Dependency**: Requires internet connection
5. **Less Control**: Cannot fine-tune chunking/embedding strategies
6. **Data Privacy**: Documents stored on Google's servers

## Migration from Traditional RAG Factory

To convert an existing traditional RAG Factory project:

1. **Create new Gemini File Search Store** for each project
2. **Re-ingest documents** using new workers (documents will be uploaded to Gemini)
3. **Update frontend** to remove embedding/database config UI
4. **Delete user vector databases** (data is now in Gemini)

## Testing

### Test Gemini File Search Service
```bash
cd backend
GOOGLE_AI_API_KEY='your-key' python3 -m services.gemini_file_search_service
```

Expected output:
- ✓ Create File Search Store
- ✓ Upload test documents
- ✓ Query with Gemini
- ✓ Delete test store

### Test Full Pipeline
1. Start services: `docker-compose up -d`
2. Create project via API: `POST /projects`
3. Add data source: `POST /sources`
4. Trigger ingestion: `POST /jobs`
5. Query documents: `POST /query`

## Cost Estimation

**Free Tier (1,500 queries/day, 1 GB storage):**
- Indexing: $0.15 per 1M tokens (~500-1000 documents)
- Storage: FREE
- Queries: FREE

**Example Monthly Cost:**
- 100,000 documents indexed: ~$150
- Unlimited queries: $0
- Storage: $0

**Compare to Traditional RAG Factory:**
- Self-hosted: $0 (but requires GPU server ~$500-1000/month)
- Cloud Vector DB (Pinecone, etc.): ~$70-200/month

## Future Enhancements

- Support for direct file uploads (PDF, DOCX)
- Multi-store queries (search across multiple projects)
- Advanced filtering (by date, document type, metadata)
- Real-time ingestion via webhooks
- Analytics dashboard (query patterns, popular documents)
- Batch document deletion
- Store migration tools

## Resources

- **Gemini File Search API Docs**: https://ai.google.dev/gemini-api/docs/file-search
- **Get API Key**: https://aistudio.google.com/apikey
- **Pricing**: https://ai.google.dev/pricing
- **Python SDK**: https://github.com/google-gemini/generative-ai-python

## Branch Information

This is a **variant branch** of RAG Factory. The main branch uses traditional vector databases.

- **Main Branch** (`main`): Traditional RAG with Ollama + pgvector
- **This Branch** (`claude/gemini-file-search-*`): Gemini File Search powered RAG
