"""
Enhanced connector for US Congress API that fetches FULL TEXT of bills.
Replaces metadata-only queries with rich bill content.
"""

import logging
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from services.rate_limiter import RateLimiter, RateLimitConfig, get_preset_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CongressFullTextConnector:
    """
    Fetches US Congress bills with full text content from Congress.gov API.
    """

    def __init__(
        self,
        api_key: str = "DEMO_KEY",
        rate_limit_config: Optional[Dict] = None
    ):
        """
        Initialize connector.

        Args:
            api_key: Congress.gov API key (default uses DEMO_KEY with rate limits)
            rate_limit_config: Rate limiting config dict (preset name or full config)
        """
        self.api_key = api_key
        self.base_url = "https://api.congress.gov/v3"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RAGFactory/1.0 (Educational Project)'
        })

        # Initialize rate limiter
        if rate_limit_config:
            if 'preset' in rate_limit_config:
                # Use preset config
                config = get_preset_config(rate_limit_config['preset'])
            else:
                # Use custom config
                config = RateLimitConfig(**rate_limit_config)
        else:
            # Default based on API key
            if api_key == "DEMO_KEY":
                config = get_preset_config('congress_api_demo')
            else:
                config = get_preset_config('congress_api_registered')

        self.rate_limiter = RateLimiter(config, source_name="Congress API")

    def _api_request(self, url: str) -> Optional[Dict]:
        """Make API request with error handling and rate limiting."""
        try:
            # Wait if necessary to respect rate limits
            wait_time = self.rate_limiter.wait_if_needed()
            if wait_time > 0:
                logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

            response = self.session.get(url, timeout=15)

            # Record the request
            self.rate_limiter.record_request()

            # Handle 429 (rate limit) response
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                retry_after_int = int(retry_after) if retry_after else None
                self.rate_limiter.record_429_response(retry_after_int)
                logger.warning(f"⚠️  429 Rate limit hit, backing off...")
                # Retry after backoff
                wait_time = self.rate_limiter.wait_if_needed()
                if wait_time > 0:
                    logger.info(f"⏱️  Backoff wait: {wait_time:.1f}s")
                response = self.session.get(url, timeout=15)
                self.rate_limiter.record_request()

            if response.status_code == 200:
                # Reset 429 counter on success
                self.rate_limiter.record_success()
                return response.json()
            else:
                logger.error(f"API request failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    def fetch_bill_list(self, congress: int = 119, limit: int = 10, offset: int = 0) -> List[Dict]:
        """
        Fetch list of bills from specified Congress.

        Args:
            congress: Congress number (e.g., 119 for current)
            limit: Number of bills to fetch
            offset: Number of bills to skip

        Returns:
            List of bill metadata
        """
        url = f"{self.base_url}/bill/{congress}?format=json&api_key={self.api_key}&limit={limit}&offset={offset}"
        logger.info(f"Fetching bill list for Congress {congress}...")

        data = self._api_request(url)

        if data and 'bills' in data:
            bills = data['bills']
            logger.info(f"✓ Retrieved {len(bills)} bills")
            return bills
        else:
            logger.error("Failed to fetch bill list")
            return []

    def _extract_all_text(self, element) -> List[str]:
        """
        Recursively extract all text content from an XML element.

        Args:
            element: XML element to extract text from

        Returns:
            List of text strings found in element and its children
        """
        texts = []
        if element.text and element.text.strip():
            texts.append(element.text.strip())
        for child in element:
            texts.extend(self._extract_all_text(child))
            if child.tail and child.tail.strip():
                texts.append(child.tail.strip())
        return texts

    def fetch_bill_text_xml(self, congress: int, bill_type: str, bill_number: int) -> Optional[str]:
        """
        Fetch full text of a bill in XML format.

        Args:
            congress: Congress number
            bill_type: Type of bill (hr, s, hjres, sjres, etc.)
            bill_number: Bill number

        Returns:
            Full text content or None
        """
        # First, get text versions
        url = f"{self.base_url}/bill/{congress}/{bill_type}/{bill_number}/text?format=json&api_key={self.api_key}"
        logger.info(f"Fetching text for {bill_type}{bill_number}...")

        data = self._api_request(url)

        if not data or 'textVersions' not in data:
            logger.warning(f"No text versions available for {bill_type}{bill_number}")
            return None

        text_versions = data.get('textVersions', [])

        if not text_versions:
            logger.warning(f"No text versions found")
            return None

        # Get the latest version (usually first in list)
        latest_version = text_versions[0]

        # Find XML format URL
        xml_url = None
        for fmt in latest_version.get('formats', []):
            if 'XML' in fmt.get('type', ''):
                xml_url = fmt.get('url')
                break

        if not xml_url:
            logger.warning(f"No XML format available for {bill_type}{bill_number}")
            return None

        # Fetch XML content
        try:
            logger.info(f"Downloading XML from {xml_url}")
            response = requests.get(xml_url, timeout=30)

            if response.status_code != 200:
                logger.error(f"XML download failed: {response.status_code}")
                return None

            # Parse XML and extract ALL text recursively
            # This handles any XML schema without needing to know specific tag names
            root = ET.fromstring(response.content)

            # Extract all text from all elements recursively
            all_texts = self._extract_all_text(root)
            full_text = ' '.join(all_texts)

            if full_text and len(full_text) > 100:
                logger.info(f"✓ Extracted {len(full_text)} characters from XML")
                return full_text
            else:
                logger.warning(f"Insufficient text in XML (only {len(full_text)} chars)")
                return None

        except Exception as e:
            logger.error(f"Error processing XML: {e}")
            return None

    def get_bills_with_full_text(self, congress: int = 119, limit: int = 10, offset: int = 0) -> List[Dict]:
        """
        Fetch bills with full text content.

        Args:
            congress: Congress number
            limit: Maximum number of bills
            offset: Number of bills to skip

        Returns:
            List of bills with full text
        """
        # Fetch bill list
        bills = self.fetch_bill_list(congress=congress, limit=limit, offset=offset)

        if not bills:
            return []

        enriched_bills = []

        for bill in bills:
            bill_type = bill.get('type', '').lower()
            bill_number = bill.get('number')
            title = bill.get('title', 'Untitled')
            latest_action = bill.get('latestAction', {}).get('text', 'No action')
            url = bill.get('url', '')

            if not all([bill_type, bill_number]):
                logger.warning(f"Skipping incomplete bill record")
                continue

            # Build bill ID
            bill_id = f"{bill_type}{bill_number}-{congress}"

            # Fetch full text
            full_text = self.fetch_bill_text_xml(congress, bill_type, bill_number)

            # Build content
            if full_text and len(full_text) > 200:
                # Has substantial content
                content = f"{title}\n\nBill Number: {bill_type.upper()}. {bill_number}\n"
                content += f"Congress: {congress}\n"
                content += f"Latest Action: {latest_action}\n\n"
                content += f"FULL TEXT:\n{full_text}"
            else:
                # Fallback to metadata only
                content = f"{title}\nBill Number: {bill_type.upper()}. {bill_number}\n"
                content += f"Congress: {congress}\nTitle: {title}\n"
                content += f"Latest Action: {latest_action}"
                logger.warning(f"Using metadata-only for {bill_id} (full text unavailable)")

            document = {
                'id': bill_id,
                'title': title,
                'content': content,
                'bill_type': bill_type,
                'bill_number': bill_number,
                'congress': congress,
                'latest_action': latest_action,
                'url': url,
                'content_length': len(content)
            }

            enriched_bills.append(document)
            logger.info(f"✓ {bill_id}: {len(content)} chars")

        logger.info(f"✓ Fetched {len(enriched_bills)} bills with content")
        return enriched_bills


if __name__ == '__main__':
    """Test the enhanced connector"""
    print("=" * 70)
    print("Testing Congress Full Text Connector")
    print("=" * 70)

    connector = CongressFullTextConnector()

    # Fetch 3 bills with full text
    print("\n📥 Fetching 3 US Congress bills with full text...\n")
    bills = connector.get_bills_with_full_text(congress=119, limit=3)

    if bills:
        print(f"✅ Successfully fetched {len(bills)} bills\n")
        for i, bill in enumerate(bills, 1):
            print(f"{'─' * 70}")
            print(f"Bill {i}:")
            print(f"  ID: {bill['id']}")
            print(f"  Title: {bill['title'][:80]}...")
            print(f"  Type: {bill['bill_type'].upper()}. {bill['bill_number']}")
            print(f"  Content Length: {bill['content_length']} characters")
            print(f"  Preview: {bill['content'][:200]}...")
            print()
    else:
        print("❌ Failed to fetch bills")

    print("=" * 70)
