"""
RAG Factory MCP Server

Model Context Protocol server that exposes RAG Factory capabilities
to AI assistants like Claude Desktop, ChatGPT, and others.

This allows any MCP-compatible AI to:
- Search through RAG project knowledge bases
- Get contextual information for queries
- List available projects
- Access project statistics
"""

import os
import sys
import json
import logging
from typing import Any, Dict, List, Optional
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        ImageContent,
        EmbeddedResource,
        GetPromptResult,
        PromptMessage,
        PromptArgument,
    )
except ImportError:
    print("Error: mcp package not installed. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# RAG Factory imports
from core.database import get_db_connection
from services.embedding_service import EmbeddingService
from services.vector_db_writer import VectorDBWriter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGFactoryMCPServer:
    """MCP Server for RAG Factory"""

    def __init__(self):
        self.server = Server("rag-factory")
        self.embedding_service = None
        self.db_conn = None

        # Register handlers
        self._register_tools()
        self._register_prompts()

    def _register_tools(self):
        """Register MCP tools"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available RAG Factory tools"""
            return [
                Tool(
                    name="rag_search",
                    description="Search for similar documents in a RAG project knowledge base",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query text"
                            },
                            "project_id": {
                                "type": "integer",
                                "description": "RAG project ID to search in"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 5)",
                                "default": 5
                            },
                            "threshold": {
                                "type": "number",
                                "description": "Minimum similarity threshold 0-1 (default: 0.7)",
                                "default": 0.7
                            },
                            "document_type": {
                                "type": "string",
                                "description": "Filter by document type (optional)"
                            },
                            "specialty": {
                                "type": "string",
                                "description": "Filter by specialty (optional)"
                            }
                        },
                        "required": ["query", "project_id"]
                    }
                ),
                Tool(
                    name="rag_list_projects",
                    description="List all available RAG projects",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status_filter": {
                                "type": "string",
                                "description": "Filter by status: active, inactive, or all (default: active)",
                                "enum": ["active", "inactive", "all"],
                                "default": "active"
                            }
                        }
                    }
                ),
                Tool(
                    name="rag_get_context",
                    description="Get formatted context for a query (performs search and formats results for AI consumption)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The query to get context for"
                            },
                            "project_id": {
                                "type": "integer",
                                "description": "RAG project ID"
                            },
                            "max_chunks": {
                                "type": "integer",
                                "description": "Maximum number of context chunks (default: 5)",
                                "default": 5
                            },
                            "include_metadata": {
                                "type": "boolean",
                                "description": "Include source metadata (default: true)",
                                "default": True
                            }
                        },
                        "required": ["query", "project_id"]
                    }
                ),
                Tool(
                    name="rag_get_stats",
                    description="Get statistics and info about a RAG project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_id": {
                                "type": "integer",
                                "description": "RAG project ID"
                            }
                        },
                        "required": ["project_id"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            try:
                if name == "rag_search":
                    return await self._handle_rag_search(arguments)
                elif name == "rag_list_projects":
                    return await self._handle_list_projects(arguments)
                elif name == "rag_get_context":
                    return await self._handle_get_context(arguments)
                elif name == "rag_get_stats":
                    return await self._handle_get_stats(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]

    def _register_prompts(self):
        """Register MCP prompts (templates)"""

        @self.server.list_prompts()
        async def list_prompts() -> List[Any]:
            """List available prompt templates"""
            return [
                {
                    "name": "rag_qa",
                    "description": "Answer a question using RAG context",
                    "arguments": [
                        PromptArgument(
                            name="question",
                            description="The question to answer",
                            required=True
                        ),
                        PromptArgument(
                            name="project_id",
                            description="RAG project ID to use",
                            required=True
                        )
                    ]
                }
            ]

        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: Dict[str, str]) -> GetPromptResult:
            """Get a prompt template"""
            if name == "rag_qa":
                question = arguments.get("question", "")
                project_id = int(arguments.get("project_id", 0))

                # Get context
                context_result = await self._handle_get_context({
                    "query": question,
                    "project_id": project_id,
                    "max_chunks": 5
                })

                context_text = context_result[0].text if context_result else "No context found"

                prompt = f"""Answer the following question using the provided context.

Context:
{context_text}

Question: {question}

Answer:"""

                return GetPromptResult(
                    description=f"RAG Q&A for project {project_id}",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(type="text", text=prompt)
                        )
                    ]
                )

    async def _handle_rag_search(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle RAG search tool"""
        query = args["query"]
        project_id = args["project_id"]
        limit = args.get("limit", 5)
        threshold = args.get("threshold", 0.7)
        document_type = args.get("document_type")
        specialty = args.get("specialty")

        # Get project config
        project = await self._get_project(project_id)
        if not project:
            return [TextContent(type="text", text=f"Project {project_id} not found")]

        # Generate query embedding
        if not self.embedding_service:
            self.embedding_service = EmbeddingService(
                model=project['embedding_model'],
                embedding_dimension=project['embedding_dimension']
            )

        query_embedding = self.embedding_service.embed_text(query)

        # Connect to user's vector DB
        writer = VectorDBWriter(
            host=project['target_db_host'],
            port=project['target_db_port'],
            database=project['target_db_name'],
            user=project['target_db_user'],
            password=project['target_db_password'],
            table_name=project['target_table_name'],
            embedding_dimension=project['embedding_dimension']
        )

        if not writer.connect():
            return [TextContent(type="text", text="Failed to connect to vector database")]

        try:
            # Perform similarity search
            results = writer.similarity_search(
                query_embedding=query_embedding,
                limit=limit,
                threshold=threshold,
                document_type=document_type,
                specialty=specialty
            )

            # Format results
            if not results:
                return [TextContent(type="text", text="No similar documents found")]

            formatted_results = {
                "query": query,
                "project": project['name'],
                "results_count": len(results),
                "results": [
                    {
                        "id": r.get('id'),
                        "title": r.get('title', 'Untitled'),
                        "content": r.get('content', '')[:500] + "..." if len(r.get('content', '')) > 500 else r.get('content', ''),
                        "document_type": r.get('document_type'),
                        "specialty": r.get('specialty'),
                        "similarity": round(r['similarity'], 3),
                        "metadata": r.get('metadata', {})
                    }
                    for r in results
                ]
            }

            return [TextContent(
                type="text",
                text=json.dumps(formatted_results, indent=2, ensure_ascii=False)
            )]

        finally:
            writer.close()

    async def _handle_list_projects(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle list projects tool"""
        status_filter = args.get("status_filter", "active")

        conn = self._get_db_conn()
        cur = conn.cursor()

        try:
            if status_filter == "all":
                cur.execute("""
                    SELECT id, name, description, status, target_table_name,
                           embedding_model, embedding_dimension, created_at
                    FROM rag_projects
                    ORDER BY created_at DESC;
                """)
            else:
                cur.execute("""
                    SELECT id, name, description, status, target_table_name,
                           embedding_model, embedding_dimension, created_at
                    FROM rag_projects
                    WHERE status = %s
                    ORDER BY created_at DESC;
                """, (status_filter,))

            projects = []
            for row in cur.fetchall():
                projects.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "status": row[3],
                    "target_table": row[4],
                    "embedding_model": row[5],
                    "embedding_dimension": row[6],
                    "created_at": row[7].isoformat() if row[7] else None
                })

            result = {
                "total_projects": len(projects),
                "filter": status_filter,
                "projects": projects
            }

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]

        finally:
            cur.close()

    async def _handle_get_context(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle get context tool - search and format for AI"""
        query = args["query"]
        project_id = args["project_id"]
        max_chunks = args.get("max_chunks", 5)
        include_metadata = args.get("include_metadata", True)

        # Use search to get results
        search_results = await self._handle_rag_search({
            "query": query,
            "project_id": project_id,
            "limit": max_chunks,
            "threshold": 0.6  # Lower threshold for context
        })

        # Parse search results
        try:
            results_data = json.loads(search_results[0].text)
            results = results_data.get("results", [])
        except:
            return search_results

        # Format as context
        context_parts = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'Untitled')
            content = result.get('content', '')
            doc_type = result.get('document_type', '')
            similarity = result.get('similarity', 0)

            context_parts.append(f"[Document {i}] {title}")
            if include_metadata and doc_type:
                context_parts.append(f"Type: {doc_type} | Relevance: {similarity:.1%}")
            context_parts.append(content)
            context_parts.append("")  # Blank line

        formatted_context = "\n".join(context_parts)

        return [TextContent(type="text", text=formatted_context)]

    async def _handle_get_stats(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle get stats tool"""
        project_id = args["project_id"]

        project = await self._get_project(project_id)
        if not project:
            return [TextContent(type="text", text=f"Project {project_id} not found")]

        # Connect to user's DB to get stats
        writer = VectorDBWriter(
            host=project['target_db_host'],
            port=project['target_db_port'],
            database=project['target_db_name'],
            user=project['target_db_user'],
            password=project['target_db_password'],
            table_name=project['target_table_name'],
            embedding_dimension=project['embedding_dimension']
        )

        if not writer.connect():
            return [TextContent(type="text", text="Failed to connect to vector database")]

        try:
            stats = writer.get_table_stats()

            result = {
                "project_id": project_id,
                "project_name": project['name'],
                "document_count": stats.get('document_count', 0),
                "table_size": stats.get('table_size', 'Unknown'),
                "schema_version": stats.get('schema_version', 1),
                "embedding_model": project['embedding_model'],
                "embedding_dimension": project['embedding_dimension']
            }

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]

        finally:
            writer.close()

    async def _get_project(self, project_id: int) -> Optional[Dict]:
        """Get project configuration"""
        conn = self._get_db_conn()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT id, name, description, status,
                       target_db_host, target_db_port, target_db_name,
                       target_db_user, target_db_password, target_table_name,
                       embedding_model, embedding_dimension
                FROM rag_projects
                WHERE id = %s;
            """, (project_id,))

            row = cur.fetchone()
            if not row:
                return None

            return {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "status": row[3],
                "target_db_host": row[4],
                "target_db_port": row[5],
                "target_db_name": row[6],
                "target_db_user": row[7],
                "target_db_password": row[8],
                "target_table_name": row[9],
                "embedding_model": row[10],
                "embedding_dimension": row[11]
            }

        finally:
            cur.close()

    def _get_db_conn(self):
        """Get database connection"""
        if not self.db_conn or self.db_conn.closed:
            self.db_conn = get_db_connection()
        return self.db_conn

    async def run(self):
        """Run the MCP server"""
        logger.info("Starting RAG Factory MCP Server...")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point"""
    server = RAGFactoryMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
