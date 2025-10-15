# 🌐 RAG Factory MCP Server

**Make your RAG knowledge bases available to any AI assistant**

The RAG Factory MCP (Model Context Protocol) Server exposes your RAG projects as tools that can be used by AI assistants like Claude Desktop, ChatGPT with plugins, and any other MCP-compatible AI.

## ✨ The Poetic Vision

Imagine: Your RAG Factory becomes a **universal oracle** that any AI can consult. Legal documents, medical knowledge, technical documentation - all accessible through a standard protocol. It's like creating a Library of Alexandria for AI assistants. 📚✨

## 🎯 What Can AIs Do With This?

Once connected, AI assistants can:

1. **Search your knowledge bases** - "Find legal precedents about immigration in Chile"
2. **Get contextual answers** - Automatically fetch relevant context for questions
3. **List available projects** - Discover what knowledge bases are available
4. **Get project stats** - Check how many documents, size, last update

## 🛠️ Available Tools

### 1. `rag_search`
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

### 2. `rag_list_projects`
List all available RAG projects.

**Input:**
- `status_filter` (string, optional): "active", "inactive", or "all" (default: "active")

**Output:** JSON with project list.

### 3. `rag_get_context`
Get formatted context for a query (performs search + formats for AI).

**Input:**
- `query` (string, required): Query to get context for
- `project_id` (integer, required): RAG project ID
- `max_chunks` (integer, optional): Max context chunks (default: 5)
- `include_metadata` (boolean, optional): Include metadata (default: true)

**Output:** Formatted text context ready for AI consumption.

### 4. `rag_get_stats`
Get statistics about a RAG project.

**Input:**
- `project_id` (integer, required): RAG project ID

**Output:** JSON with document count, table size, schema version, etc.

## 📦 Installation

### Prerequisites

1. **RAG Factory running** with at least one project configured
2. **Python 3.11+**
3. **MCP package**: `pip install mcp`

### Quick Setup

1. Install the MCP package:
```bash
cd /path/to/rag-factory/backend
pip install mcp
```

2. Test the server:
```bash
python mcp/server.py
```

The server runs on stdio (standard input/output) and waits for MCP protocol messages.

## 🔌 Integration with AI Assistants

### Claude Desktop

1. **Find your Claude Desktop config file:**
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Add RAG Factory MCP server:**

```json
{
  "mcpServers": {
    "rag-factory": {
      "command": "python",
      "args": [
        "/Users/yourname/Projects/rag-factory/backend/mcp/server.py"
      ],
      "env": {
        "DATABASE_URL": "postgresql://user:password@localhost:5433/rag_factory_db",
        "OLLAMA_HOST": "localhost"
      }
    }
  }
}
```

3. **Restart Claude Desktop**

4. **Test it:**
   - Start a new conversation
   - Ask: "List available RAG projects"
   - Claude will use the `rag_list_projects` tool automatically!

### ChatGPT / Custom GPTs

For ChatGPT integration, you'll need to expose the MCP server via HTTP (coming soon in v1.1).

## 💡 Usage Examples

### Example 1: Legal Research with Claude Desktop

**You:** "Search the Chilean immigration law RAG for information about visa requirements for tech workers"

**Claude uses:**
```
Tool: rag_list_projects
→ Finds project ID 15 (Journey Law - Chile)

Tool: rag_search
Parameters:
  query: "visa requirements tech workers"
  project_id: 15
  limit: 5

→ Returns relevant legal articles
```

**Claude responds:** "Based on the Chilean immigration law database, here are the visa requirements for tech workers..."

### Example 2: Multi-Project Search

**You:** "Compare immigration policies between Chile and USA"

**Claude uses:**
```
Tool: rag_search (project_id: 15, query: "immigration policy")
Tool: rag_search (project_id: 14, query: "immigration policy")

→ Compares results from both projects
```

### Example 3: Context-Aware Answers

**You:** "What does Article 23 say about family reunification?"

**Claude uses:**
```
Tool: rag_get_context
Parameters:
  query: "Article 23 family reunification"
  project_id: 15
  max_chunks: 3

→ Gets formatted context
```

**Claude responds:** With precise quotes and sources.

## 🔒 Security Considerations

### Database Access
The MCP server needs read access to:
- RAG Factory internal database (for project configs)
- User vector databases (for similarity search)

**Important:**
- Use read-only credentials when possible
- Don't expose sensitive project passwords in config files
- Consider using environment variables for credentials

### Network Access
- The MCP server runs locally on stdio (no network exposure by default)
- For remote access, use SSH tunneling or VPN

## 🐛 Troubleshooting

### "mcp package not installed"
```bash
pip install mcp
```

### "Failed to connect to vector database"
- Check DATABASE_URL environment variable
- Verify PostgreSQL is running
- Check credentials in project configuration

### "No projects found"
- Ensure RAG Factory has at least one active project
- Check project status (should be "active")

### Claude Desktop doesn't show tools
- Restart Claude Desktop after config changes
- Check config file syntax (valid JSON)
- View logs: `~/Library/Logs/Claude/mcp-server-rag-factory.log` (macOS)

## 📊 Performance

**Typical response times:**
- List projects: ~50ms
- Search (5 results): ~200-500ms (depends on embedding model and DB size)
- Get context: ~300-600ms

**Optimization tips:**
- Use PostgreSQL connection pooling
- Keep embedding models loaded in memory
- Use Schema v2 for faster queries (30-50% improvement)

## 🚀 Advanced Usage

### Custom Filters

Search with specific filters:
```json
{
  "tool": "rag_search",
  "query": "employment visa",
  "project_id": 15,
  "document_type": "IMMIGRATION_LAW",
  "specialty": "WORK_PERMITS",
  "threshold": 0.8
}
```

### Batch Operations

Search multiple projects:
```python
# In your AI assistant
results = []
for project_id in [14, 15, 16]:
    results.append(rag_search(query, project_id))
```

## 🔄 Future Enhancements (Roadmap)

- [ ] **HTTP endpoint** for non-MCP integrations (ChatGPT plugins)
- [ ] **Caching layer** for repeated queries
- [ ] **Streaming responses** for large contexts
- [ ] **Multi-lingual query translation**
- [ ] **Query analytics** and usage tracking
- [ ] **Rate limiting** and quotas
- [ ] **Webhook notifications** for new documents

## 📚 Learn More

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [RAG Factory Documentation](./CLAUDE.md)
- [Schema v2 Best Practices](./CLAUDE.md#vector-database-schema-v2---postgresql-best-practices)

## 🤝 Contributing

Have ideas for new MCP tools? Open an issue or PR!

Possible additions:
- `rag_add_document` - Add documents via MCP
- `rag_create_project` - Create projects via MCP
- `rag_export_results` - Export search results to various formats

## 📝 License

Same as RAG Factory (MIT)

---

**Built with ❤️ for the AI community**

*Making RAG accessible to every AI assistant, everywhere.*
