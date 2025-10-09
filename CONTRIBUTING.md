# Contributing to RAG Factory

Thank you for your interest in contributing to RAG Factory! This document provides guidelines and instructions for contributing to the project.

## 🎯 Ways to Contribute

### 1. Report Bugs 🐛
Found a bug? Please [open an issue](https://github.com/felixrivasuxdesigner/rag-factory/issues/new?template=bug_report.md) with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Docker version, etc.)

### 2. Suggest Features 💡
Have an idea? [Open a feature request](https://github.com/felixrivasuxdesigner/rag-factory/issues/new?template=feature_request.md) with:
- Use case description
- Expected behavior
- Why it would benefit the community

### 3. Contribute Code 🚀

#### Easy Contributions (Good First Issues)
- Add new data source connectors
- Improve error messages
- Write documentation
- Add examples and tutorials
- Fix typos and formatting

#### Medium Contributions
- Optimize SQL queries
- Improve UI/UX components
- Add tests (unit/integration)
- Implement new chunking strategies

#### Advanced Contributions
- Add re-ranking for search results
- Implement WebSocket for real-time updates
- Create Kubernetes deployment configs
- Add multi-modal support (images, audio)

## 🛠️ Development Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- Git

### Local Development

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/rag-factory.git
   cd rag-factory
   ```

2. **Start Infrastructure**
   ```bash
   docker-compose -f docker/docker-compose.yml up -d db redis ollama
   ```

3. **Backend Development**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt

   # Run API locally
   uvicorn api.main:app --reload --port 8000

   # Run worker locally (in another terminal)
   rq worker --url redis://localhost:6380/0 rag-tasks
   ```

4. **Frontend Development**
   ```bash
   cd frontend
   npm install
   npm run dev  # Opens on http://localhost:3000
   ```

5. **Run Tests**
   ```bash
   # Backend tests
   python -m pytest

   # API integration test
   python test_api.py

   # Frontend tests
   cd frontend && npm test
   ```

## 📝 Code Guidelines

### Python (Backend)
- Follow PEP 8 style guide
- Use type hints where possible
- Write docstrings for functions/classes
- Keep functions small and focused
- Use meaningful variable names

```python
# Good ✅
def fetch_documents(source_id: int, limit: int = 100) -> List[Document]:
    """Fetch documents from a data source.

    Args:
        source_id: ID of the data source
        limit: Maximum number of documents to fetch

    Returns:
        List of Document objects
    """
    # Implementation...
```

### TypeScript (Frontend)
- Use TypeScript, not JavaScript
- Use functional components with hooks
- Keep components small (< 200 lines)
- Use meaningful prop names
- Add JSDoc comments for complex logic

```typescript
// Good ✅
interface ProjectCardProps {
  project: Project;
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
}

const ProjectCard: React.FC<ProjectCardProps> = ({ project, onEdit, onDelete }) => {
  // Implementation...
};
```

### Git Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: Add RSS feed connector
fix: Resolve embedding timeout issue
docs: Update API usage guide
test: Add unit tests for chunking service
refactor: Simplify database connection logic
```

## 🔌 Creating a New Connector

The easiest way to contribute! Follow these steps:

### 1. Create Connector File
```bash
# Create in backend/connectors/
touch backend/connectors/my_connector.py
```

### 2. Implement BaseConnector Interface
```python
from typing import List, Dict, Any, Optional
from datetime import datetime

class MyConnector:
    """Connector for My Data Source."""

    # Connector metadata
    TYPE = "my_source"
    CATEGORY = "public"  # or "example" or "private"
    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Initialize your connector

    def fetch_documents(self, limit: int = 100,
                       last_sync: Optional[datetime] = None) -> List[Dict]:
        """Fetch documents from source.

        Returns:
            List of dicts with keys: id, title, content, metadata
        """
        documents = []
        # Your implementation here
        return documents

    def validate_config(self) -> bool:
        """Validate connector configuration."""
        required_fields = ['api_key', 'endpoint']
        return all(field in self.config for field in required_fields)
```

### 3. Register Connector in Worker
Edit `backend/workers/ingestion_tasks.py`:
```python
from connectors.my_connector import MyConnector

# Add to connector mapping
if source_type == 'my_source':
    connector = MyConnector(source_config)
```

### 4. Add Frontend Support
Edit `frontend/src/utils/exampleConfigs.ts`:
```typescript
export const connectorTypes = [
  // ... existing types
  {
    type: 'my_source',
    name: 'My Data Source',
    icon: 'Database',
    description: 'Connect to My Data Source API',
    configSchema: {
      api_key: { type: 'text', required: true, label: 'API Key' },
      endpoint: { type: 'text', required: true, label: 'API Endpoint' }
    }
  }
];
```

### 5. Add Documentation
Create `docs/connectors/my_source.md` with:
- What the connector does
- Required configuration
- Example usage
- Rate limits/considerations

### 6. Test Your Connector
```bash
# Create test project and source via API
curl -X POST http://localhost:8000/sources -d '{
  "project_id": 1,
  "name": "Test My Source",
  "source_type": "my_source",
  "config": {"api_key": "...", "endpoint": "..."}
}'

# Trigger ingestion
curl -X POST http://localhost:8000/jobs -d '{"project_id": 1, "source_id": X}'
```

## 🧪 Testing Guidelines

### Unit Tests
- Write tests for new functions
- Aim for >80% coverage
- Use pytest fixtures for setup

```python
# tests/test_my_connector.py
def test_fetch_documents():
    connector = MyConnector(config={'api_key': 'test'})
    docs = connector.fetch_documents(limit=5)
    assert len(docs) <= 5
    assert all('id' in doc for doc in docs)
```

### Integration Tests
- Test full workflow (API → Worker → DB)
- Use test database/fixtures
- Clean up after tests

## 📚 Documentation

### API Documentation
- All endpoints must have OpenAPI/Swagger docs
- Use Pydantic models for request/response
- Include example requests

### Code Documentation
- Docstrings for all public functions/classes
- Inline comments for complex logic
- README for each major component

### User Documentation
- Update README.md for user-facing changes
- Add examples to API_USAGE.md
- Create tutorials for new features

## 🚀 Pull Request Process

### Before Submitting
- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No sensitive data (API keys, passwords)
- [ ] Commit messages follow convention

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No new warnings
```

### Review Process
1. Automated checks run (linting, tests)
2. Maintainer review (usually within 48 hours)
3. Address feedback
4. Merge when approved

## 📋 Connector Contribution Checklist

- [ ] Connector implements required interface
- [ ] Handles errors gracefully
- [ ] Respects rate limits
- [ ] Supports incremental sync (if applicable)
- [ ] Has configuration validation
- [ ] Includes unit tests
- [ ] Documentation added
- [ ] Example configuration provided
- [ ] Frontend integration (if UI needed)

## 🤝 Community Guidelines

### Code of Conduct
- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- No harassment or discrimination

### Getting Help
- Check existing issues/discussions
- Ask in GitHub Discussions
- Join our Discord (coming soon)
- Tag maintainers if urgent

### Recognition
Contributors are recognized in:
- README.md contributors section
- Release notes
- Special "Contributor" badge (coming soon)

## 🎁 Rewards for Contributors

### Good First Issue
- Get started with easy tasks
- Mentorship from maintainers
- Recognition in next release

### Connector Marketplace
- Your connector featured on website
- Author credit with link
- Downloads/usage stats

### Top Contributors
- Special Discord role
- Priority feature requests
- Beta access to new features

## 📞 Contact

- **Issues**: [GitHub Issues](https://github.com/felixrivasuxdesigner/vector-doc-ingestion/issues)
- **Discussions**: [GitHub Discussions](https://github.com/felixrivasuxdesigner/vector-doc-ingestion/discussions)
- **Email**: felix.rivas.ux@gmail.com
- **Discord**: (coming soon)

---

## 📖 Resources

- [Project Roadmap](ROADMAP.md)
- [API Documentation](http://localhost:8000/docs)
- [Architecture Guide](CLAUDE.md)
- [API Usage Examples](API_USAGE.md)

---

Thank you for contributing to RAG Factory! 🎉

*Built with ❤️ by the RAG Factory community*
