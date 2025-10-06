"""
Base connector class for RAG Factory plugin architecture.
All connectors should inherit from this base class to ensure consistency.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConnectorMetadata:
    """
    Metadata about a connector implementation.
    """
    def __init__(
        self,
        name: str,
        source_type: str,
        description: str,
        version: str = "1.0.0",
        author: str = "RAG Factory",
        category: str = "public",
        supports_incremental_sync: bool = False,
        supports_rate_limiting: bool = False,
        required_config_fields: List[str] = None,
        optional_config_fields: List[str] = None,
        default_rate_limit_preset: Optional[str] = None
    ):
        """
        Initialize connector metadata.

        Args:
            name: Human-readable connector name (e.g., "GitHub Repository")
            source_type: Unique type identifier (e.g., "github")
            description: Brief description of what this connector does
            version: Semantic version of the connector
            author: Connector author/maintainer
            category: Connector category:
                     - "public": Universal/shareable connectors (GitHub, Slack, etc.)
                     - "example": Pre-configured examples of generic connectors
                     - "private": User-specific/internal connectors
            supports_incremental_sync: Whether connector supports date-based filtering
            supports_rate_limiting: Whether connector implements rate limiting
            required_config_fields: List of required config keys
            optional_config_fields: List of optional config keys
            default_rate_limit_preset: Default rate limit preset to use
        """
        self.name = name
        self.source_type = source_type
        self.description = description
        self.version = version
        self.author = author
        self.category = category
        self.supports_incremental_sync = supports_incremental_sync
        self.supports_rate_limiting = supports_rate_limiting
        self.required_config_fields = required_config_fields or []
        self.optional_config_fields = optional_config_fields or []
        self.default_rate_limit_preset = default_rate_limit_preset

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            'name': self.name,
            'source_type': self.source_type,
            'description': self.description,
            'version': self.version,
            'author': self.author,
            'category': self.category,
            'supports_incremental_sync': self.supports_incremental_sync,
            'supports_rate_limiting': self.supports_rate_limiting,
            'required_config_fields': self.required_config_fields,
            'optional_config_fields': self.optional_config_fields,
            'default_rate_limit_preset': self.default_rate_limit_preset
        }


class BaseConnector(ABC):
    """
    Abstract base class for all RAG Factory connectors.

    All connectors must implement the core methods defined here.
    This ensures a consistent interface for the ingestion pipeline.
    """

    def __init__(self, config: Dict[str, Any], rate_limit_config: Optional[Dict] = None):
        """
        Initialize connector.

        Args:
            config: Connector-specific configuration
            rate_limit_config: Optional rate limiting configuration
        """
        self.config = config
        self.rate_limit_config = rate_limit_config
        self._validate_config()

    @classmethod
    @abstractmethod
    def get_metadata(cls) -> ConnectorMetadata:
        """
        Return metadata about this connector.

        Returns:
            ConnectorMetadata instance describing this connector
        """
        pass

    @abstractmethod
    def fetch_documents(
        self,
        limit: int = 10,
        offset: int = 0,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch documents from the source.

        Args:
            limit: Maximum number of documents to fetch
            offset: Number of documents to skip (for pagination)
            since: ISO date string (YYYY-MM-DD) for incremental sync.
                   Only fetch documents created/updated after this date.

        Returns:
            List of document dictionaries. Each document must have:
            - 'id': Unique document identifier (str)
            - 'content': Full text content (str)
            - 'title': Document title (str, optional)
            - Additional metadata fields as needed

        Raises:
            NotImplementedError: If connector doesn't support incremental sync but since is provided
            ConnectionError: If unable to connect to data source
            ValueError: If configuration is invalid
        """
        pass

    def validate_config(self) -> bool:
        """
        Validate connector configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        metadata = self.get_metadata()

        # Check required fields
        for field in metadata.required_config_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")

        return True

    def _validate_config(self):
        """Internal validation called during __init__."""
        try:
            self.validate_config()
        except ValueError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to the data source.

        Returns:
            Dictionary with test results:
            - 'success': bool
            - 'message': str
            - 'details': dict (optional)
        """
        try:
            # Try fetching 1 document as a connection test
            docs = self.fetch_documents(limit=1)
            return {
                'success': True,
                'message': f'Successfully connected and fetched {len(docs)} document(s)',
                'details': {
                    'connector': self.get_metadata().name,
                    'documents_retrieved': len(docs)
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'details': {
                    'connector': self.get_metadata().name,
                    'error': str(e)
                }
            }

    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for this connector's configuration.

        Returns:
            JSON schema dictionary describing required/optional fields
        """
        metadata = self.get_metadata()

        properties = {}
        required = []

        # Add required fields
        for field in metadata.required_config_fields:
            properties[field] = {"type": "string"}  # Default to string, override in subclass
            required.append(field)

        # Add optional fields
        for field in metadata.optional_config_fields:
            properties[field] = {"type": "string"}

        schema = {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": True
        }

        return schema

    def __repr__(self) -> str:
        """String representation of connector."""
        metadata = self.get_metadata()
        return f"<{metadata.name} v{metadata.version} ({metadata.source_type})>"
