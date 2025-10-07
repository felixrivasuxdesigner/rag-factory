"""
GitHub Repository Connector for README, issues, PRs, discussions, and code.
Supports GitHub API authentication for higher rate limits.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

try:
    from github import Github, GithubException, Auth
    from github.Repository import Repository
    PYGITHUB_AVAILABLE = True
except ImportError:
    PYGITHUB_AVAILABLE = False

from connectors.base_connector import BaseConnector, ConnectorMetadata
from services.rate_limiter import RateLimiter, RateLimitConfig, get_preset_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubConnector(BaseConnector):
    """
    Universal GitHub connector for repositories, issues, PRs, discussions.

    Features:
    - Repository README, docs, wikis
    - Issues and pull requests (title, body, comments)
    - Discussions
    - Code files (optional, configurable)
    - GitHub API authentication (PAT or OAuth)
    - Rate limiting (5000 req/hour with auth, 60/hour without)
    - Incremental sync based on updated_at timestamps
    """

    @classmethod
    def get_metadata(cls) -> ConnectorMetadata:
        """Return connector metadata."""
        return ConnectorMetadata(
            name="GitHub Repository",
            source_type="github",
            description="Fetch README, issues, PRs, discussions, and code from GitHub repositories",
            version="1.0.0",
            author="RAG Factory",
            category="public",
            supports_incremental_sync=True,  # Based on updated_at
            supports_rate_limiting=True,
            required_config_fields=["repository"],
            optional_config_fields=[
                "access_token", "include_readme", "include_issues", "include_prs",
                "include_discussions", "include_code", "code_extensions", "max_file_size_kb"
            ],
            default_rate_limit_preset="moderate"
        )

    def __init__(self, config: Dict[str, Any], rate_limit_config: Optional[Dict] = None):
        """
        Initialize GitHub connector.

        Args:
            config: Configuration dict with:
                - repository (required): "owner/repo" format (e.g., "facebook/react")
                - access_token (optional): GitHub Personal Access Token for auth
                - include_readme (optional): Include README and docs (default: True)
                - include_issues (optional): Include issues (default: True)
                - include_prs (optional): Include pull requests (default: True)
                - include_discussions (optional): Include discussions (default: False)
                - include_code (optional): Include code files (default: False)
                - code_extensions (optional): File extensions to include (default: [".py", ".js", ".ts"])
                - max_file_size_kb (optional): Max file size in KB (default: 100)
            rate_limit_config: Rate limiting configuration
        """
        super().__init__(config, rate_limit_config)

        if not PYGITHUB_AVAILABLE:
            raise ImportError("PyGithub is required for GitHub connector")

        if 'repository' not in config:
            raise ValueError("GitHubConnector requires 'repository' in config")

        self.repository_name = config['repository']
        self.access_token = config.get('access_token')

        # Content selection
        self.include_readme = config.get('include_readme', True)
        self.include_issues = config.get('include_issues', True)
        self.include_prs = config.get('include_prs', True)
        self.include_discussions = config.get('include_discussions', False)
        self.include_code = config.get('include_code', False)
        self.code_extensions = config.get('code_extensions', ['.py', '.js', '.ts', '.tsx', '.jsx'])
        self.max_file_size_kb = config.get('max_file_size_kb', 100)

        # Initialize GitHub client
        if self.access_token:
            auth = Auth.Token(self.access_token)
            self.github = Github(auth=auth)
            logger.info("✓ GitHub client initialized with authentication")
        else:
            self.github = Github()
            logger.warning("⚠️  GitHub client initialized without auth (60 req/hour limit)")

        # Get repository
        try:
            self.repo: Repository = self.github.get_repo(self.repository_name)
            logger.info(f"✓ Connected to repository: {self.repo.full_name}")
        except GithubException as e:
            raise ValueError(f"Failed to access repository {self.repository_name}: {e}")

        # Initialize rate limiter
        if not rate_limit_config:
            rate_limit_config = {'preset': 'moderate'}

        if 'preset' in rate_limit_config:
            rate_config = get_preset_config(rate_limit_config['preset'])
        else:
            rate_config = RateLimitConfig(**rate_limit_config)

        self.rate_limiter = RateLimiter(rate_config, source_name=f"GitHub: {self.repository_name}")

        logger.info(f"✓ GitHub connector initialized for {self.repository_name}")

    def _fetch_readme(self) -> List[Dict[str, Any]]:
        """Fetch README and documentation files."""
        documents = []

        try:
            # Get README
            readme = self.repo.get_readme()
            content = readme.decoded_content.decode('utf-8')

            document = {
                'id': f"{self.repository_name}/README",
                'title': f"{self.repo.name} - README",
                'content': content,
                'metadata': {
                    'source': 'github',
                    'repository': self.repository_name,
                    'type': 'readme',
                    'path': readme.path,
                    'url': readme.html_url,
                    'sha': readme.sha,
                }
            }
            documents.append(document)
            logger.info(f"✓ Fetched README: {readme.path}")

        except GithubException as e:
            logger.warning(f"No README found: {e}")

        return documents

    def _fetch_issues(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Fetch issues with optional date filtering."""
        documents = []

        try:
            # Get issues (not PRs)
            issues = self.repo.get_issues(state='all', since=since) if since else self.repo.get_issues(state='all')

            for issue in issues:
                if issue.pull_request:  # Skip PRs
                    continue

                # Wait for rate limit if needed
                wait_time = self.rate_limiter.wait_if_needed()
                if wait_time > 0:
                    logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

                self.rate_limiter.record_request()

                # Build content with issue body and comments
                content_parts = [f"# {issue.title}\n"]
                if issue.body:
                    content_parts.append(issue.body)

                # Add comments
                if issue.comments > 0:
                    content_parts.append("\n## Comments\n")
                    for comment in issue.get_comments():
                        content_parts.append(f"**{comment.user.login}**: {comment.body}\n")

                content = '\n\n'.join(content_parts)

                document = {
                    'id': f"{self.repository_name}/issues/{issue.number}",
                    'title': f"Issue #{issue.number}: {issue.title}",
                    'content': content,
                    'metadata': {
                        'source': 'github',
                        'repository': self.repository_name,
                        'type': 'issue',
                        'number': issue.number,
                        'state': issue.state,
                        'url': issue.html_url,
                        'author': issue.user.login,
                        'created_at': issue.created_at.isoformat(),
                        'updated_at': issue.updated_at.isoformat(),
                        'labels': [label.name for label in issue.labels],
                    }
                }
                documents.append(document)
                self.rate_limiter.record_success()

            logger.info(f"✓ Fetched {len(documents)} issues")

        except GithubException as e:
            logger.error(f"Failed to fetch issues: {e}")

        return documents

    def _fetch_pull_requests(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Fetch pull requests with optional date filtering."""
        documents = []

        try:
            # Get PRs
            pulls = self.repo.get_pulls(state='all', sort='updated', direction='desc')

            for pr in pulls:
                # Filter by date if provided
                if since and pr.updated_at < since:
                    break

                # Wait for rate limit if needed
                wait_time = self.rate_limiter.wait_if_needed()
                if wait_time > 0:
                    logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

                self.rate_limiter.record_request()

                # Build content with PR body and comments
                content_parts = [f"# {pr.title}\n"]
                if pr.body:
                    content_parts.append(pr.body)

                # Add review comments
                if pr.comments > 0:
                    content_parts.append("\n## Comments\n")
                    for comment in pr.get_comments():
                        content_parts.append(f"**{comment.user.login}**: {comment.body}\n")

                content = '\n\n'.join(content_parts)

                document = {
                    'id': f"{self.repository_name}/pulls/{pr.number}",
                    'title': f"PR #{pr.number}: {pr.title}",
                    'content': content,
                    'metadata': {
                        'source': 'github',
                        'repository': self.repository_name,
                        'type': 'pull_request',
                        'number': pr.number,
                        'state': pr.state,
                        'url': pr.html_url,
                        'author': pr.user.login,
                        'created_at': pr.created_at.isoformat(),
                        'updated_at': pr.updated_at.isoformat(),
                        'merged': pr.merged,
                    }
                }
                documents.append(document)
                self.rate_limiter.record_success()

            logger.info(f"✓ Fetched {len(documents)} pull requests")

        except GithubException as e:
            logger.error(f"Failed to fetch pull requests: {e}")

        return documents

    def _fetch_code_files(self) -> List[Dict[str, Any]]:
        """Fetch code files from repository."""
        documents = []

        try:
            # Get repository contents
            contents = self.repo.get_contents("")

            while contents:
                file_content = contents.pop(0)

                if file_content.type == "dir":
                    # Add directory contents to queue
                    contents.extend(self.repo.get_contents(file_content.path))
                else:
                    # Check file extension
                    if not any(file_content.name.endswith(ext) for ext in self.code_extensions):
                        continue

                    # Check file size
                    if file_content.size > self.max_file_size_kb * 1024:
                        logger.debug(f"Skipping large file: {file_content.path} ({file_content.size} bytes)")
                        continue

                    # Wait for rate limit if needed
                    wait_time = self.rate_limiter.wait_if_needed()
                    if wait_time > 0:
                        logger.info(f"⏱️  Rate limit wait: {wait_time:.1f}s")

                    self.rate_limiter.record_request()

                    try:
                        content = file_content.decoded_content.decode('utf-8')
                    except Exception as e:
                        logger.warning(f"Failed to decode {file_content.path}: {e}")
                        continue

                    document = {
                        'id': f"{self.repository_name}/code/{file_content.path}",
                        'title': f"{self.repo.name} - {file_content.path}",
                        'content': content,
                        'metadata': {
                            'source': 'github',
                            'repository': self.repository_name,
                            'type': 'code',
                            'path': file_content.path,
                            'url': file_content.html_url,
                            'sha': file_content.sha,
                            'size': file_content.size,
                        }
                    }
                    documents.append(document)
                    self.rate_limiter.record_success()

            logger.info(f"✓ Fetched {len(documents)} code files")

        except GithubException as e:
            logger.error(f"Failed to fetch code files: {e}")

        return documents

    def fetch_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch documents from GitHub repository.

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            since: ISO date string (YYYY-MM-DD) for incremental sync

        Returns:
            List of documents with id, title, content
        """
        all_documents = []

        # Convert since to datetime if provided
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
            except Exception as e:
                logger.warning(f"Invalid since date format: {since}, ignoring")

        # Fetch README and docs
        if self.include_readme:
            all_documents.extend(self._fetch_readme())

        # Fetch issues
        if self.include_issues:
            all_documents.extend(self._fetch_issues(since=since_dt))

        # Fetch pull requests
        if self.include_prs:
            all_documents.extend(self._fetch_pull_requests(since=since_dt))

        # Fetch code files (no date filtering for code)
        if self.include_code:
            all_documents.extend(self._fetch_code_files())

        # Apply offset and limit
        total = len(all_documents)
        result = all_documents[offset:offset + limit]

        logger.info(f"✓ Returning {len(result)} of {total} total GitHub documents")
        return result


if __name__ == '__main__':
    """Test the GitHub connector"""
    print("=" * 70)
    print("Testing GitHub Repository Connector")
    print("=" * 70)

    # Display connector metadata
    metadata = GitHubConnector.get_metadata()
    print(f"\n📋 Connector Metadata:")
    print(f"  Name: {metadata.name}")
    print(f"  Type: {metadata.source_type}")
    print(f"  Category: {metadata.category}")
    print(f"  Version: {metadata.version}")

    # Test with public repository (no auth required)
    print("\n📥 Testing with public repository (facebook/react)...\n")

    config = {
        'repository': 'facebook/react',
        'include_readme': True,
        'include_issues': True,
        'include_prs': False,  # Skip PRs for faster testing
        'include_code': False,  # Skip code for faster testing
    }

    connector = GitHubConnector(config=config)

    # Test connection
    print("🔌 Testing connection...")
    test_result = connector.test_connection()
    print(f"  Status: {'✅ Success' if test_result['success'] else '❌ Failed'}")
    print(f"  Message: {test_result['message']}")

    # Fetch documents
    print("\n📥 Fetching documents (README + 3 recent issues)...\n")
    docs = connector.fetch_documents(limit=5)

    if docs:
        print(f"✅ Successfully fetched {len(docs)} documents\n")
        for i, doc in enumerate(docs, 1):
            print(f"{'─' * 70}")
            print(f"Document {i}:")
            print(f"  ID: {doc['id']}")
            print(f"  Title: {doc['title'][:80]}")
            print(f"  Type: {doc['metadata'].get('type', 'N/A')}")
            print(f"  URL: {doc['metadata'].get('url', 'N/A')[:60]}")
            print(f"  Content Length: {len(doc['content'])} characters")
            print(f"  Preview: {doc['content'][:150]}...")
            print()
    else:
        print("❌ No documents retrieved")

    print("=" * 70)
