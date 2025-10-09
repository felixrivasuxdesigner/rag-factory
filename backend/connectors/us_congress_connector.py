"""
US Congress API full-text connector.
Pre-configured connector for US legislative bills with COMPLETE TEXT extraction.

This connector:
1. Fetches bills from Congress.gov API
2. Downloads the FULL XML text content for each bill
3. Extracts ALL legislative text recursively from XML
4. Returns complete bills (2,000-10,000+ characters vs ~200-300 with titles only)
"""

import logging
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Any, List
from connectors.generic_rest_api_connector import GenericRESTAPIConnector
from connectors.base_connector import ConnectorMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class USCongressConnector(GenericRESTAPIConnector):
    """
    Full-text connector for US Congress legislative data.

    Downloads COMPLETE bill text from Congress.gov XML instead of just titles.
    """

    @classmethod
    def get_metadata(cls) -> ConnectorMetadata:
        """Return connector metadata."""
        return ConnectorMetadata(
            name="US Congress Bills (Full-Text)",
            source_type="us_congress",
            description="US legislative bills with COMPLETE text from Congress.gov API and XML",
            version="2.0.0",
            author="RAG Factory",
            category="example",
            supports_incremental_sync=True,
            supports_rate_limiting=True,
            required_config_fields=["api_key"],
            optional_config_fields=["limit", "congress_number"],
            default_rate_limit_preset="congress_api_demo"
        )

    def __init__(self, config: Dict[str, Any], rate_limit_config: Optional[Dict] = None):
        """
        Initialize US Congress full-text connector.

        Args:
            config: Configuration dict with:
                - api_key (required): Congress.gov API key
                - limit (optional): Results per page (default: 25)
                - congress_number (optional): Congress number (default: 119)
            rate_limit_config: Optional rate limiting configuration
        """
        if not config or 'api_key' not in config:
            raise ValueError("US Congress connector requires 'api_key' in config")

        self.api_key = config['api_key']
        self.congress_number = config.get('congress_number', 119)
        limit = config.get('limit', 25)

        # Build config for generic REST API connector
        rest_api_config = {
            'base_url': 'https://api.congress.gov/v3',
            'endpoint': f'/bill/{self.congress_number}',
            'method': 'GET',
            'headers': {'Accept': 'application/json'},
            'auth_type': 'api_key',
            'api_key': self.api_key,
            'api_key_header': 'x-api-key',
            'response_data_path': 'bills',
            'id_field': 'number',
            'content_field': '',  # We'll override fetch_documents to get full text
            'title_field': 'title',
            'date_field': 'updateDate',
            'limit_param': 'limit',
            'offset_param': 'offset',
            'date_param': 'fromDateTime'
        }

        # Use congress_api_demo rate limiting by default (for DEMO_KEY)
        if not rate_limit_config:
            rate_limit_config = {'preset': 'congress_api_demo'}

        # Initialize parent with hardcoded config
        super().__init__(config=rest_api_config, rate_limit_config=rate_limit_config)

        logger.info(f"✓ US Congress FULL-TEXT connector initialized (Congress #{self.congress_number})")

    def _download_bill_xml_text(self, bill_data: Dict) -> Optional[str]:
        """
        Download full XML text content for a bill.

        Args:
            bill_data: Bill metadata from API

        Returns:
            Full bill text extracted from XML, or None if failed
        """
        # Get text versions URL
        bill_number = bill_data.get('number')
        bill_type = bill_data.get('type', '').lower()

        if not bill_number or not bill_type:
            logger.warning(f"  ⚠ Missing bill number or type: {bill_data}")
            return None

        # Construct text API URL
        text_url = f"{self.base_url}/bill/{self.congress_number}/{bill_type}/{bill_number}/text"

        try:
            # Apply rate limiting
            if self.rate_limiter:
                self.rate_limiter.wait_if_needed()

            # Fetch text versions
            response = requests.get(
                text_url,
                headers={'x-api-key': self.api_key, 'Accept': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            text_data = response.json()

            # Get the first available text version
            text_versions = text_data.get('textVersions', [])
            if not text_versions:
                logger.warning(f"  ⚠ No text versions available for {bill_type}{bill_number}")
                return None

            # Get the formatted text URL (XML)
            first_version = text_versions[0]
            formats = first_version.get('formats', [])

            xml_url = None
            for fmt in formats:
                if fmt.get('type') == 'Formatted Text':
                    xml_url = fmt.get('url')
                    break

            if not xml_url:
                logger.warning(f"  ⚠ No XML format found for {bill_type}{bill_number}")
                return None

            # Download XML
            if self.rate_limiter:
                self.rate_limiter.wait_if_needed()

            xml_response = requests.get(xml_url, timeout=30)
            xml_response.raise_for_status()

            # Parse XML and extract all text
            root = ET.fromstring(xml_response.content)
            full_text = self._extract_all_text(root)

            if full_text and len(full_text.strip()) > 0:
                logger.info(f"  ✓ Downloaded {len(full_text)} chars from XML for {bill_type}{bill_number}")
                return full_text.strip()
            else:
                logger.warning(f"  ⚠ Empty content in XML for {bill_type}{bill_number}")
                return None

        except Exception as e:
            logger.error(f"  ✗ Failed to download XML for {bill_type}{bill_number}: {e}")
            return None

    def _extract_all_text(self, element) -> str:
        """
        Recursively extract all text from an XML element.

        Args:
            element: XML Element

        Returns:
            All text content concatenated
        """
        texts = []

        # Get text from this element
        if element.text:
            texts.append(element.text.strip())

        # Recursively get text from children
        for child in element:
            child_text = self._extract_all_text(child)
            if child_text:
                texts.append(child_text)

        # Get tail text
        if element.tail:
            texts.append(element.tail.strip())

        return ' '.join(filter(None, texts))

    def fetch_documents(self, limit: Optional[int] = None, offset: Optional[int] = None, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch bills from Congress.gov API and download FULL TEXT from XML.

        Args:
            limit: Maximum number of documents to fetch
            offset: Offset for pagination (passed to parent)
            since: Optional date filter (ISO format)

        Returns:
            List of document dictionaries with COMPLETE text content
        """
        # First, get metadata from API
        docs = super().fetch_documents(limit=limit, since=since)

        logger.info(f"\n📥 Fetched {len(docs)} bills from API, now downloading FULL TEXT from XML...")

        # Now download full text for each bill
        enriched_docs = []
        for i, doc in enumerate(docs, 1):
            bill_id = doc['id']
            logger.info(f"  [{i}/{len(docs)}] Downloading full text for bill {bill_id}...")

            # Get bill data from metadata to extract type
            bill_data = {
                'number': bill_id,
                'type': doc['metadata'].get('type', 'hr')  # Default to 'hr' if not found
            }

            # Download XML content
            full_text = self._download_bill_xml_text(bill_data)

            if full_text:
                # Replace title-only content with FULL TEXT
                doc['content'] = full_text
                doc['metadata']['has_full_text'] = True
                doc['metadata']['content_length'] = len(full_text)
                enriched_docs.append(doc)
                logger.info(f"    ✓ Enriched: {len(full_text)} characters")
            else:
                # Fallback to title if XML download failed
                logger.warning(f"    ⚠ Using title as fallback for bill {bill_id}")
                doc['content'] = doc['title']
                doc['metadata']['has_full_text'] = False
                doc['metadata']['content_length'] = len(doc['title'])
                enriched_docs.append(doc)

        logger.info(f"\n✅ Successfully enriched {len(enriched_docs)} bills with full text")
        return enriched_docs


if __name__ == '__main__':
    """Test the US Congress full-text connector"""
    print("=" * 70)
    print("Testing US Congress FULL-TEXT Connector")
    print("=" * 70)

    connector = USCongressConnector(config={'api_key': 'DEMO_KEY', 'limit': 3})

    print("\n🔌 Testing connection...")
    test_result = connector.test_connection()
    print(f"  Status: {'✅ Success' if test_result['success'] else '❌ Failed'}")

    if test_result['success']:
        print("\n📥 Fetching 3 bills with FULL TEXT...\n")
        docs = connector.fetch_documents(limit=3)

        if docs:
            print(f"\n✅ Successfully fetched {len(docs)} bills\n")
            for i, doc in enumerate(docs, 1):
                print(f"{'─' * 70}")
                print(f"Bill {i}:")
                print(f"  Number: {doc['id']}")
                print(f"  Title: {doc['title'][:100]}...")
                print(f"  Content Length: {len(doc['content'])} characters")
                print(f"  Has Full Text: {doc['metadata'].get('has_full_text', False)}")
                print(f"  Preview: {doc['content'][:200]}...")
                print()
        else:
            print("❌ No bills retrieved")

    print("=" * 70)
