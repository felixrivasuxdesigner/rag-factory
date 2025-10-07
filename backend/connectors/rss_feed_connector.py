"""
RSS/Atom Feed Connector for blogs, news, and podcasts.
Supports RSS 2.0, RSS 1.0, Atom feeds with auto-discovery.
"""

import logging
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime
from urllib.parse import urljoin

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

from connectors.base_connector import BaseConnector, ConnectorMetadata
from services.rate_limiter import RateLimiter, RateLimitConfig, get_preset_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RSSFeedConnector(BaseConnector):
    """
    Universal RSS/Atom feed connector for blogs, news sites, and podcasts.

    Features:
    - Supports RSS 2.0, RSS 1.0, and Atom formats
    - Auto-discovery of feed URLs from web pages
    - Extracts title, content, summary, author, date
    - Handles enclosures (images, audio, video)
    - Rate limiting support
    - Incremental sync based on publication date
    """

    @classmethod
    def get_metadata(cls) -> ConnectorMetadata:
        """Return connector metadata."""
        return ConnectorMetadata(
            name="RSS/Atom Feed",
            source_type="rss_feed",
            description="Subscribe to RSS/Atom feeds from blogs, news sites, and podcasts",
            version="1.0.0",
            author="RAG Factory",
            category="public",
            supports_incremental_sync=True,  # Feeds have publication dates
            supports_rate_limiting=True,
            required_config_fields=["feed_urls"],
            optional_config_fields=[
                "auto_discover", "max_entries_per_feed", "include_summary",
                "include_content", "user_agent"
            ],
            default_rate_limit_preset="moderate"
        )

    def __init__(self, config: Dict[str, Any], rate_limit_config: Optional[Dict] = None):
        """
        Initialize RSS/Atom feed connector.

        Args:
            config: Configuration dict with:
                - feed_urls (required): List of feed URLs or webpage URLs (for auto-discovery)
                - auto_discover (optional): Auto-discover feeds from webpages (default: True)
                - max_entries_per_feed (optional): Max entries per feed (default: 50)
                - include_summary (optional): Include entry summary (default: True)
                - include_content (optional): Include full content if available (default: True)
                - user_agent (optional): Custom user agent
            rate_limit_config: Rate limiting configuration
        """
        super().__init__(config, rate_limit_config)

        if not FEEDPARSER_AVAILABLE:
            raise ImportError("feedparser is required for RSS/Atom feed parsing")

        if 'feed_urls' not in config:
            raise ValueError("RSSFeedConnector requires 'feed_urls' in config")

        self.feed_urls = config['feed_urls']
        if isinstance(self.feed_urls, str):
            self.feed_urls = [self.feed_urls]

        self.auto_discover = config.get('auto_discover', True)
        self.max_entries_per_feed = config.get('max_entries_per_feed', 50)
        self.include_summary = config.get('include_summary', True)
        self.include_content = config.get('include_content', True)
        self.user_agent = config.get('user_agent', 'RAGFactory-FeedReader/1.0')

        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*'
        })

        # Initialize rate limiter
        if not rate_limit_config:
            rate_limit_config = {'preset': 'moderate'}

        if 'preset' in rate_limit_config:
            rate_config = get_preset_config(rate_limit_config['preset'])
        else:
            rate_config = RateLimitConfig(**rate_limit_config)

        self.rate_limiter = RateLimiter(rate_config, source_name="RSS Feed")

        logger.info(f"✓ RSS Feed connector initialized with {len(self.feed_urls)} URLs")

    def _discover_feeds(self, url: str) -> List[str]:
        """
        Auto-discover feed URLs from a webpage.

        Args:
            url: Webpage URL

        Returns:
            List of discovered feed URLs
        """
        if not BS4_AVAILABLE or not self.auto_discover:
            return [url]

        try:
            logger.info(f"Auto-discovering feeds from {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')
            feed_links = []

            # Look for RSS/Atom link tags
            for link in soup.find_all('link', type=['application/rss+xml', 'application/atom+xml']):
                feed_url = link.get('href')
                if feed_url:
                    # Make absolute URL
                    feed_url = urljoin(url, feed_url)
                    feed_links.append(feed_url)
                    logger.info(f"  Found feed: {feed_url}")

            if feed_links:
                logger.info(f"✓ Discovered {len(feed_links)} feeds from {url}")
                return feed_links
            else:
                logger.warning(f"No feeds discovered, trying URL as direct feed: {url}")
                return [url]

        except Exception as e:
            logger.warning(f"Feed discovery failed for {url}: {e}, trying as direct feed")
            return [url]

    def _parse_entry_date(self, entry) -> Optional[str]:
        """Extract and format entry publication date."""
        # Try different date fields
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']

        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                time_struct = getattr(entry, field)
                try:
                    dt = datetime(*time_struct[:6])
                    return dt.isoformat()
                except Exception:
                    pass

        return None

    def _extract_content(self, entry) -> str:
        """Extract content from feed entry."""
        content_parts = []

        # Try content first (Atom, some RSS)
        if self.include_content and hasattr(entry, 'content') and entry.content:
            for content_item in entry.content:
                if hasattr(content_item, 'value'):
                    content_parts.append(content_item.value)

        # Try summary/description
        if self.include_summary:
            if hasattr(entry, 'summary') and entry.summary:
                content_parts.append(entry.summary)
            elif hasattr(entry, 'description') and entry.description:
                content_parts.append(entry.description)

        # Fallback to title
        if not content_parts and hasattr(entry, 'title'):
            content_parts.append(entry.title)

        # Clean HTML tags if present
        full_content = '\n\n'.join(content_parts)

        # Simple HTML tag removal
        if '<' in full_content and '>' in full_content:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(full_content, 'lxml')
                full_content = soup.get_text(separator='\n', strip=True)
            except Exception:
                # If BS4 fails, keep as is
                pass

        return full_content.strip()

    def fetch_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch entries from RSS/Atom feeds.

        Args:
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            since: ISO date string (YYYY-MM-DD) for incremental sync

        Returns:
            List of documents with id, title, content
        """
        all_documents = []

        # Convert since to datetime if provided
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
            except Exception as e:
                logger.warning(f"Invalid since date format: {since}, ignoring")

        for feed_url in self.feed_urls:
            try:
                # Discover feeds if auto-discovery is enabled
                discovered_feeds = self._discover_feeds(feed_url)

                for actual_feed_url in discovered_feeds:
                    try:
                        # Rate limiting
                        wait_time = self.rate_limiter.wait_if_needed()
                        if wait_time > 0:
                            logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

                        logger.info(f"Fetching feed: {actual_feed_url}")

                        # Parse feed
                        feed = feedparser.parse(actual_feed_url)

                        self.rate_limiter.record_request()
                        self.rate_limiter.record_success()

                        # Check for feed errors
                        if hasattr(feed, 'bozo') and feed.bozo:
                            logger.warning(f"Feed parsing warning for {actual_feed_url}: {feed.bozo_exception}")

                        # Process entries
                        entries_processed = 0
                        for entry in feed.entries[:self.max_entries_per_feed]:
                            # Check date filter
                            entry_date_str = self._parse_entry_date(entry)
                            if since_dt and entry_date_str:
                                try:
                                    entry_dt = datetime.fromisoformat(entry_date_str)
                                    if entry_dt < since_dt:
                                        logger.debug(f"Skipping old entry: {entry.get('title', 'Untitled')}")
                                        continue
                                except Exception:
                                    pass

                            # Extract data
                            doc_id = entry.get('id') or entry.get('link') or f"{actual_feed_url}#{entries_processed}"
                            title = entry.get('title', 'Untitled')
                            content = self._extract_content(entry)
                            link = entry.get('link', '')
                            author = entry.get('author', '')

                            # Create document
                            document = {
                                'id': doc_id,
                                'title': title,
                                'content': content,
                                'metadata': {
                                    'source': 'rss_feed',
                                    'feed_url': actual_feed_url,
                                    'link': link,
                                    'author': author,
                                    'published': entry_date_str,
                                    'feed_title': feed.feed.get('title', ''),
                                }
                            }

                            all_documents.append(document)
                            entries_processed += 1

                        logger.info(f"✓ Fetched {entries_processed} entries from {actual_feed_url}")

                    except Exception as e:
                        logger.error(f"Failed to fetch feed {actual_feed_url}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Failed to process feed URL {feed_url}: {e}")
                continue

        # Apply offset and limit
        total = len(all_documents)
        result = all_documents[offset:offset + limit]

        logger.info(f"✓ Returning {len(result)} of {total} total feed entries")
        return result


if __name__ == '__main__':
    """Test the RSS feed connector"""
    print("=" * 70)
    print("Testing RSS/Atom Feed Connector")
    print("=" * 70)

    # Display connector metadata
    metadata = RSSFeedConnector.get_metadata()
    print(f"\n📋 Connector Metadata:")
    print(f"  Name: {metadata.name}")
    print(f"  Type: {metadata.source_type}")
    print(f"  Category: {metadata.category}")
    print(f"  Version: {metadata.version}")

    # Test with example feed
    print("\n📥 Testing with example RSS feed...\n")

    config = {
        'feed_urls': [
            'https://hnrss.org/newest',  # Hacker News RSS
        ],
        'auto_discover': False,
        'max_entries_per_feed': 5
    }

    connector = RSSFeedConnector(config=config)

    # Test connection
    print("🔌 Testing connection...")
    test_result = connector.test_connection()
    print(f"  Status: {'✅ Success' if test_result['success'] else '❌ Failed'}")
    print(f"  Message: {test_result['message']}")

    # Fetch documents
    print("\n📥 Fetching feed entries...\n")
    docs = connector.fetch_documents(limit=3)

    if docs:
        print(f"✅ Successfully fetched {len(docs)} entries\n")
        for i, doc in enumerate(docs, 1):
            print(f"{'─' * 70}")
            print(f"Entry {i}:")
            print(f"  ID: {doc['id'][:60]}...")
            print(f"  Title: {doc['title'][:80]}")
            print(f"  Author: {doc['metadata'].get('author', 'N/A')}")
            print(f"  Published: {doc['metadata'].get('published', 'N/A')}")
            print(f"  Link: {doc['metadata'].get('link', 'N/A')[:60]}...")
            print(f"  Content: {doc['content'][:150]}...")
            print()
    else:
        print("❌ No entries retrieved")

    print("=" * 70)
