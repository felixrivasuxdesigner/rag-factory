"""
Embedding service for generating vector embeddings using Ollama.
Supports multiple embedding models and batching for performance.
"""

import logging
import requests
import hashlib
from typing import List, Dict, Optional
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings using Ollama's embedding models.
    """

    def __init__(
        self,
        model: str = "mxbai-embed-large",
        ollama_host: str = None,
        embedding_dimension: int = 1024
    ):
        """
        Initialize the embedding service.

        Args:
            model (str): The Ollama embedding model to use
            ollama_host (str): Ollama server host (default: from env or localhost)
            embedding_dimension (int): Dimension of the embeddings
        """
        self.model = model
        self.embedding_dimension = embedding_dimension

        # Get Ollama host from env or use default
        if ollama_host is None:
            ollama_host = os.environ.get('OLLAMA_HOST', 'localhost')

        # Build the full URL
        if not ollama_host.startswith('http'):
            self.ollama_url = f"http://{ollama_host}:11434"
        else:
            self.ollama_url = ollama_host

        self.embed_endpoint = f"{self.ollama_url}/api/embeddings"

        logger.info(f"Initialized EmbeddingService with model={model}, ollama_url={self.ollama_url}")

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate an embedding vector for a single text.

        Args:
            text (str): The text to embed

        Returns:
            List[float]: The embedding vector, or None if failed
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None

        try:
            payload = {
                "model": self.model,
                "prompt": text
            }

            response = requests.post(
                self.embed_endpoint,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                embedding = result.get('embedding')

                if embedding and len(embedding) == self.embedding_dimension:
                    return embedding
                else:
                    logger.error(f"Unexpected embedding dimension: expected {self.embedding_dimension}, got {len(embedding) if embedding else 0}")
                    return None
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to generate embedding: {e}", exc_info=True)
            return None

    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts (List[str]): List of texts to embed

        Returns:
            List[Optional[List[float]]]: List of embedding vectors (None for failed items)
        """
        embeddings = []

        for i, text in enumerate(texts):
            if i > 0 and i % 10 == 0:
                logger.info(f"Generated {i}/{len(texts)} embeddings...")

            embedding = self.generate_embedding(text)
            embeddings.append(embedding)

        logger.info(f"Completed batch: {len([e for e in embeddings if e is not None])}/{len(texts)} successful")
        return embeddings

    def compute_content_hash(self, text: str) -> str:
        """
        Compute a SHA-256 hash of the text content for deduplication.

        Args:
            text (str): The text content

        Returns:
            str: Hexadecimal hash string
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Dict[str, any]]:
        """
        Split text into overlapping chunks for embedding.

        Args:
            text (str): The text to chunk
            chunk_size (int): Maximum characters per chunk
            chunk_overlap (int): Overlap between chunks

        Returns:
            List[Dict]: List of chunks with metadata
        """
        if not text or len(text) <= chunk_size:
            return [{
                'text': text,
                'chunk_index': 0,
                'start_pos': 0,
                'end_pos': len(text) if text else 0
            }]

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings near the chunk boundary
                sentence_endings = ['. ', '.\n', '! ', '!\n', '? ', '?\n']
                best_break = -1

                for ending in sentence_endings:
                    pos = text.rfind(ending, start, end)
                    if pos > best_break:
                        best_break = pos + len(ending)

                if best_break > start:
                    end = best_break

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    'text': chunk_text,
                    'chunk_index': chunk_index,
                    'start_pos': start,
                    'end_pos': end,
                    'content_hash': self.compute_content_hash(chunk_text)
                })
                chunk_index += 1

            # Move start position with overlap
            start = end - chunk_overlap if end < len(text) else end

        logger.info(f"Chunked text into {len(chunks)} chunks (size={chunk_size}, overlap={chunk_overlap})")
        return chunks

    def health_check(self) -> bool:
        """
        Check if Ollama service is available.

        Returns:
            bool: True if service is healthy
        """
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False


if __name__ == '__main__':
    """
    Test the embedding service
    """
    print("--- Testing Embedding Service ---\n")

    # Initialize service
    service = EmbeddingService(model="mxbai-embed-large")

    # Health check
    print("Checking Ollama service health...")
    if service.health_check():
        print("✓ Ollama service is healthy\n")
    else:
        print("✗ Ollama service is not available")
        print("Make sure Ollama is running: docker-compose up ollama")
        exit(1)

    # Test single embedding
    print("Testing single embedding...")
    test_text = "This is a test document about machine learning and artificial intelligence."
    embedding = service.generate_embedding(test_text)

    if embedding:
        print(f"✓ Generated embedding with dimension: {len(embedding)}")
        print(f"  First 5 values: {embedding[:5]}")
        print(f"  Content hash: {service.compute_content_hash(test_text)}\n")
    else:
        print("✗ Failed to generate embedding\n")

    # Test text chunking
    print("Testing text chunking...")
    long_text = """
    Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to the natural intelligence displayed by humans and animals.
    Leading AI textbooks define the field as the study of "intelligent agents": any device that perceives its environment and takes actions that maximize its chance of successfully achieving its goals.
    Colloquially, the term "artificial intelligence" is often used to describe machines that mimic "cognitive" functions that humans associate with the human mind, such as "learning" and "problem solving".
    """
    chunks = service.chunk_text(long_text, chunk_size=150, chunk_overlap=30)
    print(f"✓ Created {len(chunks)} chunks from text")
    for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
        print(f"  Chunk {i}: {chunk['text'][:50]}... (pos {chunk['start_pos']}-{chunk['end_pos']})")
    print()

    # Test batch embeddings
    print("Testing batch embeddings...")
    test_texts = [
        "Machine learning is a subset of AI",
        "Deep learning uses neural networks",
        "Natural language processing enables text understanding"
    ]
    batch_embeddings = service.generate_embeddings_batch(test_texts)
    successful = len([e for e in batch_embeddings if e is not None])
    print(f"✓ Generated {successful}/{len(test_texts)} embeddings in batch\n")

    print("--- Embedding Service test completed ---")
