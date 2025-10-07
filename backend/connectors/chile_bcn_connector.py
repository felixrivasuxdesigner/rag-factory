"""
Chile BCN (Biblioteca del Congreso Nacional) example connector.
Pre-configured connector for Chilean legal norms and legislative documents.
"""

import logging
from typing import Dict, Optional, Any
from connectors.generic_sparql_connector import GenericSPARQLConnector
from connectors.base_connector import ConnectorMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChileBCNConnector(GenericSPARQLConnector):
    """
    Pre-configured connector for Chile's Biblioteca del Congreso Nacional (BCN).

    Provides access to Chilean legal norms, bills, and legislative documents
    via the BCN SPARQL endpoint at https://datos.bcn.cl/sparql

    This is an example connector with hardcoded configuration - users just need
    to provide optional pagination parameters.
    """

    # Hardcoded SPARQL query for Chilean legal norms
    CHILE_BCN_QUERY = """
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
"""

    @classmethod
    def get_metadata(cls) -> ConnectorMetadata:
        """Return connector metadata."""
        return ConnectorMetadata(
            name="Chile BCN Legal Norms",
            source_type="chile_bcn",
            description="Pre-configured connector for Chilean legal norms from Biblioteca del Congreso Nacional",
            version="1.0.0",
            author="RAG Factory",
            category="example",
            supports_incremental_sync=True,
            supports_rate_limiting=True,
            required_config_fields=[],  # No required fields - all hardcoded
            optional_config_fields=["limit"],
            default_rate_limit_preset="conservative"
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None, rate_limit_config: Optional[Dict] = None):
        """
        Initialize Chile BCN connector with hardcoded configuration.

        Args:
            config: Optional configuration dict (only 'limit' is used, default: 25)
            rate_limit_config: Optional rate limiting configuration
        """
        # Build hardcoded config for generic SPARQL connector
        sparql_config = {
            'endpoint': 'https://datos.bcn.cl/sparql',
            'query': self.CHILE_BCN_QUERY,
            'id_field': 'id',
            'content_fields': ['title'],  # Use title as content since we don't have full text
            'title_field': 'title',
            'date_field': 'date',
            'limit': config.get('limit', 25) if config else 25
        }

        # Use conservative rate limiting by default
        if not rate_limit_config:
            rate_limit_config = {'preset': 'conservative'}

        # Initialize parent with hardcoded config
        super().__init__(config=sparql_config, rate_limit_config=rate_limit_config)

        logger.info("✓ Chile BCN connector initialized with hardcoded configuration")


if __name__ == '__main__':
    """Test the Chile BCN connector"""
    print("=" * 70)
    print("Testing Chile BCN Connector (Example Connector)")
    print("=" * 70)

    # Display connector metadata
    metadata = ChileBCNConnector.get_metadata()
    print(f"\n📋 Connector Metadata:")
    print(f"  Name: {metadata.name}")
    print(f"  Type: {metadata.source_type}")
    print(f"  Category: {metadata.category}")
    print(f"  Version: {metadata.version}")
    print(f"  Required Config: {metadata.required_config_fields}")
    print(f"  Optional Config: {metadata.optional_config_fields}")

    # Create connector with minimal config (or no config)
    print("\n🔌 Creating connector (no config needed)...")
    connector = ChileBCNConnector()

    # Test connection
    print("\n🔌 Testing connection to Chile BCN SPARQL endpoint...")
    test_result = connector.test_connection()
    print(f"  Status: {'✅ Success' if test_result['success'] else '❌ Failed'}")
    print(f"  Message: {test_result['message']}")

    # Fetch documents
    print("\n📥 Fetching 3 Chilean legal norms...\n")
    docs = connector.fetch_documents(limit=3)

    if docs:
        print(f"✅ Successfully fetched {len(docs)} documents\n")
        for i, doc in enumerate(docs, 1):
            print(f"{'─' * 70}")
            print(f"Document {i}:")
            print(f"  ID: {doc['id']}")
            print(f"  Title: {doc['title'][:80]}...")
            print(f"  Content Length: {len(doc['content'])} characters")
            if 'date' in doc['metadata']:
                print(f"  Date: {doc['metadata'].get('date', 'N/A')}")
            print()
    else:
        print("❌ No documents retrieved")

    print("=" * 70)
