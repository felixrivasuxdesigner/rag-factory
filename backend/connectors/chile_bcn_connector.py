"""
Chile BCN (Biblioteca del Congreso Nacional) full-text connector.
Pre-configured connector for Chilean legal norms with COMPLETE TEXT extraction.

This connector:
1. Fetches norms from BCN SPARQL endpoint (https://datos.bcn.cl/sparql)
2. Downloads the FULL XML content from LeyChile
3. Extracts ALL text recursively from XML
4. Returns complete legal documents (~900+ characters vs ~70 with titles only)
"""

import logging
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Any, List
from connectors.generic_sparql_connector import GenericSPARQLConnector
from connectors.base_connector import ConnectorMetadata
from services.content_cache_service import ContentCacheService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChileBCNConnector(GenericSPARQLConnector):
    """
    Full-text connector for Chile's Biblioteca del Congreso Nacional (BCN).

    Downloads COMPLETE legal text from LeyChile XML instead of just titles.
    """

    # SPARQL query to get norm metadata INCLUDING XML document URL
    CHILE_BCN_QUERY = """
PREFIX bcnnorms: <http://datos.bcn.cl/ontologies/bcn-norms#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>

SELECT DISTINCT ?id ?title ?date ?xmlDoc
WHERE {{
    ?norma dc:identifier ?id .
    ?norma dc:title ?title .
    ?norma a bcnnorms:Norm .
    OPTIONAL {{ ?norma bcnnorms:publishDate ?date }}
    OPTIONAL {{ ?norma bcnnorms:hasXmlDocument ?xmlDoc }}
    {date_filter}
}}
ORDER BY DESC(?date)
OFFSET {offset}
LIMIT {limit}
"""

    @classmethod
    def get_metadata(cls) -> ConnectorMetadata:
        """Return connector metadata."""
        return ConnectorMetadata(
            name="Chile BCN Legal Norms (Full-Text)",
            source_type="chile_bcn",
            description="Chilean legal documents with COMPLETE text from BCN and LeyChile XML",
            version="2.0.0",
            author="RAG Factory",
            category="example",
            supports_incremental_sync=True,
            supports_rate_limiting=True,
            required_config_fields=[],
            optional_config_fields=["limit"],
            default_rate_limit_preset="conservative"
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None, rate_limit_config: Optional[Dict] = None,
                 cache_service: Optional[ContentCacheService] = None, source_id: Optional[int] = None):
        """
        Initialize Chile BCN full-text connector.

        Args:
            config: Optional configuration dict (only 'limit' is used, default: 25)
            rate_limit_config: Optional rate limiting configuration
            cache_service: Optional content cache service for caching downloaded XMLs
            source_id: Source ID for cache lookups
        """
        # Build config for generic SPARQL connector
        sparql_config = {
            'endpoint': 'https://datos.bcn.cl/sparql',
            'query': self.CHILE_BCN_QUERY,
            'id_field': 'id',
            'content_fields': [],  # We'll override fetch_documents to get full text
            'title_field': 'title',
            'date_field': 'date',
            'limit': config.get('limit', 25) if config else 25
        }

        # Use conservative rate limiting
        if not rate_limit_config:
            rate_limit_config = {'preset': 'conservative'}

        # Initialize parent
        super().__init__(config=sparql_config, rate_limit_config=rate_limit_config)

        # Store cache service
        self.cache_service = cache_service
        self.source_id = source_id

        logger.info("✓ Chile BCN FULL-TEXT connector initialized")

    def _download_xml_content(self, xml_url: str) -> Optional[str]:
        """
        Download full XML content from LeyChile using the provided URL.

        Args:
            xml_url: The complete XML document URL from BCN SPARQL

        Returns:
            Full text content extracted from XML, or None if failed
        """
        try:
            # Apply rate limiting
            if self.rate_limiter:
                self.rate_limiter.wait_if_needed()

            # CRITICAL: LeyChile blocks requests without User-Agent
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(xml_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Parse XML and extract all text
            root = ET.fromstring(response.content)
            full_text = self._extract_all_text(root)

            if full_text and len(full_text.strip()) > 0:
                logger.info(f"  ✓ Downloaded {len(full_text)} chars from XML")
                return full_text.strip()
            else:
                logger.warning(f"  ⚠ Empty content in XML")
                return None

        except Exception as e:
            logger.error(f"  ✗ Failed to download XML from {xml_url}: {e}")
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
        Fetch documents from BCN SPARQL endpoint and download FULL TEXT from XML.

        Args:
            limit: Maximum number of documents to fetch
            offset: Offset for pagination (passed to parent)
            since: Optional date filter (YYYY-MM-DD format)

        Returns:
            List of document dictionaries with COMPLETE text content
        """
        # First, get metadata from SPARQL
        docs = super().fetch_documents(limit=limit, since=since)

        logger.info(f"\n📥 Fetched {len(docs)} norms from SPARQL, now downloading FULL TEXT from XML...")

        # Now download full text for each document (with caching)
        enriched_docs = []
        cache_hits = 0
        cache_misses = 0

        for i, doc in enumerate(docs, 1):
            norm_id = doc['id']
            xml_url = doc.get('metadata', {}).get('xmlDoc')

            if not xml_url:
                logger.warning(f"  [{i}/{len(docs)}] No XML URL for norm {norm_id}, using title only")
                doc['content'] = doc['title']
                doc['metadata']['has_full_text'] = False
                enriched_docs.append(doc)
                continue

            # Check cache first if available
            full_text = None
            if self.cache_service and self.source_id:
                cached = self.cache_service.get_cached_content(self.source_id, norm_id)
                if cached:
                    full_text = cached['content']
                    cache_hits += 1
                    logger.info(f"  [{i}/{len(docs)}] ✓ Cache HIT for norm {norm_id} ({len(full_text)} chars)")
                else:
                    cache_misses += 1

            # Download if not in cache
            if not full_text:
                logger.info(f"  [{i}/{len(docs)}] Downloading full text for norm {norm_id} from {xml_url}...")
                full_text = self._download_xml_content(xml_url)

                # Save to cache if download succeeded
                if full_text and self.cache_service and self.source_id:
                    self.cache_service.save_to_cache(
                        source_id=self.source_id,
                        external_id=norm_id,
                        content=full_text,
                        title=doc['title'],
                        source_url=xml_url,
                        source_metadata={'date': doc.get('metadata', {}).get('date')}
                    )

            if full_text:
                # Replace title-only content with FULL TEXT
                doc['content'] = full_text
                doc['metadata']['has_full_text'] = True
                doc['metadata']['content_length'] = len(full_text)
                enriched_docs.append(doc)
                if not self.cache_service or cache_misses > 0:
                    logger.info(f"    ✓ Enriched: {len(full_text)} characters")
            else:
                # Fallback to title if XML download failed
                logger.warning(f"    ⚠ Using title as fallback for norm {norm_id}")
                doc['content'] = doc['title']
                doc['metadata']['has_full_text'] = False
                doc['metadata']['content_length'] = len(doc['title'])
                enriched_docs.append(doc)

        # Log cache statistics
        if self.cache_service:
            logger.info(f"\n📊 Cache Statistics: {cache_hits} hits, {cache_misses} misses ({cache_hits/(cache_hits+cache_misses)*100:.1f}% hit rate)")

        logger.info(f"✅ Successfully enriched {len(enriched_docs)} documents with full text")
        return enriched_docs


if __name__ == '__main__':
    """Test the Chile BCN full-text connector"""
    print("=" * 70)
    print("Testing Chile BCN FULL-TEXT Connector")
    print("=" * 70)

    connector = ChileBCNConnector(config={'limit': 3})

    print("\n🔌 Testing connection...")
    test_result = connector.test_connection()
    print(f"  Status: {'✅ Success' if test_result['success'] else '❌ Failed'}")

    if test_result['success']:
        print("\n📥 Fetching 3 norms with FULL TEXT...\n")
        docs = connector.fetch_documents(limit=3)

        if docs:
            print(f"\n✅ Successfully fetched {len(docs)} documents\n")
            for i, doc in enumerate(docs, 1):
                print(f"{'─' * 70}")
                print(f"Document {i}:")
                print(f"  ID: {doc['id']}")
                print(f"  Title: {doc['title'][:80]}...")
                print(f"  Content Length: {len(doc['content'])} characters")
                print(f"  Has Full Text: {doc['metadata'].get('has_full_text', False)}")
                print(f"  Preview: {doc['content'][:200]}...")
                print()
        else:
            print("❌ No documents retrieved")

    print("=" * 70)
