# RAG Factory

A multi-project RAG (Retrieval-Augmented Generation) management system that lets you create, configure, and manage multiple RAG projects. Ingest documents from various sources, generate embeddings locally with Ollama, and store vectors in your own PostgreSQL databases.

## 🎯 What is RAG Factory?

RAG Factory is a tool for developers who need to build multiple RAG systems. Instead of managing separate infrastructure for each RAG project, RAG Factory provides:

- **Multi-Project Management**: Create unlimited RAG projects, each with its own configuration
- **Flexible Data Sources**: Connect to SPARQL endpoints, REST APIs, file uploads, and more
- **Local Embeddings**: Generate vectors using Ollama (no API costs, complete privacy)
- **Your Database**: Store vectors in *your own* PostgreSQL databases, not ours
- **Country/Region Filtering**: Tag documents by jurisdiction for multi-country applications
- **Async Processing**: Background job queue handles large document ingestion
- **Deduplication**: Hash-based tracking prevents processing the same document twice

## 🏗️ Architecture

```
┌─────────────┐
│   Frontend  │ (React - Coming Soon)
└──────┬──────┘
       │
       v
┌─────────────┐     ┌─────────────┐
│  FastAPI    │────>│    Redis    │
│  (REST API) │     │   (Queue)   │
└──────┬──────┘     └──────┬──────┘
       │                   │
       │                   v
       │            ┌──────────────┐
       │            │  RQ Workers  │
       │            └──────┬───────┘
       │                   │
       v                   v
┌──────────────────────────────────┐
│   Internal DB (rag_factory_db)   │
│   - Project configs              │
│   - Document hashes (dedup)      │
│   - Job tracking                 │
└──────────────────────────────────┘
       │
       v
┌──────────────┐     ┌─────────────────┐
│   Ollama     │────>│ Your PostgreSQL │
│  (Embeddings)│     │  + pgvector     │
└──────────────┘     └─────────────────┘
```

**Two-Database System:**
1. **Internal DB**: Tracks projects, jobs, and document hashes
2. **Your DB**: Stores the actual vector embeddings (you control it)

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- PostgreSQL database with pgvector extension (your target DB)

### 1. Clone and Start Services

```bash
git clone https://github.com/yourusername/vector-doc-ingestion.git
cd vector-doc-ingestion

# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Check health
curl http://localhost:8000/health
```

Services:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Ollama**: http://localhost:11434

### 2. Create Your First RAG Project

```bash
curl -X POST "http://localhost:8000/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Legal Assistant",
    "description": "RAG for legal documents",
    "target_db_host": "your-db-host",
    "target_db_port": 5432,
    "target_db_name": "your_database",
    "target_db_user": "your_user",
    "target_db_password": "your_password",
    "target_table_name": "legal_vectors",
    "embedding_model": "mxbai-embed-large",
    "embedding_dimension": 1024
  }'
```

### 3. Add a Data Source

```bash
curl -X POST "http://localhost:8000/sources" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "name": "Chile Legal Documents",
    "source_type": "sparql",
    "country_code": "CL",
    "tags": {"language": "es"},
    "config": {
      "endpoint": "https://datos.bcn.cl/es/endpoint-sparql",
      "limit": 100
    }
  }'
```

### 4. Trigger Ingestion

```bash
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "job_type": "full_sync"}'
```

### 5. Monitor Progress

```bash
# Check job status
curl "http://localhost:8000/jobs/1"

# Check project stats
curl "http://localhost:8000/projects/1/stats"
```

## 📚 Documentation

- **[API Usage Guide](API_USAGE.md)** - Complete API reference with examples
- **[CLAUDE.md](CLAUDE.md)** - Technical documentation for developers
- **[Interactive API Docs](http://localhost:8000/docs)** - Swagger UI (when running)

## 🌍 Multi-Country Example

Perfect for applications that need to handle documents from different jurisdictions:

```bash
# Source 1: Chile
curl -X POST "http://localhost:8000/sources" -H "Content-Type: application/json" -d '{
  "project_id": 1,
  "name": "Chile BCN",
  "source_type": "sparql",
  "country_code": "CL",
  "tags": {"language": "es", "jurisdiction": "national"},
  "config": {"endpoint": "https://datos.bcn.cl/es/endpoint-sparql"}
}'

# Source 2: USA
curl -X POST "http://localhost:8000/sources" -H "Content-Type: application/json" -d '{
  "project_id": 1,
  "name": "USA Federal",
  "source_type": "rest_api",
  "country_code": "US",
  "tags": {"language": "en", "jurisdiction": "federal"},
  "config": {"endpoint": "https://api.congress.gov/..."}
}'
```

Then query with country filtering:

```python
# Search only Chile documents
results = writer.similarity_search(
    query_embedding,
    country_code='CL',
    limit=10
)
```

## 🧪 Testing

Run the automated end-to-end test:

```bash
python3 test_api.py
```

This tests:
- ✅ Health check
- ✅ Project creation
- ✅ Database connection
- ✅ Data source creation
- ✅ Job enqueueing
- ✅ Job progress monitoring
- ✅ Statistics retrieval

## 🛠️ Tech Stack

- **Backend**: Python 3.11, FastAPI
- **Job Queue**: Redis + RQ (Redis Queue)
- **Database**: PostgreSQL + pgvector
- **Embeddings**: Ollama (mxbai-embed-large, 1024 dimensions)
- **Frontend**: React 19 + TypeScript + Vite (coming soon)
- **Containerization**: Docker Compose

## 📋 Features

### ✅ MVP (Current)
- [x] Multi-project management
- [x] SPARQL data source connector
- [x] Ollama embedding generation
- [x] pgvector storage in user databases
- [x] Async job processing with RQ
- [x] Country/region tagging and filtering
- [x] Hash-based deduplication
- [x] REST API with auto-docs
- [x] Complete testing suite

### 🚧 Coming Soon
- [ ] WebSocket for real-time progress updates
- [ ] REST API and file upload connectors
- [ ] Frontend dashboard
- [ ] Scheduled/automated syncs
- [ ] User authentication
- [ ] Advanced chunking with LangChain

## 🔧 Development

```bash
# Backend development
cd backend
pip install -r requirements.txt
uvicorn api.main:app --reload

# Run RQ worker locally
rq worker --url redis://localhost:6379/0 rag-tasks

# Run tests
python -m core.schema  # Test schema
python -m services.embedding_service  # Test embeddings
python -m services.vector_db_writer  # Test vector DB
```

See [CLAUDE.md](CLAUDE.md) for detailed development instructions.

## 📝 Environment Variables

See `docker-compose.yml` for configuration options:

- `DATABASE_URL` - Internal database connection
- `REDIS_URL` - Redis connection for job queue
- `OLLAMA_HOST` - Ollama service hostname

## 🤝 Contributing

This project was built with [Claude Code](https://claude.com/claude-code). Contributions welcome!

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

[MIT License](LICENSE) (or your preferred license)

## 🙏 Acknowledgments

- Built with Claude Code
- Uses Ollama for local embeddings
- Powered by pgvector for efficient similarity search
- SPARQL connector example uses Chile's BCN open data

---

**Ready to build your RAG system?** Start with the [API Usage Guide](API_USAGE.md)!
