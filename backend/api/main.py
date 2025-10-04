"""
RAG Factory API - FastAPI application for managing multi-project RAG systems.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import logging
import psycopg2
from redis import Redis
from rq import Queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from api.models import (
    RAGProjectCreate, RAGProjectUpdate, RAGProjectResponse,
    DataSourceCreate, DataSourceUpdate, DataSourceResponse,
    IngestionJobCreate, IngestionJobResponse,
    DocumentTrackingResponse, ProjectStats,
    DatabaseConnectionTest, ConnectionTestResponse
)
from core.database import get_db_connection
from services.vector_db_writer import VectorDBWriter

# Initialize FastAPI app
app = FastAPI(
    title="RAG Factory API",
    description="API for creating and managing multi-project RAG systems",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection for job queue
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
redis_conn = Redis.from_url(REDIS_URL)
task_queue = Queue('rag-tasks', connection=redis_conn)


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.get("/")
def read_root():
    return {
        "message": "RAG Factory API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Check health of API and dependencies."""
    health = {
        "api": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "ollama": "unknown"
    }

    # Check database
    try:
        conn = get_db_connection()
        if conn:
            conn.close()
            health["database"] = "healthy"
    except:
        health["database"] = "unhealthy"

    # Check Redis
    try:
        redis_conn.ping()
        health["redis"] = "healthy"
    except:
        health["redis"] = "unhealthy"

    # Check Ollama
    try:
        import requests
        ollama_host = os.environ.get('OLLAMA_HOST', 'localhost')
        response = requests.get(f"http://{ollama_host}:11434/api/tags", timeout=2)
        if response.status_code == 200:
            health["ollama"] = "healthy"
    except:
        health["ollama"] = "unhealthy"

    return health


# ============================================================================
# RAG Project Endpoints
# ============================================================================

@app.post("/projects", response_model=RAGProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project: RAGProjectCreate):
    """Create a new RAG project."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO rag_projects (
                    name, description, target_db_host, target_db_port, target_db_name,
                    target_db_user, target_db_password, target_table_name,
                    embedding_model, embedding_dimension, chunk_size, chunk_overlap
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *;
            """, (
                project.name, project.description, project.target_db_host,
                project.target_db_port, project.target_db_name, project.target_db_user,
                project.target_db_password, project.target_table_name,
                project.embedding_model, project.embedding_dimension,
                project.chunk_size, project.chunk_overlap
            ))
            result = cur.fetchone()
            columns = [desc[0] for desc in cur.description]
            project_data = dict(zip(columns, result))

        conn.commit()
        return RAGProjectResponse(**project_data)

    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=400, detail="Project name already exists")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/projects", response_model=List[RAGProjectResponse])
def list_projects(status_filter: str = None):
    """List all RAG projects."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            if status_filter:
                cur.execute("SELECT * FROM rag_projects WHERE status = %s ORDER BY created_at DESC;", (status_filter,))
            else:
                cur.execute("SELECT * FROM rag_projects ORDER BY created_at DESC;")

            columns = [desc[0] for desc in cur.description]
            projects = [dict(zip(columns, row)) for row in cur.fetchall()]

        return [RAGProjectResponse(**proj) for proj in projects]

    finally:
        conn.close()


@app.get("/projects/{project_id}", response_model=RAGProjectResponse)
def get_project(project_id: int):
    """Get a specific RAG project by ID."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM rag_projects WHERE id = %s;", (project_id,))
            result = cur.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Project not found")

            columns = [desc[0] for desc in cur.description]
            project_data = dict(zip(columns, result))

        return RAGProjectResponse(**project_data)

    finally:
        conn.close()


@app.patch("/projects/{project_id}", response_model=RAGProjectResponse)
def update_project(project_id: int, updates: RAGProjectUpdate):
    """Update a RAG project."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        # Build dynamic update query
        update_data = updates.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        set_clauses = []
        values = []
        for key, value in update_data.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        values.append(project_id)

        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE rag_projects
                SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING *;
            """, values)

            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Project not found")

            columns = [desc[0] for desc in cur.description]
            project_data = dict(zip(columns, result))

        conn.commit()
        return RAGProjectResponse(**project_data)

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int):
    """Delete a RAG project (cascades to sources, jobs, documents)."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM rag_projects WHERE id = %s;", (project_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Project not found")

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/projects/{project_id}/stats", response_model=ProjectStats)
def get_project_stats(project_id: int):
    """Get statistics for a RAG project."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        stats = {}

        with conn.cursor() as cur:
            # Document stats
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'processing') as processing,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed
                FROM documents_tracking
                WHERE project_id = %s;
            """, (project_id,))
            doc_stats = cur.fetchone()

            # Job stats
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'running') as running,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed
                FROM ingestion_jobs
                WHERE project_id = %s;
            """, (project_id,))
            job_stats = cur.fetchone()

        stats = {
            'total_documents': doc_stats[0],
            'documents_pending': doc_stats[1],
            'documents_processing': doc_stats[2],
            'documents_completed': doc_stats[3],
            'documents_failed': doc_stats[4],
            'total_jobs': job_stats[0],
            'jobs_running': job_stats[1],
            'jobs_completed': job_stats[2],
            'jobs_failed': job_stats[3]
        }

        return ProjectStats(**stats)

    finally:
        conn.close()


# ============================================================================
# Data Source Endpoints
# ============================================================================

@app.post("/sources", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
def create_data_source(source: DataSourceCreate):
    """Create a new data source for a project."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO data_sources (
                    project_id, name, source_type, config,
                    country_code, region, tags, sync_frequency
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *;
            """, (
                source.project_id, source.name, source.source_type.value,
                psycopg2.extras.Json(source.config),
                source.country_code, source.region,
                psycopg2.extras.Json(source.tags) if source.tags else None,
                source.sync_frequency
            ))

            result = cur.fetchone()
            columns = [desc[0] for desc in cur.description]
            source_data = dict(zip(columns, result))

        conn.commit()
        return DataSourceResponse(**source_data)

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/projects/{project_id}/sources", response_model=List[DataSourceResponse])
def list_project_sources(project_id: int):
    """List all data sources for a project."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM data_sources
                WHERE project_id = %s
                ORDER BY created_at DESC;
            """, (project_id,))

            columns = [desc[0] for desc in cur.description]
            sources = [dict(zip(columns, row)) for row in cur.fetchall()]

        return [DataSourceResponse(**src) for src in sources]

    finally:
        conn.close()


@app.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_data_source(source_id: int):
    """Delete a data source."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            # Check if source exists
            cur.execute("SELECT id FROM data_sources WHERE id = %s;", (source_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Data source not found")

            # Delete the source (will cascade to related records)
            cur.execute("DELETE FROM data_sources WHERE id = %s;", (source_id,))

        conn.commit()
        return None

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to delete source: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ============================================================================
# Ingestion Job Endpoints
# ============================================================================

@app.post("/jobs", response_model=IngestionJobResponse, status_code=status.HTTP_201_CREATED)
def create_ingestion_job(job: IngestionJobCreate):
    """Create and enqueue a new ingestion job."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        # Get project and source configuration
        with conn.cursor() as cur:
            # Get project
            cur.execute("SELECT * FROM rag_projects WHERE id = %s;", (job.project_id,))
            project_row = cur.fetchone()
            if not project_row:
                raise HTTPException(status_code=404, detail="Project not found")

            project_columns = [desc[0] for desc in cur.description]
            project = dict(zip(project_columns, project_row))

            # Get source if specified
            source = None
            if job.source_id:
                cur.execute("SELECT * FROM data_sources WHERE id = %s AND project_id = %s;",
                          (job.source_id, job.project_id))
                source_row = cur.fetchone()
                if not source_row:
                    raise HTTPException(status_code=404, detail="Data source not found")

                source_columns = [desc[0] for desc in cur.description]
                source = dict(zip(source_columns, source_row))
            else:
                # If no source specified, get first active source for the project
                cur.execute("""
                    SELECT * FROM data_sources
                    WHERE project_id = %s AND is_active = TRUE
                    ORDER BY created_at ASC LIMIT 1;
                """, (job.project_id,))
                source_row = cur.fetchone()
                if not source_row:
                    raise HTTPException(status_code=400, detail="No active data source found for project")

                source_columns = [desc[0] for desc in cur.description]
                source = dict(zip(source_columns, source_row))

            # Create job record
            cur.execute("""
                INSERT INTO ingestion_jobs (project_id, source_id, job_type, status)
                VALUES (%s, %s, %s, 'queued')
                RETURNING *;
            """, (job.project_id, source['id'], job.job_type))

            result = cur.fetchone()
            columns = [desc[0] for desc in cur.description]
            job_data = dict(zip(columns, result))
            job_id = job_data['id']

        conn.commit()

        # Enqueue job to RQ
        from workers.ingestion_tasks import ingest_documents_from_source

        # Prepare configurations for worker
        source_config = {
            'source_type': source['source_type'],
            'config': source['config'],
            'country_code': source.get('country_code'),
            'region': source.get('region'),
            'tags': source.get('tags')
        }

        target_db_config = {
            'host': project['target_db_host'],
            'port': project['target_db_port'],
            'database': project['target_db_name'],
            'user': project['target_db_user'],
            'password': project['target_db_password'],
            'table_name': project['target_table_name']
        }

        embedding_config = {
            'model': project['embedding_model'],
            'dimension': project['embedding_dimension'],
            'chunk_size': project['chunk_size'],
            'chunk_overlap': project['chunk_overlap']
        }

        # Enqueue the job with 10 minute timeout
        task_queue.enqueue(
            ingest_documents_from_source,
            job_id,
            job.project_id,
            source['id'],
            source_config,
            target_db_config,
            embedding_config,
            job_timeout=600  # 10 minutes
        )

        logger.info(f"✓ Enqueued ingestion job {job_id} for project {job.project_id}")

        return IngestionJobResponse(**job_data)

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to create job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/jobs/{job_id}", response_model=IngestionJobResponse)
def get_job_status(job_id: int):
    """Get status of an ingestion job."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM ingestion_jobs WHERE id = %s;", (job_id,))
            result = cur.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Job not found")

            columns = [desc[0] for desc in cur.description]
            job_data = dict(zip(columns, result))

        return IngestionJobResponse(**job_data)

    finally:
        conn.close()


@app.get("/projects/{project_id}/jobs", response_model=List[IngestionJobResponse])
def list_project_jobs(project_id: int, status_filter: str = None, limit: int = 50):
    """List ingestion jobs for a project."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            if status_filter:
                cur.execute("""
                    SELECT * FROM ingestion_jobs
                    WHERE project_id = %s AND status = %s
                    ORDER BY created_at DESC
                    LIMIT %s;
                """, (project_id, status_filter, limit))
            else:
                cur.execute("""
                    SELECT * FROM ingestion_jobs
                    WHERE project_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s;
                """, (project_id, limit))

            columns = [desc[0] for desc in cur.description]
            jobs = [dict(zip(columns, row)) for row in cur.fetchall()]

        return [IngestionJobResponse(**job) for job in jobs]

    finally:
        conn.close()


# ============================================================================
# Utility Endpoints
# ============================================================================

@app.post("/test-connection", response_model=ConnectionTestResponse)
def test_database_connection(db_config: DatabaseConnectionTest):
    """Test connection to a user's PostgreSQL database."""
    try:
        writer = VectorDBWriter(
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
            user=db_config.user,
            password=db_config.password,
            table_name="test_connection"
        )

        if not writer.connect():
            return ConnectionTestResponse(
                success=False,
                message="Failed to connect to database"
            )

        # Check for pgvector
        pgvector_available = False
        try:
            with writer.conn.cursor() as cur:
                cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
                pgvector_available = cur.fetchone() is not None
        except:
            pass

        writer.close()

        return ConnectionTestResponse(
            success=True,
            message="Connection successful",
            pgvector_available=pgvector_available
        )

    except Exception as e:
        return ConnectionTestResponse(
            success=False,
            message=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
