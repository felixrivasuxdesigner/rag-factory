import logging
import os
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost:5432/vector_db')

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database.

    Returns:
        psycopg2.connection: A connection object or None if connection fails.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"Could not connect to the database: {e}", exc_info=True)
        return None

def create_documents_table(conn):
    """
    Creates the 'documents' table if it does not already exist.
    The table stores processed documents before they are vectorized.
    """
    create_table_query = """
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        publication_date DATE,
        source VARCHAR(255),
        content TEXT, -- Placeholder for full document content
        ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        with conn.cursor() as cur:
            cur.execute(create_table_query)
        conn.commit()
        logger.info("'documents' table created or already exists.")
    except psycopg2.Error as e:
        logger.error(f"Error creating 'documents' table: {e}", exc_info=True)
        conn.rollback()

def insert_documents(conn, documents: list[dict]):
    """
    Inserts a list of processed documents into the 'documents' table.
    It ignores documents with IDs that already exist in the table.

    Args:
        conn (psycopg2.connection): The database connection object.
        documents (list[dict]): A list of document dictionaries to insert.
    """
    if not documents:
        logger.info("No documents to insert.")
        return

    insert_query = """
    INSERT INTO documents (id, title, publication_date, source)
    VALUES %s
    ON CONFLICT (id) DO NOTHING;
    """

    # Prepare data for execute_values, ensuring all keys are present
    data_to_insert = [
        (
            doc.get('id'),
            doc.get('title'),
            doc.get('publication_date'),
            doc.get('source')
        ) for doc in documents
    ]

    try:
        with conn.cursor() as cur:
            execute_values(cur, insert_query, data_to_insert)
        conn.commit()
        logger.info(f"Successfully inserted/updated {len(data_to_insert)} documents.")
    except psycopg2.Error as e:
        logger.error(f"Error inserting documents: {e}", exc_info=True)
        conn.rollback()

if __name__ == '__main__':
    # This block is for demonstration and requires a running database.
    # It will not be executed as part of the main application flow.
    print("--- Testing Database Module ---")

    connection = get_db_connection()
    if connection:
        print("Successfully connected to the database.")

        # 1. Create the table
        create_documents_table(connection)

        # 2. Insert sample data
        sample_docs = [
            {'id': 'BCN-LEY-1', 'title': 'Ley de Ejemplo 1', 'publication_date': '2023-01-01', 'source': 'TEST'},
            {'id': 'BCN-LEY-2', 'title': 'Ley de Ejemplo 2', 'publication_date': '2023-01-02', 'source': 'TEST'},
            {'id': 'BCN-LEY-1', 'title': 'Ley de Ejemplo 1 Duplicada', 'publication_date': '2023-01-01', 'source': 'TEST'},
        ]
        print(f"\nAttempting to insert {len(sample_docs)} documents (including one duplicate)...")
        insert_documents(connection, sample_docs)

        # 3. Verify insertion
        with connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM documents WHERE source = 'TEST';")
            count = cur.fetchone()[0]
            print(f"Verification: Found {count} documents with source='TEST' in the table.")
            assert count == 2

            # Clean up test data
            cur.execute("DELETE FROM documents WHERE source = 'TEST';")
        connection.commit()
        print("Cleaned up test data.")

        connection.close()
        print("\nDatabase connection closed.")
    else:
        print("Failed to connect to the database. Skipping tests.")

    print("\n--- Database Module testing complete ---")