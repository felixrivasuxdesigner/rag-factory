"""
RQ worker tasks for document ingestion pipeline using Gemini File Search.
These tasks run asynchronously to fetch documents and upload them to Gemini.

Key differences from traditional RAG:
- No embedding generation (Gemini handles this)
- No vector database writing (documents uploaded to Gemini File Search Stores)
- Simpler pipeline: Fetch → Upload to Gemini
"""

import logging
import os
import hashlib
from datetime import datetime
from typing import Dict, List
import psycopg2

from services.gemini_file_search_service import GeminiFileSearchService
from services.content_cache_service import ContentCacheService
from connectors.registry import ConnectorRegistry
from processors.document_processor import DocumentProcessor
from core.database import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_job_progress(job_id: int, **updates):
    """
    Update job progress in the internal database.

    Args:
        job_id: The ingestion job ID
        **updates: Fields to update (processed_documents, successful_documents, etc.)
    """
    conn = get_db_connection()
    if not conn:
        logger.error("Failed to connect to internal database for job update")
        return

    try:
        set_clauses = []
        values = []

        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return

        values.append(job_id)
        query = f"""
        UPDATE ingestion_jobs
        SET {', '.join(set_clauses)}
        WHERE id = %s;
        """

        with conn.cursor() as cur:
            cur.execute(query, values)
        conn.commit()

    except Exception as e:
        logger.error(f"Failed to update job progress: {e}", exc_info=True)
        conn.rollback()
    finally:
        conn.close()


def is_job_cancelled(job_id: int) -> bool:
    """
    Check if a job has been cancelled.

    Args:
        job_id: The ingestion job ID

    Returns:
        True if the job status is 'cancelled', False otherwise
    """
    conn = get_db_connection()
    if not conn:
        logger.error("Failed to connect to internal database for job status check")
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM ingestion_jobs WHERE id = %s;", (job_id,))
            result = cur.fetchone()

            if result and result[0] == 'cancelled':
                return True

        return False

    except Exception as e:
        logger.error(f"Error checking job {job_id} status: {e}")
        return False
    finally:
        conn.close()


def mark_document_processed(project_id: int, doc_hash: str, status: str, error: str = None):
    """
    Mark a document as processed in the tracking table.

    Args:
        project_id: RAG project ID
        doc_hash: Document content hash
        status: Status (completed/failed)
        error: Error message if failed
    """
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE documents_tracking
                SET status = %s, error_message = %s, processed_at = %s
                WHERE project_id = %s AND document_hash = %s;
            """, (status, error, datetime.utcnow(), project_id, doc_hash))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to mark document as processed: {e}", exc_info=True)
        conn.rollback()
    finally:
        conn.close()


def ingest_documents_from_source(
    job_id: int,
    project_id: int,
    source_id: int,
    source_config: Dict,
    gemini_store_id: str
):
    """
    Main ingestion task: fetch documents and upload to Gemini File Search Store.

    Args:
        job_id: Ingestion job ID
        project_id: RAG project ID
        source_id: Data source ID
        source_config: Source configuration (type, endpoint, etc.)
        gemini_store_id: Gemini File Search Store ID
    """
    logger.info(f"Starting Gemini File Search ingestion job {job_id} for project {project_id}")

    # Update job status to running
    update_job_progress(job_id, status='running', started_at=datetime.utcnow())

    # Get last_sync_at for incremental sync
    last_sync_at = None
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT last_sync_at FROM data_sources WHERE id = %s",
                    (source_id,)
                )
                result = cur.fetchone()
                if result and result[0]:
                    last_sync_at = result[0].strftime('%Y-%m-%d')
                    logger.info(f"Incremental sync: fetching documents since {last_sync_at}")
        except Exception as e:
            logger.warning(f"Failed to get last_sync_at: {e}")
        finally:
            conn.close()

    total_documents = 0
    processed = 0
    successful = 0
    failed = 0
    errors = []

    try:
        # Step 1: Initialize content cache service
        internal_conn = get_db_connection()
        cache_service = ContentCacheService(internal_conn) if internal_conn else None

        if cache_service:
            logger.info(f"✓ Content cache service initialized")

        # Step 2: Fetch documents from source using ConnectorRegistry
        logger.info(f"Fetching documents from {source_config['source_type']}...")

        # Use ConnectorRegistry to get the appropriate connector
        registry = ConnectorRegistry()
        connector_class = registry.get_connector_class(source_config['source_type'])

        if not connector_class:
            raise NotImplementedError(f"Source type {source_config['source_type']} not found in registry")

        # Initialize connector with config and cache service
        connector_kwargs = {
            'config': source_config['config'],
            'rate_limit_config': source_config.get('rate_limits')
        }

        # Add cache service for supported connectors (chile_bcn, us_congress, etc.)
        if cache_service and source_config['source_type'] in ['chile_bcn', 'us_congress']:
            connector_kwargs['cache_service'] = cache_service
            connector_kwargs['source_id'] = source_id
            logger.info(f"✓ Cache enabled for {source_config['source_type']} connector")

        connector = connector_class(**connector_kwargs)

        # Fetch documents
        limit = source_config['config'].get('limit', 10)
        offset = source_config['config'].get('offset', 0)

        documents = connector.fetch_documents(
            limit=limit,
            offset=offset,
            since=last_sync_at
        )

        total_documents = len(documents)
        update_job_progress(job_id, total_documents=total_documents)

        logger.info(f"Fetched {total_documents} documents")

        # Step 3: Initialize Gemini File Search service
        gemini_service = GeminiFileSearchService()

        # Check API health
        if not gemini_service.health_check():
            raise RuntimeError("Gemini File Search API is not available")

        logger.info(f"✓ Connected to Gemini File Search Store: {gemini_store_id}")

        # Step 4: Upload each document to Gemini
        for doc in documents:
            # Check if job has been cancelled
            if is_job_cancelled(job_id):
                logger.warning(f"Job {job_id} has been cancelled. Stopping processing.")
                break

            processed += 1

            try:
                # Compute content hash for deduplication
                content = doc.get('title', '') + ' ' + doc.get('content', '')
                content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

                # Check if already processed (in internal tracking DB)
                if is_document_processed(project_id, content_hash):
                    logger.info(f"Skipping duplicate document: {doc.get('id')}")
                    successful += 1
                    continue

                # Track document as processing
                track_document(project_id, source_id, doc, content_hash, content)

                # Upload document to Gemini File Search
                # Gemini handles chunking, embedding, and indexing automatically
                title = doc.get('title', f"Document {doc.get('id')}")
                document_content = f"# {title}\n\n{doc.get('content', '')}"

                # Add metadata as text prefix (Gemini will index it)
                metadata = doc.get('metadata', {})
                if source_config.get('country_code'):
                    metadata['country_code'] = source_config['country_code']
                if source_config.get('region'):
                    metadata['region'] = source_config['region']
                if source_config.get('tags'):
                    metadata.update(source_config['tags'])

                # Prepend metadata to content for better search
                if metadata:
                    metadata_text = "\n".join([f"{k}: {v}" for k, v in metadata.items()])
                    document_content = f"{metadata_text}\n\n{document_content}"

                gemini_doc_id = gemini_service.upload_text_document(
                    store_id=gemini_store_id,
                    title=title,
                    content=document_content,
                    document_id=doc.get('id'),
                    metadata=metadata
                )

                if not gemini_doc_id:
                    raise ValueError("Failed to upload document to Gemini File Search")

                logger.info(f"✓ Uploaded to Gemini: {gemini_doc_id}")

                # Mark as successfully processed
                mark_document_processed(project_id, content_hash, 'completed')
                successful += 1

                logger.info(f"✓ Processed document {doc.get('id')} ({processed}/{total_documents})")

            except Exception as e:
                failed += 1
                error_msg = str(e)
                errors.append(f"Document {doc.get('id')}: {error_msg}")
                logger.error(f"Failed to process document {doc.get('id')}: {e}", exc_info=True)

                # Mark as failed
                mark_document_processed(project_id, content_hash, 'failed', error_msg)

            # Update progress
            update_job_progress(
                job_id,
                processed_documents=processed,
                successful_documents=successful,
                failed_documents=failed
            )

        # Step 5: Update final job status
        update_job_progress(
            job_id,
            status='completed',
            completed_at=datetime.utcnow(),
            error_log='\n'.join(errors) if errors else None
        )

        # Step 6: Update last_sync_at for incremental sync
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE data_sources SET last_sync_at = %s WHERE id = %s",
                        (datetime.utcnow(), source_id)
                    )
                conn.commit()
                logger.info(f"Updated last_sync_at for source {source_id}")
            except Exception as e:
                logger.warning(f"Failed to update last_sync_at: {e}")
                conn.rollback()
            finally:
                conn.close()

        logger.info(f"Job {job_id} completed: {successful} successful, {failed} failed out of {total_documents}")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        update_job_progress(
            job_id,
            status='failed',
            completed_at=datetime.utcnow(),
            error_log=str(e)
        )
        raise


def is_document_processed(project_id: int, content_hash: str) -> bool:
    """
    Check if document has already been processed.

    Args:
        project_id: RAG project ID
        content_hash: Document content hash

    Returns:
        bool: True if already processed
    """
    conn = get_db_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM documents_tracking
                WHERE project_id = %s AND document_hash = %s AND status = 'completed'
                LIMIT 1;
            """, (project_id, content_hash))
            return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking document: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def track_document(project_id: int, source_id: int, doc: Dict, content_hash: str, content: str):
    """
    Add document to tracking table.

    Args:
        project_id: RAG project ID
        source_id: Data source ID
        doc: Document data
        content_hash: Content hash
        content: Full content
    """
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents_tracking (
                    project_id, source_id, document_hash, external_id, title,
                    status, content_preview, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_id, document_hash) DO NOTHING;
            """, (
                project_id,
                source_id,
                content_hash,
                doc.get('id'),
                doc.get('title'),
                'processing',
                content[:500],  # Preview
                psycopg2.extras.Json(doc)
            ))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to track document: {e}", exc_info=True)
        conn.rollback()
    finally:
        conn.close()
