"""
Generic SPARQL connector for querying any SPARQL endpoint.
This is a universal connector that can be configured for any SPARQL data source.
"""

import logging
import requests
from SPARQLWrapper import SPARQLWrapper, JSON
from typing import List, Dict, Optional, Any
from services.rate_limiter import RateLimiter, RateLimitConfig, get_preset_config
from connectors.base_connector import BaseConnector, ConnectorMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GenericSPARQLConnector(BaseConnector):
    """
    Universal SPARQL connector for querying any SPARQL endpoint.

    Examples of compatible endpoints:
    - DBpedia: https://dbpedia.org/sparql
    - Wikidata: https://query.wikidata.org/sparql
    - Chile BCN: https://datos.bcn.cl/sparql
    - LinkedGeoData: http://linkedgeodata.org/sparql
    - Bio2RDF: http://bio2rdf.org/sparql
    """

    @classmethod
    def get_metadata(cls) -> ConnectorMetadata:
        """Return connector metadata."""
        return ConnectorMetadata(
            name="Generic SPARQL Endpoint",
            source_type="sparql",
            description="Universal connector for any SPARQL endpoint (DBpedia, Wikidata, government data, etc.)",
            version="1.0.0",
            author="RAG Factory",
            category="public",
            supports_incremental_sync=True,
            supports_rate_limiting=True,
            required_config_fields=["endpoint", "query"],
            optional_config_fields=["limit", "offset", "id_field", "content_fields", "title_field", "date_field"],
            default_rate_limit_preset=None
        )

    def __init__(self, config: Dict[str, Any], rate_limit_config: Optional[Dict] = None):
        """
        Initialize generic SPARQL connector.

        Args:
            config: Configuration dict with:
                - endpoint (required): SPARQL endpoint URL
                - query (required): SPARQL query template (use {limit}, {offset}, {since} placeholders)
                - id_field (optional): SPARQL variable name for document ID (default: "id")
                - content_fields (optional): List of SPARQL variables to combine for content (default: ["content"])
                - title_field (optional): SPARQL variable name for title (default: "title")
                - date_field (optional): SPARQL variable name for date filtering (default: "date")
                - limit (optional): Default result limit (default: 10)
                - offset (optional): Default offset (default: 0)
            rate_limit_config: Optional rate limiting configuration
        """
        super().__init__(config, rate_limit_config)

        # Extract config
        self.endpoint = config['endpoint']
        self.query_template = config['query']
        self.id_field = config.get('id_field', 'id')
        self.content_fields = config.get('content_fields', ['content'])
        self.title_field = config.get('title_field', 'title')
        self.date_field = config.get('date_field', 'date')

        # Initialize SPARQL wrapper
        self.sparql = SPARQLWrapper(self.endpoint)
        self.sparql.agent = "Mozilla/5.0 (compatible; RAGFactory/1.0)"
        self.sparql.setReturnFormat(JSON)

        # Initialize rate limiter if configured
        self.rate_limiter = None
        if rate_limit_config:
            if 'preset' in rate_limit_config:
                rate_config = get_preset_config(rate_limit_config['preset'])
            else:
                rate_config = RateLimitConfig(**rate_limit_config)
            self.rate_limiter = RateLimiter(rate_config, source_name=f"SPARQL: {self.endpoint}")

    def _build_query(self, limit: int, offset: int, since: Optional[str] = None) -> str:
        """
        Build SPARQL query from template with parameters.

        Args:
            limit: Maximum results
            offset: Offset for pagination
            since: ISO date for filtering (YYYY-MM-DD)

        Returns:
            Rendered SPARQL query
        """
        query = self.query_template

        # Replace placeholders
        query = query.replace('{limit}', str(limit))
        query = query.replace('{offset}', str(offset))

        if since:
            # Add date filter if since is provided
            date_filter = f'FILTER(?{self.date_field} > "{since}"^^xsd:date)'
            query = query.replace('{date_filter}', date_filter)
        else:
            # Remove placeholder if no date filter
            query = query.replace('{date_filter}', '')

        return query

    def fetch_documents(
        self,
        limit: int = 10,
        offset: int = 0,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch documents from SPARQL endpoint.

        Args:
            limit: Maximum number of documents to fetch
            offset: Number of documents to skip
            since: ISO date string (YYYY-MM-DD) for incremental sync

        Returns:
            List of documents with id, title, content
        """
        # Build query
        query = self._build_query(limit, offset, since)

        # Execute query with rate limiting
        if self.rate_limiter:
            wait_time = self.rate_limiter.wait_if_needed()
            if wait_time > 0:
                logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

        logger.info(f"Executing SPARQL query on {self.endpoint}")

        try:
            self.sparql.setQuery(query)
            results = self.sparql.query().convert()

            if self.rate_limiter:
                self.rate_limiter.record_request()

            bindings = results.get("results", {}).get("bindings", [])
            logger.info(f"✓ Retrieved {len(bindings)} results")

            # Transform results to documents
            documents = []
            for binding in bindings:
                # Extract ID
                doc_id = binding.get(self.id_field, {}).get('value')
                if not doc_id:
                    logger.warning(f"Skipping result without ID field '{self.id_field}'")
                    continue

                # Extract title
                title = binding.get(self.title_field, {}).get('value', 'Untitled')

                # Combine content fields
                content_parts = []
                for field in self.content_fields:
                    value = binding.get(field, {}).get('value')
                    if value:
                        content_parts.append(value)

                content = '\n\n'.join(content_parts) if content_parts else title

                # Build document
                document = {
                    'id': doc_id,
                    'title': title,
                    'content': content,
                    'metadata': {
                        'source': 'sparql',
                        'endpoint': self.endpoint,
                        **{k: v.get('value') for k, v in binding.items() if k not in [self.id_field, self.title_field] + self.content_fields}
                    }
                }

                documents.append(document)

            logger.info(f"✓ Processed {len(documents)} documents")
            return documents

        except Exception as e:
            logger.error(f"SPARQL query failed: {e}", exc_info=True)
            raise


if __name__ == '__main__':
    """Test the generic SPARQL connector with Chile BCN example"""
    print("=" * 70)
    print("Testing Generic SPARQL Connector (Chile BCN Example)")
    print("=" * 70)

    # Display connector metadata
    metadata = GenericSPARQLConnector.get_metadata()
    print(f"\n📋 Connector Metadata:")
    print(f"  Name: {metadata.name}")
    print(f"  Type: {metadata.source_type}")
    print(f"  Category: {metadata.category}")
    print(f"  Version: {metadata.version}")

    # Chile BCN example configuration
    chile_config = {
        'endpoint': 'https://datos.bcn.cl/sparql',
        'query': '''
PREFIX bcnnorms: <http://datos.bcn.cl/ontologies/bcn-norms#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>

SELECT DISTINCT ?id ?title ?date
WHERE {
    ?norma dc:identifier ?id .
    ?norma dc:title ?title .
    ?norma a bcnnorms:Norm .
    OPTIONAL { ?norma bcnnorms:publishDate ?date }
    {date_filter}
}
ORDER BY DESC(?date)
OFFSET {offset}
LIMIT {limit}
''',
        'id_field': 'id',
        'content_fields': ['title'],
        'title_field': 'title',
        'date_field': 'date',
        'limit': 3
    }

    # Create connector
    connector = GenericSPARQLConnector(config=chile_config)

    # Test connection
    print("\n🔌 Testing connection...")
    test_result = connector.test_connection()
    print(f"  Status: {'✅ Success' if test_result['success'] else '❌ Failed'}")
    print(f"  Message: {test_result['message']}")

    # Fetch documents
    print("\n📥 Fetching 3 documents from Chile BCN...\n")
    docs = connector.fetch_documents(limit=3)

    if docs:
        print(f"✅ Successfully fetched {len(docs)} documents\n")
        for i, doc in enumerate(docs, 1):
            print(f"{'─' * 70}")
            print(f"Document {i}:")
            print(f"  ID: {doc['id']}")
            print(f"  Title: {doc['title'][:80]}...")
            print(f"  Content Length: {len(doc['content'])} characters")
            print()
    else:
        print("❌ No documents retrieved")

    print("=" * 70)
