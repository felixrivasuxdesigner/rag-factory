"""
Document Content Cache Service

Manages caching of downloaded document content to avoid re-downloading
on job restarts or subsequent runs. This significantly improves performance
for large document sets.

Usage:
    from services.content_cache_service import ContentCacheService

    cache = ContentCacheService(db_connection)

    # Check if document is cached
    cached = cache.get_cached_content(source_id, external_id)
    if cached:
        content = cached['content']
    else:
        # Download from source
        content = download_from_source(url)
        cache.save_to_cache(source_id, external_id, content, metadata)
"""

import logging
import hashlib
import psycopg2
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentCacheService:
    """
    Service for caching downloaded document content.
    """

    def __init__(self, db_connection):
        """
        Initialize the cache service.

        Args:
            db_connection: psycopg2 connection to internal database
        """
        self.conn = db_connection

    def get_cached_content(self, source_id: int, external_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached content for a document.

        Args:
            source_id: ID of the data source
            external_id: External ID of the document (e.g., BCN norm ID)

        Returns:
            Dictionary with cached data if found, None otherwise
            {
                'id': int,
                'content': str,
                'title': str,
                'content_hash': str,
                'content_size': int,
                'source_url': str,
                'source_metadata': dict,
                'downloaded_at': datetime,
                'access_count': int
            }
        """
        try:
            with self.conn.cursor() as cur:
                query = """
                    UPDATE documents_content_cache
                    SET last_accessed_at = CURRENT_TIMESTAMP,
                        access_count = access_count + 1
                    WHERE source_id = %s AND external_id = %s
                    RETURNING id, external_id, content_hash, title, content,
                              content_size, source_url, source_metadata,
                              downloaded_at, access_count;
                """
                cur.execute(query, (source_id, external_id))
                row = cur.fetchone()

                if row:
                    self.conn.commit()
                    logger.debug(f"Cache HIT for document {external_id} (source {source_id})")
                    return {
                        'id': row[0],
                        'external_id': row[1],
                        'content_hash': row[2],
                        'title': row[3],
                        'content': row[4],
                        'content_size': row[5],
                        'source_url': row[6],
                        'source_metadata': row[7],
                        'downloaded_at': row[8],
                        'access_count': row[9]
                    }
                else:
                    logger.debug(f"Cache MISS for document {external_id} (source {source_id})")
                    return None

        except psycopg2.Error as e:
            logger.error(f"Error retrieving from cache: {e}")
            self.conn.rollback()
            return None

    def save_to_cache(
        self,
        source_id: int,
        external_id: str,
        content: str,
        title: str = None,
        source_url: str = None,
        source_metadata: Dict = None
    ) -> bool:
        """
        Save document content to cache.

        Args:
            source_id: ID of the data source
            external_id: External ID of the document
            content: Full document content
            title: Document title (optional)
            source_url: Original download URL (optional)
            source_metadata: Additional metadata (optional)

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Compute content hash
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            content_size = len(content.encode('utf-8'))

            with self.conn.cursor() as cur:
                query = """
                    INSERT INTO documents_content_cache
                    (source_id, external_id, content_hash, title, content,
                     content_size, source_url, source_metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_id, external_id)
                    DO UPDATE SET
                        content = EXCLUDED.content,
                        content_hash = EXCLUDED.content_hash,
                        content_size = EXCLUDED.content_size,
                        title = EXCLUDED.title,
                        source_url = EXCLUDED.source_url,
                        source_metadata = EXCLUDED.source_metadata,
                        downloaded_at = CURRENT_TIMESTAMP,
                        last_accessed_at = CURRENT_TIMESTAMP,
                        access_count = 1
                    RETURNING id;
                """

                import json
                metadata_json = json.dumps(source_metadata) if source_metadata else None

                cur.execute(query, (
                    source_id, external_id, content_hash, title, content,
                    content_size, source_url, metadata_json
                ))

                cache_id = cur.fetchone()[0]
                self.conn.commit()

                logger.debug(f"Cached document {external_id} (source {source_id}, cache_id {cache_id}, size {content_size} bytes)")
                return True

        except psycopg2.Error as e:
            logger.error(f"Error saving to cache: {e}")
            self.conn.rollback()
            return False

    def get_cache_stats(self, source_id: int) -> Dict[str, Any]:
        """
        Get cache statistics for a data source.

        Args:
            source_id: ID of the data source

        Returns:
            Dictionary with cache stats
        """
        try:
            with self.conn.cursor() as cur:
                query = """
                    SELECT
                        COUNT(*) as total_cached,
                        SUM(content_size) as total_size,
                        AVG(content_size) as avg_size,
                        SUM(access_count) as total_accesses,
                        MIN(downloaded_at) as first_download,
                        MAX(downloaded_at) as last_download
                    FROM documents_content_cache
                    WHERE source_id = %s;
                """
                cur.execute(query, (source_id,))
                row = cur.fetchone()

                return {
                    'total_cached': row[0] or 0,
                    'total_size_bytes': row[1] or 0,
                    'avg_size_bytes': float(row[2]) if row[2] else 0,
                    'total_accesses': row[3] or 0,
                    'first_download': row[4],
                    'last_download': row[5]
                }

        except psycopg2.Error as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

    def clear_old_cache(self, source_id: int, days: int = 30) -> int:
        """
        Clear cache entries older than specified days that haven't been accessed.

        Args:
            source_id: ID of the data source
            days: Number of days (default 30)

        Returns:
            Number of entries deleted
        """
        try:
            with self.conn.cursor() as cur:
                query = """
                    DELETE FROM documents_content_cache
                    WHERE source_id = %s
                    AND last_accessed_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                    RETURNING id;
                """
                cur.execute(query, (source_id, days))
                deleted_count = cur.rowcount
                self.conn.commit()

                logger.info(f"Cleared {deleted_count} old cache entries for source {source_id}")
                return deleted_count

        except psycopg2.Error as e:
            logger.error(f"Error clearing old cache: {e}")
            self.conn.rollback()
            return 0


if __name__ == '__main__':
    # Test the cache service
    import os
    from core.database import get_db_connection

    print("--- Testing Content Cache Service ---\n")

    conn = get_db_connection()
    cache = ContentCacheService(conn)

    # Test saving to cache
    print("1. Testing save_to_cache...")
    success = cache.save_to_cache(
        source_id=17,
        external_id="test_doc_123",
        content="This is test content for caching",
        title="Test Document",
        source_url="http://example.com/test",
        source_metadata={"type": "test", "version": 1}
    )
    print(f"   Save result: {'✓ Success' if success else '✗ Failed'}\n")

    # Test retrieving from cache
    print("2. Testing get_cached_content...")
    cached = cache.get_cached_content(17, "test_doc_123")
    if cached:
        print(f"   ✓ Retrieved from cache:")
        print(f"     - Title: {cached['title']}")
        print(f"     - Content size: {cached['content_size']} bytes")
        print(f"     - Access count: {cached['access_count']}")
    else:
        print("   ✗ Not found in cache\n")

    # Test cache stats
    print("\n3. Testing get_cache_stats...")
    stats = cache.get_cache_stats(17)
    print(f"   Cache statistics:")
    print(f"     - Total cached: {stats['total_cached']}")
    print(f"     - Total size: {stats['total_size_bytes']} bytes")
    print(f"     - Total accesses: {stats['total_accesses']}")

    # Cleanup test data
    print("\n4. Cleaning up test data...")
    with conn.cursor() as cur:
        cur.execute("DELETE FROM documents_content_cache WHERE external_id = 'test_doc_123'")
        conn.commit()
    print("   ✓ Test data cleaned up")

    conn.close()
    print("\n--- Test completed successfully ---")
