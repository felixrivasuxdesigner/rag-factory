"""
Database schema for internal tracking of RAG projects, data sources, and ingestion jobs.
This is separate from the user's target PostgreSQL database where vectors are stored.
"""

import logging
import psycopg2
from psycopg2 import sql

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_internal_schema(conn):
    """
    Creates all internal tables needed for RAG project management.
    These tables track projects, data sources, documents, and job status.

    Args:
        conn (psycopg2.connection): Database connection to the internal database.
    """

    # Table 1: RAG Projects
    # Stores configuration for each RAG project (target database credentials, settings)
    create_projects_table = """
    CREATE TABLE IF NOT EXISTS rag_projects (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        description TEXT,

        -- Target PostgreSQL database where vectors will be stored
        target_db_host VARCHAR(255) NOT NULL,
        target_db_port INTEGER NOT NULL DEFAULT 5432,
        target_db_name VARCHAR(255) NOT NULL,
        target_db_user VARCHAR(255) NOT NULL,
        target_db_password VARCHAR(255) NOT NULL,
        target_table_name VARCHAR(255) NOT NULL,

        -- Embedding configuration
        embedding_model VARCHAR(100) NOT NULL DEFAULT 'jina/jina-embeddings-v2-base-es',
        embedding_dimension INTEGER NOT NULL DEFAULT 768,
        chunk_size INTEGER DEFAULT 1000,
        chunk_overlap INTEGER DEFAULT 200,

        -- Metadata
        status VARCHAR(50) DEFAULT 'active', -- active, paused, archived
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """

    # Table 2: Data Sources
    # Each project can have multiple data sources (APIs, SPARQL, files, etc.)
    create_sources_table = """
    CREATE TABLE IF NOT EXISTS data_sources (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES rag_projects(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        source_type VARCHAR(50) NOT NULL, -- sparql, rest_api, file_upload, web_scrape

        -- Connection details (stored as JSONB for flexibility)
        config JSONB NOT NULL, -- { "endpoint": "...", "query": "...", "headers": {...} }

        -- Regional/Country identification
        country_code VARCHAR(10), -- ISO 3166-1 alpha-2 (e.g., 'CL', 'US') or custom
        region VARCHAR(100), -- Optional: region/state (e.g., 'California', 'Santiago')
        tags JSONB, -- Additional flexible tags { "jurisdiction": "federal", "language": "es" }

        -- Scheduling
        sync_frequency VARCHAR(50) DEFAULT 'manual', -- manual, hourly, daily, weekly
        last_sync_at TIMESTAMP WITH TIME ZONE,
        next_sync_at TIMESTAMP WITH TIME ZONE,

        -- Status
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

        UNIQUE(project_id, name)
    );
    """

    # Table 3: Document Tracking
    # Tracks all documents processed to avoid duplicates
    create_documents_tracking_table = """
    CREATE TABLE IF NOT EXISTS documents_tracking (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES rag_projects(id) ON DELETE CASCADE,
        source_id INTEGER REFERENCES data_sources(id) ON DELETE SET NULL,

        -- Document identification
        document_hash VARCHAR(64) NOT NULL, -- SHA-256 hash of content for deduplication
        external_id TEXT, -- Original ID from source (e.g., SPARQL URI)
        title TEXT,

        -- Processing status
        status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed
        error_message TEXT,

        -- Metadata
        content_preview TEXT, -- First 500 chars for reference
        metadata JSONB, -- Flexible field for source-specific data

        -- Timestamps
        discovered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMP WITH TIME ZONE,

        -- Prevent duplicate processing
        UNIQUE(project_id, document_hash)
    );
    """

    # Table 4: Ingestion Jobs
    # Tracks batch ingestion jobs with progress and errors
    create_jobs_table = """
    CREATE TABLE IF NOT EXISTS ingestion_jobs (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES rag_projects(id) ON DELETE CASCADE,
        source_id INTEGER REFERENCES data_sources(id) ON DELETE SET NULL,

        -- Job details
        job_type VARCHAR(50) NOT NULL, -- full_sync, incremental, retry_failed
        status VARCHAR(50) NOT NULL DEFAULT 'queued', -- queued, running, completed, failed, cancelled

        -- Progress tracking
        total_documents INTEGER DEFAULT 0,
        processed_documents INTEGER DEFAULT 0,
        successful_documents INTEGER DEFAULT 0,
        failed_documents INTEGER DEFAULT 0,

        -- Error handling
        error_log TEXT,

        -- Timestamps
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE
    );
    """

    # Table 5: Document Content Cache
    # Caches downloaded document content to avoid re-downloading on job restarts
    create_content_cache_table = """
    CREATE TABLE IF NOT EXISTS documents_content_cache (
        id SERIAL PRIMARY KEY,
        source_id INTEGER NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,

        -- Document identification
        external_id TEXT NOT NULL, -- Original ID from source (e.g., BCN norm ID)
        content_hash VARCHAR(64) NOT NULL, -- SHA-256 hash for quick comparison

        -- Cached content
        title TEXT,
        content TEXT NOT NULL, -- Full document content (XML, JSON, etc.)
        content_size INTEGER, -- Size in bytes for monitoring

        -- Metadata from source
        source_url TEXT, -- Original download URL
        source_metadata JSONB, -- Additional metadata from source

        -- Cache management
        downloaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        access_count INTEGER DEFAULT 1,

        -- Prevent duplicates per source
        UNIQUE(source_id, external_id)
    );
    """

    # Indexes for performance
    create_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_data_sources_project ON data_sources(project_id);",
        "CREATE INDEX IF NOT EXISTS idx_documents_project ON documents_tracking(project_id);",
        "CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents_tracking(document_hash);",
        "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents_tracking(status);",
        "CREATE INDEX IF NOT EXISTS idx_jobs_project ON ingestion_jobs(project_id);",
        "CREATE INDEX IF NOT EXISTS idx_jobs_status ON ingestion_jobs(status);",
        "CREATE INDEX IF NOT EXISTS idx_cache_source ON documents_content_cache(source_id);",
        "CREATE INDEX IF NOT EXISTS idx_cache_external_id ON documents_content_cache(external_id);",
        "CREATE INDEX IF NOT EXISTS idx_cache_hash ON documents_content_cache(content_hash);",
        "CREATE INDEX IF NOT EXISTS idx_cache_accessed ON documents_content_cache(last_accessed_at);",
    ]

    try:
        with conn.cursor() as cur:
            logger.info("Creating internal schema tables...")

            cur.execute(create_projects_table)
            logger.info("✓ Created rag_projects table")

            cur.execute(create_sources_table)
            logger.info("✓ Created data_sources table")

            cur.execute(create_documents_tracking_table)
            logger.info("✓ Created documents_tracking table")

            cur.execute(create_jobs_table)
            logger.info("✓ Created ingestion_jobs table")

            cur.execute(create_content_cache_table)
            logger.info("✓ Created documents_content_cache table")

            for idx_query in create_indexes:
                cur.execute(idx_query)
            logger.info("✓ Created indexes")

        conn.commit()
        logger.info("Internal schema created successfully!")

    except psycopg2.Error as e:
        logger.error(f"Error creating internal schema: {e}", exc_info=True)
        conn.rollback()
        raise


def drop_internal_schema(conn):
    """
    Drops all internal tables. Use with caution!

    Args:
        conn (psycopg2.connection): Database connection to the internal database.
    """
    drop_queries = [
        "DROP TABLE IF EXISTS ingestion_jobs CASCADE;",
        "DROP TABLE IF EXISTS documents_tracking CASCADE;",
        "DROP TABLE IF EXISTS data_sources CASCADE;",
        "DROP TABLE IF EXISTS rag_projects CASCADE;",
    ]

    try:
        with conn.cursor() as cur:
            for query in drop_queries:
                cur.execute(query)
        conn.commit()
        logger.info("Internal schema dropped successfully")
    except psycopg2.Error as e:
        logger.error(f"Error dropping internal schema: {e}", exc_info=True)
        conn.rollback()
        raise


if __name__ == '__main__':
    """
    Test the schema creation with the internal database
    """
    from .database import get_db_connection

    print("--- Testing Internal Schema Creation ---\n")

    conn = get_db_connection()
    if conn:
        try:
            # Create the schema
            create_internal_schema(conn)

            # Verify tables exist
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name IN ('rag_projects', 'data_sources', 'documents_tracking', 'ingestion_jobs')
                    ORDER BY table_name;
                """)
                tables = cur.fetchall()
                print(f"\n✓ Verified {len(tables)} tables created:")
                for table in tables:
                    print(f"  - {table[0]}")

            print("\n--- Schema creation test completed successfully ---")

        finally:
            conn.close()
    else:
        print("Failed to connect to database")
