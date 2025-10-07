"""
US Congress API example connector.
Pre-configured connector for US legislative bills via Congress.gov API.
"""

import logging
from typing import Dict, Optional, Any
from connectors.generic_rest_api_connector import GenericRESTAPIConnector
from connectors.base_connector import ConnectorMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class USCongressConnector(GenericRESTAPIConnector):
    """
    Pre-configured connector for US Congress legislative data.

    Provides access to US bills, resolutions, and legislative documents
    via the Congress.gov API at https://api.congress.gov

    This is an example connector with hardcoded configuration - users just need
    to provide their Congress.gov API key and optional pagination parameters.

    Get your API key at: https://api.congress.gov/sign-up/
    """

    @classmethod
    def get_metadata(cls) -> ConnectorMetadata:
        """Return connector metadata."""
        return ConnectorMetadata(
            name="US Congress Bills",
            source_type="us_congress",
            description="Pre-configured connector for US legislative bills from Congress.gov API",
            version="1.0.0",
            author="RAG Factory",
            category="example",
            supports_incremental_sync=True,
            supports_rate_limiting=True,
            required_config_fields=["api_key"],  # API key is required
            optional_config_fields=["limit", "congress_number"],
            default_rate_limit_preset="moderate"
        )

    def __init__(self, config: Dict[str, Any], rate_limit_config: Optional[Dict] = None):
        """
        Initialize US Congress connector with hardcoded configuration.

        Args:
            config: Configuration dict with:
                - api_key (required): Congress.gov API key
                - limit (optional): Results per page (default: 25)
                - congress_number (optional): Congress number (e.g., 119 for 119th Congress, default: 119)
            rate_limit_config: Optional rate limiting configuration
        """
        # Validate API key
        if not config or 'api_key' not in config:
            raise ValueError("US Congress connector requires 'api_key' in config")

        api_key = config['api_key']
        congress_number = config.get('congress_number', 119)  # 119th Congress (2025-2026)
        limit = config.get('limit', 25)

        # Build hardcoded config for generic REST API connector
        rest_api_config = {
            'base_url': 'https://api.congress.gov/v3',
            'endpoint': f'/bill/{congress_number}',
            'method': 'GET',
            'headers': {
                'Accept': 'application/json'
            },
            'auth_type': 'api_key',
            'api_key': api_key,
            'api_key_header': 'x-api-key',  # Congress API uses this header
            'response_data_path': 'bills',  # Data is in response.bills
            'id_field': 'number',
            'content_field': 'title',  # Use title as content (full text requires separate API call)
            'title_field': 'title',
            'date_field': 'updateDate',
            'limit_param': 'limit',
            'offset_param': 'offset',
            'date_param': 'fromDateTime'
        }

        # Use moderate rate limiting by default
        if not rate_limit_config:
            rate_limit_config = {'preset': 'moderate'}

        # Initialize parent with hardcoded config
        super().__init__(config=rest_api_config, rate_limit_config=rate_limit_config)

        self.congress_number = congress_number
        logger.info(f"✓ US Congress connector initialized (Congress #{congress_number})")


if __name__ == '__main__':
    """Test the US Congress connector"""
    print("=" * 70)
    print("Testing US Congress Connector (Example Connector)")
    print("=" * 70)

    # Display connector metadata
    metadata = USCongressConnector.get_metadata()
    print(f"\n📋 Connector Metadata:")
    print(f"  Name: {metadata.name}")
    print(f"  Type: {metadata.source_type}")
    print(f"  Category: {metadata.category}")
    print(f"  Version: {metadata.version}")
    print(f"  Required Config: {metadata.required_config_fields}")
    print(f"  Optional Config: {metadata.optional_config_fields}")

    # Test with DEMO_KEY (limited rate)
    print("\n🔌 Creating connector with DEMO_KEY...")
    print("  Note: Get your own key at https://api.congress.gov/sign-up/")

    connector = USCongressConnector(config={'api_key': 'DEMO_KEY'})

    # Test connection
    print("\n🔌 Testing connection to Congress.gov API...")
    test_result = connector.test_connection()
    print(f"  Status: {'✅ Success' if test_result['success'] else '❌ Failed'}")
    print(f"  Message: {test_result['message']}")

    if test_result['success']:
        # Fetch documents
        print("\n📥 Fetching 3 US bills from 119th Congress...\n")
        docs = connector.fetch_documents(limit=3)

        if docs:
            print(f"✅ Successfully fetched {len(docs)} documents\n")
            for i, doc in enumerate(docs, 1):
                print(f"{'─' * 70}")
                print(f"Bill {i}:")
                print(f"  Number: {doc['id']}")
                print(f"  Title: {doc['title'][:100]}...")
                if 'updateDate' in doc['metadata']:
                    print(f"  Updated: {doc['metadata'].get('updateDate', 'N/A')}")
                print()
        else:
            print("❌ No documents retrieved")
    else:
        print("\n⚠️  Connection test failed. Cannot fetch documents.")

    print("=" * 70)
