"""
Connector registry for auto-discovery and management of available connectors.
This module scans the connectors directory and registers all available connector classes.
"""

import os
import importlib
import inspect
from typing import Dict, List, Type, Optional
from pathlib import Path
import logging

from connectors.base_connector import BaseConnector, ConnectorMetadata

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Registry for managing and discovering available connectors.
    Automatically scans the connectors directory and registers all BaseConnector subclasses.
    """

    def __init__(self):
        """Initialize the registry."""
        self._connectors: Dict[str, Type[BaseConnector]] = {}
        self._metadata_cache: Dict[str, ConnectorMetadata] = {}
        self._discover_connectors()

    def _discover_connectors(self):
        """
        Auto-discover all connector classes in the connectors directory.
        Looks for classes that inherit from BaseConnector.
        """
        # Get the connectors directory path
        connectors_dir = Path(__file__).parent

        # Scan all Python files in the connectors directory
        for filepath in connectors_dir.glob("*.py"):
            # Skip special files
            if filepath.name.startswith("__") or filepath.name in ["base_connector.py", "registry.py"]:
                continue

            module_name = filepath.stem
            try:
                # Import the module
                module = importlib.import_module(f"connectors.{module_name}")

                # Find all classes in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if it's a BaseConnector subclass (but not BaseConnector itself)
                    if (
                        issubclass(obj, BaseConnector)
                        and obj is not BaseConnector
                        and obj.__module__ == module.__name__
                    ):
                        # Get metadata
                        try:
                            metadata = obj.get_metadata()
                            source_type = metadata.source_type

                            # Register the connector
                            self._connectors[source_type] = obj
                            self._metadata_cache[source_type] = metadata

                            logger.info(
                                f"Registered connector: {metadata.name} "
                                f"(type={source_type}, version={metadata.version})"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to get metadata for {name} in {module_name}: {e}"
                            )

            except Exception as e:
                logger.warning(f"Failed to import connector module {module_name}: {e}")

        logger.info(f"Connector discovery complete: {len(self._connectors)} connectors registered")

    def get_connector_class(self, source_type: str) -> Optional[Type[BaseConnector]]:
        """
        Get a connector class by its source type.

        Args:
            source_type: The source type identifier (e.g., 'chile_fulltext')

        Returns:
            The connector class, or None if not found
        """
        return self._connectors.get(source_type)

    def get_metadata(self, source_type: str) -> Optional[ConnectorMetadata]:
        """
        Get metadata for a connector by its source type.

        Args:
            source_type: The source type identifier

        Returns:
            ConnectorMetadata instance, or None if not found
        """
        return self._metadata_cache.get(source_type)

    def list_connectors(self) -> List[Dict[str, any]]:
        """
        List all registered connectors with their metadata.

        Returns:
            List of connector metadata dictionaries
        """
        return [metadata.to_dict() for metadata in self._metadata_cache.values()]

    def get_connector_types(self) -> List[str]:
        """
        Get a list of all registered connector type identifiers.

        Returns:
            List of source type strings
        """
        return list(self._connectors.keys())

    def is_registered(self, source_type: str) -> bool:
        """
        Check if a connector type is registered.

        Args:
            source_type: The source type identifier

        Returns:
            True if registered, False otherwise
        """
        return source_type in self._connectors

    def create_connector(
        self,
        source_type: str,
        config: Dict,
        rate_limit_config: Optional[Dict] = None
    ) -> Optional[BaseConnector]:
        """
        Create a connector instance by source type.

        Args:
            source_type: The source type identifier
            config: Configuration dict for the connector
            rate_limit_config: Optional rate limiting configuration

        Returns:
            Connector instance, or None if source_type not found

        Raises:
            ValueError: If connector class is not found or instantiation fails
        """
        connector_class = self.get_connector_class(source_type)

        if not connector_class:
            raise ValueError(f"Unknown connector type: {source_type}")

        try:
            return connector_class(config=config, rate_limit_config=rate_limit_config)
        except Exception as e:
            logger.error(f"Failed to create connector {source_type}: {e}", exc_info=True)
            raise


# Global registry instance
_registry = None


def get_registry() -> ConnectorRegistry:
    """
    Get the global connector registry instance (singleton).

    Returns:
        ConnectorRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ConnectorRegistry()
    return _registry


# Convenience functions
def list_connectors() -> List[Dict[str, any]]:
    """List all registered connectors."""
    return get_registry().list_connectors()


def get_connector_metadata(source_type: str) -> Optional[ConnectorMetadata]:
    """Get metadata for a specific connector."""
    return get_registry().get_metadata(source_type)


def create_connector(
    source_type: str,
    config: Dict,
    rate_limit_config: Optional[Dict] = None
) -> BaseConnector:
    """Create a connector instance."""
    return get_registry().create_connector(source_type, config, rate_limit_config)


if __name__ == '__main__':
    """Test the registry"""
    print("=" * 70)
    print("Testing Connector Registry")
    print("=" * 70)

    registry = get_registry()

    print(f"\n📋 Registered Connectors: {len(registry.get_connector_types())}")
    print("-" * 70)

    for connector_info in registry.list_connectors():
        print(f"\n✅ {connector_info['name']}")
        print(f"   Type: {connector_info['source_type']}")
        print(f"   Version: {connector_info['version']}")
        print(f"   Author: {connector_info['author']}")
        print(f"   Description: {connector_info['description']}")
        print(f"   Incremental Sync: {connector_info['supports_incremental_sync']}")
        print(f"   Rate Limiting: {connector_info['supports_rate_limiting']}")
        print(f"   Required Config: {connector_info['required_config_fields']}")
        print(f"   Optional Config: {connector_info['optional_config_fields']}")

    print("\n" + "=" * 70)
    print(f"Total: {len(registry.get_connector_types())} connectors ready")
    print("=" * 70)
