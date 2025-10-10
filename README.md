# RAG Factory 🏭

**A production-ready, open-source platform for building and managing multiple RAG (Retrieval-Augmented Generation) systems — 100% local, no vendor lock-in.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![React 19](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)

> **⚡ Quick Start**: `git clone` → `docker-compose up -d` → Open [http://localhost:3000](http://localhost:3000) → Start building RAG systems in minutes!

---

## 🎯 What is RAG Factory?

RAG Factory is a **complete platform** for developers, researchers, and teams who need to build production-grade RAG systems **without the complexity**. No expensive API costs, no cloud dependencies, no vendor lock-in.

### Why RAG Factory?

- **🏠 100% Local**: Everything runs in Docker — your data never leaves your infrastructure
- **🎨 Beautiful UI**: Modern React dashboard for managing projects, sources, and jobs
- **🔌 10+ Connectors**: SPARQL, REST APIs, GitHub, Google Drive, Notion, RSS, Web Scraper, and more
- **📅 Smart Scheduling**: Automate syncs with cron expressions, intervals, or presets
- **🤖 Full RAG Pipeline**: Semantic search + LLM generation (using local Ollama models)
- **📊 Real-Time Monitoring**: Live job progress, analytics dashboard, and insights
- **🗄️ Your Database**: Vectors stored in *your* PostgreSQL — you control everything
- **🌍 Multi-Jurisdiction**: Built-in country/region tagging for global applications
- **⚡ Production-Ready**: Deduplication, retry logic, rate limiting, error handling

## 🏗️ Architecture

```ascii
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Port 3000)              │
│  • Project Management  • Source Configuration               │
│  • Job Monitoring      • RAG Search & Query UI              │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Port 8000)               │
│  • REST API        • Health Checks    • Scheduling          │
└─────────┬───────────────────────────────────────┬───────────┘
          │                                       │
          ▼                                       ▼
┌──────────────────┐                    ┌─────────────────────┐
│  Redis (Queue)   │───────────────────>│   RQ Workers        │
│  • Job Queue     │                    │   • Fetch docs      │
│  • Scheduling    │                    │   • Embed & Store   │
└──────────────────┘                    └──────────┬──────────┘
                                                   │
          ┌────────────────────────────────────────┼─────────────┐
          │                                        │             │
          ▼                                        ▼             ▼
┌──────────────────┐                    ┌─────────────┐  ┌─────────────┐
│  Internal DB     │                    │   Ollama    │  │  Your DB    │
│  rag_factory_db  │                    │  • Embed    │  │  • Vectors  │
│  • Projects      │                    │  • LLM Gen  │  │  • Metadata │
│  • Jobs tracking │                    └─────────────┘  └─────────────┘
│  • Doc hashes    │                    (Port 11434)     (Your config)
└──────────────────┘
(Port 5433)
```

**🔑 Key Concepts:**

- **Two-Database System**: Internal DB tracks everything; your DB stores only vectors
- **Async Processing**: Redis Queue + RQ Workers handle long-running ingestion jobs
- **Local LLM**: Ollama provides embeddings (jina/jina-embeddings-v2-base-es bilingual ES/EN) and generation (Gemma 3)
- **No Vendor Lock-In**: Your vectors live in your PostgreSQL database

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- 8GB RAM minimum (16GB recommended for Ollama models)
- PostgreSQL database with pgvector extension (for production use)

### Option 1: One-Command Setup (Recommended)

```bash
# Clone, start, and open dashboard
git clone https://github.com/felixrivasuxdesigner/rag-factory.git
cd rag-factory
./setup.sh
```

This script will:
1. Start all Docker services
2. Wait for services to be healthy
3. Download Ollama models (embeddings + LLM)
4. Open the dashboard at http://localhost:3000

### Option 2: Manual Setup

```bash
git clone https://github.com/felixrivasuxdesigner/rag-factory.git
cd rag-factory

# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Wait for services (check health)
curl http://localhost:8000/health

# Download Ollama models (required for embeddings)
docker exec ollama ollama pull jina/jina-embeddings-v2-base-es
docker exec ollama ollama pull gemma3:1b-it-qat

# Open the dashboard
open http://localhost:3000  # macOS
# or visit http://localhost:3000 in your browser
```

### 🌐 Access Points

- **Dashboard**: <http://localhost:3000> (React UI)
- **API**: <http://localhost:8000>
- **API Docs**: <http://localhost:8000/docs> (Swagger)
- **PostgreSQL**: `localhost:5433`
- **Redis**: `localhost:6380`
- **Ollama**: <http://localhost:11434>

### ⚡ Optional: Enable Google AI Cloud (Recommended)

Get **15x faster** RAG responses with Google AI's free cloud LLMs:

```bash
# 1. Get free API key from https://aistudio.google.com/apikey
# 2. Configure environment
cd docker
echo "GOOGLE_AI_API_KEY=your-api-key-here" > .env

# 3. Restart API
docker-compose restart api

# 4. In the UI, select "Google AI Cloud" from the LLM Provider dropdown
```

**Performance:**
- Google AI Cloud: ~8 seconds ⚡
- Ollama Local: ~40-120 seconds 🐌

**Cost:** FREE (1,500 queries/day)

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
    "embedding_model": "jina/jina-embeddings-v2-base-es",
    "embedding_dimension": 768
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
- **Embeddings**: Ollama (jina/jina-embeddings-v2-base-es, 768 dimensions, bilingual ES/EN)
- **LLM Providers**:
  - **Google AI Cloud** (default) - gemini-flash-lite, gemma-3-4b, gemma-3-12b (free 1,500/day)
  - **Ollama Local** - gemma3:1b, gemma3:4b (optional, privacy-focused)
- **Frontend**: React 19 + TypeScript + Vite
- **Containerization**: Docker Compose

## ✨ Features

### 🎯 Core Features (v0.8 - Production Ready)

**Backend & API**
- ✅ Multi-project RAG management
- ✅ 10+ data source connectors (see below)
- ✅ REST API with OpenAPI/Swagger docs
- ✅ Async job processing (Redis + RQ)
- ✅ Hash-based deduplication (SHA-256)
- ✅ Smart chunking (adaptive based on doc size)
- ✅ Rate limiting & retry logic
- ✅ Incremental sync support

**Frontend Dashboard**
- ✅ Modern React 19 + TypeScript UI
- ✅ Project & source management (CRUD)
- ✅ Real-time job monitoring with progress bars
- ✅ Analytics dashboard with charts
- ✅ RAG search & query interface
- ✅ Scheduling UI (presets + custom)
- ✅ 15+ pre-configured connector examples

**RAG Pipeline**
- ✅ Semantic search (cosine similarity)
- ✅ Full RAG queries (search + LLM generation)
- ✅ Local embeddings (Ollama jina/jina-embeddings-v2-base-es, 768d, bilingual ES/EN)
- ✅ **Dual LLM Support**: Google AI Cloud (fast, 8s) or Ollama Local (private, 40s+)
- ✅ **UI LLM Selector**: Switch providers & adjust response length in-app
- ✅ **Auto Language Detection**: Spanish/English bilingual support
- ✅ Country/region filtering
- ✅ Metadata-rich results

**Scheduling & Automation**
- ✅ APScheduler integration
- ✅ Cron expressions support
- ✅ Interval-based schedules (30m, 1h, 6h, daily, weekly)
- ✅ Manual trigger ("Sync Now")
- ✅ Pause/resume schedules
- ✅ Auto-load schedules on restart

### 🔌 Available Connectors

**Public (Generic)**
1. ✅ **SPARQL** - Any SPARQL endpoint (legal databases, knowledge graphs)
2. ✅ **REST API** - Generic JSON API connector
3. ✅ **File Upload** - PDF, DOCX, TXT, MD, JSON, CSV
4. ✅ **Web Scraper** - BeautifulSoup4 with CSS selectors
5. ✅ **RSS/Atom** - Blogs, news feeds, podcasts
6. ✅ **GitHub** - README, issues, PRs, code files
7. ✅ **Google Drive** - Docs, Sheets, PDFs (OAuth2)
8. ✅ **Notion** - Pages, databases (Integration Token)

**Example (Pre-configured)**
9. ✅ **Chile BCN** - Chilean legal norms (SPARQL)
10. ✅ **US Congress** - Federal bills (Congress.gov API)

### 🚧 Roadmap (See [ROADMAP.md](ROADMAP.md))

**Next (Phase 6+)**
- [ ] WebSocket for real-time updates
- [ ] Multi-tenancy & authentication
- [ ] Re-ranking for better search quality
- [ ] Kubernetes deployment configs
- [ ] Multi-modal support (images, audio)
- [ ] Query analytics dashboard

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
- `GOOGLE_AI_API_KEY` - (Optional) Google AI API key for cloud LLM providers

**To enable Google AI Cloud:**
```bash
cd docker
echo "GOOGLE_AI_API_KEY=your-key-here" > .env
docker-compose restart api
```

## 🤝 Contributing

We ❤️ contributions! RAG Factory was built with [Claude Code](https://claude.com/claude-code) and is designed to be community-driven.

### Ways to Contribute

- 🐛 **Report bugs** - [Open an issue](https://github.com/felixrivasuxdesigner/vector-doc-ingestion/issues/new?template=bug_report.md)
- 💡 **Suggest features** - [Request a feature](https://github.com/felixrivasuxdesigner/vector-doc-ingestion/issues/new?template=feature_request.md)
- 🔌 **Build connectors** - Add support for new data sources ([Guide](CONTRIBUTING.md#creating-a-new-connector))
- 📝 **Improve docs** - Fix typos, add examples, write tutorials
- 🧪 **Write tests** - Help us reach 100% coverage
- 🎨 **Enhance UI** - Improve the frontend experience

### Quick Start for Contributors

```bash
# Fork the repo, then:
git clone https://github.com/YOUR_USERNAME/vector-doc-ingestion.git
cd vector-doc-ingestion

# Backend development
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload

# Frontend development (in another terminal)
cd frontend
npm install
npm run dev
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Good First Issues

Looking for easy tasks to get started? Check out issues labeled [`good-first-issue`](https://github.com/felixrivasuxdesigner/vector-doc-ingestion/labels/good-first-issue):

- Add new connector for popular APIs
- Improve error messages
- Write documentation
- Add unit tests

## 📄 License

[MIT License](LICENSE) - Free to use, modify, and distribute.

## 🙏 Acknowledgments

- **Built with** [Claude Code](https://claude.com/claude-code) - AI-powered development assistant
- **Embeddings & LLM** [Ollama](https://ollama.ai/) - Local AI models (jina/jina-embeddings-v2-base-es bilingual, Gemma 3)
- **Vector Search** [pgvector](https://github.com/pgvector/pgvector) - PostgreSQL extension for similarity search
- **Job Queue** [RQ](https://python-rq.org/) - Redis Queue for async processing
- **Frontend** [React 19](https://react.dev/) + [Vite](https://vitejs.dev/) - Modern web stack
- **Example Data** Chile's [BCN Open Data](https://datos.bcn.cl/) (SPARQL endpoint)

## 📞 Support & Community

- 📖 **Documentation**: [API Usage Guide](API_USAGE.md) | [Architecture](CLAUDE.md) | [Roadmap](ROADMAP.md)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/felixrivasuxdesigner/vector-doc-ingestion/discussions)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/felixrivasuxdesigner/vector-doc-ingestion/issues)
- 📧 **Email**: felix.rivas.ux@gmail.com
- 🌟 **Star us on GitHub** if you find this useful!

## 🚀 What's Next?

1. **Try it out**: Run `./setup.sh` and explore the dashboard
2. **Read the docs**: Check out [API_USAGE.md](API_USAGE.md) for examples
3. **Build a connector**: Follow the [Connector Guide](CONTRIBUTING.md#creating-a-new-connector)
4. **Join the community**: Share your use case in [Discussions](https://github.com/felixrivasuxdesigner/vector-doc-ingestion/discussions)

## 💼 Use Cases

RAG Factory is perfect for:

- 📚 **Research & Academia** - Index papers, books, and research materials
- ⚖️ **Legal Tech** - Build legal document search systems
- 🏢 **Enterprise Knowledge Base** - Internal docs, wikis, and resources
- 🏥 **Healthcare** - Medical literature and patient resources
- 🌐 **Multi-lingual Apps** - Handle documents from different countries/languages
- 🎓 **Education** - Course materials and learning resources

---

<div align="center">

**⭐ Star us on GitHub • 🔌 Contribute a connector • 📣 Share your RAG Factory project!**

Built with ❤️ by the RAG Factory community

</div>
