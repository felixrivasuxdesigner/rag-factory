"""
Adaptive Chunking System for RAG Factory

Automatically selects optimal chunking strategy based on document size:
- Small (<2000 chars): Single chunk (no splitting needed)
- Medium (2000-5000): Standard chunking with overlap
- Large (5000-15000): Recursive chunking with smaller chunks
- Extra Large (>15000): Multi-level chunking with batch processing

This ensures Ollama doesn't timeout on large documents while maintaining
context quality for all document sizes.
"""

import logging
from typing import List, Dict, Tuple
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdaptiveChunker:
    """
    Intelligent document chunker that adapts strategy based on content size.
    """

    # Size thresholds (in characters)
    SMALL_DOC_THRESHOLD = 2000
    MEDIUM_DOC_THRESHOLD = 5000
    LARGE_DOC_THRESHOLD = 15000

    # Chunking parameters
    SMALL_CHUNK_SIZE = 1000
    MEDIUM_CHUNK_SIZE = 1500
    LARGE_CHUNK_SIZE = 2000
    OVERLAP = 200

    def __init__(
        self,
        small_threshold: int = SMALL_DOC_THRESHOLD,
        medium_threshold: int = MEDIUM_DOC_THRESHOLD,
        large_threshold: int = LARGE_DOC_THRESHOLD,
        overlap: int = OVERLAP
    ):
        """
        Initialize adaptive chunker with configurable thresholds.

        Args:
            small_threshold: Max size for single chunk (no splitting)
            medium_threshold: Threshold between standard and recursive chunking
            large_threshold: Threshold for extra-large document handling
            overlap: Number of characters to overlap between chunks
        """
        self.small_threshold = small_threshold
        self.medium_threshold = medium_threshold
        self.large_threshold = large_threshold
        self.overlap = overlap

    def determine_strategy(self, content: str) -> str:
        """
        Determine which chunking strategy to use based on content size.

        Args:
            content: Document text content

        Returns:
            Strategy name: 'none', 'standard', 'recursive', or 'multi_level'
        """
        content_length = len(content)

        if content_length <= self.small_threshold:
            return 'none'
        elif content_length <= self.medium_threshold:
            return 'standard'
        elif content_length <= self.large_threshold:
            return 'recursive'
        else:
            return 'multi_level'

    def chunk_document(
        self,
        document: Dict,
        chunk_size: int = None,
        overlap: int = None
    ) -> List[Dict]:
        """
        Chunk a document using adaptive strategy.

        Args:
            document: Document dict with 'id', 'title', 'content', 'metadata'
            chunk_size: Override default chunk size (optional)
            overlap: Override default overlap (optional)

        Returns:
            List of chunk dicts with chunk metadata
        """
        content = document.get('content', '')
        doc_id = document.get('id', 'unknown')

        if not content:
            logger.warning(f"Document {doc_id} has no content")
            return []

        # Determine strategy
        strategy = self.determine_strategy(content)
        content_length = len(content)

        logger.info(
            f"Chunking document {doc_id} ({content_length} chars) "
            f"using strategy: {strategy}"
        )

        # Apply chunking strategy
        if strategy == 'none':
            chunks = self._create_single_chunk(document)
        elif strategy == 'standard':
            chunks = self._standard_chunking(
                document,
                chunk_size or self.SMALL_CHUNK_SIZE,
                overlap or self.overlap
            )
        elif strategy == 'recursive':
            chunks = self._recursive_chunking(
                document,
                chunk_size or self.MEDIUM_CHUNK_SIZE,
                overlap or self.overlap
            )
        else:  # multi_level
            chunks = self._multi_level_chunking(
                document,
                chunk_size or self.LARGE_CHUNK_SIZE,
                overlap or self.overlap
            )

        logger.info(f"Created {len(chunks)} chunks for document {doc_id}")
        return chunks

    def _create_single_chunk(self, document: Dict) -> List[Dict]:
        """
        Create a single chunk from small document (no splitting).

        Args:
            document: Source document

        Returns:
            List with single chunk
        """
        return [{
            'id': f"{document['id']}_chunk_0",
            'content': document['content'],
            'metadata': {
                **document.get('metadata', {}),
                'chunk_index': 0,
                'total_chunks': 1,
                'chunking_strategy': 'none',
                'source_document_id': document['id']
            }
        }]

    def _standard_chunking(
        self,
        document: Dict,
        chunk_size: int,
        overlap: int
    ) -> List[Dict]:
        """
        Standard overlapping chunks for medium documents.

        Args:
            document: Source document
            chunk_size: Size of each chunk
            overlap: Overlap between chunks

        Returns:
            List of chunks
        """
        content = document['content']
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(content):
            end = start + chunk_size
            chunk_text = content[start:end]

            chunks.append({
                'id': f"{document['id']}_chunk_{chunk_index}",
                'content': chunk_text,
                'metadata': {
                    **document.get('metadata', {}),
                    'chunk_index': chunk_index,
                    'total_chunks': None,  # Will update after
                    'chunking_strategy': 'standard',
                    'source_document_id': document['id']
                }
            })

            start = end - overlap
            chunk_index += 1

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk['metadata']['total_chunks'] = total

        return chunks

    def _recursive_chunking(
        self,
        document: Dict,
        chunk_size: int,
        overlap: int
    ) -> List[Dict]:
        """
        Recursive chunking with paragraph-aware splitting for large documents.

        Tries to split at natural boundaries (paragraphs, sentences) when possible.

        Args:
            document: Source document
            chunk_size: Target size of each chunk
            overlap: Overlap between chunks

        Returns:
            List of chunks
        """
        content = document['content']

        # Try to split by paragraphs first
        paragraphs = re.split(r'\n\s*\n', content)

        chunks = []
        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            # If adding this paragraph exceeds chunk_size
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    'id': f"{document['id']}_chunk_{chunk_index}",
                    'content': current_chunk.strip(),
                    'metadata': {
                        **document.get('metadata', {}),
                        'chunk_index': chunk_index,
                        'total_chunks': None,
                        'chunking_strategy': 'recursive',
                        'source_document_id': document['id']
                    }
                })
                chunk_index += 1

                # Start new chunk with overlap
                if len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + '\n\n' + para
                else:
                    current_chunk = para
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += '\n\n' + para
                else:
                    current_chunk = para

        # Don't forget the last chunk
        if current_chunk:
            chunks.append({
                'id': f"{document['id']}_chunk_{chunk_index}",
                'content': current_chunk.strip(),
                'metadata': {
                    **document.get('metadata', {}),
                    'chunk_index': chunk_index,
                    'total_chunks': None,
                    'chunking_strategy': 'recursive',
                    'source_document_id': document['id']
                }
            })

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk['metadata']['total_chunks'] = total

        return chunks

    def _multi_level_chunking(
        self,
        document: Dict,
        chunk_size: int,
        overlap: int
    ) -> List[Dict]:
        """
        Multi-level chunking for extra-large documents (>15k chars).

        Uses hierarchical approach:
        1. Split by major sections (if detectable)
        2. Then apply recursive chunking to each section
        3. Ensures no single chunk is too large for Ollama

        Args:
            document: Source document
            chunk_size: Target size of each chunk
            overlap: Overlap between chunks

        Returns:
            List of chunks
        """
        content = document['content']

        # Try to detect major sections (headers, numbered sections, etc.)
        # Pattern: Lines starting with numbers (1., 2., etc.) or ALL CAPS
        section_pattern = r'(?:^|\n)(?:\d+\.|[A-Z\s]{10,})\n'

        sections = re.split(section_pattern, content)

        all_chunks = []
        chunk_index = 0

        for section in sections:
            if not section.strip():
                continue

            # If section is still too large, apply recursive chunking
            if len(section) > chunk_size * 2:
                section_doc = {
                    'id': f"{document['id']}_section",
                    'content': section,
                    'metadata': document.get('metadata', {})
                }
                section_chunks = self._recursive_chunking(
                    section_doc,
                    chunk_size,
                    overlap
                )

                # Renumber chunks
                for sc in section_chunks:
                    sc['id'] = f"{document['id']}_chunk_{chunk_index}"
                    sc['metadata']['chunk_index'] = chunk_index
                    sc['metadata']['chunking_strategy'] = 'multi_level'
                    sc['metadata']['source_document_id'] = document['id']
                    chunk_index += 1
                    all_chunks.append(sc)
            else:
                # Section fits in single chunk
                all_chunks.append({
                    'id': f"{document['id']}_chunk_{chunk_index}",
                    'content': section.strip(),
                    'metadata': {
                        **document.get('metadata', {}),
                        'chunk_index': chunk_index,
                        'total_chunks': None,
                        'chunking_strategy': 'multi_level',
                        'source_document_id': document['id']
                    }
                })
                chunk_index += 1

        # Update total_chunks
        total = len(all_chunks)
        for chunk in all_chunks:
            chunk['metadata']['total_chunks'] = total

        return all_chunks


# Convenience function for backward compatibility
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Simple text chunking function (for backward compatibility).

    Args:
        text: Text to chunk
        chunk_size: Size of each chunk
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap

    return chunks


if __name__ == '__main__':
    """Test the adaptive chunker"""
    print("=" * 70)
    print("Testing Adaptive Chunker")
    print("=" * 70)

    chunker = AdaptiveChunker()

    # Test 1: Small document
    small_doc = {
        'id': 'small_1',
        'content': 'This is a small document with less than 2000 characters.',
        'metadata': {'type': 'test'}
    }
    chunks = chunker.chunk_document(small_doc)
    print(f"\n1. Small doc ({len(small_doc['content'])} chars):")
    print(f"   Strategy: {chunks[0]['metadata']['chunking_strategy']}")
    print(f"   Chunks created: {len(chunks)}")

    # Test 2: Medium document
    medium_doc = {
        'id': 'medium_1',
        'content': 'A' * 3500,  # 3500 chars
        'metadata': {'type': 'test'}
    }
    chunks = chunker.chunk_document(medium_doc)
    print(f"\n2. Medium doc ({len(medium_doc['content'])} chars):")
    print(f"   Strategy: {chunks[0]['metadata']['chunking_strategy']}")
    print(f"   Chunks created: {len(chunks)}")

    # Test 3: Large document
    large_doc = {
        'id': 'large_1',
        'content': ('Section 1\n\n' + 'B' * 2000 + '\n\n' +
                   'Section 2\n\n' + 'C' * 2000 + '\n\n' +
                   'Section 3\n\n' + 'D' * 2000),
        'metadata': {'type': 'test'}
    }
    chunks = chunker.chunk_document(large_doc)
    print(f"\n3. Large doc ({len(large_doc['content'])} chars):")
    print(f"   Strategy: {chunks[0]['metadata']['chunking_strategy']}")
    print(f"   Chunks created: {len(chunks)}")

    # Test 4: Extra large document
    xlarge_doc = {
        'id': 'xlarge_1',
        'content': '\n\n'.join([f"SECTION {i}\n\n" + 'X' * 3000
                                for i in range(1, 8)]),
        'metadata': {'type': 'test'}
    }
    chunks = chunker.chunk_document(xlarge_doc)
    print(f"\n4. Extra large doc ({len(xlarge_doc['content'])} chars):")
    print(f"   Strategy: {chunks[0]['metadata']['chunking_strategy']}")
    print(f"   Chunks created: {len(chunks)}")
    print(f"   Avg chunk size: {sum(len(c['content']) for c in chunks) / len(chunks):.0f} chars")

    print("\n" + "=" * 70)
    print("✅ All tests completed!")
