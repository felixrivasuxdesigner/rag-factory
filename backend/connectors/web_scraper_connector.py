"""
Web Scraper Connector for extracting content from web pages.
Supports configurable CSS selectors and respects robots.txt.
"""

import logging
import re
import requests
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

from connectors.base_connector import BaseConnector, ConnectorMetadata
from services.rate_limiter import RateLimiter, RateLimitConfig, get_preset_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebScraperConnector(BaseConnector):
    """
    Universal web scraper connector for extracting content from web pages.

    Features:
    - CSS selector support for targeted content extraction
    - HTML to clean text conversion
    - Robots.txt respect
    - Configurable element removal (nav, footer, ads, etc.)
    - Rate limiting per domain
    - Custom user agent support
    """

    DEFAULT_USER_AGENT = "RAGFactory-Bot/1.0 (+https://github.com/yourusername/rag-factory)"

    @classmethod
    def get_metadata(cls) -> ConnectorMetadata:
        """Return connector metadata."""
        return ConnectorMetadata(
            name="Web Scraper",
            source_type="web_scraper",
            description="Scrape content from web pages using CSS selectors",
            version="1.0.0",
            author="RAG Factory",
            category="public",
            supports_incremental_sync=False,  # Web pages don't have reliable timestamps
            supports_rate_limiting=True,
            required_config_fields=["urls"],
            optional_config_fields=[
                "content_selector", "title_selector", "remove_selectors",
                "respect_robots_txt", "user_agent", "max_pages"
            ],
            default_rate_limit_preset="moderate"
        )

    def __init__(self, config: Dict[str, Any], rate_limit_config: Optional[Dict] = None):
        """
        Initialize web scraper connector.

        Args:
            config: Configuration dict with:
                - urls (required): List of URLs to scrape
                - content_selector (optional): CSS selector for main content (default: "body")
                - title_selector (optional): CSS selector for title (default: "title")
                - remove_selectors (optional): List of selectors to remove (default: ["nav", "footer", "script", "style"])
                - respect_robots_txt (optional): Check robots.txt (default: True)
                - user_agent (optional): Custom user agent string
                - max_pages (optional): Maximum number of pages to scrape (default: 10)
            rate_limit_config: Rate limiting configuration (default: moderate preset)
        """
        super().__init__(config, rate_limit_config)

        if not BS4_AVAILABLE:
            raise ImportError("BeautifulSoup4 is required for web scraping")

        if 'urls' not in config:
            raise ValueError("WebScraperConnector requires 'urls' in config")

        self.urls = config['urls']
        if isinstance(self.urls, str):
            self.urls = [self.urls]

        self.content_selector = config.get('content_selector', 'body')
        self.title_selector = config.get('title_selector', 'title')
        self.remove_selectors = config.get('remove_selectors', ['nav', 'footer', 'script', 'style', 'aside'])
        self.respect_robots_txt = config.get('respect_robots_txt', True)
        self.user_agent = config.get('user_agent', self.DEFAULT_USER_AGENT)
        self.max_pages = config.get('max_pages', 10)

        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

        # Initialize rate limiter
        if not rate_limit_config:
            rate_limit_config = {'preset': 'moderate'}

        if 'preset' in rate_limit_config:
            rate_config = get_preset_config(rate_limit_config['preset'])
        else:
            rate_config = RateLimitConfig(**rate_limit_config)

        self.rate_limiter = RateLimiter(rate_config, source_name="Web Scraper")

        # Robots.txt parser cache (per domain)
        self.robots_parsers: Dict[str, RobotFileParser] = {}

        logger.info(f"✓ Web Scraper connector initialized with {len(self.urls)} URLs")

    def _get_robots_parser(self, url: str) -> Optional[RobotFileParser]:
        """Get or create robots.txt parser for a domain."""
        if not self.respect_robots_txt:
            return None

        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain not in self.robots_parsers:
            robots_url = urljoin(domain, '/robots.txt')
            parser = RobotFileParser()
            parser.set_url(robots_url)

            try:
                parser.read()
                self.robots_parsers[domain] = parser
                logger.debug(f"Loaded robots.txt from {robots_url}")
            except Exception as e:
                logger.warning(f"Failed to load robots.txt from {robots_url}: {e}")
                # Create permissive parser if robots.txt fails
                self.robots_parsers[domain] = None

        return self.robots_parsers[domain]

    def _can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        if not self.respect_robots_txt:
            return True

        parser = self._get_robots_parser(url)
        if parser is None:
            return True  # If no robots.txt or failed to load, allow

        can_fetch = parser.can_fetch(self.user_agent, url)
        if not can_fetch:
            logger.warning(f"robots.txt disallows fetching: {url}")

        return can_fetch

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove multiple newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)

        return text.strip()

    def _extract_content(self, html: str, url: str) -> Dict[str, str]:
        """Extract title and content from HTML using configured selectors."""
        soup = BeautifulSoup(html, 'lxml')

        # Remove unwanted elements
        for selector in self.remove_selectors:
            for element in soup.select(selector):
                element.decompose()

        # Extract title
        title_element = soup.select_one(self.title_selector)
        if title_element:
            title = title_element.get_text(strip=True)
        else:
            # Fallback to URL
            title = urlparse(url).path.split('/')[-1] or url

        # Extract content
        content_element = soup.select_one(self.content_selector)
        if content_element:
            # Get text with some structure preserved
            content = content_element.get_text(separator='\n', strip=True)
        else:
            # Fallback to full body
            content = soup.get_text(separator='\n', strip=True)

        # Clean text
        title = self._clean_text(title)
        content = self._clean_text(content)

        return {
            'title': title,
            'content': content
        }

    def fetch_documents(
        self,
        limit: int = 10,
        offset: int = 0,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape web pages and extract documents.

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            since: Not used (web scraping doesn't support incremental sync)

        Returns:
            List of documents with id, title, content
        """
        documents = []

        # Apply offset and limit to URLs
        urls_to_scrape = self.urls[offset:offset + limit]
        urls_to_scrape = urls_to_scrape[:self.max_pages]

        for url in urls_to_scrape:
            try:
                # Check robots.txt
                if not self._can_fetch(url):
                    logger.warning(f"Skipping URL (robots.txt): {url}")
                    continue

                # Rate limiting
                wait_time = self.rate_limiter.wait_if_needed()
                if wait_time > 0:
                    logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

                # Fetch page
                logger.info(f"Fetching: {url}")
                response = self.session.get(url, timeout=30)

                self.rate_limiter.record_request()

                # Handle 429
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    retry_after_int = int(retry_after) if retry_after else None
                    self.rate_limiter.record_429_response(retry_after_int)
                    logger.warning(f"⚠️  429 Rate limit hit for {url}")
                    continue

                # Check response
                response.raise_for_status()

                # Record success
                self.rate_limiter.record_success()

                # Check content type
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type:
                    logger.warning(f"Skipping non-HTML content: {url} ({content_type})")
                    continue

                # Extract content
                extracted = self._extract_content(response.text, url)

                # Create document
                document = {
                    'id': url,
                    'title': extracted['title'],
                    'content': extracted['content'],
                    'metadata': {
                        'source': 'web_scraper',
                        'url': url,
                        'status_code': response.status_code,
                        'content_type': content_type,
                        'content_selector': self.content_selector,
                        'title_selector': self.title_selector
                    }
                }

                documents.append(document)
                logger.info(f"✓ Scraped {url}: {len(extracted['content'])} characters")

            except requests.RequestException as e:
                logger.error(f"Failed to fetch {url}: {e}")
                continue
            except Exception as e:
                logger.error(f"Failed to process {url}: {e}", exc_info=True)
                continue

        logger.info(f"✓ Scraped {len(documents)} pages successfully")
        return documents


if __name__ == '__main__':
    """Test the web scraper connector"""
    print("=" * 70)
    print("Testing Web Scraper Connector")
    print("=" * 70)

    # Display connector metadata
    metadata = WebScraperConnector.get_metadata()
    print(f"\n📋 Connector Metadata:")
    print(f"  Name: {metadata.name}")
    print(f"  Type: {metadata.source_type}")
    print(f"  Category: {metadata.category}")
    print(f"  Version: {metadata.version}")

    # Test with example URLs
    print("\n📥 Testing with example URLs...\n")

    config = {
        'urls': [
            'https://example.com',
        ],
        'content_selector': 'body',
        'title_selector': 'title',
        'remove_selectors': ['script', 'style'],
        'respect_robots_txt': True
    }

    connector = WebScraperConnector(config=config)

    # Test connection
    print("🔌 Testing connection...")
    test_result = connector.test_connection()
    print(f"  Status: {'✅ Success' if test_result['success'] else '❌ Failed'}")
    print(f"  Message: {test_result['message']}")

    # Fetch documents
    print("\n📥 Fetching web pages...\n")
    docs = connector.fetch_documents(limit=1)

    if docs:
        print(f"✅ Successfully scraped {len(docs)} pages\n")
        for i, doc in enumerate(docs, 1):
            print(f"{'─' * 70}")
            print(f"Page {i}:")
            print(f"  URL: {doc['id']}")
            print(f"  Title: {doc['title']}")
            print(f"  Content Length: {len(doc['content'])} characters")
            print(f"  Preview: {doc['content'][:200]}...")
            print()
    else:
        print("❌ No pages scraped")

    print("=" * 70)
