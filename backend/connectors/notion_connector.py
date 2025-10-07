"""
Notion Connector for pages and databases using Notion API v1.
Supports Integration Token and OAuth2 authentication.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

try:
    from notion_client import Client
    from notion_client.errors import APIResponseError
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False

from connectors.base_connector import BaseConnector, ConnectorMetadata
from services.rate_limiter import RateLimiter, RateLimitConfig, get_preset_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotionConnector(BaseConnector):
    """
    Universal Notion connector for pages and databases.

    Features:
    - Notion pages (full content as markdown-like text)
    - Notion databases (rows as documents)
    - Integration Token or OAuth2 authentication
    - Incremental sync based on last_edited_time
    - Rate limiting (3 requests/second by Notion API)
    - Rich text to plain text conversion
    """

    @classmethod
    def get_metadata(cls) -> ConnectorMetadata:
        """Return connector metadata."""
        return ConnectorMetadata(
            name="Notion Workspace",
            source_type="notion",
            description="Fetch pages and databases from Notion workspace",
            version="1.0.0",
            author="RAG Factory",
            category="public",
            supports_incremental_sync=True,  # Based on last_edited_time
            supports_rate_limiting=True,
            required_config_fields=["auth_token"],
            optional_config_fields=[
                "database_ids", "page_ids", "include_children", "max_depth"
            ],
            default_rate_limit_preset="conservative"
        )

    def __init__(self, config: Dict[str, Any], rate_limit_config: Optional[Dict] = None):
        """
        Initialize Notion connector.

        Args:
            config: Configuration dict with:
                - auth_token (required): Notion Integration Token or OAuth access token
                - database_ids (optional): List of database IDs to sync (if empty, searches all)
                - page_ids (optional): List of specific page IDs to sync
                - include_children (optional): Include child pages/blocks (default: True)
                - max_depth (optional): Max depth for child pages (default: 2)
            rate_limit_config: Rate limiting configuration (Notion allows 3 req/sec)
        """
        super().__init__(config, rate_limit_config)

        if not NOTION_AVAILABLE:
            raise ImportError("notion-client is required for Notion connector")

        if 'auth_token' not in config:
            raise ValueError("NotionConnector requires 'auth_token' (Integration Token or OAuth)")

        self.auth_token = config['auth_token']
        self.database_ids = config.get('database_ids', [])
        self.page_ids = config.get('page_ids', [])
        self.include_children = config.get('include_children', True)
        self.max_depth = config.get('max_depth', 2)

        # Initialize Notion client
        self.notion = Client(auth=self.auth_token)

        # Initialize rate limiter (Notion allows 3 requests/second)
        if not rate_limit_config:
            rate_limit_config = {'preset': 'conservative'}

        if 'preset' in rate_limit_config:
            rate_config = get_preset_config(rate_limit_config['preset'])
        else:
            rate_config = RateLimitConfig(**rate_limit_config)

        self.rate_limiter = RateLimiter(rate_config, source_name="Notion")

        logger.info("✓ Notion connector initialized")

    def _rich_text_to_plain(self, rich_text_array: List[Dict]) -> str:
        """Convert Notion rich text array to plain text."""
        if not rich_text_array:
            return ""

        parts = []
        for rt in rich_text_array:
            if rt.get('type') == 'text':
                parts.append(rt['text']['content'])

        return ''.join(parts)

    def _block_to_text(self, block: Dict) -> str:
        """Convert a Notion block to plain text."""
        block_type = block.get('type')

        if not block_type or block_type not in block:
            return ""

        block_content = block[block_type]
        text_parts = []

        # Handle different block types
        if block_type == 'paragraph':
            text_parts.append(self._rich_text_to_plain(block_content.get('rich_text', [])))
        elif block_type == 'heading_1':
            text = self._rich_text_to_plain(block_content.get('rich_text', []))
            text_parts.append(f"# {text}")
        elif block_type == 'heading_2':
            text = self._rich_text_to_plain(block_content.get('rich_text', []))
            text_parts.append(f"## {text}")
        elif block_type == 'heading_3':
            text = self._rich_text_to_plain(block_content.get('rich_text', []))
            text_parts.append(f"### {text}")
        elif block_type == 'bulleted_list_item':
            text = self._rich_text_to_plain(block_content.get('rich_text', []))
            text_parts.append(f"• {text}")
        elif block_type == 'numbered_list_item':
            text = self._rich_text_to_plain(block_content.get('rich_text', []))
            text_parts.append(f"1. {text}")
        elif block_type == 'to_do':
            text = self._rich_text_to_plain(block_content.get('rich_text', []))
            checked = "✓" if block_content.get('checked') else "☐"
            text_parts.append(f"{checked} {text}")
        elif block_type == 'toggle':
            text = self._rich_text_to_plain(block_content.get('rich_text', []))
            text_parts.append(text)
        elif block_type == 'code':
            text = self._rich_text_to_plain(block_content.get('rich_text', []))
            lang = block_content.get('language', '')
            text_parts.append(f"```{lang}\n{text}\n```")
        elif block_type == 'quote':
            text = self._rich_text_to_plain(block_content.get('rich_text', []))
            text_parts.append(f"> {text}")
        elif block_type == 'callout':
            text = self._rich_text_to_plain(block_content.get('rich_text', []))
            text_parts.append(f"📌 {text}")

        return '\n'.join(text_parts)

    def _get_page_content(self, page_id: str) -> str:
        """Fetch and convert page content to text."""
        content_parts = []

        try:
            # Wait for rate limit
            wait_time = self.rate_limiter.wait_if_needed()
            if wait_time > 0:
                logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

            self.rate_limiter.record_request()

            # Get blocks (page content)
            blocks = self.notion.blocks.children.list(block_id=page_id)
            self.rate_limiter.record_success()

            for block in blocks.get('results', []):
                block_text = self._block_to_text(block)
                if block_text:
                    content_parts.append(block_text)

        except APIResponseError as e:
            logger.error(f"Failed to fetch blocks for page {page_id}: {e}")

        return '\n\n'.join(content_parts)

    def _get_page_title(self, page: Dict) -> str:
        """Extract title from Notion page properties."""
        properties = page.get('properties', {})

        # Look for title property
        for prop_name, prop_value in properties.items():
            if prop_value.get('type') == 'title':
                title_array = prop_value.get('title', [])
                return self._rich_text_to_plain(title_array) or 'Untitled'

        return 'Untitled'

    def _fetch_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single page and convert to document."""
        try:
            # Wait for rate limit
            wait_time = self.rate_limiter.wait_if_needed()
            if wait_time > 0:
                logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

            self.rate_limiter.record_request()

            # Get page metadata
            page = self.notion.pages.retrieve(page_id=page_id)
            self.rate_limiter.record_success()

            # Extract title
            title = self._get_page_title(page)

            # Get content
            content = self._get_page_content(page_id)

            # Create document
            document = {
                'id': page['id'],
                'title': title,
                'content': content if content else title,
                'metadata': {
                    'source': 'notion',
                    'type': 'page',
                    'url': page.get('url', ''),
                    'created_time': page.get('created_time'),
                    'last_edited_time': page.get('last_edited_time'),
                }
            }

            logger.info(f"✓ Fetched page: {title}")
            return document

        except APIResponseError as e:
            logger.error(f"Failed to fetch page {page_id}: {e}")
            return None

    def _fetch_database(self, database_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Fetch all pages from a database."""
        documents = []

        try:
            # Build filter for incremental sync
            filter_obj = None
            if since:
                filter_obj = {
                    "timestamp": "last_edited_time",
                    "last_edited_time": {
                        "after": since.isoformat()
                    }
                }

            # Wait for rate limit
            wait_time = self.rate_limiter.wait_if_needed()
            if wait_time > 0:
                logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

            self.rate_limiter.record_request()

            # Query database
            results = self.notion.databases.query(
                database_id=database_id,
                filter=filter_obj if filter_obj else None
            )
            self.rate_limiter.record_success()

            # Process each page in database
            for page in results.get('results', []):
                doc = self._fetch_page(page['id'])
                if doc:
                    doc['metadata']['database_id'] = database_id
                    documents.append(doc)

            logger.info(f"✓ Fetched {len(documents)} pages from database {database_id}")

        except APIResponseError as e:
            logger.error(f"Failed to query database {database_id}: {e}")

        return documents

    def _search_all_pages(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Search for all accessible pages."""
        documents = []

        try:
            # Build filter for search
            filter_obj = {"value": "page", "property": "object"}

            # Wait for rate limit
            wait_time = self.rate_limiter.wait_if_needed()
            if wait_time > 0:
                logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

            self.rate_limiter.record_request()

            # Search
            results = self.notion.search(filter=filter_obj)
            self.rate_limiter.record_success()

            # Process each page
            for page in results.get('results', []):
                # Filter by date if provided
                if since:
                    last_edited = page.get('last_edited_time')
                    if last_edited:
                        page_dt = datetime.fromisoformat(last_edited.replace('Z', '+00:00'))
                        if page_dt < since:
                            continue

                doc = self._fetch_page(page['id'])
                if doc:
                    documents.append(doc)

            logger.info(f"✓ Found {len(documents)} pages via search")

        except APIResponseError as e:
            logger.error(f"Failed to search pages: {e}")

        return documents

    def fetch_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch documents from Notion workspace.

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
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

        # Fetch from specific databases
        if self.database_ids:
            for db_id in self.database_ids:
                all_documents.extend(self._fetch_database(db_id, since=since_dt))

        # Fetch specific pages
        if self.page_ids:
            for page_id in self.page_ids:
                doc = self._fetch_page(page_id)
                if doc:
                    all_documents.append(doc)

        # If no specific IDs provided, search all accessible pages
        if not self.database_ids and not self.page_ids:
            all_documents.extend(self._search_all_pages(since=since_dt))

        # Apply offset and limit
        total = len(all_documents)
        result = all_documents[offset:offset + limit]

        logger.info(f"✓ Returning {len(result)} of {total} total Notion documents")
        return result


if __name__ == '__main__':
    """Test the Notion connector"""
    print("=" * 70)
    print("Testing Notion Workspace Connector")
    print("=" * 70)

    # Display connector metadata
    metadata = NotionConnector.get_metadata()
    print(f"\n📋 Connector Metadata:")
    print(f"  Name: {metadata.name}")
    print(f"  Type: {metadata.source_type}")
    print(f"  Category: {metadata.category}")
    print(f"  Version: {metadata.version}")

    print("\n" + "=" * 70)
    print("⚠️  MANUAL TESTING REQUIRED")
    print("=" * 70)
    print("\nTo test this connector, you need:")
    print("1. Notion workspace with pages/databases")
    print("2. Notion Integration created at https://www.notion.so/my-integrations")
    print("3. Integration token (starts with 'secret_')")
    print("4. Share pages/databases with the integration")
    print("\nExample configuration:")
    print("""
config = {
    'auth_token': 'secret_xxxxxxxxxxxx',
    'database_ids': ['database-id-1', 'database-id-2'],  # Optional
    'page_ids': ['page-id-1'],  # Optional
    'include_children': True,
}

connector = NotionConnector(config=config)
docs = connector.fetch_documents(limit=5)
    """)
    print("\n" + "=" * 70)
