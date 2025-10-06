"""
Enhanced connector for Chilean BCN SPARQL that fetches FULL TEXT content from LeyChile XML.
This replaces the basic title-only queries with rich document content.
"""

import logging
import requests
import xml.etree.ElementTree as ET
from SPARQLWrapper import SPARQLWrapper, JSON
from typing import List, Dict, Optional, Any
from services.rate_limiter import RateLimiter, RateLimitConfig, get_preset_config
from connectors.base_connector import BaseConnector, ConnectorMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChileFullTextConnector(BaseConnector):
    """
    Fetches Chilean norms with full text content from BCN SPARQL + LeyChile XML.
    """

    @classmethod
    def get_metadata(cls) -> ConnectorMetadata:
        """Return connector metadata."""
        return ConnectorMetadata(
            name="Chile BCN Full Text",
            source_type="chile_fulltext",
            description="Fetches Chilean legal norms with complete text from BCN SPARQL and LeyChile XML",
            version="2.0.0",
            author="RAG Factory",
            supports_incremental_sync=True,
            supports_rate_limiting=True,
            required_config_fields=[],
            optional_config_fields=["endpoint", "limit", "offset"],
            default_rate_limit_preset="chile_bcn_conservative"
        )

    def __init__(self, config: Dict[str, Any], rate_limit_config: Optional[Dict] = None):
        """
        Initialize connector.

        Args:
            config: Configuration dict with optional 'endpoint', 'limit', 'offset'
            rate_limit_config: Rate limiting config dict (preset name or full config)
        """
        # Call parent init for validation
        super().__init__(config, rate_limit_config)

        # Extract config
        self.sparql_endpoint = config.get('endpoint', 'https://datos.bcn.cl/sparql')
        self.sparql = SPARQLWrapper(self.sparql_endpoint)
        self.sparql.agent = "Mozilla/5.0 (compatible; RAGFactory/1.0)"

        # Initialize rate limiter
        if rate_limit_config:
            if 'preset' in rate_limit_config:
                # Use preset config
                rate_config = get_preset_config(rate_limit_config['preset'])
            else:
                # Use custom config
                rate_config = RateLimitConfig(**rate_limit_config)
        else:
            # Default to conservative Chile config
            rate_config = get_preset_config('chile_bcn_conservative')

        self.rate_limiter = RateLimiter(rate_config, source_name="Chile BCN")

    def execute_sparql(self, query: str) -> List[Dict]:
        """Execute SPARQL query and return results."""
        self.sparql.setQuery(query)
        self.sparql.setReturnFormat(JSON)

        try:
            logger.info(f"Executing SPARQL query...")
            results = self.sparql.query().convert()
            bindings = results["results"]["bindings"]
            logger.info(f"✓ Retrieved {len(bindings)} records from SPARQL")
            return bindings
        except Exception as e:
            logger.error(f"SPARQL query failed: {e}")
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

    def fetch_xml_content(self, leychile_code: str) -> Optional[str]:
        """
        Fetch full text content from LeyChile XML.

        Args:
            leychile_code: The LeyChile numeric code

        Returns:
            Full text content or None if failed
        """
        xml_url = f"http://www.leychile.cl/Consulta/obtxml?opt=7&idNorma={leychile_code}"

        try:
            # Wait if necessary to respect rate limits
            wait_time = self.rate_limiter.wait_if_needed()
            if wait_time > 0:
                logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

            logger.info(f"Fetching XML from LeyChile: {leychile_code}")
            response = requests.get(xml_url, timeout=15)

            # Record the request
            self.rate_limiter.record_request()

            # Handle 429 (rate limit) response
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                retry_after_int = int(retry_after) if retry_after else None
                self.rate_limiter.record_429_response(retry_after_int)
                logger.warning(f"⚠️  429 Rate limit hit, backing off...")
                return None

            if response.status_code != 200:
                logger.warning(f"XML fetch failed with status {response.status_code}")
                return None

            # Parse XML and extract ALL text recursively
            # LeyChile uses XML with namespaces, so we extract all text content
            root = ET.fromstring(response.content)

            # Extract all text from all elements (handles namespaces automatically)
            all_texts = self._extract_all_text(root)
            full_text = ' '.join(all_texts)

            if full_text and len(full_text) > 50:
                logger.info(f"✓ Extracted {len(full_text)} characters from XML")
                return full_text
            else:
                logger.warning(f"Insufficient text content in XML (only {len(full_text)} chars)")
                return None

        except requests.RequestException as e:
            logger.error(f"HTTP error fetching XML: {e}")
            return None
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching XML: {e}")
            return None

    def fetch_documents(
        self,
        limit: int = 10,
        offset: int = 0,
        since: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch Chilean norms with full text content.

        Args:
            limit: Maximum number of documents to fetch
            offset: Number of documents to skip
            since: ISO date string (YYYY-MM-DD) to fetch only norms published after this date

        Returns:
            List of documents with full text content
        """
        # Build date filter if provided
        date_filter = ""
        if since:
            date_filter = f'FILTER(?publishDate > "{since}"^^xsd:date)'

        # Query to get norm metadata including LeyChile codes
        query = f"""
PREFIX bcnnorms: <http://datos.bcn.cl/ontologies/bcn-norms#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?norma ?id ?title ?leychileCode ?publishDate ?type
WHERE {{
    ?norma dc:identifier ?id .
    ?norma dc:title ?title .
    ?norma a bcnnorms:Norm .
    ?norma bcnnorms:leychileCode ?leychileCode .
    ?norma bcnnorms:publishDate ?publishDate .
    {date_filter}
    OPTIONAL {{ ?norma a ?type }}
}}
ORDER BY DESC(?publishDate)
OFFSET {offset}
LIMIT {limit}
"""

        sparql_results = self.execute_sparql(query)

        if not sparql_results:
            logger.warning("No results from SPARQL query")
            return []

        # Fetch full text for each norm
        enriched_documents = []

        for result in sparql_results:
            doc_id = result.get('id', {}).get('value')
            title = result.get('title', {}).get('value')
            leychile_code = result.get('leychileCode', {}).get('value')
            norma_uri = result.get('norma', {}).get('value')
            publish_date = result.get('publishDate', {}).get('value', 'unknown')

            if not all([doc_id, title, leychile_code]):
                logger.warning(f"Skipping incomplete record: {doc_id}")
                continue

            # Fetch full XML content
            full_text = self.fetch_xml_content(leychile_code)

            # Build document
            if full_text and len(full_text) > 100:
                # Has substantial content
                content = f"{title}\n\n{full_text}"
            else:
                # Fallback to title only if XML fetch failed
                content = title
                logger.warning(f"Using title-only for {doc_id} (XML fetch failed)")

            document = {
                'id': doc_id,
                'title': title,
                'content': content,
                'uri': norma_uri,
                'leychile_code': leychile_code,
                'publish_date': publish_date,
                'content_length': len(content)
            }

            enriched_documents.append(document)
            logger.info(f"✓ {doc_id}: {len(content)} chars")

        logger.info(f"✓ Fetched {len(enriched_documents)} norms with full text")
        return enriched_documents

    def get_norms_with_full_text(self, limit: int = 10, offset: int = 0, since: Optional[str] = None) -> List[Dict]:
        """
        Legacy method name for backward compatibility.
        Calls fetch_documents() internally.
        """
        return self.fetch_documents(limit=limit, offset=offset, since=since)


if __name__ == '__main__':
    """Test the enhanced connector"""
    print("=" * 70)
    print("Testing Chile Full Text Connector (Plugin Architecture)")
    print("=" * 70)

    # Display connector metadata
    metadata = ChileFullTextConnector.get_metadata()
    print(f"\n📋 Connector Metadata:")
    print(f"  Name: {metadata.name}")
    print(f"  Type: {metadata.source_type}")
    print(f"  Version: {metadata.version}")
    print(f"  Supports Incremental Sync: {metadata.supports_incremental_sync}")
    print(f"  Supports Rate Limiting: {metadata.supports_rate_limiting}")
    print(f"  Default Rate Limit: {metadata.default_rate_limit_preset}")

    # Initialize connector
    config = {}  # Using defaults
    connector = ChileFullTextConnector(config)

    # Test connection
    print("\n🔌 Testing connection...")
    test_result = connector.test_connection()
    print(f"  Status: {'✅ Success' if test_result['success'] else '❌ Failed'}")
    print(f"  Message: {test_result['message']}")

    # Fetch 3 norms with full text
    print("\n📥 Fetching 3 Chilean norms with full text content...\n")
    norms = connector.fetch_documents(limit=3)

    if norms:
        print(f"✅ Successfully fetched {len(norms)} norms\n")
        for i, norm in enumerate(norms, 1):
            print(f"{'─' * 70}")
            print(f"Norm {i}:")
            print(f"  ID: {norm['id']}")
            print(f"  Title: {norm['title'][:80]}...")
            print(f"  LeyChile Code: {norm['leychile_code']}")
            print(f"  Content Length: {norm['content_length']} characters")
            print(f"  Preview: {norm['content'][:200]}...")
            print()
    else:
        print("❌ Failed to fetch norms")

    print("=" * 70)
