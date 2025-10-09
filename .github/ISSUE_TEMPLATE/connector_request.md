---
name: New Connector Request
about: Request support for a new data source connector
title: '[CONNECTOR] '
labels: connector, enhancement
assignees: ''
---

## 🔌 Data Source Information

**Name**: [e.g. Confluence, Jira, HubSpot]
**Type**: [e.g. REST API, Database, File System]
**Website**: [URL to documentation]

## 📊 Use Case

Describe why you need this connector and how you would use it:

## 🔑 Authentication

How does this data source handle authentication?
- [ ] API Key
- [ ] OAuth 2.0
- [ ] Basic Auth (username/password)
- [ ] Token-based
- [ ] None (public)
- [ ] Other: _______

## 📄 Available Documentation

Links to API documentation or data source specs:
- API Docs: [URL]
- SDKs available: [Python, JavaScript, etc.]
- OpenAPI/Swagger: [URL if available]

## 🚦 Rate Limits

Does this data source have rate limits?
- Requests per hour: _______
- Requests per day: _______
- Special considerations: _______

## 📋 Data Structure

What kind of data does this source provide?
- [ ] Documents/Articles
- [ ] Issues/Tickets
- [ ] Messages/Comments
- [ ] Code/Files
- [ ] Structured data (tables)
- [ ] Other: _______

Example data structure (if known):
```json
{
  "id": "...",
  "title": "...",
  "content": "...",
  "created_at": "..."
}
```

## 🔄 Incremental Sync Support

Does the API support fetching only new/updated items?
- [ ] Yes - via timestamp filter
- [ ] Yes - via cursor/pagination
- [ ] No - only full sync
- [ ] Unknown

## 🎯 Required Configuration

What configuration would users need to provide?
- [ ] API endpoint URL
- [ ] API key/credentials
- [ ] Project/Space ID
- [ ] Filter/query parameters
- [ ] Other: _______

Example configuration:
```json
{
  "endpoint": "https://api.example.com",
  "api_key": "...",
  "project_id": "..."
}
```

## 🌟 Priority

Why is this connector important?
- [ ] Very popular data source
- [ ] Blocks my use case
- [ ] Common in enterprise
- [ ] Educational value
- [ ] Other: _______

## 🤝 Contribution

Can you help implement this connector?
- [ ] I can implement it (Python skills)
- [ ] I can provide API credentials for testing
- [ ] I can help with documentation
- [ ] I can help with testing
- [ ] I need maintainer help

## 📚 Similar Connectors

Are there similar connectors already implemented?
- Similar to: [e.g. github, notion, rest_api]
- Can be based on: [e.g. generic REST API connector]

## 🔗 Example Connector Code (if you have it)

If you've started implementing or have sample code, please share:

```python
# Your connector code here
```

## ✅ Checklist
- [ ] I have searched existing issues for this connector
- [ ] I have provided API documentation links
- [ ] I have described authentication method
- [ ] I have explained the use case
- [ ] I have indicated if I can help implement
