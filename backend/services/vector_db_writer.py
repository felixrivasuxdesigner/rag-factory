"""
Dynamic vector database writer service.
Connects to user-provided PostgreSQL databases and writes embeddings with pgvector.

Schema v2 - PostgreSQL Best Practices:
- SERIAL auto-increment IDs (more efficient than TEXT)
- Structured fields (title, document_type, source, specialty)
- Proper indexing on common query fields
- Backward compatible with v1 schema (TEXT id)
"""

import logging
import psycopg2
from psycopg2.extras import execute_values
from typing import List, Dict, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorDBWriter:
    """
    Handles dynamic connections to user PostgreSQL databases
    and writes document embeddings with pgvector support.

    Supports both Schema v1 (legacy) and Schema v2 (best practices).
    Automatically detects existing table schema.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        table_name: str,
        embedding_dimension: int = 768,
        schema_version: int = 2  # Default to v2 (best practices)
    ):
        """
        Initialize connection to user's vector database.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Username
            password: Password
            table_name: Table name where vectors will be stored
            embedding_dimension: Vector dimension (default 768 for jina/jina-embeddings-v2-base-es)
            schema_version: 1 (legacy TEXT id) or 2 (SERIAL id, structured fields)
        """
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        self.table_name = table_name
        self.embedding_dimension = embedding_dimension
        self.schema_version = schema_version
        self.detected_schema = None  # Will be set after inspecting table
        self.conn = None

    def connect(self) -> bool:
        """
        Establish connection to the user's database.

        Returns:
            bool: True if successful
        """
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            logger.info(f"✓ Connected to {self.connection_params['host']}:{self.connection_params['port']}/{self.connection_params['database']}")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to user database: {e}", exc_info=True)
            return False

    def ensure_pgvector_extension(self):
        """
        Ensure pgvector extension is installed.
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")

        try:
            with self.conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            self.conn.commit()
            logger.info("✓ pgvector extension enabled")
        except psycopg2.Error as e:
            logger.error(f"Failed to enable pgvector: {e}", exc_info=True)
            self.conn.rollback()
            raise

    def detect_table_schema(self) -> int:
        """
        Detect which schema version an existing table uses.

        Returns:
            int: 1 (legacy) or 2 (best practices), or 0 if table doesn't exist
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")

        try:
            with self.conn.cursor() as cur:
                # Check if table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = %s
                    );
                """, (self.table_name,))

                if not cur.fetchone()[0]:
                    logger.info(f"Table '{self.table_name}' does not exist")
                    return 0

                # Get column information
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position;
                """, (self.table_name,))

                columns = {row[0]: row[1] for row in cur.fetchall()}

                # Detect schema version based on columns
                if 'id' in columns:
                    if columns['id'] == 'integer':
                        # Check for v2-specific columns
                        if 'title' in columns and 'document_type' in columns:
                            logger.info(f"✓ Detected Schema v2 (SERIAL id, structured fields)")
                            self.detected_schema = 2
                            return 2
                    elif columns['id'] in ('text', 'character varying'):
                        logger.info(f"✓ Detected Schema v1 (TEXT id)")
                        self.detected_schema = 1
                        return 1

                logger.warning(f"Unknown schema for table '{self.table_name}'")
                return 0

        except psycopg2.Error as e:
            logger.error(f"Failed to detect schema: {e}", exc_info=True)
            return 0

    def create_table(self, metadata_columns: Optional[Dict[str, str]] = None):
        """
        Create the vector table if it doesn't exist.
        Uses schema_version to determine which schema to create.

        Args:
            metadata_columns: Additional columns to add (legacy v1 only)
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")

        # Check if table already exists and detect its schema
        existing_schema = self.detect_table_schema()
        if existing_schema > 0:
            logger.info(f"Table '{self.table_name}' already exists with schema v{existing_schema}")
            self.detected_schema = existing_schema  # IMPORTANT: Save detected schema
            return

        # Create table based on schema version
        if self.schema_version == 2:
            self._create_table_v2()
        else:
            self._create_table_v1(metadata_columns)

    def _create_table_v1(self, metadata_columns: Optional[Dict[str, str]] = None):
        """Create table with legacy schema (TEXT id)."""
        columns = f"""
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            embedding vector({self.embedding_dimension}) NOT NULL,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        """

        if metadata_columns:
            for col_name, col_type in metadata_columns.items():
                columns += f",\n            {col_name} {col_type}"

        create_query = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            {columns}
        );
        """

        index_query = f"""
        CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx
        ON {self.table_name}
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """

        try:
            with self.conn.cursor() as cur:
                cur.execute(create_query)
                logger.info(f"✓ Created table '{self.table_name}' (Schema v1 - legacy)")

                cur.execute(index_query)
                logger.info(f"✓ Created vector index on '{self.table_name}'")

            self.conn.commit()
            self.detected_schema = 1
        except psycopg2.Error as e:
            logger.error(f"Failed to create table: {e}", exc_info=True)
            self.conn.rollback()
            raise

    def _create_table_v2(self):
        """Create table with Schema v2 (PostgreSQL best practices)."""
        create_query = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id SERIAL PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            content TEXT NOT NULL,
            document_type VARCHAR(50) NOT NULL,
            source VARCHAR(255),
            specialty VARCHAR(50),
            embedding vector({self.embedding_dimension}),
            metadata JSONB DEFAULT '{{}}'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """

        # Create indexes for common queries
        indexes = [
            f"CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx ON {self.table_name} USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);",
            f"CREATE INDEX IF NOT EXISTS {self.table_name}_document_type_idx ON {self.table_name} (document_type);",
            f"CREATE INDEX IF NOT EXISTS {self.table_name}_specialty_idx ON {self.table_name} (specialty);",
            f"CREATE INDEX IF NOT EXISTS {self.table_name}_metadata_idx ON {self.table_name} USING GIN (metadata jsonb_path_ops);",
            f"CREATE INDEX IF NOT EXISTS {self.table_name}_created_at_idx ON {self.table_name} (created_at);"
        ]

        try:
            with self.conn.cursor() as cur:
                cur.execute(create_query)
                logger.info(f"✓ Created table '{self.table_name}' (Schema v2 - best practices)")

                for index_query in indexes:
                    cur.execute(index_query)
                logger.info(f"✓ Created {len(indexes)} indexes on '{self.table_name}'")

            self.conn.commit()
            self.detected_schema = 2
        except psycopg2.Error as e:
            logger.error(f"Failed to create table: {e}", exc_info=True)
            self.conn.rollback()
            raise

    def insert_vectors(
        self,
        documents: List[Dict],
        on_conflict: str = "DO NOTHING"
    ) -> int:
        """
        Insert documents with embeddings into the vector table.
        Automatically adapts to detected schema version.

        Args:
            documents: List of dicts with document data
            on_conflict: Action on ID conflict

        Returns:
            int: Number of documents inserted
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")

        if not documents:
            logger.warning("No documents to insert")
            return 0

        # Auto-detect schema if not already detected
        if self.detected_schema is None:
            self.detect_table_schema()

        # Use detected schema or fallback to configured version
        schema_to_use = self.detected_schema or self.schema_version

        if schema_to_use == 2:
            return self._insert_vectors_v2(documents, on_conflict)
        else:
            return self._insert_vectors_v1(documents, on_conflict)

    def _insert_vectors_v1(self, documents: List[Dict], on_conflict: str) -> int:
        """Insert vectors using legacy schema (TEXT id)."""
        data = []
        for doc in documents:
            if 'embedding' not in doc or doc['embedding'] is None:
                logger.warning(f"Skipping document {doc.get('id', 'unknown')} - no embedding")
                continue

            embedding_str = '[' + ','.join(str(x) for x in doc['embedding']) + ']'

            data.append((
                doc.get('id'),
                doc.get('content', ''),
                embedding_str,
                psycopg2.extras.Json(doc.get('metadata', {}))
            ))

        if not data:
            logger.warning("No valid documents with embeddings to insert")
            return 0

        insert_query = f"""
        INSERT INTO {self.table_name} (id, content, embedding, metadata)
        VALUES %s
        ON CONFLICT (id) {on_conflict};
        """

        try:
            with self.conn.cursor() as cur:
                execute_values(cur, insert_query, data, template=None, page_size=100)
            self.conn.commit()

            inserted_count = len(data)
            logger.info(f"✓ Inserted {inserted_count} documents into '{self.table_name}' (Schema v1)")
            return inserted_count

        except psycopg2.Error as e:
            logger.error(f"Failed to insert vectors: {e}", exc_info=True)
            self.conn.rollback()
            raise

    def _insert_vectors_v2(self, documents: List[Dict], on_conflict: str) -> int:
        """Insert vectors using Schema v2 (SERIAL id, structured fields)."""
        data = []
        for doc in documents:
            if 'embedding' not in doc or doc['embedding'] is None:
                logger.warning(f"Skipping document {doc.get('id', 'unknown')} - no embedding")
                continue

            embedding_str = '[' + ','.join(str(x) for x in doc['embedding']) + ']'

            # Extract metadata
            metadata = doc.get('metadata', {})

            # Get title (from doc or metadata)
            title = doc.get('title') or metadata.get('title', 'Untitled')
            if len(title) > 500:
                title = title[:497] + '...'

            # Get document type from metadata or infer from source
            doc_type = metadata.get('document_type', 'UNKNOWN')

            # Get source URL
            source = doc.get('source') or metadata.get('source') or metadata.get('url')

            # Get specialty
            specialty = metadata.get('specialty')

            # Clean metadata - remove fields that are now columns
            clean_metadata = {k: v for k, v in metadata.items()
                            if k not in ('title', 'document_type', 'source', 'specialty', 'url')}

            # Add chunk info to metadata
            if 'id' in doc and isinstance(doc['id'], str) and '_chunk_' in doc['id']:
                parts = doc['id'].split('_chunk_')
                if len(parts) == 2:
                    clean_metadata['chunk_index'] = int(parts[1])
                    clean_metadata['original_document_id'] = parts[0]

            data.append((
                title,
                doc.get('content', ''),
                doc_type,
                source,
                specialty,
                embedding_str,
                psycopg2.extras.Json(clean_metadata)
            ))

        if not data:
            logger.warning("No valid documents with embeddings to insert")
            return 0

        insert_query = f"""
        INSERT INTO {self.table_name}
            (title, content, document_type, source, specialty, embedding, metadata)
        VALUES %s
        """

        # For v2, we can't use ON CONFLICT with SERIAL id easily
        # Instead, we just insert (duplicates handled by deduplication in tracking table)

        try:
            with self.conn.cursor() as cur:
                execute_values(cur, insert_query, data, template=None, page_size=100)
            self.conn.commit()

            inserted_count = len(data)
            logger.info(f"✓ Inserted {inserted_count} documents into '{self.table_name}' (Schema v2)")
            return inserted_count

        except psycopg2.Error as e:
            logger.error(f"Failed to insert vectors: {e}", exc_info=True)
            self.conn.rollback()
            raise

    def document_exists(self, document_id: str) -> bool:
        """
        Check if a document already exists in the table.

        Note: For Schema v2, this checks metadata->>'original_document_id'
        since the id is auto-increment.

        Args:
            document_id: The document ID to check (can be "doc_id" or "doc_id_chunk_N")

        Returns:
            bool: True if exists
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")

        # Auto-detect schema if needed
        if self.detected_schema is None:
            self.detect_table_schema()

        schema_to_use = self.detected_schema or self.schema_version

        # Extract base document ID if this is a chunk ID
        base_doc_id = document_id
        if '_chunk_' in str(document_id):
            parts = str(document_id).split('_chunk_')
            if len(parts) == 2:
                base_doc_id = parts[0]

        try:
            with self.conn.cursor() as cur:
                if schema_to_use == 2:
                    # For v2, check in metadata
                    cur.execute(f"""
                        SELECT 1 FROM {self.table_name}
                        WHERE metadata->>'original_document_id' = %s
                        LIMIT 1;
                    """, (base_doc_id,))
                else:
                    # For v1, check id directly (including chunk suffix)
                    cur.execute(f"""
                        SELECT 1 FROM {self.table_name}
                        WHERE id = %s
                        LIMIT 1;
                    """, (document_id,))

                return cur.fetchone() is not None
        except psycopg2.Error as e:
            logger.error(f"Error checking document existence: {e}", exc_info=True)
            return False

    def similarity_search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        threshold: float = 0.7,
        country_code: str = None,
        region: str = None,
        document_type: str = None,
        specialty: str = None,
        tags: Dict = None
    ) -> List[Dict]:
        """
        Perform similarity search using cosine similarity with optional filtering.

        Args:
            query_embedding: The query vector
            limit: Max results to return
            threshold: Minimum similarity score (0-1)
            country_code: Filter by country code (e.g., 'CL', 'US')
            region: Filter by region
            document_type: Filter by document type (v2 only)
            specialty: Filter by specialty (v2 only)
            tags: Filter by metadata tags

        Returns:
            List of matching documents with similarity scores
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")

        # Auto-detect schema if needed
        if self.detected_schema is None:
            self.detect_table_schema()

        schema_to_use = self.detected_schema or self.schema_version

        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

        # Build WHERE clause
        where_clauses = ["1 - (embedding <=> %s::vector) >= %s"]
        params = [embedding_str, threshold]

        # Schema v2 supports direct column filtering
        if schema_to_use == 2:
            if document_type:
                where_clauses.append("document_type = %s")
                params.append(document_type)

            if specialty:
                where_clauses.append("specialty = %s")
                params.append(specialty)

        # Both schemas support metadata filtering
        if country_code:
            where_clauses.append("metadata->>'country_code' = %s")
            params.append(country_code)

        if region:
            where_clauses.append("metadata->>'region' = %s")
            params.append(region)

        if tags:
            for tag_key, tag_value in tags.items():
                where_clauses.append("metadata->'tags'->>%s = %s")
                params.extend([tag_key, str(tag_value)])

        where_clause = " AND ".join(where_clauses)

        # Build SELECT clause based on schema
        if schema_to_use == 2:
            select_fields = "id, title, content, document_type, specialty, metadata"
        else:
            select_fields = "id, content, metadata"

        query = f"""
        SELECT
            {select_fields},
            1 - (embedding <=> %s::vector) as similarity
        FROM {self.table_name}
        WHERE {where_clause}
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
        """

        final_params = [embedding_str] + params + [embedding_str, limit]

        try:
            with self.conn.cursor() as cur:
                cur.execute(query, final_params)
                results = []
                for row in cur.fetchall():
                    if schema_to_use == 2:
                        results.append({
                            'id': row[0],
                            'title': row[1],
                            'content': row[2],
                            'document_type': row[3],
                            'specialty': row[4],
                            'metadata': row[5],
                            'similarity': float(row[6])
                        })
                    else:
                        results.append({
                            'id': row[0],
                            'content': row[1],
                            'metadata': row[2],
                            'similarity': float(row[3])
                        })

                logger.info(f"Similarity search returned {len(results)} results")
                return results
        except psycopg2.Error as e:
            logger.error(f"Similarity search failed: {e}", exc_info=True)
            return []

    def get_table_stats(self) -> Dict:
        """
        Get statistics about the vector table.

        Returns:
            Dict with count, table size, schema version
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")

        # Auto-detect schema if needed
        if self.detected_schema is None:
            self.detect_table_schema()

        try:
            with self.conn.cursor() as cur:
                # Document count
                cur.execute(f"SELECT COUNT(*) FROM {self.table_name};")
                count = cur.fetchone()[0]

                # Table size
                cur.execute(f"""
                    SELECT pg_size_pretty(pg_total_relation_size('{self.table_name}')) as size;
                """)
                size = cur.fetchone()[0]

                return {
                    'document_count': count,
                    'table_size': size,
                    'table_name': self.table_name,
                    'schema_version': self.detected_schema or self.schema_version
                }
        except psycopg2.Error as e:
            logger.error(f"Failed to get table stats: {e}", exc_info=True)
            return {}

    def reconnect(self) -> bool:
        """
        Refresh the database connection.
        Useful for long-running operations that may timeout.

        Returns:
            bool: True if reconnection successful
        """
        logger.info("Refreshing database connection...")
        self.close()
        return self.connect()

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == '__main__':
    """
    Test the vector DB writer with both schemas
    """
    print("--- Testing Vector DB Writer (Schema v2) ---\n")

    # Test configuration
    config = {
        'host': 'localhost',
        'port': 5433,
        'database': 'rag_factory_db',
        'user': 'user',
        'password': 'password',
        'table_name': 'test_vectors_v2',
        'schema_version': 2
    }

    writer = VectorDBWriter(**config)

    try:
        # Connect
        if not writer.connect():
            print("Failed to connect")
            exit(1)

        # Ensure pgvector
        writer.ensure_pgvector_extension()

        # Create table with v2 schema
        print("\nCreating table with Schema v2...")
        writer.create_table()

        # Test data
        print("\nInserting test documents...")
        import random
        test_docs = [
            {
                'id': '1001_chunk_0',
                'title': 'Immigration Law - Chile',
                'content': 'Ley de Migración de Chile - Artículo 1...',
                'embedding': [random.random() for _ in range(768)],
                'metadata': {
                    'document_type': 'IMMIGRATION_LAW',
                    'source': 'https://bcn.cl/leychile',
                    'specialty': 'IMMIGRATION',
                    'country_code': 'CL',
                    'year': 2024
                }
            },
            {
                'id': '1001_chunk_1',
                'title': 'Immigration Law - Chile',
                'content': 'Ley de Migración de Chile - Artículo 2...',
                'embedding': [random.random() for _ in range(768)],
                'metadata': {
                    'document_type': 'IMMIGRATION_LAW',
                    'source': 'https://bcn.cl/leychile',
                    'specialty': 'IMMIGRATION',
                    'country_code': 'CL',
                    'year': 2024
                }
            }
        ]

        inserted = writer.insert_vectors(test_docs)
        print(f"✓ Inserted {inserted} documents")

        # Get stats
        print("\nTable statistics:")
        stats = writer.get_table_stats()
        print(f"  Documents: {stats['document_count']}")
        print(f"  Table size: {stats['table_size']}")
        print(f"  Schema version: v{stats['schema_version']}")

        # Test similarity search
        print("\nTesting similarity search...")
        query_vec = [random.random() for _ in range(768)]
        results = writer.similarity_search(query_vec, limit=5, threshold=0.0, document_type='IMMIGRATION_LAW')
        print(f"✓ Found {len(results)} similar documents")
        if results:
            print(f"  Top result: {results[0]['title'][:50]}... (similarity: {results[0]['similarity']:.3f})")

        # Cleanup
        print("\nCleaning up test data...")
        with writer.conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {config['table_name']};")
        writer.conn.commit()
        print("✓ Test table dropped")

    finally:
        writer.close()

    print("\n--- Vector DB Writer test completed ---")
