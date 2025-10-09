---
name: Bug Report
about: Report a bug to help us improve RAG Factory
title: '[BUG] '
labels: bug
assignees: ''
---

## 🐛 Bug Description
A clear and concise description of what the bug is.

## 📋 Steps to Reproduce
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '...'
3. Execute command '...'
4. See error

## ✅ Expected Behavior
A clear description of what you expected to happen.

## ❌ Actual Behavior
What actually happened instead.

## 📸 Screenshots/Logs
If applicable, add screenshots or paste error logs:

```
Paste logs here
```

## 🖥️ Environment
- **OS**: [e.g. macOS 14, Ubuntu 22.04, Windows 11]
- **Docker Version**: [e.g. 24.0.5]
- **Docker Compose Version**: [e.g. 2.20.2]
- **RAG Factory Version**: [e.g. v0.8, main branch, commit hash]
- **Browser** (if frontend issue): [e.g. Chrome 120, Firefox 121]

## 📦 Service Health
Run `curl http://localhost:8000/health` and paste output:

```json
{
  "api": "...",
  "database": "...",
  "redis": "...",
  "ollama": "..."
}
```

## 🔍 Additional Context
Add any other context about the problem here:
- Which connector were you using?
- How many documents were being processed?
- Did this work before?
- Any custom configuration?

## 🚑 Workaround (if found)
If you found a temporary workaround, please share it here.

## ✅ Checklist
- [ ] I have searched existing issues to avoid duplicates
- [ ] I have included all relevant environment details
- [ ] I have included error logs/screenshots
- [ ] I have tried restarting Docker services
- [ ] I can reproduce this consistently
