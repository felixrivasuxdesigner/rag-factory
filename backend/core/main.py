import logging
import os
from ..connectors.sparql_connector import SparqlConnector
from ..processors.document_processor import DocumentProcessor
from ..processors.vectorizer import Vectorizer
from .database import get_db_connection, setup_database, insert_documents, get_documents_without_embedding, update_document_embedding

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
SPARQL_ENDPOINT = os.environ.get('SPARQL_ENDPOINT', 'https://datos.bcn.cl/es/endpoint-sparql')
DOCUMENT_LIMIT = int(os.environ.get('DOCUMENT_LIMIT', 25))

def run_ingestion_pipeline():
    """
    Executes the full document ingestion and vectorization pipeline.
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
    logger.info("Connecting to the database...")
    db_conn = get_db_connection()
    if db_conn:
        try:
            # Step 3a: Ensure the table and extension exist, and insert documents
            setup_database(db_conn)
            logger.info(f"Inserting {len(processed_documents)} processed documents into the database.")
            insert_documents(db_conn, processed_documents)

            # Step 3b: Vectorize documents that don't have an embedding
            logger.info("--- Starting vectorization process ---")
            vectorizer = Vectorizer()
            docs_to_vectorize = get_documents_without_embedding(db_conn, limit=DOCUMENT_LIMIT)

            if not docs_to_vectorize:
                logger.info("No new documents to vectorize.")
            else:
                logger.info(f"Found {len(docs_to_vectorize)} documents to vectorize.")
                for doc_id, doc_title in docs_to_vectorize:
                    logger.info(f"Generating embedding for doc: {doc_id} - '{doc_title[:50]}...'")
                    embedding = vectorizer.generate_embedding(doc_title)

                    if embedding:
                        update_document_embedding(db_conn, doc_id, embedding)
                    else:
                        logger.warning(f"Could not generate embedding for doc {doc_id}. Skipping.")

            logger.info("--- Vectorization process finished ---")

        finally:
            db_conn.close()
            logger.info("Database connection closed.")
    else:
        logger.error("Could not establish a database connection. Documents were not saved or vectorized.")

    logger.info("--- Document ingestion pipeline finished ---")

if __name__ == "__main__":
    run_ingestion_pipeline()