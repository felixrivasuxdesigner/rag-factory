"""
Dynamic vector database writer service.
Connects to user-provided PostgreSQL databases and writes embeddings with pgvector.
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
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        table_name: str,
        embedding_dimension: int = 1024
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
            embedding_dimension: Vector dimension (default 1024 for mxbai-embed-large)
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

    def create_table(self, metadata_columns: Optional[Dict[str, str]] = None):
        """
        Create the vector table if it doesn't exist.

        Args:
            metadata_columns: Additional columns to add (e.g., {'source': 'VARCHAR(255)', 'publication_date': 'DATE'})
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")

        # Base columns
        columns = f"""
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            embedding vector({self.embedding_dimension}) NOT NULL,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        """

        # Add custom metadata columns if provided
        if metadata_columns:
            for col_name, col_type in metadata_columns.items():
                columns += f",\n            {col_name} {col_type}"

        create_query = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            {columns}
        );
        """

        # Create index for vector similarity search
        index_query = f"""
        CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx
        ON {self.table_name}
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """

        try:
            with self.conn.cursor() as cur:
                cur.execute(create_query)
                logger.info(f"✓ Created table '{self.table_name}'")

                cur.execute(index_query)
                logger.info(f"✓ Created vector index on '{self.table_name}'")

            self.conn.commit()
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

        Args:
            documents: List of dicts with keys: id, content, embedding, metadata
            on_conflict: Action on ID conflict (default: DO NOTHING, or DO UPDATE SET...)

        Returns:
            int: Number of documents inserted
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")

        if not documents:
            logger.warning("No documents to insert")
            return 0

        # Prepare data for insertion
        data = []
        for doc in documents:
            if 'embedding' not in doc or doc['embedding'] is None:
                logger.warning(f"Skipping document {doc.get('id', 'unknown')} - no embedding")
                continue

            # Convert embedding list to pgvector format
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
            logger.info(f"✓ Inserted {inserted_count} documents into '{self.table_name}'")
            return inserted_count

        except psycopg2.Error as e:
            logger.error(f"Failed to insert vectors: {e}", exc_info=True)
            self.conn.rollback()
            raise

    def document_exists(self, document_id: str) -> bool:
        """
        Check if a document already exists in the table.

        Args:
            document_id: The document ID to check

        Returns:
            bool: True if exists
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"SELECT 1 FROM {self.table_name} WHERE id = %s LIMIT 1;",
                    (document_id,)
                )
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
        tags: Dict = None
    ) -> List[Dict]:
        """
        Perform similarity search using cosine similarity with optional country/region filtering.

        Args:
            query_embedding: The query vector
            limit: Max results to return
            threshold: Minimum similarity score (0-1)
            country_code: Filter by country code (e.g., 'CL', 'US')
            region: Filter by region
            tags: Filter by tags (must match all provided tags)

        Returns:
            List of matching documents with similarity scores
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")

        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

        # Build WHERE clause with filters
        where_clauses = ["1 - (embedding <=> %s::vector) >= %s"]
        params = [embedding_str, threshold]

        if country_code:
            where_clauses.append("metadata->>'country_code' = %s")
            params.append(country_code)

        if region:
            where_clauses.append("metadata->>'region' = %s")
            params.append(region)

        if tags:
            # Filter by tags - all provided tags must match
            for tag_key, tag_value in tags.items():
                where_clauses.append(f"metadata->'tags'->>{%s} = %s")
                params.extend([tag_key, str(tag_value)])

        where_clause = " AND ".join(where_clauses)

        query = f"""
        SELECT
            id,
            content,
            metadata,
            1 - (embedding <=> %s::vector) as similarity
        FROM {self.table_name}
        WHERE {where_clause}
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
        """

        # Add parameters for similarity calculation and ordering
        final_params = [embedding_str] + params + [embedding_str, limit]

        try:
            with self.conn.cursor() as cur:
                cur.execute(query, final_params)
                results = []
                for row in cur.fetchall():
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
            Dict with count, table size, index size
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")

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
                    'table_name': self.table_name
                }
        except psycopg2.Error as e:
            logger.error(f"Failed to get table stats: {e}", exc_info=True)
            return {}

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
    Test the vector DB writer
    """
    print("--- Testing Vector DB Writer ---\n")

    # Test configuration (using the existing DB for testing)
    config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rag_factory_db',
        'user': 'journeylaw',
        'password': 'journeylaw_dev_2024',
        'table_name': 'test_vectors'
    }

    # Initialize writer
    writer = VectorDBWriter(**config)

    try:
        # Connect
        if not writer.connect():
            print("Failed to connect")
            exit(1)

        # Ensure pgvector
        writer.ensure_pgvector_extension()

        # Create table
        print("\nCreating table with custom metadata columns...")
        writer.create_table(metadata_columns={
            'source': 'VARCHAR(255)',
            'publication_date': 'DATE'
        })

        # Test data with dummy embeddings
        print("\nInserting test documents...")
        import random
        test_docs = [
            {
                'id': 'doc-001',
                'content': 'This is a test document about machine learning',
                'embedding': [random.random() for _ in range(1024)],
                'metadata': {'source': 'test', 'topic': 'ML'}
            },
            {
                'id': 'doc-002',
                'content': 'Another document about artificial intelligence',
                'embedding': [random.random() for _ in range(1024)],
                'metadata': {'source': 'test', 'topic': 'AI'}
            }
        ]

        inserted = writer.insert_vectors(test_docs)
        print(f"✓ Inserted {inserted} documents")

        # Check existence
        print("\nChecking document existence...")
        exists = writer.document_exists('doc-001')
        print(f"✓ Document 'doc-001' exists: {exists}")

        # Get stats
        print("\nTable statistics:")
        stats = writer.get_table_stats()
        print(f"  Documents: {stats['document_count']}")
        print(f"  Table size: {stats['table_size']}")

        # Cleanup test data
        print("\nCleaning up test data...")
        with writer.conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {config['table_name']};")
        writer.conn.commit()
        print("✓ Test table dropped")

    finally:
        writer.close()

    print("\n--- Vector DB Writer test completed ---")
