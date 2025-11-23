"""
Gemini File Search service for managing document stores and queries.
Replaces the traditional RAG pipeline (Ollama embeddings + pgvector) with Google's
fully managed File Search solution.

See: https://ai.google.dev/gemini-api/docs/file-search
"""

import logging
import os
import tempfile
from typing import List, Dict, Optional
from datetime import datetime
import mimetypes

from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiFileSearchService:
    """
    Service for interacting with Google Gemini File Search API.

    Features:
    - Create and manage File Search Stores (corpora)
    - Upload documents to stores
    - Query documents using Gemini's built-in RAG
    """

    def __init__(self, api_key: str = None):
        """
        Initialize the Gemini File Search service.

        Args:
            api_key: Google AI API key (defaults to GOOGLE_AI_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get('GOOGLE_AI_API_KEY')

        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY environment variable or api_key parameter is required")

        # Initialize the client
        self.client = genai.Client(api_key=self.api_key)

        logger.info("✓ Initialized GeminiFileSearchService")

    def create_store(self, display_name: str) -> str:
        """
        Create a new File Search Store.

        Args:
            display_name: Human-readable name for the store

        Returns:
            str: The store ID (name)

        Raises:
            Exception: If store creation fails
        """
        try:
            logger.info(f"Creating File Search Store: {display_name}")

            store = self.client.file_search_stores.create(
                config={'display_name': display_name}
            )

            store_id = store.name  # Format: "file_search_stores/abc123"
            logger.info(f"✓ Created File Search Store: {store_id}")

            return store_id

        except Exception as e:
            logger.error(f"Failed to create File Search Store: {e}", exc_info=True)
            raise

    def get_store(self, store_id: str) -> Optional[Dict]:
        """
        Get information about a File Search Store.

        Args:
            store_id: The store ID

        Returns:
            Dict with store information, or None if not found
        """
        try:
            store = self.client.file_search_stores.get(name=store_id)

            return {
                'id': store.name,
                'display_name': store.display_name,
                'create_time': store.create_time,
                'update_time': store.update_time
            }

        except Exception as e:
            logger.error(f"Failed to get File Search Store {store_id}: {e}", exc_info=True)
            return None

    def delete_store(self, store_id: str) -> bool:
        """
        Delete a File Search Store and all its documents.

        Args:
            store_id: The store ID

        Returns:
            bool: True if successful
        """
        try:
            logger.info(f"Deleting File Search Store: {store_id}")

            self.client.file_search_stores.delete(name=store_id)

            logger.info(f"✓ Deleted File Search Store: {store_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete File Search Store {store_id}: {e}", exc_info=True)
            return False

    def upload_document(
        self,
        store_id: str,
        content: str,
        filename: str,
        mime_type: str = None,
        metadata: Dict = None
    ) -> Optional[str]:
        """
        Upload a document to a File Search Store.

        Args:
            store_id: The store ID
            content: Document content (text or binary)
            filename: Original filename (used to infer mime type)
            mime_type: MIME type (auto-detected if not provided)
            metadata: Optional metadata dict

        Returns:
            str: The document ID, or None if failed
        """
        try:
            # Auto-detect MIME type if not provided
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(filename)
                if not mime_type:
                    mime_type = 'text/plain'  # Default to text

            logger.info(f"Uploading document: {filename} ({mime_type}) to store {store_id}")

            # Create a temporary file for upload
            with tempfile.NamedTemporaryFile(mode='w' if isinstance(content, str) else 'wb',
                                            suffix=os.path.splitext(filename)[1],
                                            delete=False) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name

            try:
                # Upload to File Search Store
                # Note: The API handles chunking, embedding, and indexing automatically
                uploaded_file = self.client.file_search_stores.upload_to_file_search_store(
                    store_name=store_id,
                    path=temp_path,
                    config={
                        'display_name': filename,
                        'mime_type': mime_type
                    }
                )

                document_id = uploaded_file.name  # Format: "file_search_stores/abc/documents/xyz"
                logger.info(f"✓ Uploaded document: {document_id}")

                return document_id

            finally:
                # Clean up temp file
                os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Failed to upload document {filename}: {e}", exc_info=True)
            return None

    def upload_text_document(
        self,
        store_id: str,
        title: str,
        content: str,
        document_id: str = None,
        metadata: Dict = None
    ) -> Optional[str]:
        """
        Upload a text document to a File Search Store.
        Convenience method for text-only documents.

        Args:
            store_id: The store ID
            title: Document title
            content: Document text content
            document_id: Optional ID (used for tracking)
            metadata: Optional metadata dict

        Returns:
            str: The Gemini document ID, or None if failed
        """
        # Create a safe filename from title
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
        filename = f"{safe_title[:50]}.txt"

        return self.upload_document(
            store_id=store_id,
            content=content,
            filename=filename,
            mime_type='text/plain',
            metadata=metadata
        )

    def query(
        self,
        store_id: str,
        question: str,
        model: str = "gemini-2.0-flash-exp",
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Dict:
        """
        Query documents in a File Search Store using Gemini.

        Args:
            store_id: The store ID to query
            question: The question to answer
            model: Gemini model to use (default: gemini-2.0-flash-exp)
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0.0 = deterministic, 1.0 = creative)

        Returns:
            Dict with 'answer' and 'sources' (if available)
        """
        try:
            logger.info(f"Querying File Search Store {store_id} with question: {question[:100]}...")

            # Create a File Search tool pointing to this store
            file_search_tool = types.Tool(
                file_search=types.FileSearchTool(
                    file_search_stores=[store_id]
                )
            )

            # Generate content with File Search
            response = self.client.models.generate_content(
                model=model,
                contents=question,
                config=types.GenerateContentConfig(
                    tools=[file_search_tool],
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            )

            # Extract answer
            answer = response.text if hasattr(response, 'text') else str(response)

            # Extract sources if available
            # Note: Gemini File Search may include citations in the response
            sources = []
            if hasattr(response, 'grounding_metadata'):
                for chunk in response.grounding_metadata.grounding_chunks:
                    sources.append({
                        'content': chunk.retrieved_context.text if hasattr(chunk, 'retrieved_context') else '',
                        'uri': chunk.retrieved_context.uri if hasattr(chunk, 'retrieved_context') else ''
                    })

            logger.info(f"✓ Query completed. Answer length: {len(answer)} chars, Sources: {len(sources)}")

            return {
                'answer': answer,
                'sources': sources,
                'model': model
            }

        except Exception as e:
            logger.error(f"Failed to query File Search Store: {e}", exc_info=True)
            return {
                'answer': f"Error: {str(e)}",
                'sources': [],
                'model': model
            }

    def list_stores(self) -> List[Dict]:
        """
        List all File Search Stores.

        Returns:
            List of store information dicts
        """
        try:
            stores = self.client.file_search_stores.list()

            result = []
            for store in stores:
                result.append({
                    'id': store.name,
                    'display_name': store.display_name,
                    'create_time': store.create_time,
                    'update_time': store.update_time
                })

            logger.info(f"✓ Listed {len(result)} File Search Stores")
            return result

        except Exception as e:
            logger.error(f"Failed to list File Search Stores: {e}", exc_info=True)
            return []

    def health_check(self) -> bool:
        """
        Check if the Gemini API is accessible.

        Returns:
            bool: True if healthy
        """
        try:
            # Try to list stores as a health check
            self.client.file_search_stores.list(page_size=1)
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


if __name__ == '__main__':
    """
    Test the Gemini File Search service
    """
    print("--- Testing Gemini File Search Service ---\n")

    # Check for API key
    api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if not api_key:
        print("✗ GOOGLE_AI_API_KEY environment variable not set")
        print("Get your API key at: https://aistudio.google.com/apikey")
        exit(1)

    # Initialize service
    print("Initializing service...")
    service = GeminiFileSearchService(api_key=api_key)

    # Health check
    print("\nChecking API health...")
    if service.health_check():
        print("✓ Gemini API is accessible\n")
    else:
        print("✗ Gemini API is not accessible")
        exit(1)

    # Create a test store
    print("Creating test File Search Store...")
    test_store_name = f"test_store_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    store_id = service.create_store(display_name=test_store_name)
    print(f"✓ Created store: {store_id}\n")

    try:
        # Upload test documents
        print("Uploading test documents...")

        test_docs = [
            {
                'title': 'Python Basics',
                'content': 'Python is a high-level programming language. It emphasizes code readability and simplicity.'
            },
            {
                'title': 'Machine Learning',
                'content': 'Machine learning is a subset of artificial intelligence that enables systems to learn from data.'
            },
            {
                'title': 'Web Development',
                'content': 'Web development involves creating websites and web applications using HTML, CSS, and JavaScript.'
            }
        ]

        uploaded_count = 0
        for doc in test_docs:
            doc_id = service.upload_text_document(
                store_id=store_id,
                title=doc['title'],
                content=doc['content']
            )
            if doc_id:
                uploaded_count += 1
                print(f"  ✓ Uploaded: {doc['title']}")

        print(f"\n✓ Uploaded {uploaded_count}/{len(test_docs)} documents\n")

        # Wait a moment for indexing (Gemini processes async)
        print("Waiting for indexing to complete...")
        import time
        time.sleep(5)
        print("✓ Ready\n")

        # Test query
        print("Testing query...")
        question = "What is Python?"
        result = service.query(
            store_id=store_id,
            question=question,
            model="gemini-2.0-flash-exp"
        )

        print(f"\nQuestion: {question}")
        print(f"Answer: {result['answer']}")
        print(f"Model: {result['model']}")
        print(f"Sources: {len(result['sources'])} found\n")

        # List stores
        print("Listing all stores...")
        stores = service.list_stores()
        print(f"✓ Found {len(stores)} total stores")
        for store in stores[:3]:  # Show first 3
            print(f"  - {store['display_name']} ({store['id']})")
        print()

    finally:
        # Cleanup
        print("Cleaning up test store...")
        if service.delete_store(store_id):
            print("✓ Test store deleted")
        else:
            print(f"⚠ Failed to delete test store: {store_id}")
            print("  You may need to delete it manually at: https://aistudio.google.com")

    print("\n--- Gemini File Search Service test completed ---")
