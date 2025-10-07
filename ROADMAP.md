# RAG Factory - Product Roadmap

## 🎯 Vision

**RAG Factory** será una plataforma **open-source, autocontenida y fácil de usar** para que desarrolladores, investigadores y empresas puedan construir sistemas RAG (Retrieval-Augmented Generation) de calidad profesional **sin necesidad de servicios cloud costosos**.

### Diferenciadores Clave:
- ✅ **100% Local**: Todo corre en Docker (PostgreSQL + Ollama + Redis)
- ✅ **Multi-proyecto**: Maneja múltiples RAG projects desde una UI
- ✅ **Conectores extensibles**: Fácil añadir nuevas fuentes de datos
- ✅ **User's own database**: Embeddings en la BD del usuario, no vendor lock-in
- ✅ **Production-ready**: Job queue, deduplicación, tracking, error handling

## 📊 Estado Actual (v0.4 - Connector Ecosystem Expansion)

### ✅ Core Features Implemented
- [x] Multi-project management (CRUD)
- [x] PostgreSQL + pgvector for embeddings
- [x] Ollama integration (local embeddings + LLM)
- [x] Redis + RQ for async job processing
- [x] Deduplication by content hash (SHA-256)
- [x] React frontend with full CRUD UI
- [x] Search endpoint (semantic similarity)
- [x] RAG query endpoint (search + LLM generation)
- [x] Document tracking in internal DB
- [x] Vector storage in user's target DB

### ✅ Production Hardening (Phase 1 - COMPLETED)
- [x] **Smart Chunking** - Adaptive chunking based on document size
- [x] **Rate Limiting Framework** - Configurable per-source with presets
- [x] **Incremental Sync** - Date-based filtering, skip processed docs
- [x] **Retry Logic** - Exponential backoff for API failures
- [x] **429 Handling** - Automatic retry-after detection

### ✅ Connector Architecture (Phase 2 - COMPLETED)
- [x] **BaseConnector** - Abstract base class for all connectors
- [x] **ConnectorRegistry** - Auto-discovery plugin system
- [x] **Connector Categorization** - public/example/private
- [x] **Metadata System** - Version, author, config schema
- [x] **Generic SPARQL Connector** - Universal SPARQL endpoint support
- [x] **Generic REST API Connector** - Universal JSON API support
- [x] **Chile BCN Example** - Pre-configured SPARQL connector
- [x] **US Congress Example** - Pre-configured REST API connector

### ✅ Current Connectors (8 Total)
**Public (Generic):**
- [x] `sparql` - Generic SPARQL Endpoint
- [x] `rest_api` - Generic REST API
- [x] `file_upload` - File Upload (PDF, DOCX, TXT, MD, JSON, CSV)
- [x] `web_scraper` - Web Scraper (BeautifulSoup4, CSS selectors)
- [x] `rss_feed` - RSS/Atom Feed (feedparser, auto-discovery)
- [x] `github` - GitHub Repository (README, issues, PRs, code)

**Example (Pre-configured):**
- [x] `chile_bcn` - Chile BCN Legal Norms
- [x] `us_congress` - US Congress Bills

### ✅ Technical Foundation
- [x] Docker Compose setup
- [x] Health check endpoints
- [x] Error logging and job status tracking
- [x] Configurable chunking (size + overlap)
- [x] Gemma 3 LLM for generation
- [x] Frontend dynamic connector loading
- [x] Frontend example configurations UI

## 🚀 Roadmap to v1.0 (Community Release)

### ~~Phase 1: Production Hardening~~ ✅ COMPLETED

**Objetivo**: ✅ Sistema robusto y confiable para uso real

### ~~Phase 2: Connector Architecture~~ ✅ COMPLETED

**Objetivo**: ✅ Framework extensible de conectores con auto-discovery

---

## 🎯 Next 3 Phases (Current Focus)

### Phase 3: Additional Data Source Connectors 🔌

**Objetivo**: Expandir el ecosistema de conectores para fuentes de datos populares

**Priority Connectors** (implementar en orden):

1. **File Upload Connector** ✅ COMPLETED
   - [x] PDF files (PyPDF2/pdfplumber)
   - [x] DOCX files (python-docx)
   - [x] TXT/MD files (plain text)
   - [x] CSV/JSON files (structured data)
   - [x] Batch upload support
   - [x] File size validation
   - [x] Category: public

2. **Web Scraper Connector** ✅ COMPLETED
   - [x] URL fetching with BeautifulSoup4
   - [x] Configurable CSS selectors (content, title, remove)
   - [ ] JavaScript rendering (Playwright/Selenium optional) - Future
   - [x] Robots.txt respect
   - [x] Rate limiting per domain
   - [x] Category: public

3. **RSS/Atom Feed Connector** ✅ COMPLETED
   - [x] Feed parsing (feedparser)
   - [x] Auto-discovery of feeds from web pages
   - [x] Support for RSS 2.0, RSS 1.0, Atom
   - [x] Content extraction (title, content, summary, author, date)
   - [x] Incremental sync based on publication dates
   - [x] HTML tag cleaning from feed content
   - [x] Rate limiting support
   - [x] Category: public

4. **GitHub Connector** ✅ COMPLETED
   - [x] Repository README and documentation
   - [x] Issues with comments (title + body + comments)
   - [x] Pull requests with comments (title + body + comments)
   - [x] Code files (optional, configurable by extension)
   - [x] Personal Access Token authentication
   - [x] Rate limiting (5000/hour with auth, 60/hour without)
   - [x] Incremental sync based on updated_at timestamps
   - [x] File size validation for code files
   - [x] Category: public

5. **Google Drive Connector** (LOWER PRIORITY - OAuth complex)
   - [ ] OAuth2 authentication
   - [ ] Google Docs, Sheets (export as text)
   - [ ] PDFs in Drive
   - [ ] Folder selection
   - [ ] Category: public

6. **Notion Connector** (LOWER PRIORITY - OAuth complex)
   - [ ] Notion API v1
   - [ ] Pages and databases
   - [ ] Workspace selection
   - [ ] OAuth authentication
   - [ ] Category: public

**Connector Template System**:
- [ ] Create connector template/boilerplate
- [ ] Documentation: "How to Build a Connector"
- [ ] Validation script for new connectors
- [ ] Testing framework for connectors

---

### Phase 4: Frontend & UX Improvements 🎨

**Objetivo**: Mejorar la experiencia de usuario y visualización

#### 4.1 Connector Selection UX
- [ ] Dropdown para seleccionar ejemplo y auto-llenar form
- [ ] Preview de configuración antes de crear source
- [ ] Connector cards con iconos y descripciones
- [ ] "Test Connection" button en UI

#### 4.2 Job Monitoring Dashboard
- [ ] Real-time job progress (polling o SSE)
- [ ] Progress bars con % completado
- [ ] Documents ingested counter
- [ ] Error messages en UI (no solo logs)
- [ ] Cancel/pause job functionality

#### 4.3 UI Organization
- [ ] Tabs para Projects / Sources / Jobs
- [ ] Collapsible sections
- [ ] Search/filter sources
- [ ] Pagination para listas largas

#### 4.4 Data Visualization
- [ ] Chart de documentos por fuente
- [ ] Timeline de syncs
- [ ] Storage usage visualization
- [ ] Search quality metrics

---

### Phase 5: Smart Scheduling & Automation ⏰

**Objetivo**: Sincronización automática sin intervención manual

#### 5.1 Scheduling System (APScheduler)
- [ ] Cron expression support
- [ ] Interval-based scheduling (every N hours)
- [ ] Per-source scheduling configuration
- [ ] Timezone support
- [ ] Enable/disable schedules

#### 5.2 Schedule Management UI
- [ ] Visual cron builder
- [ ] Calendar view de próximos syncs
- [ ] Manual trigger button
- [ ] Pause/resume schedules
- [ ] Sync history log

#### 5.3 Smart Features
- [ ] Detect source inactivity → reduce frequency
- [ ] Detect high activity → increase frequency
- [ ] Auto-adjust on rate limit 429s
- [ ] Email/webhook notifications on completion

---

## 🔮 Future Phases (Post v1.0)

### Phase 1: Production Hardening (CRITICAL) 🔥

**Objetivo**: ~~Hacer el sistema robusto y confiable para uso real~~

#### 1.1 Smart Chunking & Large Document Handling
**Problema**: Documentos >5,000 chars causan timeouts en Ollama
**Solución**:
```python
class AdaptiveChunker:
    """
    Estrategia adaptativa basada en tamaño del documento:
    - Small (<2000 chars): Chunk único
    - Medium (2000-5000): Chunking normal con overlap
    - Large (>5000): Chunking recursivo + batch processing
    - Extra Large (>20000): Semantic chunking (por párrafos/secciones)
    """
    def chunk_document(self, document):
        if len(document) > 20000:
            return semantic_chunk(document)  # LangChain integration
        elif len(document) > 5000:
            return recursive_chunk(document, max_size=2000)
        elif len(document) > 2000:
            return standard_chunk(document, size=1000, overlap=200)
        else:
            return [document]  # Single chunk
```

**Beneficio para comunidad**: Cualquier API que retorne documentos largos funcionará out-of-the-box

#### 1.2 Robust Worker Configuration
- [ ] Aumentar worker timeout: 60s → 300s (configurable)
- [ ] Retry logic con exponential backoff
- [ ] Graceful degradation (saltar docs problemáticos sin fallar el job completo)
- [ ] Worker health monitoring
- [ ] Dead letter queue para documentos fallidos

#### 1.3 Rate Limiting Framework
**Problema**: Cada API tiene límites diferentes
**Solución**: Sistema generalizado de rate limiting

```python
class RateLimiter:
    """
    Configurable per-source rate limiting:
    - requests_per_day: 5000
    - requests_per_hour: 500
    - requests_per_minute: 10
    - delay_between_requests: 2.0 (seconds)
    - burst_limit: 5 (ráfaga permitida)
    """

# Configuración en data_source:
{
  "rate_limits": {
    "daily": 5000,
    "hourly": 500,
    "delay": 2.0,
    "retry_after_429": true
  }
}
```

**Beneficio**: Cualquier nueva API que alguien agregue puede especificar sus límites

#### 1.4 Incremental Sync
- [ ] Detectar documentos nuevos/modificados (por fecha/hash)
- [ ] Skip documentos ya procesados
- [ ] Update only changed documents
- [ ] Configurable sync strategy (full/incremental)

**Beneficio**: Syncs diarias consumen solo recursos necesarios

### Phase 2: Connector Ecosystem (EXTENSIBILIDAD) 🔌

**Objetivo**: Hacer trivial añadir nuevas fuentes de datos

#### 2.1 Connector SDK/Framework
```python
class BaseConnector(ABC):
    """
    Abstract base class para todos los connectors
    Define contrato que cualquier connector debe cumplir
    """

    @abstractmethod
    def fetch_documents(self, limit: int, offset: int,
                       last_sync: datetime) -> List[Document]:
        """Fetch documents from source"""
        pass

    @abstractmethod
    def get_rate_limits(self) -> RateLimitConfig:
        """Return rate limit configuration"""
        pass

    @property
    @abstractmethod
    def supports_incremental(self) -> bool:
        """Does this connector support incremental sync?"""
        pass

    def health_check(self) -> bool:
        """Check if source is accessible"""
        return True
```

**Connectors planeados para comunidad**:
- [ ] **Generic REST API** - Configurable via JSON schema
- [ ] **RSS/Atom Feeds** - Blogs, noticias
- [ ] **GitHub** - Issues, PRs, discussions, code
- [ ] **Slack/Discord** - Message history
- [ ] **Google Drive/Docs** - Documents
- [ ] **Notion** - Pages and databases
- [ ] **Confluence** - Wiki pages
- [ ] **Jira** - Tickets and comments
- [ ] **HubSpot/Salesforce** - CRM data
- [ ] **arXiv** - Research papers
- [ ] **PubMed** - Medical literature
- [ ] **Web Scraper** - Configurable selectors
- [ ] **PDF/DOCX Upload** - Local files
- [ ] **CSV/Excel** - Structured data

#### 2.2 Connector Plugin System
```yaml
# connectors/github/manifest.yaml
name: "GitHub Repository Connector"
version: "1.0.0"
author: "RAG Factory Community"
description: "Fetch issues, PRs, and code from GitHub repos"
config_schema:
  repo: string
  token: string (optional)
  include_code: boolean
  include_issues: boolean
  include_prs: boolean
rate_limits:
  requests_per_hour: 5000 (with token)
  requests_per_hour_anonymous: 60
supports_incremental: true
```

**Beneficio**: Comunidad puede contribuir connectors sin modificar código core

### Phase 3: Smart Scheduling (AUTOMATIZACIÓN) ⏰

**Objetivo**: Zero-touch operation después de configuración inicial

#### 3.1 Flexible Scheduling System
```python
# Basado en APScheduler
class SyncScheduler:
    """
    Soporta múltiples estrategias de scheduling:
    - Cron expressions: "0 9,15,21 * * MON-FRI"
    - Interval: every 6 hours
    - Smart: detecta actividad y ajusta frecuencia
    - Event-driven: webhook triggers
    """
```

**Configuración por source**:
```json
{
  "sync_schedule": {
    "type": "cron",
    "expression": "0 9,15,21 * * MON-FRI",
    "max_docs_per_sync": 30,
    "enabled": true,
    "timezone": "America/Santiago"
  }
}
```

#### 3.2 Smart Scheduling
```python
class SmartScheduler:
    """
    Aprende patrones de actividad:
    - Si una fuente tiene muchos updates los lunes → aumenta frecuencia
    - Si source está inactivo → reduce frecuencia
    - Si rate limit es alcanzado → ajusta automáticamente
    """
```

#### 3.3 Scheduling UI
- [ ] Visual cron builder
- [ ] Calendar view de próximos syncs
- [ ] Pause/resume schedules
- [ ] Manual trigger de sync
- [ ] Histórico de syncs

### Phase 4: Advanced RAG Features (CALIDAD) 🎯

**Objetivo**: Estado del arte en calidad de respuestas

#### 4.1 Hybrid Search
- [ ] Combinar semantic search (embeddings) con keyword search (BM25)
- [ ] Configurable weights: 70% semantic + 30% keyword
- [ ] Better recall para queries técnicas

#### 4.2 Re-ranking
```python
class ReRanker:
    """
    Después de retrieval inicial (top-k=20):
    1. Cross-encoder model re-rankea resultados
    2. Considera query context y document relevance
    3. Retorna top-n (n=5) más relevantes

    Mejora precision sin sacrificar recall
    """
```

#### 4.3 Query Enhancement
- [ ] Query expansion (sinónimos, términos relacionados)
- [ ] Spelling correction
- [ ] Multi-query generation (HyDE - Hypothetical Document Embeddings)

#### 4.4 Streaming Responses
```python
@app.post("/query/stream")
async def stream_rag_query():
    """
    Server-Sent Events (SSE) para streaming:
    1. Stream retrieved documents primero
    2. Stream LLM generation token-by-token
    3. Better UX para queries lentas
    """
```

#### 4.5 Citation & Source Tracking
- [ ] Highlight text passages used in answer
- [ ] Link back to original source URL
- [ ] Confidence scores per citation

### Phase 5: Multi-tenancy & Auth (PRODUCTION) 🔐

**Objetivo**: Deployment seguro para equipos/organizaciones

#### 5.1 Authentication
- [ ] User registration/login
- [ ] API keys para programmatic access
- [ ] OAuth (Google, GitHub)
- [ ] JWT tokens

#### 5.2 Multi-tenancy
- [ ] Projects por usuario/organización
- [ ] Permissions (owner, editor, viewer)
- [ ] Shared projects
- [ ] Usage quotas

#### 5.3 API Rate Limiting
- [ ] Por usuario/API key
- [ ] Tiered plans (free/pro/enterprise)

### Phase 6: Observability (ENTERPRISE) 📊

**Objetivo**: Insights y debugging para production deployments

#### 6.1 Metrics Dashboard
- [ ] Documents ingested (por fuente, por día)
- [ ] Query volume y latency
- [ ] Embedding generation time
- [ ] Top queries
- [ ] Error rates

#### 6.2 Quality Metrics
- [ ] Average similarity scores
- [ ] User feedback (thumbs up/down)
- [ ] Answer length distribution
- [ ] Source diversity in responses

#### 6.3 Cost Tracking
- [ ] Ollama compute time
- [ ] Storage usage
- [ ] API call counts
- [ ] Projected monthly costs

#### 6.4 Alerting
- [ ] Sync failures
- [ ] Low similarity scores (degraded quality)
- [ ] Rate limit warnings
- [ ] Disk space alerts

### Phase 7: Deployment & Scaling (CLOUD-READY) ☁️

**Objetivo**: Fácil deployment en cualquier infraestructura

#### 7.1 Deployment Options
- [ ] **Docker Compose** (actual - single machine)
- [ ] **Kubernetes Helm Chart** - Multi-node, auto-scaling
- [ ] **Railway/Render templates** - One-click deploy
- [ ] **AWS/GCP/Azure** - IaC templates (Terraform)

#### 7.2 Horizontal Scaling
```yaml
# Kubernetes example
replicas:
  api: 3
  worker: 5
  ollama: 2 (GPU instances)
autoscaling:
  workers:
    min: 2
    max: 20
    trigger: queue_length > 100
```

#### 7.3 High Availability
- [ ] PostgreSQL replication
- [ ] Redis Sentinel/Cluster
- [ ] Load balancing
- [ ] Health checks y auto-restart

#### 7.4 Backup & Recovery
- [ ] Automated backups (projects + vectors)
- [ ] Point-in-time recovery
- [ ] Export/import functionality

### Phase 8: Developer Experience (COMMUNITY) 👥

**Objetivo**: Fácil contribuir y extender

#### 8.1 Documentation
- [ ] **Quick Start Guide** - 5 minutos para primer RAG
- [ ] **Architecture Overview** - Diagramas, flujos
- [ ] **API Documentation** - OpenAPI/Swagger completo
- [ ] **Connector Development Guide** - Template + ejemplos
- [ ] **Deployment Guides** - Por plataforma
- [ ] **Video Tutorials** - YouTube series

#### 8.2 Testing
- [ ] Unit tests (pytest)
- [ ] Integration tests
- [ ] E2E tests (Playwright)
- [ ] Load testing scripts
- [ ] CI/CD pipeline (GitHub Actions)

#### 8.3 CLI Tool
```bash
rag-factory init my-project
rag-factory add-source --type github --repo user/repo
rag-factory sync --project my-project
rag-factory query "What is the main feature?"
rag-factory deploy --platform railway
```

#### 8.4 SDK/Client Libraries
```python
# Python SDK
from rag_factory import RAGFactory

rag = RAGFactory(api_url="http://localhost:8000")
project = rag.create_project("My Docs")
project.add_source("github", repo="user/repo")
project.sync()
answer = project.query("What does this code do?")
```

```javascript
// JavaScript SDK
import { RAGFactory } from 'rag-factory-js';

const rag = new RAGFactory('http://localhost:8000');
const answer = await rag.query(projectId, 'What is this about?');
```

#### 8.5 Community
- [ ] Discord server
- [ ] GitHub Discussions
- [ ] Contribution guidelines
- [ ] Code of Conduct
- [ ] Connector marketplace/registry
- [ ] Showcase page (real-world use cases)

## 🎁 Bonus Features (Nice-to-Have)

### Advanced Chunking Strategies
- [ ] Semantic chunking (LangChain)
- [ ] Recursive summarization para docs muy largos
- [ ] Table extraction y structured data handling

### Multi-modal Support
- [ ] Image embeddings (CLIP)
- [ ] PDF con imágenes
- [ ] Audio transcription (Whisper) → RAG

### Advanced LLM Features
- [ ] Multiple LLM support (GPT-4, Claude, local models)
- [ ] Model switching per project
- [ ] Fine-tuning support
- [ ] Prompt templates library

### Analytics
- [ ] A/B testing (different chunking strategies)
- [ ] Query clustering (temas comunes)
- [ ] Knowledge gap detection (queries sin buenas respuestas)

## 📅 Timeline Estimado

```
v0.2 (2 semanas): Phase 1 - Production Hardening
v0.3 (1 mes): Phase 2 - Connector Ecosystem
v0.4 (1.5 meses): Phase 3 - Smart Scheduling
v0.5 (2 meses): Phase 4 - Advanced RAG
v0.6 (2.5 meses): Phase 5 - Auth & Multi-tenancy
v0.7 (3 meses): Phase 6 - Observability
v0.8 (3.5 meses): Phase 7 - Deployment Options
v0.9 (4 meses): Phase 8 - Developer Experience
v1.0 (4.5 meses): Community Launch 🎉
```

## 🌟 Success Metrics for v1.0

- [ ] 100+ GitHub stars
- [ ] 10+ community connectors contributed
- [ ] 5+ production deployments documented
- [ ] 1000+ documents on connector marketplace
- [ ] <5 minutos para primer RAG working
- [ ] 99% uptime en deployment de referencia
- [ ] Documentación completa en 3 idiomas (EN, ES, PT)

## 🤝 Community Contribution Areas

### Fácil (Good First Issue):
- Nuevos connectors para APIs públicas
- Traducir documentación
- Escribir ejemplos/tutoriales
- Reportar bugs
- Mejorar mensajes de error

### Medium:
- Implementar chunking strategies
- Optimizar queries SQL
- Añadir tests
- Mejorar UI/UX

### Hard:
- Implementar re-ranking
- Kubernetes deployment
- Advanced monitoring
- Multi-modal support

---

## 💭 Notas para el Futuro

**Filosofía del Proyecto**:
1. **Local-first**: Debe funcionar 100% offline
2. **No vendor lock-in**: User's data en su propia DB
3. **Extensible**: Plugin system para todo
4. **Production-ready**: No es solo un demo/tutorial
5. **Educational**: Código limpio, bien documentado, aprende mientras usas

**Comparación con competencia**:
- **LangChain**: Nosotros somos más opinionated, end-to-end solution
- **LlamaIndex**: Similar, pero nosotros multi-proyecto + job queue
- **Pinecone/Weaviate**: Ellos vendor lock-in, nosotros user's DB
- **Haystack**: Más enterprise, nosotros más developer-friendly

**Target Audience**:
- 🎓 Estudiantes aprendiendo RAG
- 🚀 Startups que necesitan RAG pero no pueden pagar OpenAI embeddings
- 🏢 Empresas con datos sensibles (no pueden cloud)
- 🔬 Investigadores experimentando con técnicas RAG
- 👨‍💻 Developers building internal tools

---

**¿Tu visión adicional?** Por favor agregar tus ideas aquí 👇
