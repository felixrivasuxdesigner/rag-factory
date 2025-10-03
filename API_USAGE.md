# RAG Factory API - Usage Guide

Complete guide to using the RAG Factory API for creating multi-project RAG systems.

## Quick Start

### 1. Start All Services

```bash
docker-compose -f docker/docker-compose.yml up -d
```

Wait for all services to be healthy:
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Ollama: `localhost:11434`
- API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

### 2. Check Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "api": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "ollama": "healthy"
}
```

## Complete Workflow Example

### Step 1: Create a RAG Project

```bash
curl -X POST "http://localhost:8000/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Legal Assistant - Chile",
    "description": "RAG system for Chilean legal documents",
    "target_db_host": "localhost",
    "target_db_port": 5432,
    "target_db_name": "my_app_db",
    "target_db_user": "myuser",
    "target_db_password": "mypassword",
    "target_table_name": "chile_legal_vectors",
    "embedding_model": "mxbai-embed-large",
    "embedding_dimension": 1024,
    "chunk_size": 1000,
    "chunk_overlap": 200
  }'
```

Response:
```json
{
  "id": 1,
  "name": "Legal Assistant - Chile",
  "status": "active",
  "target_table_name": "chile_legal_vectors",
  ...
}
```

**Save the `id` for subsequent requests!**

### Step 2: Test Database Connection (Optional but Recommended)

```bash
curl -X POST "http://localhost:8000/test-connection" \
  -H "Content-Type: application/json" \
  -d '{
    "host": "localhost",
    "port": 5432,
    "database": "my_app_db",
    "user": "myuser",
    "password": "mypassword"
  }'
```

Response:
```json
{
  "success": true,
  "message": "Connection successful",
  "pgvector_available": true
}
```

### Step 3: Add a Data Source

```bash
curl -X POST "http://localhost:8000/sources" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "name": "Chile BCN Laws",
    "source_type": "sparql",
    "country_code": "CL",
    "region": "National",
    "tags": {
      "language": "es",
      "jurisdiction": "national"
    },
    "config": {
      "endpoint": "https://datos.bcn.cl/es/endpoint-sparql",
      "limit": 100
    },
    "sync_frequency": "manual"
  }'
```

Response:
```json
{
  "id": 1,
  "project_id": 1,
  "name": "Chile BCN Laws",
  "source_type": "sparql",
  "country_code": "CL",
  "region": "National",
  ...
}
```

### Step 4: Trigger Ingestion Job

```bash
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "source_id": 1,
    "job_type": "full_sync"
  }'
```

Response:
```json
{
  "id": 1,
  "project_id": 1,
  "source_id": 1,
  "status": "queued",
  "total_documents": 0,
  "processed_documents": 0,
  ...
}
```

### Step 5: Monitor Job Progress

```bash
# Poll every few seconds
curl "http://localhost:8000/jobs/1"
```

Response (while running):
```json
{
  "id": 1,
  "status": "running",
  "total_documents": 100,
  "processed_documents": 45,
  "successful_documents": 45,
  "failed_documents": 0,
  ...
}
```

Response (completed):
```json
{
  "id": 1,
  "status": "completed",
  "total_documents": 100,
  "processed_documents": 100,
  "successful_documents": 98,
  "failed_documents": 2,
  "completed_at": "2025-10-03T20:30:00Z",
  ...
}
```

### Step 6: Check Project Statistics

```bash
curl "http://localhost:8000/projects/1/stats"
```

Response:
```json
{
  "total_documents": 100,
  "documents_completed": 98,
  "documents_failed": 2,
  "documents_pending": 0,
  "documents_processing": 0,
  "total_jobs": 1,
  "jobs_running": 0,
  "jobs_completed": 1,
  "jobs_failed": 0
}
```

## Advanced Examples

### Multi-Country Setup

**Project 1: Chile Legal**
```bash
curl -X POST "http://localhost:8000/projects" -H "Content-Type: application/json" -d '{
  "name": "Chile Legal System",
  "target_table_name": "chile_legal_vectors",
  ...
}'
```

**Source 1: Chile BCN**
```bash
curl -X POST "http://localhost:8000/sources" -H "Content-Type: application/json" -d '{
  "project_id": 1,
  "name": "Chile BCN",
  "source_type": "sparql",
  "country_code": "CL",
  "tags": {"language": "es", "type": "statutory"},
  "config": {"endpoint": "https://datos.bcn.cl/es/endpoint-sparql"}
}'
```

**Project 2: USA Legal**
```bash
curl -X POST "http://localhost:8000/projects" -H "Content-Type: application/json" -d '{
  "name": "USA Legal System",
  "target_table_name": "usa_legal_vectors",
  ...
}'
```

**Source 2: USA Federal**
```bash
curl -X POST "http://localhost:8000/sources" -H "Content-Type: application/json" -d '{
  "project_id": 2,
  "name": "USA Federal Laws",
  "source_type": "rest_api",
  "country_code": "US",
  "region": "Federal",
  "tags": {"language": "en", "jurisdiction": "federal"},
  "config": {"endpoint": "https://api.congress.gov/..."}
}'
```

### Filtering Vector Search (Direct DB Query)

Once documents are ingested, query your vector database with country filtering:

```python
from services.vector_db_writer import VectorDBWriter
from services.embedding_service import EmbeddingService

# Connect to your DB
writer = VectorDBWriter(
    host='localhost',
    database='my_app_db',
    user='myuser',
    password='mypassword',
    table_name='chile_legal_vectors'
)
writer.connect()

# Generate query embedding
embedding_service = EmbeddingService()
query_embedding = embedding_service.generate_embedding("derecho laboral teletrabajo")

# Search only Chile documents
results = writer.similarity_search(
    query_embedding,
    country_code='CL',
    limit=10,
    threshold=0.75
)

for result in results:
    print(f"Similarity: {result['similarity']:.2f}")
    print(f"Content: {result['content'][:200]}...")
    print(f"Country: {result['metadata']['country_code']}")
    print("---")
```

## API Endpoints Reference

### Projects
- `POST /projects` - Create project
- `GET /projects` - List all projects
- `GET /projects/{id}` - Get project details
- `PATCH /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project
- `GET /projects/{id}/stats` - Get project statistics
- `GET /projects/{id}/sources` - List project sources
- `GET /projects/{id}/jobs` - List project jobs

### Data Sources
- `POST /sources` - Create data source

### Jobs
- `POST /jobs` - Create and enqueue job
- `GET /jobs/{id}` - Get job status

### Utilities
- `GET /` - API info
- `GET /health` - Health check
- `POST /test-connection` - Test database connection

## Running the Test Script

```bash
# Make sure API is running
docker-compose -f docker/docker-compose.yml up -d api worker redis ollama

# Run end-to-end test
python3 test_api.py
```

## Common Issues

### 1. Job Stuck in "queued"
**Cause:** Worker not running
**Fix:** `docker-compose -f docker/docker-compose.yml up -d worker`

### 2. "Ollama service not available"
**Cause:** Ollama not started or models not downloaded
**Fix:**
```bash
docker-compose -f docker/docker-compose.yml up -d ollama
docker exec ollama ollama pull mxbai-embed-large
```

### 3. Connection test fails
**Cause:** Database credentials incorrect or pgvector not installed
**Fix:** Check credentials and ensure `CREATE EXTENSION vector;` was run

### 4. SPARQL endpoint timeouts
**Cause:** BCN endpoint is unreliable
**Fix:** Use smaller `limit` in config or implement retry logic

## Next Steps

1. Query your vector database for similarity search
2. Integrate with your application
3. Add more data sources
4. Set up scheduled syncs (coming soon)
5. Build frontend dashboard (coming soon)

For more details, see the [CLAUDE.md](CLAUDE.md) documentation.
