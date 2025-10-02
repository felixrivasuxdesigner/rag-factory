import logging
import os
from ..connectors.sparql_connector import SparqlConnector
from ..processors.document_processor import DocumentProcessor
from .database import get_db_connection, create_documents_table, insert_documents

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
# In a real application, this would come from a config file (e.g., config/config.yml)
# Note: The BCN endpoint has been unreliable during development.
# The code is structured to work, but may fail if the endpoint is down or blocking requests.
SPARQL_ENDPOINT = os.environ.get('SPARQL_ENDPOINT', 'https://datos.bcn.cl/es/endpoint-sparql')
DOCUMENT_LIMIT = int(os.environ.get('DOCUMENT_LIMIT', 25))

def run_ingestion_pipeline():
    """
    Executes the full document ingestion pipeline.
    1. Fetches data from a SPARQL source.
    2. Processes the raw data into a clean format.
    3. Stores the clean data in the database.
    """
    logger.info("--- Starting document ingestion pipeline ---")

    # 1. Fetch data from SPARQL endpoint
    logger.info(f"Connecting to SPARQL endpoint: {SPARQL_ENDPOINT}")
    sparql_connector = SparqlConnector(endpoint_url=SPARQL_ENDPOINT)
    raw_documents = sparql_connector.get_leyes(limit=DOCUMENT_LIMIT)

    if not raw_documents:
        logger.warning("No documents were fetched from the SPARQL endpoint. The endpoint might be down or returned no data. Pipeline will stop.")
        return

    # 2. Process the raw documents
    logger.info(f"Processing {len(raw_documents)} raw documents...")
    processed_documents = DocumentProcessor.process_sparql_result(raw_documents)

    if not processed_documents:
        logger.warning("No documents were successfully processed. Pipeline will stop.")
        return

    # 3. Store documents in the database
    logger.info("Connecting to the database to store documents...")
    db_conn = get_db_connection()
    if db_conn:
        try:
            # Ensure the table exists
            create_documents_table(db_conn)

            # Insert the processed documents
            logger.info(f"Inserting {len(processed_documents)} processed documents into the database.")
            insert_documents(db_conn, processed_documents)
        finally:
            db_conn.close()
            logger.info("Database connection closed.")
    else:
        logger.error("Could not establish a database connection. Documents were not saved.")

    logger.info("--- Document ingestion pipeline finished ---")

if __name__ == "__main__":
    run_ingestion_pipeline()