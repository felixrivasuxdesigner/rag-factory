"""
Generic REST API connector for any JSON REST API.
This is a universal connector that can be configured for any REST API endpoint.
"""

import logging
import requests
from typing import List, Dict, Optional, Any
from services.rate_limiter import RateLimiter, RateLimitConfig, get_preset_config
from connectors.base_connector import BaseConnector, ConnectorMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GenericRESTAPIConnector(BaseConnector):
    """
    Universal REST API connector for any JSON-based API.

    Examples of compatible APIs:
    - GitHub API
    - Congress.gov API
    - OpenAI API
    - Any custom REST API that returns JSON
    """

    @classmethod
    def get_metadata(cls) -> ConnectorMetadata:
        """Return connector metadata."""
        return ConnectorMetadata(
            name="Generic REST API",
            source_type="rest_api",
            description="Universal connector for any JSON REST API (GitHub, custom APIs, etc.)",
            version="1.0.0",
            author="RAG Factory",
            category="public",
            supports_incremental_sync=True,
            supports_rate_limiting=True,
            required_config_fields=["base_url", "endpoint"],
            optional_config_fields=[
                "method", "headers", "auth_type", "api_key", "api_key_header",
                "response_data_path", "id_field", "content_field", "title_field",
                "date_field", "limit_param", "offset_param", "date_param"
            ],
            default_rate_limit_preset=None
        )

    def __init__(self, config: Dict[str, Any], rate_limit_config: Optional[Dict] = None):
        """
        Initialize generic REST API connector.

        Args:
            config: Configuration dict with:
                - base_url (required): API base URL (e.g., "https://api.github.com")
                - endpoint (required): API endpoint path (e.g., "/repos/{owner}/{repo}/issues")
                - method (optional): HTTP method (default: "GET")
                - headers (optional): Additional headers dict
                - auth_type (optional): "api_key", "bearer", or None
                - api_key (optional): API key value
                - api_key_header (optional): Header name for API key (default: "Authorization")
                - response_data_path (optional): JSON path to data array (e.g., "items" or "data.results")
                - id_field (optional): JSON field name for document ID (default: "id")
                - content_field (optional): JSON field for content (default: "body")
                - title_field (optional): JSON field for title (default: "title")
                - date_field (optional): JSON field for date (default: "created_at")
                - limit_param (optional): URL param name for limit (default: "limit")
                - offset_param (optional): URL param name for offset (default: "offset")
                - date_param (optional): URL param name for date filter (default: "since")
            rate_limit_config: Optional rate limiting configuration
        """
        super().__init__(config, rate_limit_config)

        # Extract config
        self.base_url = config['base_url'].rstrip('/')
        self.endpoint = config['endpoint']
        self.method = config.get('method', 'GET').upper()
        self.headers = config.get('headers', {})
        self.auth_type = config.get('auth_type')
        self.api_key = config.get('api_key')
        self.api_key_header = config.get('api_key_header', 'Authorization')

        # Response parsing config
        self.response_data_path = config.get('response_data_path', '').split('.') if config.get('response_data_path') else []
        self.id_field = config.get('id_field', 'id')
        self.content_field = config.get('content_field', 'body')
        self.title_field = config.get('title_field', 'title')
        self.date_field = config.get('date_field', 'created_at')

        # URL parameter names
        self.limit_param = config.get('limit_param', 'limit')
        self.offset_param = config.get('offset_param', 'offset')
        self.date_param = config.get('date_param', 'since')

        # Setup session
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Add authentication
        if self.auth_type == 'api_key' and self.api_key:
            self.session.headers[self.api_key_header] = self.api_key
        elif self.auth_type == 'bearer' and self.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'

        # Initialize rate limiter if configured
        self.rate_limiter = None
        if rate_limit_config:
            if 'preset' in rate_limit_config:
                rate_config = get_preset_config(rate_limit_config['preset'])
            else:
                rate_config = RateLimitConfig(**rate_limit_config)
            self.rate_limiter = RateLimiter(rate_config, source_name=f"REST API: {self.base_url}")

    def _extract_data_from_response(self, response_json: Any) -> List[Dict]:
        """
        Extract data array from JSON response using configured path.

        Args:
            response_json: Parsed JSON response

        Returns:
            List of data items
        """
        data = response_json

        # Navigate through response_data_path
        for key in self.response_data_path:
            if key and isinstance(data, dict):
                data = data.get(key, [])

        # If data is not a list, wrap it
        if not isinstance(data, list):
            data = [data] if data else []

        return data

    def fetch_documents(
        self,
        limit: int = 10,
        offset: int = 0,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch documents from REST API.

        Args:
            limit: Maximum number of documents to fetch
            offset: Number of documents to skip
            since: ISO date string (YYYY-MM-DD) for incremental sync

        Returns:
            List of documents with id, title, content
        """
        # Build URL with parameters
        url = f"{self.base_url}{self.endpoint}"
        params = {
            self.limit_param: limit,
            self.offset_param: offset
        }

        if since:
            params[self.date_param] = since

        # Execute request with rate limiting
        if self.rate_limiter:
            wait_time = self.rate_limiter.wait_if_needed()
            if wait_time > 0:
                logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

        logger.info(f"Fetching from {url}")

        try:
            response = self.session.request(self.method, url, params=params, timeout=30)

            if self.rate_limiter:
                self.rate_limiter.record_request()

                # Handle 429
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    retry_after_int = int(retry_after) if retry_after else None
                    self.rate_limiter.record_429_response(retry_after_int)
                    logger.warning(f"⚠️  429 Rate limit hit")
                    return []

                # Reset on success
                if response.status_code == 200:
                    self.rate_limiter.record_success()

            response.raise_for_status()
            data = response.json()

            # Extract items from response
            items = self._extract_data_from_response(data)
            logger.info(f"✓ Retrieved {len(items)} items")

            # Transform items to documents
            documents = []
            for item in items:
                # Extract fields
                doc_id = item.get(self.id_field)
                if not doc_id:
                    logger.warning(f"Skipping item without ID field '{self.id_field}'")
                    continue

                title = item.get(self.title_field, 'Untitled')
                content = item.get(self.content_field, '')

                # If content is empty, use title
                if not content:
                    content = title

                # Build document
                document = {
                    'id': str(doc_id),
                    'title': title,
                    'content': content,
                    'metadata': {
                        'source': 'rest_api',
                        'url': url,
                        'date': item.get(self.date_field),
                        **{k: v for k, v in item.items() if k not in [self.id_field, self.title_field, self.content_field]}
                    }
                }

                documents.append(document)

            logger.info(f"✓ Processed {len(documents)} documents")
            return documents

        except requests.RequestException as e:
            logger.error(f"API request failed: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise


if __name__ == '__main__':
    """Test the generic REST API connector with GitHub example"""
    print("=" * 70)
    print("Testing Generic REST API Connector (GitHub Example)")
    print("=" * 70)

    # Display connector metadata
    metadata = GenericRESTAPIConnector.get_metadata()
    print(f"\n📋 Connector Metadata:")
    print(f"  Name: {metadata.name}")
    print(f"  Type: {metadata.source_type}")
    print(f"  Category: {metadata.category}")
    print(f"  Version: {metadata.version}")

    # GitHub example configuration (public repos issues)
    github_config = {
        'base_url': 'https://api.github.com',
        'endpoint': '/repos/python/cpython/issues',
        'method': 'GET',
        'headers': {'Accept': 'application/vnd.github.v3+json'},
        'id_field': 'id',
        'content_field': 'body',
        'title_field': 'title',
        'date_field': 'created_at',
        'limit_param': 'per_page',
        'offset_param': 'page',
        'date_param': 'since'
    }

    # Create connector
    connector = GenericRESTAPIConnector(config=github_config)

    # Test connection
    print("\n🔌 Testing connection...")
    test_result = connector.test_connection()
    print(f"  Status: {'✅ Success' if test_result['success'] else '❌ Failed'}")
    print(f"  Message: {test_result['message']}")

    # Fetch documents
    print("\n📥 Fetching 3 GitHub issues...\n")
    docs = connector.fetch_documents(limit=3)

    if docs:
        print(f"✅ Successfully fetched {len(docs)} documents\n")
        for i, doc in enumerate(docs, 1):
            print(f"{'─' * 70}")
            print(f"Document {i}:")
            print(f"  ID: {doc['id']}")
            print(f"  Title: {doc['title'][:80]}...")
            print(f"  Content Length: {len(doc['content'])} characters")
            print(f"  Preview: {doc['content'][:150] if doc['content'] else 'No content'}...")
            print()
    else:
        print("❌ No documents retrieved")

    print("=" * 70)
