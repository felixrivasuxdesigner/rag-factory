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
    SearchRequest, SearchResponse, SearchResult,
    RAGQueryRequest, RAGQueryResponse
)
from core.database import get_db_connection
from services.gemini_file_search_service import GeminiFileSearchService
from connectors.registry import get_registry
from services import scheduler_service

# Initialize FastAPI app
app = FastAPI(
    title="RAG Factory API - Gemini File Search Edition",
    description="API for creating and managing RAG projects using Google Gemini File Search",
    version="2.0.0-gemini"
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

# Initialize Gemini File Search service
try:
    gemini_file_search = GeminiFileSearchService()
    logger.info("✓ Gemini File Search service initialized")
except Exception as e:
    logger.error(f"Failed to initialize Gemini File Search: {e}")
    gemini_file_search = None


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
        "gemini_file_search": "unknown"
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

    # Check Gemini File Search
    try:
        if gemini_file_search and gemini_file_search.health_check():
            health["gemini_file_search"] = "healthy"
        else:
            health["gemini_file_search"] = "unhealthy"
    except:
        health["gemini_file_search"] = "unhealthy"

    return health


@app.get("/connectors")
def list_connectors(category: str = None):
    """
    List all available connectors with their metadata.

    Args:
        category: Optional filter by category ("public", "example", "private").
                 Defaults to None (all connectors).
                 Use "public" to get only universal/shareable connectors.

    Returns connector information including:
    - name: Human-readable connector name
    - source_type: Unique type identifier
    - description: What the connector does
    - version: Connector version
    - category: Connector category (public/example/private)
    - supports_incremental_sync: Whether it supports date-based filtering
    - supports_rate_limiting: Whether it implements rate limiting
    - required_config_fields: Required configuration fields
    - optional_config_fields: Optional configuration fields
    """
    try:
        registry = get_registry()
        connectors = registry.list_connectors(category=category)

        return {
            "total": len(connectors),
            "category": category if category else "all",
            "connectors": connectors
        }
    except Exception as e:
        logger.error(f"Failed to list connectors: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve connector list: {str(e)}"
        )


@app.get("/connectors/{source_type}")
def get_connector_info(source_type: str):
    """
    Get detailed information about a specific connector.

    Args:
        source_type: The connector type identifier (e.g., 'chile_fulltext')
    """
    try:
        registry = get_registry()
        metadata = registry.get_metadata(source_type)

        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector type '{source_type}' not found"
            )

        return metadata.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get connector info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve connector info: {str(e)}"
        )


# ============================================================================
# RAG Project Endpoints
# ============================================================================

@app.post("/projects", response_model=RAGProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project: RAGProjectCreate):
    """Create a new RAG project with Gemini File Search Store."""
    if not gemini_file_search:
        raise HTTPException(status_code=500, detail="Gemini File Search service not initialized")

    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        # Create File Search Store in Gemini
        logger.info(f"Creating Gemini File Search Store for project: {project.name}")
        store_id = gemini_file_search.create_store(display_name=project.name)

        # Insert project into database with store_id
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO rag_projects (
                    name, description, gemini_file_search_store_id, gemini_file_search_store_name
                ) VALUES (%s, %s, %s, %s)
                RETURNING *;
            """, (
                project.name, project.description, store_id, project.name
            ))
            result = cur.fetchone()
            columns = [desc[0] for desc in cur.description]
            project_data = dict(zip(columns, result))

        conn.commit()
        logger.info(f"✓ Created project {project.name} with Gemini Store: {store_id}")
        return RAGProjectResponse(**project_data)

    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=400, detail="Project name already exists")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to create project: {e}", exc_info=True)
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
                    country_code, region, tags, sync_frequency, rate_limits
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *;
            """, (
                source.project_id, source.name, source.source_type.value,
                psycopg2.extras.Json(source.config),
                source.country_code, source.region,
                psycopg2.extras.Json(source.tags) if source.tags else None,
                source.sync_frequency,
                psycopg2.extras.Json(source.rate_limits) if source.rate_limits else None
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
            'tags': source.get('tags'),
            'rate_limits': source.get('rate_limits')
        }

        # Get Gemini File Search Store ID
        gemini_store_id = project.get('gemini_file_search_store_id')
        if not gemini_store_id:
            raise HTTPException(status_code=500, detail="Project has no Gemini File Search Store configured")

        # Enqueue the job with 10 minute timeout
        task_queue.enqueue(
            ingest_documents_from_source,
            job_id,
            job.project_id,
            source['id'],
            source_config,
            gemini_store_id,
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


@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: int):
    """
    Cancel a running job.

    Note: This only marks the job as cancelled in the database.
    The worker will check this status and stop processing.
    Already processed documents will remain in the database.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            # Check if job exists and get current status
            cur.execute("SELECT status FROM ingestion_jobs WHERE id = %s;", (job_id,))
            result = cur.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Job not found")

            current_status = result[0]

            # Only allow cancellation of pending, queued, or running jobs
            if current_status not in ['pending', 'queued', 'running']:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot cancel job with status '{current_status}'. Only 'pending', 'queued', or 'running' jobs can be cancelled."
                )

            # Update job status to cancelled
            cur.execute("""
                UPDATE ingestion_jobs
                SET status = 'cancelled', completed_at = NOW()
                WHERE id = %s;
            """, (job_id,))
            conn.commit()

        return {"message": f"Job {job_id} has been cancelled", "job_id": job_id, "status": "cancelled"}

    finally:
        conn.close()


@app.delete("/jobs/{job_id}")
def delete_job(job_id: int):
    """
    Delete a job from the database.

    This performs a hard delete and removes the job record completely.
    Use with caution - this action cannot be undone.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            # Check if job exists
            cur.execute("SELECT status FROM ingestion_jobs WHERE id = %s;", (job_id,))
            result = cur.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Job not found")

            current_status = result[0]

            # Don't allow deletion of running jobs
            if current_status == 'running':
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete a running job. Cancel it first."
                )

            # Delete the job
            cur.execute("DELETE FROM ingestion_jobs WHERE id = %s;", (job_id,))
            conn.commit()

        return {"message": f"Job {job_id} has been deleted", "job_id": job_id}

    finally:
        conn.close()


@app.post("/jobs/{job_id}/restart")
def restart_job(job_id: int):
    """
    Restart a failed or cancelled job.

    This creates a new job with the same configuration as the original.
    The new job will skip documents that were already successfully processed.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            # Get original job details
            cur.execute("""
                SELECT project_id, source_id, job_type, status
                FROM ingestion_jobs
                WHERE id = %s;
            """, (job_id,))
            result = cur.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Job not found")

            project_id, source_id, job_type, current_status = result

            # Only allow restart of failed or cancelled jobs
            if current_status not in ['failed', 'cancelled']:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot restart job with status '{current_status}'. Only 'failed' or 'cancelled' jobs can be restarted."
                )

            # Create new job with same configuration
            cur.execute("""
                INSERT INTO ingestion_jobs (project_id, source_id, job_type, status)
                VALUES (%s, %s, %s, 'queued')
                RETURNING id;
            """, (project_id, source_id, job_type))
            new_job_id = cur.fetchone()[0]
            conn.commit()

            # Get project and source data for enqueueing
            cur.execute("""
                SELECT p.*, s.source_type, s.config
                FROM rag_projects p
                JOIN data_sources s ON s.id = %s
                WHERE p.id = %s;
            """, (source_id, project_id))
            result = cur.fetchone()

            if result:
                columns = [desc[0] for desc in cur.description]
                project_data = dict(zip(columns, result))

                # Prepare arguments for the worker task
                target_db_config = {
                    'host': project_data['target_db_host'],
                    'port': project_data['target_db_port'],
                    'database': project_data['target_db_name'],
                    'user': project_data['target_db_user'],
                    'password': project_data['target_db_password'],
                    'table_name': project_data['target_table_name']
                }

                embedding_config = {
                    'model': project_data['embedding_model'],
                    'dimension': project_data['embedding_dimension'],
                    'chunk_size': project_data['chunk_size'],
                    'chunk_overlap': project_data['chunk_overlap']
                }

                source_config = {
                    'source_type': project_data['source_type'],
                    'config': project_data['config']
                }

                # Enqueue the new job
                queue = Queue('rag-tasks', connection=redis_conn)
                queue.enqueue(
                    'workers.ingestion_tasks.ingest_documents_from_source',
                    new_job_id,
                    project_id,
                    source_id,
                    source_config,
                    target_db_config,
                    embedding_config,
                    job_timeout='6h'
                )

        return {
            "message": f"Job {job_id} has been restarted",
            "original_job_id": job_id,
            "new_job_id": new_job_id,
            "status": "queued"
        }

    finally:
        conn.close()


@app.post("/jobs/{job_id}/pause")
def pause_job(job_id: int):
    """
    Pause a running job.

    The job will be marked as 'paused' and the worker will stop processing it.
    It can be resumed later to continue from where it left off.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            # Check if job exists and get current status
            cur.execute("SELECT status FROM ingestion_jobs WHERE id = %s;", (job_id,))
            result = cur.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Job not found")

            current_status = result[0]

            # Only allow pausing running jobs
            if current_status != 'running':
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot pause job with status '{current_status}'. Only 'running' jobs can be paused."
                )

            # Update job status to paused
            cur.execute("""
                UPDATE ingestion_jobs
                SET status = 'paused'
                WHERE id = %s;
            """, (job_id,))
            conn.commit()

        return {"message": f"Job {job_id} has been paused", "job_id": job_id, "status": "paused"}

    finally:
        conn.close()


@app.post("/jobs/{job_id}/resume")
def resume_job(job_id: int):
    """
    Resume a paused job.

    The job will be marked as 'queued' and will be picked up by a worker
    to continue processing from where it left off.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            # Check if job exists and get current status
            cur.execute("SELECT status FROM ingestion_jobs WHERE id = %s;", (job_id,))
            result = cur.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Job not found")

            current_status = result[0]

            # Only allow resuming paused jobs
            if current_status != 'paused':
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot resume job with status '{current_status}'. Only 'paused' jobs can be resumed."
                )

            # Update job status to queued so it can be picked up by worker
            cur.execute("""
                UPDATE ingestion_jobs
                SET status = 'queued'
                WHERE id = %s;
            """, (job_id,))
            conn.commit()

        return {"message": f"Job {job_id} has been resumed", "job_id": job_id, "status": "queued"}

    finally:
        conn.close()


@app.post("/jobs/{job_id}/start")
def start_job(job_id: int):
    """
    Start a pending job.

    Enqueues the job to be processed by a worker. This is useful for jobs
    that were created but not automatically started (e.g., manually created jobs).
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            # Get job details
            cur.execute("""
                SELECT j.status, j.project_id, j.source_id, j.job_type,
                       p.target_db_host, p.target_db_port, p.target_db_name,
                       p.target_db_user, p.target_db_password, p.target_table_name,
                       p.embedding_model, p.embedding_dimension, p.chunk_size, p.chunk_overlap,
                       s.source_type, s.config
                FROM ingestion_jobs j
                JOIN rag_projects p ON j.project_id = p.id
                JOIN data_sources s ON j.source_id = s.id
                WHERE j.id = %s;
            """, (job_id,))
            result = cur.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Job not found")

            current_status = result[0]

            # Only allow starting pending jobs
            if current_status != 'pending':
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot start job with status '{current_status}'. Only 'pending' jobs can be started."
                )

            # Extract job configuration
            project_id = result[1]
            source_id = result[2]

            # Prepare configurations for worker
            source_config = {
                'source_type': result[14],
                'config': result[15]
            }

            target_db_config = {
                'host': result[4],
                'port': result[5],
                'database': result[6],
                'user': result[7],
                'password': result[8],
                'table_name': result[9]
            }

            embedding_config = {
                'model': result[10],
                'dimension': result[11],
                'chunk_size': result[12],
                'chunk_overlap': result[13]
            }

            # Update job status to queued
            cur.execute("""
                UPDATE ingestion_jobs
                SET status = 'queued'
                WHERE id = %s;
            """, (job_id,))
            conn.commit()

            # Enqueue the job
            from workers.ingestion_tasks import ingest_documents_from_source

            task_queue.enqueue(
                ingest_documents_from_source,
                job_id,
                project_id,
                source_id,
                source_config,
                target_db_config,
                embedding_config,
                job_timeout=3600  # 1 hour - supports large documents (up to ~5000 chunks)
            )

            logger.info(f"✓ Started and enqueued job {job_id}")

        return {"message": f"Job {job_id} has been started", "job_id": job_id, "status": "queued"}

    finally:
        conn.close()


@app.get("/projects/{project_id}/jobs")
def list_project_jobs(
    project_id: int,
    status_filter: str = None,
    page: int = 1,
    page_size: int = 10
):
    """
    List ingestion jobs for a project with pagination.

    Args:
        project_id: The project ID
        status_filter: Optional filter by status (running, completed, failed, etc.)
        page: Page number (starts at 1)
        page_size: Number of items per page (default 10, max 100)

    Returns:
        Dict with jobs list, pagination metadata, and total count
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    # Validate and limit page_size
    page_size = min(max(1, page_size), 100)
    page = max(1, page)
    offset = (page - 1) * page_size

    try:
        with conn.cursor() as cur:
            # Get total count
            if status_filter:
                cur.execute("""
                    SELECT COUNT(*) FROM ingestion_jobs
                    WHERE project_id = %s AND status = %s;
                """, (project_id, status_filter))
            else:
                cur.execute("""
                    SELECT COUNT(*) FROM ingestion_jobs
                    WHERE project_id = %s;
                """, (project_id,))

            total_count = cur.fetchone()[0]

            # Get paginated jobs
            if status_filter:
                cur.execute("""
                    SELECT * FROM ingestion_jobs
                    WHERE project_id = %s AND status = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s;
                """, (project_id, status_filter, page_size, offset))
            else:
                cur.execute("""
                    SELECT * FROM ingestion_jobs
                    WHERE project_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s;
                """, (project_id, page_size, offset))

            columns = [desc[0] for desc in cur.description]
            jobs = [dict(zip(columns, row)) for row in cur.fetchall()]

        total_pages = (total_count + page_size - 1) // page_size  # Ceiling division

        return {
            "jobs": [IngestionJobResponse(**job).dict() for job in jobs],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }

    finally:
        conn.close()


# ============================================================================
# Search and RAG Query Endpoints
# ============================================================================

@app.post("/search", response_model=SearchResponse)
def search_documents(request: SearchRequest):
    """
    Perform semantic similarity search on project documents.

    Args:
        request: SearchRequest with project_id, query, top_k, similarity_threshold

    Returns:
        SearchResponse with matching documents and similarity scores
    """
    try:
        logger.info(f"Search request: project={request.project_id}, query='{request.query[:50]}...'")

        # Perform search using project configuration
        results = search_service.search_by_project(
            query=request.query,
            project_id=request.project_id,
            internal_db_url=DATABASE_URL,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )

        # Convert to response format
        search_results = [
            SearchResult(
                id=str(r['id']),  # Convert to string to handle both int and str IDs
                content=r['content'],
                metadata=r.get('metadata'),
                similarity=r['similarity']
            )
            for r in results
        ]

        return SearchResponse(
            query=request.query,
            results=search_results,
            total_results=len(search_results),
            project_id=request.project_id
        )

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=RAGQueryResponse)
def rag_query(request: RAGQueryRequest):
    """
    Perform RAG query using Gemini File Search.
    Gemini handles both document retrieval and answer generation in one call.

    Args:
        request: RAGQueryRequest with project_id, question, parameters

    Returns:
        RAGQueryResponse with generated answer and source documents
    """
    if not gemini_file_search:
        raise HTTPException(status_code=500, detail="Gemini File Search service not initialized")

    try:
        logger.info(f"Gemini File Search query: project={request.project_id}, question='{request.question[:50]}...'")

        # Get project to find the Gemini File Search Store ID
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT gemini_file_search_store_id FROM rag_projects WHERE id = %s;", (request.project_id,))
                result = cur.fetchone()
                if not result or not result[0]:
                    raise HTTPException(status_code=404, detail="Project not found or has no Gemini File Search Store")

                store_id = result[0]
        finally:
            conn.close()

        # Query Gemini File Search (handles retrieval + generation)
        result = gemini_file_search.query(
            store_id=store_id,
            question=request.question,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        # Convert sources to SearchResult format
        sources = [
            SearchResult(
                id=str(i),
                content=source.get('content', ''),
                metadata={'uri': source.get('uri', '')},
                similarity=1.0  # Gemini doesn't provide similarity scores
            )
            for i, source in enumerate(result.get('sources', []))
        ]

        logger.info(f"✓ Gemini File Search query completed ({len(result['answer'])} chars, {len(sources)} sources)")

        return RAGQueryResponse(
            question=request.question,
            answer=result['answer'],
            sources=sources,
            model=result['model'],
            project_id=request.project_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gemini File Search query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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


# ============================================================================
# SCHEDULING ENDPOINTS (Phase 5)
# ============================================================================

@app.get("/schedules")
def list_schedules():
    """List all active schedules with next run times."""
    try:
        jobs = scheduler_service.get_scheduled_jobs()
        return {"schedules": jobs}
    except Exception as e:
        logger.error(f"Failed to list schedules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sources/{source_id}/schedule")
def update_source_schedule(source_id: int, sync_frequency: str):
    """
    Update the schedule for a data source.

    Supported formats:
    - "manual" - No scheduling
    - "hourly" - Every hour
    - "daily" - Every day at midnight
    - "weekly" - Every Monday at midnight
    - "interval:30m" - Every 30 minutes
    - "interval:2h" - Every 2 hours
    - "cron:0 0 * * *" - Cron expression
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            # Update database
            cur.execute("""
                UPDATE data_sources
                SET sync_frequency = %s
                WHERE id = %s
                RETURNING name;
            """, (sync_frequency, source_id))

            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Source not found")

            source_name = result[0]
            conn.commit()

            # Update scheduler
            if sync_frequency == "manual":
                scheduler_service.remove_source_schedule(source_id)
                return {"message": "Schedule removed", "source_id": source_id}
            else:
                success = scheduler_service.add_source_schedule(
                    source_id, source_name, sync_frequency
                )
                if success:
                    return {
                        "message": "Schedule updated",
                        "source_id": source_id,
                        "sync_frequency": sync_frequency
                    }
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid sync_frequency format"
                    )

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.post("/sources/{source_id}/schedule/pause")
def pause_source_schedule(source_id: int):
    """Pause a source's schedule without removing it."""
    try:
        success = scheduler_service.pause_schedule(source_id)
        if success:
            return {"message": "Schedule paused", "source_id": source_id}
        else:
            raise HTTPException(status_code=404, detail="Schedule not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sources/{source_id}/schedule/resume")
def resume_source_schedule(source_id: int):
    """Resume a paused source schedule."""
    try:
        success = scheduler_service.resume_schedule(source_id)
        if success:
            return {"message": "Schedule resumed", "source_id": source_id}
        else:
            raise HTTPException(status_code=404, detail="Schedule not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sources/{source_id}/schedule")
def delete_source_schedule(source_id: int):
    """Remove a source's schedule."""
    try:
        success = scheduler_service.remove_source_schedule(source_id)
        if success:
            return {"message": "Schedule removed", "source_id": source_id}
        else:
            return {"message": "No schedule to remove", "source_id": source_id}
    except Exception as e:
        logger.error(f"Failed to remove schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sources/{source_id}/sync/trigger")
def manually_trigger_sync(source_id: int):
    """Manually trigger a sync job for a source (bypasses schedule)."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM data_sources WHERE id = %s", (source_id,))
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Source not found")

            source_name = result[0]

        # Trigger sync job
        scheduler_service.trigger_sync_job(source_id, source_name)

        return {
            "message": "Sync job triggered",
            "source_id": source_id,
            "source_name": source_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
