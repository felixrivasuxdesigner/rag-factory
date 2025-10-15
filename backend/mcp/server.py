"""
RAG Factory MCP Server

Model Context Protocol server that exposes RAG Factory capabilities
to AI assistants like Claude Desktop, ChatGPT, and others.

This allows any MCP-compatible AI to:
- Search through RAG project knowledge bases
- Get contextual information for queries
- List and manage RAG projects (create, update, delete, activate/deactivate)
- Manage data sources (create, list)
- Control ingestion jobs (create, pause, resume, cancel, delete, list)
- Test database connections
- Access project statistics
"""

import os
import sys
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

# MCP SDK imports (MUST come before path modification to avoid shadowing)
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: mcp package not installed. Install with: pip install 'mcp[cli]'", file=sys.stderr)
    sys.exit(1)

# Add parent directory to path for RAG Factory imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
                   embedding_model, embedding_dimension, chunk_size, chunk_overlap
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
            "embedding_dimension": row[11],
            "chunk_size": row[12],
            "chunk_overlap": row[13]
        }

    finally:
        cur.close()


# ============================================================================
# SEARCH & QUERY TOOLS
# ============================================================================

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


# ============================================================================
# PROJECT MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
def rag_list_projects(status_filter: str = "active") -> str:
    """
    List all available RAG projects.

    Args:
        status_filter: Filter by status - "active", "paused", "archived", or "all" (default: "active")

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
def rag_create_project(
    name: str,
    target_db_host: str,
    target_db_name: str,
    target_db_user: str,
    target_db_password: str,
    target_table_name: str,
    description: Optional[str] = None,
    target_db_port: int = 5432,
    embedding_model: str = "jina/jina-embeddings-v2-base-es",
    embedding_dimension: int = 768,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> str:
    """
    Create a new RAG project.

    Args:
        name: Project name (required)
        target_db_host: Target database host (required)
        target_db_name: Target database name (required)
        target_db_user: Target database user (required)
        target_db_password: Target database password (required)
        target_table_name: Target table name for vectors (required)
        description: Project description (optional)
        target_db_port: Target database port (default: 5432)
        embedding_model: Embedding model (default: jina/jina-embeddings-v2-base-es)
        embedding_dimension: Embedding dimension (default: 768)
        chunk_size: Document chunk size (default: 1000)
        chunk_overlap: Chunk overlap size (default: 200)

    Returns:
        JSON string with created project details
    """
    try:
        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO rag_projects (
                    name, description, status,
                    target_db_host, target_db_port, target_db_name,
                    target_db_user, target_db_password, target_table_name,
                    embedding_model, embedding_dimension,
                    chunk_size, chunk_overlap
                )
                VALUES (%s, %s, 'active', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, description, status, created_at;
            """, (
                name, description,
                target_db_host, target_db_port, target_db_name,
                target_db_user, target_db_password, target_table_name,
                embedding_model, embedding_dimension,
                chunk_size, chunk_overlap
            ))

            row = cur.fetchone()
            conn.commit()

            result = {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "status": row[3],
                "target_table": target_table_name,
                "embedding_model": embedding_model,
                "embedding_dimension": embedding_dimension,
                "created_at": row[4].isoformat() if row[4] else None,
                "message": f"Project '{name}' created successfully"
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"Error in rag_create_project: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
def rag_update_project(
    project_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    target_db_host: Optional[str] = None,
    target_db_port: Optional[int] = None,
    target_db_name: Optional[str] = None,
    target_db_user: Optional[str] = None,
    target_db_password: Optional[str] = None,
    target_table_name: Optional[str] = None
) -> str:
    """
    Update an existing RAG project.

    Args:
        project_id: Project ID to update (required)
        name: New project name (optional)
        description: New description (optional)
        status: New status - "active", "paused", or "archived" (optional)
        target_db_host: New database host (optional)
        target_db_port: New database port (optional)
        target_db_name: New database name (optional)
        target_db_user: New database user (optional)
        target_db_password: New database password (optional)
        target_table_name: New table name (optional)

    Returns:
        JSON string with update confirmation
    """
    try:
        # Build dynamic update query
        updates = []
        params = []

        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        if status is not None:
            if status not in ["active", "paused", "archived"]:
                return json.dumps({"error": f"Invalid status '{status}'. Must be 'active', 'paused', or 'archived'"})
            updates.append("status = %s")
            params.append(status)
        if target_db_host is not None:
            updates.append("target_db_host = %s")
            params.append(target_db_host)
        if target_db_port is not None:
            updates.append("target_db_port = %s")
            params.append(target_db_port)
        if target_db_name is not None:
            updates.append("target_db_name = %s")
            params.append(target_db_name)
        if target_db_user is not None:
            updates.append("target_db_user = %s")
            params.append(target_db_user)
        if target_db_password is not None:
            updates.append("target_db_password = %s")
            params.append(target_db_password)
        if target_table_name is not None:
            updates.append("target_table_name = %s")
            params.append(target_table_name)

        if not updates:
            return json.dumps({"error": "No fields to update"})

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(project_id)

        conn = get_db()
        cur = conn.cursor()

        try:
            query = f"""
                UPDATE rag_projects
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id, name, status;
            """
            cur.execute(query, params)

            row = cur.fetchone()
            if not row:
                return json.dumps({"error": f"Project {project_id} not found"})

            conn.commit()

            result = {
                "id": row[0],
                "name": row[1],
                "status": row[2],
                "message": f"Project {project_id} updated successfully"
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"Error in rag_update_project: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
def rag_delete_project(project_id: int) -> str:
    """
    Delete a RAG project (cascades to data sources, jobs, and document tracking).

    Args:
        project_id: Project ID to delete

    Returns:
        JSON string with deletion confirmation
    """
    try:
        conn = get_db()
        cur = conn.cursor()

        try:
            # Get project name before deletion
            cur.execute("SELECT name FROM rag_projects WHERE id = %s", (project_id,))
            row = cur.fetchone()
            if not row:
                return json.dumps({"error": f"Project {project_id} not found"})

            project_name = row[0]

            # Delete project (cascades due to foreign keys)
            cur.execute("DELETE FROM rag_projects WHERE id = %s", (project_id,))
            conn.commit()

            result = {
                "id": project_id,
                "name": project_name,
                "message": f"Project '{project_name}' (ID: {project_id}) deleted successfully"
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"Error in rag_delete_project: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


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


# ============================================================================
# DATA SOURCE MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
def rag_create_source(
    project_id: int,
    name: str,
    source_type: str,
    config: str,
    country_code: Optional[str] = None,
    region: Optional[str] = None,
    tags: Optional[str] = None
) -> str:
    """
    Create a new data source for a RAG project.

    Args:
        project_id: Project ID to attach source to (required)
        name: Data source name (required)
        source_type: Type of source - "sparql", "chile_bcn", "us_congress", etc. (required)
        config: JSON string with source configuration (required)
        country_code: ISO country code like "CL", "US" (optional)
        region: Region/state (optional)
        tags: JSON string with additional tags (optional)

    Returns:
        JSON string with created source details
    """
    try:
        # Parse JSON strings
        try:
            config_dict = json.loads(config)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON in config parameter"})

        tags_dict = None
        if tags:
            try:
                tags_dict = json.loads(tags)
            except json.JSONDecodeError:
                return json.dumps({"error": "Invalid JSON in tags parameter"})

        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO data_sources (
                    project_id, name, source_type, config,
                    country_code, region, tags
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, source_type, created_at;
            """, (
                project_id, name, source_type, json.dumps(config_dict),
                country_code, region, json.dumps(tags_dict) if tags_dict else None
            ))

            row = cur.fetchone()
            conn.commit()

            result = {
                "id": row[0],
                "project_id": project_id,
                "name": row[1],
                "source_type": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "message": f"Data source '{name}' created successfully"
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"Error in rag_create_source: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
def rag_list_sources(project_id: int) -> str:
    """
    List all data sources for a RAG project.

    Args:
        project_id: Project ID to list sources for

    Returns:
        JSON string with source list
    """
    try:
        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT id, name, source_type, config, country_code, region,
                       tags, is_active, last_sync_at, created_at
                FROM data_sources
                WHERE project_id = %s
                ORDER BY created_at DESC;
            """, (project_id,))

            sources = []
            for row in cur.fetchall():
                sources.append({
                    "id": row[0],
                    "name": row[1],
                    "source_type": row[2],
                    "config": row[3],
                    "country_code": row[4],
                    "region": row[5],
                    "tags": row[6],
                    "is_active": row[7],
                    "last_sync_at": row[8].isoformat() if row[8] else None,
                    "created_at": row[9].isoformat() if row[9] else None
                })

            result = {
                "project_id": project_id,
                "total_sources": len(sources),
                "sources": sources
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"Error in rag_list_sources: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


# ============================================================================
# JOB MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
def rag_create_job(
    project_id: int,
    source_id: Optional[int] = None,
    job_type: str = "full_sync"
) -> str:
    """
    Create and enqueue a new ingestion job.

    Args:
        project_id: Project ID to run job for (required)
        source_id: Specific source ID to process (optional, if None processes all sources)
        job_type: Job type - "full_sync", "incremental", etc. (default: "full_sync")

    Returns:
        JSON string with job details and status
    """
    try:
        conn = get_db()
        cur = conn.cursor()

        try:
            # Create job record
            cur.execute("""
                INSERT INTO ingestion_jobs (
                    project_id, source_id, job_type, status
                )
                VALUES (%s, %s, %s, 'queued')
                RETURNING id, project_id, source_id, job_type, status, created_at;
            """, (project_id, source_id, job_type))

            row = cur.fetchone()
            conn.commit()

            job_id = row[0]

            # TODO: Enqueue to Redis/RQ here
            # For now, just return the created job

            result = {
                "id": job_id,
                "project_id": row[1],
                "source_id": row[2],
                "job_type": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "message": f"Job {job_id} created and queued successfully"
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"Error in rag_create_job: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
def rag_list_jobs(
    project_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 20
) -> str:
    """
    List ingestion jobs with optional filters.

    Args:
        project_id: Filter by project ID (optional)
        status_filter: Filter by status - "queued", "running", "completed", "failed", "cancelled" (optional)
        limit: Maximum number of jobs to return (default: 20)

    Returns:
        JSON string with job list
    """
    try:
        conn = get_db()
        cur = conn.cursor()

        try:
            # Build query dynamically
            query = """
                SELECT j.id, j.project_id, j.source_id, j.job_type, j.status,
                       j.total_documents, j.processed_documents, j.successful_documents, j.failed_documents,
                       j.created_at, j.started_at, j.completed_at,
                       p.name as project_name
                FROM ingestion_jobs j
                LEFT JOIN rag_projects p ON j.project_id = p.id
                WHERE 1=1
            """
            params = []

            if project_id is not None:
                query += " AND j.project_id = %s"
                params.append(project_id)

            if status_filter is not None:
                query += " AND j.status = %s"
                params.append(status_filter)

            query += " ORDER BY j.created_at DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, params)

            jobs = []
            for row in cur.fetchall():
                jobs.append({
                    "id": row[0],
                    "project_id": row[1],
                    "project_name": row[12],
                    "source_id": row[2],
                    "job_type": row[3],
                    "status": row[4],
                    "total_documents": row[5],
                    "processed_documents": row[6],
                    "successful_documents": row[7],
                    "failed_documents": row[8],
                    "created_at": row[9].isoformat() if row[9] else None,
                    "started_at": row[10].isoformat() if row[10] else None,
                    "completed_at": row[11].isoformat() if row[11] else None
                })

            result = {
                "total_jobs": len(jobs),
                "filters": {
                    "project_id": project_id,
                    "status": status_filter
                },
                "jobs": jobs
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"Error in rag_list_jobs: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
def rag_get_job(job_id: int) -> str:
    """
    Get detailed status of a specific ingestion job.

    Args:
        job_id: Job ID to get status for

    Returns:
        JSON string with job details and progress
    """
    try:
        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT j.id, j.project_id, j.source_id, j.job_type, j.status,
                       j.total_documents, j.processed_documents, j.successful_documents, j.failed_documents,
                       j.error_log, j.created_at, j.started_at, j.completed_at,
                       p.name as project_name,
                       s.name as source_name
                FROM ingestion_jobs j
                LEFT JOIN rag_projects p ON j.project_id = p.id
                LEFT JOIN data_sources s ON j.source_id = s.id
                WHERE j.id = %s;
            """, (job_id,))

            row = cur.fetchone()
            if not row:
                return json.dumps({"error": f"Job {job_id} not found"})

            # Calculate progress percentage
            total = row[5] or 0
            processed = row[6] or 0
            progress = (processed / total * 100) if total > 0 else 0

            result = {
                "id": row[0],
                "project_id": row[1],
                "project_name": row[13],
                "source_id": row[2],
                "source_name": row[14],
                "job_type": row[3],
                "status": row[4],
                "progress": {
                    "total_documents": total,
                    "processed_documents": processed,
                    "successful_documents": row[7] or 0,
                    "failed_documents": row[8] or 0,
                    "percentage": round(progress, 2)
                },
                "error_log": row[9],
                "timestamps": {
                    "created_at": row[10].isoformat() if row[10] else None,
                    "started_at": row[11].isoformat() if row[11] else None,
                    "completed_at": row[12].isoformat() if row[12] else None
                }
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"Error in rag_get_job: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
def rag_cancel_job(job_id: int) -> str:
    """
    Cancel a running or queued ingestion job.

    Args:
        job_id: Job ID to cancel

    Returns:
        JSON string with cancellation confirmation
    """
    try:
        conn = get_db()
        cur = conn.cursor()

        try:
            # Check job status
            cur.execute("SELECT status FROM ingestion_jobs WHERE id = %s", (job_id,))
            row = cur.fetchone()
            if not row:
                return json.dumps({"error": f"Job {job_id} not found"})

            status = row[0]
            if status in ["completed", "failed", "cancelled"]:
                return json.dumps({
                    "error": f"Cannot cancel job in '{status}' status",
                    "job_id": job_id,
                    "current_status": status
                })

            # Update status to cancelled
            cur.execute("""
                UPDATE ingestion_jobs
                SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, status;
            """, (job_id,))

            row = cur.fetchone()
            conn.commit()

            # TODO: Send cancellation signal to Redis/RQ worker

            result = {
                "id": row[0],
                "status": row[1],
                "message": f"Job {job_id} cancelled successfully"
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"Error in rag_cancel_job: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
def rag_delete_job(job_id: int) -> str:
    """
    Delete an ingestion job record (only for completed, failed, or cancelled jobs).

    Args:
        job_id: Job ID to delete

    Returns:
        JSON string with deletion confirmation
    """
    try:
        conn = get_db()
        cur = conn.cursor()

        try:
            # Check job status
            cur.execute("SELECT status FROM ingestion_jobs WHERE id = %s", (job_id,))
            row = cur.fetchone()
            if not row:
                return json.dumps({"error": f"Job {job_id} not found"})

            status = row[0]
            if status in ["queued", "running"]:
                return json.dumps({
                    "error": f"Cannot delete active job. Cancel it first.",
                    "job_id": job_id,
                    "current_status": status
                })

            # Delete job
            cur.execute("DELETE FROM ingestion_jobs WHERE id = %s", (job_id,))
            conn.commit()

            result = {
                "id": job_id,
                "message": f"Job {job_id} deleted successfully"
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"Error in rag_delete_job: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


# ============================================================================
# UTILITY TOOLS
# ============================================================================

@mcp.tool()
def rag_test_connection(
    host: str,
    database: str,
    user: str,
    password: str,
    port: int = 5432
) -> str:
    """
    Test database connection and check for pgvector extension.

    Args:
        host: Database host (required)
        database: Database name (required)
        user: Database user (required)
        password: Database password (required)
        port: Database port (default: 5432)

    Returns:
        JSON string with connection test results
    """
    try:
        writer = VectorDBWriter(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            table_name="test_table",  # Dummy table name
            embedding_dimension=768
        )

        if not writer.connect():
            return json.dumps({
                "success": False,
                "message": "Failed to connect to database",
                "pgvector_available": False
            })

        try:
            # Check for pgvector extension
            cur = writer.conn.cursor()
            cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
            pgvector_available = cur.fetchone()[0]
            cur.close()

            result = {
                "success": True,
                "message": "Database connection successful",
                "pgvector_available": pgvector_available,
                "connection_details": {
                    "host": host,
                    "port": port,
                    "database": database,
                    "user": user
                }
            }

            if not pgvector_available:
                result["warning"] = "pgvector extension not installed. Run: CREATE EXTENSION vector;"

            return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            writer.close()

    except Exception as e:
        logger.error(f"Error in rag_test_connection: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "pgvector_available": False
        })


if __name__ == "__main__":
    logger.info("Starting RAG Factory MCP Server...")
    mcp.run()
