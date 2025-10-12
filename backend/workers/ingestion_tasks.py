"""
RQ worker tasks for document ingestion pipeline.
These tasks run asynchronously to process documents and generate embeddings.
"""

import logging
import os
import hashlib
from datetime import datetime
from typing import Dict, List
import psycopg2

from services.embedding_service import EmbeddingService
from services.vector_db_writer import VectorDBWriter
from services.content_cache_service import ContentCacheService
from connectors.registry import ConnectorRegistry
from processors.document_processor import DocumentProcessor
from processors.adaptive_chunker import AdaptiveChunker
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
    target_db_config: Dict,
    embedding_config: Dict
):
    """
    Main ingestion task: fetch documents, generate embeddings, store in user's DB.

    Args:
        job_id: Ingestion job ID
        project_id: RAG project ID
        source_id: Data source ID
        source_config: Source configuration (type, endpoint, etc.)
        target_db_config: User's PostgreSQL config (host, port, user, password, table)
        embedding_config: Embedding settings (model, dimension, chunk_size)
    """
    logger.info(f"Starting ingestion job {job_id} for project {project_id}")

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

        # Step 3: Initialize services
        embedding_service = EmbeddingService(
            model=embedding_config['model'],
            embedding_dimension=embedding_config['dimension']
        )

        # Initialize adaptive chunker
        adaptive_chunker = AdaptiveChunker(
            overlap=embedding_config.get('chunk_overlap', 200)
        )

        # Check Ollama health
        if not embedding_service.health_check():
            raise RuntimeError("Ollama service is not available")

        # Step 3: Connect to user's vector database
        writer = VectorDBWriter(
            host=target_db_config['host'],
            port=target_db_config['port'],
            database=target_db_config['database'],
            user=target_db_config['user'],
            password=target_db_config['password'],
            table_name=target_db_config['table_name'],
            embedding_dimension=embedding_config['dimension']
        )

        if not writer.connect():
            raise RuntimeError("Failed to connect to target database")

        # Ensure pgvector and create table
        writer.ensure_pgvector_extension()
        writer.create_table()

        # Step 4: Process each document
        for doc in documents:
            processed += 1

            try:
                # Compute content hash for deduplication
                content = doc.get('title', '') + ' ' + doc.get('content', '')
                content_hash = embedding_service.compute_content_hash(content)

                # Check if already processed (in internal tracking DB)
                if is_document_processed(project_id, content_hash):
                    logger.info(f"Skipping duplicate document: {doc.get('id')}")
                    continue

                # Track document as processing
                track_document(project_id, source_id, doc, content_hash, content)

                # Check if exists in user's DB
                if writer.document_exists(doc.get('id')):
                    logger.info(f"Document {doc.get('id')} already in target DB, skipping")
                    mark_document_processed(project_id, content_hash, 'completed')
                    successful += 1
                    continue

                # Use adaptive chunking based on document size
                # This automatically selects optimal strategy (none, standard, recursive, multi_level)
                doc_for_chunking = {
                    'id': doc.get('id'),
                    'content': content,
                    'metadata': doc.get('metadata', {})
                }

                chunk_dicts = adaptive_chunker.chunk_document(
                    doc_for_chunking,
                    chunk_size=embedding_config.get('chunk_size', 1000)
                )

                # Generate embeddings for chunks
                chunk_embeddings = []
                for chunk_dict in chunk_dicts:
                    embedding = embedding_service.generate_embedding(chunk_dict['content'])
                    if embedding:
                        # Build metadata from chunk and document
                        metadata = {
                            **doc,
                            **chunk_dict['metadata'],  # Includes chunking_strategy, chunk_index, etc.
                            'content_hash': content_hash,
                            'source_id': source_id
                        }

                        # Add country/region information from source_config
                        if source_config.get('country_code'):
                            metadata['country_code'] = source_config['country_code']
                        if source_config.get('region'):
                            metadata['region'] = source_config['region']
                        if source_config.get('tags'):
                            metadata['tags'] = source_config['tags']

                        chunk_embeddings.append({
                            'id': chunk_dict['id'],  # Already has format: doc_id_chunk_N
                            'content': chunk_dict['content'],
                            'embedding': embedding,
                            'metadata': metadata
                        })
                    else:
                        logger.warning(f"Failed to generate embedding for chunk {chunk_dict['id']}")

                if not chunk_embeddings:
                    raise ValueError("Failed to generate any embeddings for document")

                # Insert into user's vector DB
                writer.insert_vectors(chunk_embeddings)

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

        # Close writer connection
        writer.close()

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
