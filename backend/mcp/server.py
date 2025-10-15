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

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MCP SDK imports
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: mcp package not installed. Install with: pip install 'mcp[cli]'", file=sys.stderr)
    sys.exit(1)

# RAG Factory imports
from core.database import get_db_connection
from services.embedding_service import EmbeddingService
from services.vector_db_writer import VectorDBWriter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("RAG Factory")

# Global state
embedding_service = None
db_conn = None


def get_db():
    """Get database connection"""
    global db_conn
    if not db_conn or db_conn.closed:
        db_conn = get_db_connection()
    return db_conn


def get_project(project_id: int) -> Optional[Dict]:
    """Get project configuration"""
    conn = get_db()
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


@mcp.tool()
def rag_search(
    query: str,
    project_id: int,
    limit: int = 5,
    threshold: float = 0.7,
    document_type: Optional[str] = None,
    specialty: Optional[str] = None
) -> str:
    """
    Search for similar documents in a RAG project knowledge base.

    Args:
        query: The search query text
        project_id: RAG project ID to search in
        limit: Maximum number of results (default: 5)
        threshold: Minimum similarity threshold 0-1 (default: 0.7)
        document_type: Filter by document type (optional)
        specialty: Filter by specialty (optional)

    Returns:
        JSON string with search results
    """
    try:
        # Get project config
        project = get_project(project_id)
        if not project:
            return json.dumps({"error": f"Project {project_id} not found"})

        # Generate query embedding
        global embedding_service
        if not embedding_service:
            embedding_service = EmbeddingService(
                model=project['embedding_model'],
                embedding_dimension=project['embedding_dimension']
            )

        query_embedding = embedding_service.embed_text(query)

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
            return json.dumps({"error": "Failed to connect to vector database"})

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
                return json.dumps({
                    "query": query,
                    "project": project['name'],
                    "results_count": 0,
                    "results": []
                })

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

            return json.dumps(formatted_results, indent=2, ensure_ascii=False)

        finally:
            writer.close()

    except Exception as e:
        logger.error(f"Error in rag_search: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
def rag_list_projects(status_filter: str = "active") -> str:
    """
    List all available RAG projects.

    Args:
        status_filter: Filter by status - "active", "inactive", or "all" (default: "active")

    Returns:
        JSON string with project list
    """
    try:
        conn = get_db()
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

            return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"Error in rag_list_projects: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
def rag_get_context(
    query: str,
    project_id: int,
    max_chunks: int = 5,
    include_metadata: bool = True
) -> str:
    """
    Get formatted context for a query (performs search and formats results for AI consumption).

    Args:
        query: The query to get context for
        project_id: RAG project ID
        max_chunks: Maximum number of context chunks (default: 5)
        include_metadata: Include source metadata (default: True)

    Returns:
        Formatted text context ready for AI consumption
    """
    try:
        # Use search to get results
        search_results_json = rag_search(
            query=query,
            project_id=project_id,
            limit=max_chunks,
            threshold=0.6  # Lower threshold for context
        )

        # Parse search results
        try:
            results_data = json.loads(search_results_json)
            if "error" in results_data:
                return results_data.get("error", "Unknown error")

            results = results_data.get("results", [])
        except:
            return search_results_json

        if not results:
            return "No relevant context found for the query."

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

        return "\n".join(context_parts)

    except Exception as e:
        logger.error(f"Error in rag_get_context: {e}", exc_info=True)
        return f"Error: {str(e)}"


@mcp.tool()
def rag_get_stats(project_id: int) -> str:
    """
    Get statistics and info about a RAG project.

    Args:
        project_id: RAG project ID

    Returns:
        JSON string with project statistics
    """
    try:
        project = get_project(project_id)
        if not project:
            return json.dumps({"error": f"Project {project_id} not found"})

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
            return json.dumps({"error": "Failed to connect to vector database"})

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

            return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            writer.close()

    except Exception as e:
        logger.error(f"Error in rag_get_stats: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    logger.info("Starting RAG Factory MCP Server...")
    mcp.run()
