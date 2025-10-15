# 🌐 RAG Factory MCP Server

**Make your RAG knowledge bases available to any AI assistant - with full project and job management**

The RAG Factory MCP (Model Context Protocol) Server exposes your RAG projects as tools that can be used by AI assistants like Claude Desktop, ChatGPT with plugins, and any other MCP-compatible AI.

## ✨ The Poetic Vision

Imagine: Your RAG Factory becomes a **universal oracle** that any AI can consult. Legal documents, medical knowledge, technical documentation - all accessible through a standard protocol. Not just for querying, but for **complete lifecycle management**: create projects, ingest data, monitor jobs, all from your AI assistant. It's like giving your AI a PhD librarian with superpowers. 📚✨🤖

## 🎯 What Can AIs Do With This?

Once connected, AI assistants can:

### 📖 Query & Search
1. **Search your knowledge bases** - "Find legal precedents about immigration in Chile"
2. **Get contextual answers** - Automatically fetch relevant context for questions
3. **Get project statistics** - Check document counts, sizes, and schema versions

### 🏗️ Project Management
4. **List all projects** - Discover what knowledge bases are available
5. **Create new projects** - Set up new RAG knowledge bases with custom DB configs
6. **Update projects** - Change configurations, pause/activate projects
7. **Delete projects** - Clean up old projects (cascades to sources and jobs)

### 📊 Data Source Management
8. **Create data sources** - Add SPARQL endpoints, APIs, file uploads to projects
9. **List data sources** - View all configured sources for a project

### ⚙️ Job Lifecycle Control
10. **Create ingestion jobs** - Start document processing jobs
11. **List jobs** - View all jobs with filters (by project, status)
12. **Monitor job progress** - Check status, progress percentage, documents processed
13. **Cancel running jobs** - Stop jobs that are queued or running
14. **Delete completed jobs** - Clean up job history

### 🔧 Utilities
15. **Test database connections** - Verify PostgreSQL connections and pgvector availability

## 🛠️ Available Tools (15 total)

### 📖 Search & Query Tools

#### 1. `rag_search`
Search for similar documents in a RAG project.

**Input:**
- `query` (string, required): Search query text
- `project_id` (integer, required): RAG project ID
- `limit` (integer, optional): Max results (default: 5)
- `threshold` (number, optional): Similarity threshold 0-1 (default: 0.7)
- `document_type` (string, optional): Filter by document type
- `specialty` (string, optional): Filter by specialty

**Output:** JSON with search results including titles, content, similarity scores, and metadata.

**Example:**
```json
{
  "query": "immigration law requirements",
  "project": "Journey Law - Chile",
  "results_count": 3,
  "results": [
    {
      "id": 42,
      "title": "Ley de Migración 21.325",
      "content": "Artículo 1: Esta ley regula...",
      "document_type": "IMMIGRATION_LAW",
      "specialty": "IMMIGRATION",
      "similarity": 0.892
    }
  ]
}
```

#### 2. `rag_get_context`
Get formatted context for a query (performs search + formats for AI).

**Input:**
- `query` (string, required): Query to get context for
- `project_id` (integer, required): RAG project ID
- `max_chunks` (integer, optional): Max context chunks (default: 5)
- `include_metadata` (boolean, optional): Include metadata (default: true)

**Output:** Formatted text context ready for AI consumption.

---

### 🏗️ Project Management Tools

#### 3. `rag_list_projects`
List all available RAG projects.

**Input:**
- `status_filter` (string, optional): "active", "paused", "archived", or "all" (default: "active")

**Output:** JSON with project list.

**Example:**
```json
{
  "total_projects": 2,
  "filter": "active",
  "projects": [
    {
      "id": 14,
      "name": "Journey Law - Chile",
      "description": "Chilean immigration and labor law",
      "status": "active",
      "target_table": "legal_vectors_cl",
      "embedding_model": "jina/jina-embeddings-v2-base-es",
      "embedding_dimension": 768,
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

#### 4. `rag_create_project`
Create a new RAG project.

**Input:**
- `name` (string, required): Project name
- `target_db_host` (string, required): Target database host
- `target_db_name` (string, required): Target database name
- `target_db_user` (string, required): Target database user
- `target_db_password` (string, required): Target database password
- `target_table_name` (string, required): Target table name for vectors
- `description` (string, optional): Project description
- `target_db_port` (integer, optional): Target database port (default: 5432)
- `embedding_model` (string, optional): Embedding model (default: jina/jina-embeddings-v2-base-es)
- `embedding_dimension` (integer, optional): Embedding dimension (default: 768)
- `chunk_size` (integer, optional): Document chunk size (default: 1000)
- `chunk_overlap` (integer, optional): Chunk overlap size (default: 200)

**Output:** JSON with created project details.

#### 5. `rag_update_project`
Update an existing RAG project.

**Input:**
- `project_id` (integer, required): Project ID to update
- `name` (string, optional): New project name
- `description` (string, optional): New description
- `status` (string, optional): New status - "active", "paused", or "archived"
- `target_db_host` (string, optional): New database host
- `target_db_port` (integer, optional): New database port
- `target_db_name` (string, optional): New database name
- `target_db_user` (string, optional): New database user
- `target_db_password` (string, optional): New database password
- `target_table_name` (string, optional): New table name

**Output:** JSON with update confirmation.

#### 6. `rag_delete_project`
Delete a RAG project (cascades to data sources, jobs, and document tracking).

**Input:**
- `project_id` (integer, required): Project ID to delete

**Output:** JSON with deletion confirmation.

#### 7. `rag_get_stats`
Get statistics about a RAG project.

**Input:**
- `project_id` (integer, required): RAG project ID

**Output:** JSON with document count, table size, schema version, etc.

---

### 📊 Data Source Management Tools

#### 8. `rag_create_source`
Create a new data source for a RAG project.

**Input:**
- `project_id` (integer, required): Project ID to attach source to
- `name` (string, required): Data source name
- `source_type` (string, required): Type - "sparql", "chile_bcn", "us_congress", etc.
- `config` (JSON string, required): Source configuration
- `country_code` (string, optional): ISO country code like "CL", "US"
- `region` (string, optional): Region/state
- `tags` (JSON string, optional): Additional tags

**Output:** JSON with created source details.

**Example:**
```json
{
  "id": 5,
  "project_id": 14,
  "name": "BCN Chile Laws",
  "source_type": "chile_bcn",
  "created_at": "2025-01-15T11:00:00Z",
  "message": "Data source 'BCN Chile Laws' created successfully"
}
```

#### 9. `rag_list_sources`
List all data sources for a RAG project.

**Input:**
- `project_id` (integer, required): Project ID to list sources for

**Output:** JSON with source list.

---

### ⚙️ Job Management Tools

#### 10. `rag_create_job`
Create and enqueue a new ingestion job.

**Input:**
- `project_id` (integer, required): Project ID to run job for
- `source_id` (integer, optional): Specific source ID (if None, processes all sources)
- `job_type` (string, optional): "full_sync", "incremental", etc. (default: "full_sync")

**Output:** JSON with job details and status.

**Example:**
```json
{
  "id": 123,
  "project_id": 14,
  "source_id": 5,
  "job_type": "full_sync",
  "status": "queued",
  "created_at": "2025-01-15T12:00:00Z",
  "message": "Job 123 created and queued successfully"
}
```

#### 11. `rag_list_jobs`
List ingestion jobs with optional filters.

**Input:**
- `project_id` (integer, optional): Filter by project ID
- `status_filter` (string, optional): "queued", "running", "completed", "failed", "cancelled"
- `limit` (integer, optional): Max jobs to return (default: 20)

**Output:** JSON with job list.

#### 12. `rag_get_job`
Get detailed status of a specific ingestion job.

**Input:**
- `job_id` (integer, required): Job ID to get status for

**Output:** JSON with job details, progress percentage, and timestamps.

**Example:**
```json
{
  "id": 123,
  "project_id": 14,
  "project_name": "Journey Law - Chile",
  "source_id": 5,
  "source_name": "BCN Chile Laws",
  "job_type": "full_sync",
  "status": "running",
  "progress": {
    "total_documents": 1000,
    "processed_documents": 450,
    "successful_documents": 448,
    "failed_documents": 2,
    "percentage": 45.0
  },
  "timestamps": {
    "created_at": "2025-01-15T12:00:00Z",
    "started_at": "2025-01-15T12:01:00Z",
    "completed_at": null
  }
}
```

#### 13. `rag_cancel_job`
Cancel a running or queued ingestion job.

**Input:**
- `job_id` (integer, required): Job ID to cancel

**Output:** JSON with cancellation confirmation.

#### 14. `rag_delete_job`
Delete an ingestion job record (only for completed, failed, or cancelled jobs).

**Input:**
- `job_id` (integer, required): Job ID to delete

**Output:** JSON with deletion confirmation.

---

### 🔧 Utility Tools

#### 15. `rag_test_connection`
Test database connection and check for pgvector extension.

**Input:**
- `host` (string, required): Database host
- `database` (string, required): Database name
- `user` (string, required): Database user
- `password` (string, required): Database password
- `port` (integer, optional): Database port (default: 5432)

**Output:** JSON with connection test results.

**Example:**
```json
{
  "success": true,
  "message": "Database connection successful",
  "pgvector_available": true,
  "connection_details": {
    "host": "localhost",
    "port": 5432,
    "database": "journeylaw_db",
    "user": "journeylaw"
  }
}
```

---

## 📦 Installation

### Prerequisites

1. **RAG Factory running** with at least one project configured
2. **Python 3.10+** (3.11+ recommended)
   - macOS system Python (3.9.6) is too old
   - Install via Homebrew: `brew install python@3.12`
3. **MCP package**: `pip install "mcp[cli]"`

### Quick Setup

**Automated Setup Script (Recommended)**

```bash
cd /path/to/rag-factory
chmod +x setup-mcp.sh
./setup-mcp.sh
```

This script will:
- Detect your OS
- Check Python version (requires 3.10+)
- Create virtual environment at `./venv-mcp`
- Install MCP package
- Generate Claude Desktop config at `claude_desktop_config.json`

**Manual Setup**

```bash
# Install Python 3.12 via Homebrew (if needed)
brew install python@3.12

# Create virtual environment
python3.12 -m venv venv-mcp

# Activate virtual environment
source venv-mcp/bin/activate

# Install MCP package
pip install "mcp[cli]"
```

---

## 🎮 Claude Desktop Integration

### Step 1: Add to Claude Desktop Config

Edit your Claude Desktop configuration file:

**macOS:**
```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Linux:**
```bash
code ~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

### Step 2: Add RAG Factory Server

Copy the generated config from `claude_desktop_config.json` or add manually:

```json
{
  "mcpServers": {
    "rag-factory": {
      "command": "/absolute/path/to/rag-factory/venv-mcp/bin/python",
      "args": [
        "/absolute/path/to/rag-factory/backend/mcp/server.py"
      ],
      "env": {
        "DATABASE_URL": "postgresql://user:password@localhost:5433/rag_factory_db",
        "OLLAMA_HOST": "localhost"
      },
      "description": "RAG Factory - Manage and query RAG knowledge bases"
    }
  }
}
```

**IMPORTANT:** Use absolute paths, not relative paths or `~` expansions.

### Step 3: Restart Claude Desktop

Close and reopen Claude Desktop. The MCP server will start automatically.

### Step 4: Verify Connection

In Claude Desktop, try:
```
"List all RAG projects using the rag_list_projects tool"
```

---

## 🧪 Testing MCP Tools Locally

Test individual tools using the Python interpreter:

```bash
# Activate virtual environment
source venv-mcp/bin/activate

# Set environment variables
export DATABASE_URL='postgresql://user:password@localhost:5433/rag_factory_db'
export OLLAMA_HOST='localhost'

# Run Python
python3
```

Then in Python:
```python
import sys
sys.path.insert(0, 'backend')

from mcp.server.fastmcp import FastMCP
from core.database import get_db_connection

# Test database connection
conn = get_db_connection()
print("Database connected:", not conn.closed)

# Test getting projects
cur = conn.cursor()
cur.execute("SELECT id, name FROM rag_projects LIMIT 5")
print("Projects:", cur.fetchall())
```

---

## 🐛 Troubleshooting

### Issue 1: "spawn ENOENT" error in Claude Desktop logs

**Cause:** Incorrect Python path in config
**Fix:** Verify path exists:
```bash
ls -la /path/to/rag-factory/venv-mcp/bin/python
```

### Issue 2: "mcp package not installed"

**Cause 1:** Python path modification shadowing installed package
**Solution:** Server now imports MCP SDK before path modification

**Cause 2:** Package not installed in venv
**Solution:**
```bash
source venv-mcp/bin/activate
pip install "mcp[cli]"
```

### Issue 3: Database connection fails

**Check environment variables in Claude config:**
```json
"env": {
  "DATABASE_URL": "postgresql://user:pass@localhost:5433/rag_factory_db",
  "OLLAMA_HOST": "localhost"
}
```

**Test connection directly:**
```bash
psql -h localhost -p 5433 -U user -d rag_factory_db
```

### Issue 4: Python version too old

**Symptom:** `ERROR: Could not find a version that satisfies the requirement mcp`
**Cause:** Python < 3.10
**Solution:**
```bash
brew install python@3.12
python3.12 -m venv venv-mcp
./venv-mcp/bin/pip install "mcp[cli]"
```

### Viewing MCP Logs

**macOS:**
```bash
tail -f ~/Library/Logs/Claude/mcp-server-rag-factory.log
```

**Linux:**
```bash
tail -f ~/.config/Claude/logs/mcp-server-rag-factory.log
```

---

## 💡 Usage Examples

### Example 1: Create Project & Add Source from Claude Desktop

```
User: Create a new RAG project for US legal documents

Assistant uses tools:
1. rag_test_connection(host="localhost", database="legal_db", ...)
2. rag_create_project(name="US Legal Docs", target_db_host="localhost", ...)
3. rag_create_source(project_id=15, name="US Congress API", source_type="us_congress", ...)
4. rag_create_job(project_id=15, source_id=6)

Response: "Created project 'US Legal Docs' (ID: 15) with US Congress API source. 
Ingestion job #45 is now running and processing documents."
```

### Example 2: Monitor Job Progress

```
User: Check the status of job 45

Assistant uses: rag_get_job(job_id=45)

Response: "Job #45 is running with 65% complete (650/1000 documents processed). 
645 successful, 5 failed. Started at 12:01 PM, estimated completion in 10 minutes."
```

### Example 3: Search with Context

```
User: What are the visa requirements for skilled workers in Chile?

Assistant uses:
1. rag_list_projects() to find Chilean project
2. rag_search(query="visa requirements skilled workers", project_id=14, limit=5)
3. Analyzes results and provides answer with citations

Response: "Based on Chilean immigration law (Ley 21.325, Article 42):
Skilled workers require a Technical or Professional Visa (Visa Sujeta a Contrato).
Requirements include: [detailed answer with 3 source citations]"
```

### Example 4: Pause Project for Maintenance

```
User: Pause the Journey Law Chile project while I update the database

Assistant uses: rag_update_project(project_id=14, status="paused")

Response: "Project 'Journey Law - Chile' has been paused. 
All ingestion jobs will be cancelled and no new jobs can be started until reactivated."
```

---

## 🚀 Advanced Usage

### Custom MCP Server Port

By default, MCP uses stdio communication. For HTTP/SSE communication:

```bash
# Run server with custom host/port
MCP_SERVER_HOST=0.0.0.0 MCP_SERVER_PORT=8001 ./venv-mcp/bin/python backend/mcp/server.py
```

### Docker Integration

Add MCP server as a service in `docker-compose.yml`:

```yaml
services:
  mcp-server:
    build:
      context: .
      dockerfile: docker/Dockerfile.mcp
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/rag_factory_db
      - OLLAMA_HOST=ollama
    depends_on:
      - db
      - ollama
    ports:
      - "8001:8001"
```

---

## 📚 Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs/model-context-protocol)
- [RAG Factory Repository](https://github.com/felixrivasuxdesigner/rag-factory)

---

## 🤝 Contributing

Found a bug or want to add a new MCP tool? Contributions welcome!

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-mcp-tool`
3. Add tool in `backend/mcp/server.py` with `@mcp.tool()` decorator
4. Update this documentation
5. Test with Claude Desktop
6. Submit pull request

---

## 📄 License

Same as RAG Factory main project (see LICENSE file)

---

**Built with ❤️ using FastMCP and Anthropic's Model Context Protocol**

