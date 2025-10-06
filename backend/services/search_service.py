"""
Search service for semantic similarity search using vector embeddings.
Performs cosine similarity search on user's vector databases.
"""

import logging
import psycopg2
from typing import List, Dict, Optional
from services.embedding_service import EmbeddingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SearchService:
    """
    Service for performing semantic similarity search on vector databases.
    """

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """
        Initialize the search service.

        Args:
            embedding_service: Optional EmbeddingService instance (creates new if not provided)
        """
        self.embedding_service = embedding_service or EmbeddingService()
        logger.info("Initialized SearchService")

    def similarity_search(
        self,
        query: str,
        db_config: Dict[str, str],
        table_name: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0
    ) -> List[Dict]:
        """
        Perform semantic similarity search on a vector database.

        Args:
            query (str): The search query text
            db_config (dict): Database connection config (host, port, database, user, password)
            table_name (str): Name of the vector table
            top_k (int): Number of top results to return
            similarity_threshold (float): Minimum similarity score (0.0 to 1.0)

        Returns:
            List[Dict]: List of search results with content, metadata, and similarity scores
        """
        logger.info(f"Performing similarity search for query: '{query[:50]}...'")

        # Generate embedding for the query
        query_embedding = self.embedding_service.generate_embedding(query)

        if not query_embedding:
            logger.error("Failed to generate embedding for query")
            return []

        # Connect to user's database
        try:
            conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password']
            )
            cursor = conn.cursor()

            # Perform cosine similarity search
            # Using <=> operator for cosine distance (pgvector)
            # Similarity = 1 - distance
            query_sql = f"""
                SELECT
                    id,
                    content,
                    metadata,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM {table_name}
                WHERE 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """

            # Convert embedding to string format for pgvector
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

            cursor.execute(
                query_sql,
                (embedding_str, embedding_str, similarity_threshold, embedding_str, top_k)
            )

            results = cursor.fetchall()
            cursor.close()
            conn.close()

            # Format results
            formatted_results = []
            for row in results:
                formatted_results.append({
                    'id': row[0],
                    'content': row[1],
                    'metadata': row[2],
                    'similarity': float(row[3])
                })

            logger.info(f"Found {len(formatted_results)} results above threshold {similarity_threshold}")
            return formatted_results

        except psycopg2.Error as e:
            logger.error(f"Database error during similarity search: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Error during similarity search: {e}", exc_info=True)
            return []

    def search_by_project(
        self,
        query: str,
        project_id: int,
        internal_db_url: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0
    ) -> List[Dict]:
        """
        Perform similarity search using project configuration from internal DB.

        Args:
            query (str): The search query text
            project_id (int): RAG project ID
            internal_db_url (str): Internal database connection URL
            top_k (int): Number of top results to return
            similarity_threshold (float): Minimum similarity score

        Returns:
            List[Dict]: Search results with project metadata
        """
        # Get project configuration
        try:
            conn = psycopg2.connect(internal_db_url)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT target_db_host, target_db_port, target_db_name, "
                "target_db_user, target_db_password, target_table_name "
                "FROM rag_projects WHERE id = %s AND status = 'active'",
                (project_id,)
            )

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if not result:
                logger.error(f"Project {project_id} not found or not active")
                return []

            # Build DB config
            db_config = {
                'host': result[0],
                'port': result[1],
                'database': result[2],
                'user': result[3],
                'password': result[4]
            }
            table_name = result[5]

            # Perform search
            results = self.similarity_search(
                query=query,
                db_config=db_config,
                table_name=table_name,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )

            # Add project context
            for result in results:
                result['project_id'] = project_id

            return results

        except psycopg2.Error as e:
            logger.error(f"Database error fetching project config: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Error in search_by_project: {e}", exc_info=True)
            return []


if __name__ == '__main__':
    """
    Test the search service
    """
    import os

    print("--- Testing Search Service ---\n")

    # Initialize service
    service = SearchService()

    # Test configuration (adjust based on your test data)
    db_config = {
        'host': 'localhost',
        'port': 5433,
        'database': 'rag_factory_db',
        'user': 'user',
        'password': 'password'
    }
    table_name = 'test_vectors'  # Adjust to your test table

    # Test search
    print("Testing similarity search...")
    test_query = "What is artificial intelligence?"

    results = service.similarity_search(
        query=test_query,
        db_config=db_config,
        table_name=table_name,
        top_k=3,
        similarity_threshold=0.3
    )

    print(f"Query: '{test_query}'")
    print(f"Found {len(results)} results:\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. Similarity: {result['similarity']:.4f}")
        print(f"   Content: {result['content'][:100]}...")
        print(f"   ID: {result['id']}")
        print()

    print("--- Search Service test completed ---")
