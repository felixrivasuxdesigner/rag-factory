"""
Google Drive Connector for Docs, Sheets, PDFs, and other files.
Supports OAuth2 authentication and service account credentials.
"""

import logging
import io
import os
from typing import List, Dict, Optional, Any
from datetime import datetime

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from connectors.base_connector import BaseConnector, ConnectorMetadata
from services.rate_limiter import RateLimiter, RateLimitConfig, get_preset_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleDriveConnector(BaseConnector):
    """
    Universal Google Drive connector for documents, spreadsheets, and files.

    Features:
    - Google Docs (exported as plain text)
    - Google Sheets (exported as CSV)
    - PDF files
    - Text files
    - OAuth2 or Service Account authentication
    - Folder selection
    - Incremental sync based on modifiedTime
    - Rate limiting
    """

    # Google Drive MIME types
    MIME_TYPES = {
        'google_doc': 'application/vnd.google-apps.document',
        'google_sheet': 'application/vnd.google-apps.spreadsheet',
        'pdf': 'application/pdf',
        'text': 'text/plain',
        'markdown': 'text/markdown',
    }

    # Export MIME types
    EXPORT_FORMATS = {
        'google_doc': 'text/plain',  # Export Docs as plain text
        'google_sheet': 'text/csv',   # Export Sheets as CSV
    }

    @classmethod
    def get_metadata(cls) -> ConnectorMetadata:
        """Return connector metadata."""
        return ConnectorMetadata(
            name="Google Drive",
            source_type="google_drive",
            description="Fetch Google Docs, Sheets, PDFs, and other files from Google Drive",
            version="1.0.0",
            author="RAG Factory",
            category="public",
            supports_incremental_sync=True,  # Based on modifiedTime
            supports_rate_limiting=True,
            required_config_fields=["credentials"],
            optional_config_fields=[
                "folder_id", "include_docs", "include_sheets", "include_pdfs",
                "include_text_files", "recursive", "max_file_size_mb"
            ],
            default_rate_limit_preset="moderate"
        )

    def __init__(self, config: Dict[str, Any], rate_limit_config: Optional[Dict] = None):
        """
        Initialize Google Drive connector.

        Args:
            config: Configuration dict with:
                - credentials (required): Path to OAuth2 credentials JSON or service account JSON
                - folder_id (optional): Google Drive folder ID to scan (default: root)
                - include_docs (optional): Include Google Docs (default: True)
                - include_sheets (optional): Include Google Sheets (default: True)
                - include_pdfs (optional): Include PDF files (default: True)
                - include_text_files (optional): Include text/markdown files (default: True)
                - recursive (optional): Scan subfolders recursively (default: True)
                - max_file_size_mb (optional): Max file size in MB (default: 10)
            rate_limit_config: Rate limiting configuration
        """
        super().__init__(config, rate_limit_config)

        if not GOOGLE_AVAILABLE:
            raise ImportError("Google API libraries required: pip install google-auth google-api-python-client")

        if 'credentials' not in config:
            raise ValueError("GoogleDriveConnector requires 'credentials' (path to credentials JSON)")

        self.credentials_path = config['credentials']
        self.folder_id = config.get('folder_id', 'root')
        self.include_docs = config.get('include_docs', True)
        self.include_sheets = config.get('include_sheets', True)
        self.include_pdfs = config.get('include_pdfs', True)
        self.include_text_files = config.get('include_text_files', True)
        self.recursive = config.get('recursive', True)
        self.max_file_size_mb = config.get('max_file_size_mb', 10)

        # Initialize Google Drive API
        self.service = self._initialize_service()

        # Initialize rate limiter
        if not rate_limit_config:
            rate_limit_config = {'preset': 'moderate'}

        if 'preset' in rate_limit_config:
            rate_config = get_preset_config(rate_limit_config['preset'])
        else:
            rate_config = RateLimitConfig(**rate_limit_config)

        self.rate_limiter = RateLimiter(rate_config, source_name="Google Drive")

        logger.info(f"✓ Google Drive connector initialized (folder: {self.folder_id})")

    def _initialize_service(self):
        """Initialize Google Drive API service with credentials."""
        try:
            # Try to load credentials
            if not os.path.exists(self.credentials_path):
                raise ValueError(f"Credentials file not found: {self.credentials_path}")

            # Check if it's a service account or OAuth2 credentials
            import json
            with open(self.credentials_path, 'r') as f:
                creds_data = json.load(f)

            if creds_data.get('type') == 'service_account':
                # Service account
                logger.info("Using Service Account authentication")
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
            else:
                # OAuth2 credentials
                logger.info("Using OAuth2 credentials")
                credentials = Credentials.from_authorized_user_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/drive.readonly']
                )

                # Refresh if expired
                if credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())

            # Build Drive API service
            service = build('drive', 'v3', credentials=credentials)
            logger.info("✓ Google Drive API service initialized")
            return service

        except Exception as e:
            raise ValueError(f"Failed to initialize Google Drive API: {e}")

    def _build_query(self, since: Optional[datetime] = None) -> str:
        """Build Google Drive API query string."""
        queries = []

        # Folder filter
        if self.folder_id != 'root':
            queries.append(f"'{self.folder_id}' in parents")

        # File type filters
        mime_filters = []
        if self.include_docs:
            mime_filters.append(f"mimeType='{self.MIME_TYPES['google_doc']}'")
        if self.include_sheets:
            mime_filters.append(f"mimeType='{self.MIME_TYPES['google_sheet']}'")
        if self.include_pdfs:
            mime_filters.append(f"mimeType='{self.MIME_TYPES['pdf']}'")
        if self.include_text_files:
            mime_filters.append(f"mimeType='{self.MIME_TYPES['text']}'")
            mime_filters.append(f"mimeType='{self.MIME_TYPES['markdown']}'")

        if mime_filters:
            queries.append(f"({' or '.join(mime_filters)})")

        # Date filter for incremental sync
        if since:
            since_str = since.isoformat()
            queries.append(f"modifiedTime > '{since_str}'")

        # Exclude trashed files
        queries.append("trashed=false")

        return ' and '.join(queries)

    def _list_files(self, since: Optional[datetime] = None) -> List[Dict]:
        """List files from Google Drive."""
        query = self._build_query(since)
        files = []

        try:
            page_token = None
            while True:
                # Wait for rate limit if needed
                wait_time = self.rate_limiter.wait_if_needed()
                if wait_time > 0:
                    logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

                self.rate_limiter.record_request()

                # List files
                results = self.service.files().list(
                    q=query,
                    pageSize=100,
                    pageToken=page_token,
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink)"
                ).execute()

                self.rate_limiter.record_success()

                items = results.get('files', [])
                files.extend(items)

                page_token = results.get('nextPageToken')
                if not page_token:
                    break

            logger.info(f"✓ Found {len(files)} files in Google Drive")
            return files

        except HttpError as e:
            logger.error(f"Failed to list files: {e}")
            raise

    def _download_file_content(self, file_id: str, mime_type: str) -> str:
        """Download and extract file content."""
        try:
            # Wait for rate limit if needed
            wait_time = self.rate_limiter.wait_if_needed()
            if wait_time > 0:
                logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

            self.rate_limiter.record_request()

            # Export Google Docs/Sheets, download others
            if mime_type in self.EXPORT_FORMATS:
                # Export Google Doc/Sheet
                export_mime = self.EXPORT_FORMATS[mime_type]
                request = self.service.files().export_media(fileId=file_id, mimeType=export_mime)
            else:
                # Download regular file
                request = self.service.files().get_media(fileId=file_id)

            # Download content
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            self.rate_limiter.record_success()

            # Decode content
            content = file_buffer.getvalue().decode('utf-8', errors='ignore')
            return content

        except HttpError as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            return ""

    def fetch_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch documents from Google Drive.

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            since: ISO date string (YYYY-MM-DD) for incremental sync

        Returns:
            List of documents with id, title, content
        """
        # Convert since to datetime if provided
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
            except Exception as e:
                logger.warning(f"Invalid since date format: {since}, ignoring")

        # List files
        files = self._list_files(since=since_dt)

        # Process files
        all_documents = []
        for file_info in files:
            try:
                # Check file size
                file_size = int(file_info.get('size', 0))
                max_size_bytes = self.max_file_size_mb * 1024 * 1024
                if file_size > max_size_bytes:
                    logger.debug(f"Skipping large file: {file_info['name']} ({file_size} bytes)")
                    continue

                # Download content
                content = self._download_file_content(
                    file_id=file_info['id'],
                    mime_type=file_info['mimeType']
                )

                if not content:
                    logger.warning(f"Empty content for {file_info['name']}")
                    continue

                # Create document
                document = {
                    'id': file_info['id'],
                    'title': file_info['name'],
                    'content': content,
                    'metadata': {
                        'source': 'google_drive',
                        'mime_type': file_info['mimeType'],
                        'size': file_size,
                        'modified_time': file_info.get('modifiedTime'),
                        'url': file_info.get('webViewLink', ''),
                    }
                }

                all_documents.append(document)
                logger.info(f"✓ Processed: {file_info['name']}")

            except Exception as e:
                logger.error(f"Failed to process file {file_info.get('name', 'unknown')}: {e}")
                continue

        # Apply offset and limit
        total = len(all_documents)
        result = all_documents[offset:offset + limit]

        logger.info(f"✓ Returning {len(result)} of {total} total Google Drive documents")
        return result


if __name__ == '__main__':
    """Test the Google Drive connector"""
    print("=" * 70)
    print("Testing Google Drive Connector")
    print("=" * 70)

    # Display connector metadata
    metadata = GoogleDriveConnector.get_metadata()
    print(f"\n📋 Connector Metadata:")
    print(f"  Name: {metadata.name}")
    print(f"  Type: {metadata.source_type}")
    print(f"  Category: {metadata.category}")
    print(f"  Version: {metadata.version}")

    print("\n" + "=" * 70)
    print("⚠️  MANUAL TESTING REQUIRED")
    print("=" * 70)
    print("\nTo test this connector, you need:")
    print("1. Google Cloud Project with Drive API enabled")
    print("2. OAuth2 credentials or Service Account JSON")
    print("3. Credentials file path in config")
    print("\nExample configuration:")
    print("""
config = {
    'credentials': '/path/to/credentials.json',
    'folder_id': 'your-folder-id',  # or 'root' for root folder
    'include_docs': True,
    'include_sheets': True,
    'include_pdfs': True,
}

connector = GoogleDriveConnector(config=config)
docs = connector.fetch_documents(limit=5)
    """)
    print("\n" + "=" * 70)
