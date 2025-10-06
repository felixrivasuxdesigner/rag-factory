import { useState, useEffect } from 'react'
import {
  Factory,
  CheckCircle,
  XCircle,
  Database,
  CloudArrowUp,
  PencilSimple,
  Trash,
  ArrowsClockwise,
  Plus,
  Play,
  Info,
  Warning
} from '@phosphor-icons/react'
import SearchPanel from './components/SearchPanel'
import './App.css'

const API_URL = 'http://localhost:8000'

interface HealthStatus {
  api: string
  database: string
  redis: string
  ollama: string
}

interface Project {
  id: number
  name: string
  description: string
  status: string
  target_db_host: string
  target_db_name: string
  target_table_name: string
  embedding_model: string
  created_at: string
}

interface ProjectStats {
  total_documents: number
  documents_completed: number
  documents_failed: number
  total_jobs: number
  jobs_completed: number
  jobs_failed: number
}

interface DataSource {
  id: number
  project_id: number
  name: string
  source_type: string
  is_active: boolean
  config: any
}

interface Connector {
  name: string
  source_type: string
  description: string
  version: string
  author: string
  category: string
  supports_incremental_sync: boolean
  supports_rate_limiting: boolean
  required_config_fields: string[]
  optional_config_fields: string[]
  default_rate_limit_preset: string | null
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<number | null>(null)
  const [stats, setStats] = useState<ProjectStats | null>(null)
  const [sources, setSources] = useState<DataSource[]>([])
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [loading, setLoading] = useState(false)
  const [showCreateProject, setShowCreateProject] = useState(false)
  const [showEditProject, setShowEditProject] = useState(false)
  const [editingProject, setEditingProject] = useState<Project | null>(null)
  const [showCreateSource, setShowCreateSource] = useState(false)
  const [sourceType, setSourceType] = useState<string>('sparql')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<{type: 'project' | 'source', id: number, name: string} | null>(null)

  useEffect(() => {
    checkHealth()
    loadProjects()
    loadConnectors()
  }, [])

  useEffect(() => {
    if (selectedProject) {
      loadProjectStats(selectedProject)
      loadProjectSources(selectedProject)
    }
  }, [selectedProject])

  const checkHealth = async () => {
    try {
      const response = await fetch(`${API_URL}/health`)
      const data = await response.json()
      setHealth(data)
    } catch (error) {
      console.error('Failed to check health:', error)
    }
  }

  const loadProjects = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/projects`)
      const data = await response.json()
      setProjects(data)
      if (data.length > 0 && !selectedProject) {
        setSelectedProject(data[0].id)
      }
    } catch (error) {
      console.error('Failed to load projects:', error)
      setError('Failed to load projects')
    } finally {
      setLoading(false)
    }
  }

  const loadProjectStats = async (projectId: number) => {
    try {
      const response = await fetch(`${API_URL}/projects/${projectId}/stats`)
      const data = await response.json()
      setStats(data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }

  const loadProjectSources = async (projectId: number) => {
    try {
      const response = await fetch(`${API_URL}/projects/${projectId}/sources`)
      const data = await response.json()
      setSources(data)
    } catch (error) {
      console.error('Failed to load sources:', error)
    }
  }

  const loadConnectors = async () => {
    try {
      const response = await fetch(`${API_URL}/connectors?category=public`)
      const data = await response.json()
      setConnectors(data.connectors || [])

      // Set first connector as default if available
      if (data.connectors && data.connectors.length > 0) {
        setSourceType(data.connectors[0].source_type)
      }
    } catch (error) {
      console.error('Failed to load connectors:', error)
    }
  }

  const createProject = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)

    const projectData = {
      name: formData.get('name'),
      description: formData.get('description'),
      target_db_host: formData.get('target_db_host'),
      target_db_port: parseInt(formData.get('target_db_port') as string),
      target_db_name: formData.get('target_db_name'),
      target_db_user: formData.get('target_db_user'),
      target_db_password: formData.get('target_db_password'),
      target_table_name: formData.get('target_table_name'),
      embedding_model: formData.get('embedding_model'),
      embedding_dimension: 1024,
      chunk_size: 1000,
      chunk_overlap: 200
    }

    try {
      const response = await fetch(`${API_URL}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(projectData)
      })

      if (response.ok) {
        setSuccess('Project created successfully!')
        setShowCreateProject(false)
        loadProjects()
        setTimeout(() => setSuccess(null), 3000)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to create project')
      }
    } catch (error) {
      setError('Failed to create project')
    }
  }

  const createSource = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!selectedProject) return

    const formData = new FormData(e.currentTarget)

    let config = {}

    if (sourceType === 'sparql') {
      config = {
        endpoint: formData.get('sparql_endpoint'),
        query: formData.get('sparql_query') || 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 100',
        limit: parseInt(formData.get('limit') as string) || 25
      }
    } else if (sourceType === 'file_upload') {
      const documents = formData.get('documents')
      config = {
        documents: documents ? JSON.parse(documents as string) : []
      }
    } else if (sourceType === 'rest_api') {
      config = {
        url: formData.get('api_url'),
        method: formData.get('api_method') || 'GET',
        headers: {}
      }
    }

    const sourceData = {
      project_id: selectedProject,
      name: formData.get('name'),
      source_type: sourceType,
      config: config,
      country_code: formData.get('country_code') || null,
      region: formData.get('region') || null,
      sync_frequency: 'manual'
    }

    try {
      const response = await fetch(`${API_URL}/sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sourceData)
      })

      if (response.ok) {
        setSuccess('Data source created successfully!')
        setShowCreateSource(false)
        loadProjectSources(selectedProject)
        setTimeout(() => setSuccess(null), 3000)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to create source')
      }
    } catch (error) {
      setError('Failed to create source')
    }
  }

  const updateProject = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!editingProject) return

    const formData = new FormData(e.currentTarget)

    const projectData = {
      name: formData.get('name'),
      description: formData.get('description'),
      target_db_host: formData.get('target_db_host'),
      target_db_port: parseInt(formData.get('target_db_port') as string),
      target_db_name: formData.get('target_db_name'),
      target_db_user: formData.get('target_db_user'),
      target_db_password: formData.get('target_db_password'),
      target_table_name: formData.get('target_table_name'),
      embedding_model: formData.get('embedding_model')
    }

    try {
      const response = await fetch(`${API_URL}/projects/${editingProject.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(projectData)
      })

      if (response.ok) {
        setSuccess('Project updated successfully!')
        setShowEditProject(false)
        setEditingProject(null)
        loadProjects()
        setTimeout(() => setSuccess(null), 3000)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to update project')
      }
    } catch (error) {
      setError('Failed to update project')
    }
  }

  const deleteProject = async (id: number) => {
    try {
      const response = await fetch(`${API_URL}/projects/${id}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        setSuccess('Project deleted successfully!')
        setConfirmDelete(null)
        if (selectedProject === id) {
          setSelectedProject(null)
        }
        loadProjects()
        setTimeout(() => setSuccess(null), 3000)
      } else {
        setError('Failed to delete project')
      }
    } catch (error) {
      setError('Failed to delete project')
    }
  }

  const deleteSource = async (id: number) => {
    if (!selectedProject) return

    try {
      const response = await fetch(`${API_URL}/sources/${id}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        setSuccess('Data source deleted successfully!')
        setConfirmDelete(null)
        loadProjectSources(selectedProject)
        setTimeout(() => setSuccess(null), 3000)
      } else {
        setError('Failed to delete source')
      }
    } catch (error) {
      setError('Failed to delete source')
    }
  }

  const runIngestionJob = async (sourceId: number) => {
    if (!selectedProject) return

    try {
      const response = await fetch(`${API_URL}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: selectedProject,
          source_id: sourceId,
          job_type: 'full_sync'
        })
      })

      if (response.ok) {
        setSuccess('Ingestion job started! Check stats in a few seconds.')
        setTimeout(() => {
          loadProjectStats(selectedProject)
          setSuccess(null)
        }, 3000)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to start job')
      }
    } catch (error) {
      setError('Failed to start job')
    }
  }

  const handleEditProject = (project: Project) => {
    setEditingProject(project)
    setShowEditProject(true)
  }

  const getHealthIndicator = (status: string) => {
    return status === 'healthy'
      ? <CheckCircle size={24} weight="fill" className="text-green-500" />
      : <XCircle size={24} weight="fill" className="text-red-500" />
  }

  return (
    <div className="app">
      <header className="header">
        <h1><Factory size={32} weight="duotone" /> RAG Factory</h1>
        <p className="subtitle">Multi-Project RAG Management System</p>
      </header>

      {error && <div className="alert alert-error">{error} <button onClick={() => setError(null)}>×</button></div>}
      {success && <div className="alert alert-success">{success}</div>}

      {/* Search/RAG Panel */}
      {selectedProject && projects.find(p => p.id === selectedProject) && (
        <SearchPanel
          projectId={selectedProject}
          projectName={projects.find(p => p.id === selectedProject)!.name}
        />
      )}

      {/* Health Status */}
      <section className="health-section">
        <h2>System Health</h2>
        {health ? (
          <div className="health-grid">
            <div className="health-item">
              <span className="health-icon">{getHealthIndicator(health.api)}</span>
              <span className="health-label">API</span>
              <span className="health-status">{health.api}</span>
            </div>
            <div className="health-item">
              <span className="health-icon">{getHealthIndicator(health.database)}</span>
              <span className="health-label">Database</span>
              <span className="health-status">{health.database}</span>
            </div>
            <div className="health-item">
              <span className="health-icon">{getHealthIndicator(health.redis)}</span>
              <span className="health-label">Redis</span>
              <span className="health-status">{health.redis}</span>
            </div>
            <div className="health-item">
              <span className="health-icon">{getHealthIndicator(health.ollama)}</span>
              <span className="health-label">Ollama</span>
              <span className="health-status">{health.ollama}</span>
            </div>
          </div>
        ) : (
          <p>Loading health status...</p>
        )}
      </section>

      {/* Projects List */}
      <section className="projects-section">
        <div className="section-header">
          <h2>Projects</h2>
          <div className="button-group">
            <button onClick={loadProjects} disabled={loading} className="btn-secondary">
              <ArrowsClockwise size={18} weight={loading ? "bold" : "regular"} /> Refresh
            </button>
            <button onClick={() => setShowCreateProject(true)} className="btn-primary">
              <Plus size={18} weight="bold" /> New Project
            </button>
          </div>
        </div>

        {showCreateProject && (
          <div className="modal-overlay" onClick={() => setShowCreateProject(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <h3>Create New RAG Project</h3>

              <div className="info-box">
                <strong><Info size={18} weight="fill" /> About Database Configuration</strong>
                <p>RAG Factory uses TWO databases:</p>
                <ul>
                  <li><strong>Internal DB</strong> (automatic): Stores projects, jobs, tracking</li>
                  <li><strong>Your Vector DB</strong> (you configure): Stores embeddings</li>
                </ul>
                <p>For testing, use the same database. For production, use your own.</p>
              </div>

              <form onSubmit={createProject}>
                <div className="form-group">
                  <label>Project Name *</label>
                  <input type="text" name="name" placeholder="My Legal Documents RAG" required />
                </div>
                <div className="form-group">
                  <label>Description</label>
                  <textarea name="description" rows={2} placeholder="Optional description of this RAG project"></textarea>
                </div>

                <h4 className="section-title"><Database size={20} weight="duotone" /> Vector Database (where embeddings are stored)</h4>

                <div className="form-row">
                  <div className="form-group">
                    <label>Host *</label>
                    <input type="text" name="target_db_host" defaultValue="db" required />
                    <small>Use 'db' for Docker, 'localhost' for external</small>
                  </div>
                  <div className="form-group">
                    <label>Port *</label>
                    <input type="number" name="target_db_port" defaultValue="5432" required />
                  </div>
                </div>
                <div className="form-group">
                  <label>Database Name *</label>
                  <input type="text" name="target_db_name" defaultValue="rag_factory_db" required />
                  <small>Default: rag_factory_db (for testing)</small>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>User *</label>
                    <input type="text" name="target_db_user" defaultValue="user" required />
                  </div>
                  <div className="form-group">
                    <label>Password *</label>
                    <input type="password" name="target_db_password" defaultValue="password" required />
                  </div>
                </div>
                <div className="form-group">
                  <label>Vector Table Name *</label>
                  <input type="text" name="target_table_name" placeholder="my_vectors" required />
                  <small>Will be created automatically</small>
                </div>

                <h4 className="section-title"><CloudArrowUp size={20} weight="duotone" /> Embedding Model</h4>

                <div className="form-group">
                  <label>Model *</label>
                  <select name="embedding_model" required>
                    <option value="mxbai-embed-large">mxbai-embed-large (1024 dims)</option>
                  </select>
                  <small>Must be available in Ollama</small>
                </div>

                <div className="form-actions">
                  <button type="button" onClick={() => setShowCreateProject(false)} className="btn-secondary">
                    Cancel
                  </button>
                  <button type="submit" className="btn-primary">Create Project</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {projects.length > 0 ? (
          <div className="projects-list">
            {projects.map((project) => (
              <div
                key={project.id}
                className={`project-card ${selectedProject === project.id ? 'selected' : ''}`}
              >
                <div onClick={() => setSelectedProject(project.id)}>
                  <h3>{project.name}</h3>
                  <p className="project-description">{project.description}</p>
                  <div className="project-meta">
                    <span className="badge">{project.status}</span>
                    <span className="meta-text">Model: {project.embedding_model}</span>
                    <span className="meta-text">Table: {project.target_table_name}</span>
                  </div>
                </div>
                <div className="card-actions">
                  <button
                    className="btn-icon"
                    onClick={(e) => { e.stopPropagation(); handleEditProject(project); }}
                    title="Edit project"
                  >
                    <PencilSimple size={18} weight="bold" />
                  </button>
                  <button
                    className="btn-icon btn-danger"
                    onClick={(e) => { e.stopPropagation(); setConfirmDelete({type: 'project', id: project.id, name: project.name}); }}
                    title="Delete project"
                  >
                    <Trash size={18} weight="bold" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <p>No projects found. Create your first RAG project!</p>
          </div>
        )}
      </section>

      {/* Project Statistics */}
      {selectedProject && stats && (
        <section className="stats-section">
          <h2>Project Statistics</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.total_documents}</div>
              <div className="stat-label">Total Documents</div>
            </div>
            <div className="stat-card success">
              <div className="stat-value">{stats.documents_completed}</div>
              <div className="stat-label">Completed</div>
            </div>
            <div className="stat-card error">
              <div className="stat-value">{stats.documents_failed}</div>
              <div className="stat-label">Failed</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.total_jobs}</div>
              <div className="stat-label">Total Jobs</div>
            </div>
            <div className="stat-card success">
              <div className="stat-value">{stats.jobs_completed}</div>
              <div className="stat-label">Jobs Completed</div>
            </div>
            <div className="stat-card error">
              <div className="stat-value">{stats.jobs_failed}</div>
              <div className="stat-label">Jobs Failed</div>
            </div>
          </div>
        </section>
      )}

      {/* Data Sources */}
      {selectedProject && (
        <section className="sources-section">
          <div className="section-header">
            <h2>Data Sources</h2>
            <button onClick={() => setShowCreateSource(true)} className="btn-primary">
              <Plus size={18} weight="bold" /> New Source
            </button>
          </div>

          {showCreateSource && (
            <div className="modal-overlay" onClick={() => setShowCreateSource(false)}>
              <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
                <h3>Create Data Source</h3>
                <form onSubmit={createSource}>
                  <div className="form-group">
                    <label>Source Name *</label>
                    <input type="text" name="name" placeholder="Chilean Legal Documents" required />
                  </div>

                  <div className="form-group">
                    <label>Source Type *</label>
                    <select value={sourceType} onChange={(e) => setSourceType(e.target.value)} required>
                      {connectors.length === 0 ? (
                        <option value="">Loading connectors...</option>
                      ) : (
                        connectors.map(connector => (
                          <option key={connector.source_type} value={connector.source_type}>
                            {connector.name}
                          </option>
                        ))
                      )}
                    </select>
                    {connectors.find(c => c.source_type === sourceType)?.description && (
                      <small style={{color: '#666', marginTop: '4px', display: 'block'}}>
                        {connectors.find(c => c.source_type === sourceType)?.description}
                      </small>
                    )}
                  </div>

                  {/* Examples Section */}
                  {(sourceType === 'sparql' || sourceType === 'rest_api') && (
                    <details style={{marginBottom: '20px', padding: '15px', backgroundColor: '#f8f9fa', borderRadius: '8px', border: '1px solid #e1e4e8'}}>
                      <summary style={{cursor: 'pointer', fontWeight: 600, color: '#0366d6', marginBottom: '10px'}}>
                        📚 Example Configurations
                      </summary>

                      {sourceType === 'sparql' && (
                        <div style={{marginTop: '15px'}}>
                          <h4 style={{fontSize: '14px', fontWeight: 600, marginBottom: '10px'}}>Chile BCN Legal Norms</h4>
                          <div style={{backgroundColor: 'white', padding: '12px', borderRadius: '6px', fontSize: '13px', fontFamily: 'monospace', marginBottom: '15px'}}>
                            <div><strong>Endpoint:</strong> https://datos.bcn.cl/sparql</div>
                            <div style={{marginTop: '8px'}}><strong>Query:</strong></div>
                            <pre style={{margin: '4px 0', whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '12px'}}>
{`PREFIX bcnnorms: <http://datos.bcn.cl/ontologies/bcn-norms#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>

SELECT DISTINCT ?id ?title ?date
WHERE {
  ?norma dc:identifier ?id .
  ?norma dc:title ?title .
  ?norma bcnnorms:publishDate ?date .
  {date_filter}
}
ORDER BY DESC(?date)
OFFSET {offset}
LIMIT {limit}`}
                            </pre>
                            <div style={{marginTop: '8px'}}><strong>Field Mapping:</strong> id_field=id, title_field=title, content_fields=title</div>
                          </div>

                          <h4 style={{fontSize: '14px', fontWeight: 600, marginBottom: '10px'}}>Wikidata Example</h4>
                          <div style={{backgroundColor: 'white', padding: '12px', borderRadius: '6px', fontSize: '13px', fontFamily: 'monospace'}}>
                            <div><strong>Endpoint:</strong> https://query.wikidata.org/sparql</div>
                            <div style={{marginTop: '8px'}}><strong>Query:</strong></div>
                            <pre style={{margin: '4px 0', whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '12px'}}>
{`SELECT ?id ?title ?description
WHERE {
  ?id wdt:P31 wd:Q5 .
  ?id rdfs:label ?title .
  ?id schema:description ?description .
  FILTER(LANG(?title) = "en")
}
OFFSET {offset}
LIMIT {limit}`}
                            </pre>
                            <div style={{marginTop: '8px'}}><strong>Field Mapping:</strong> id_field=id, title_field=title, content_fields=description</div>
                          </div>
                        </div>
                      )}

                      {sourceType === 'rest_api' && (
                        <div style={{marginTop: '15px'}}>
                          <h4 style={{fontSize: '14px', fontWeight: 600, marginBottom: '10px'}}>US Congress API</h4>
                          <div style={{backgroundColor: 'white', padding: '12px', borderRadius: '6px', fontSize: '13px', fontFamily: 'monospace', marginBottom: '15px'}}>
                            <div><strong>Base URL:</strong> https://api.congress.gov/v3</div>
                            <div><strong>Endpoint:</strong> /bill/119</div>
                            <div><strong>Method:</strong> GET</div>
                            <div><strong>Auth Type:</strong> api_key</div>
                            <div><strong>API Key:</strong> DEMO_KEY (or register for your own)</div>
                            <div style={{marginTop: '8px'}}><strong>URL Parameters:</strong> limit_param=limit, offset_param=offset</div>
                            <div><strong>Response Path:</strong> bills</div>
                            <div><strong>Field Mapping:</strong> id_field=number, title_field=title, content_field=title</div>
                          </div>

                          <h4 style={{fontSize: '14px', fontWeight: 600, marginBottom: '10px'}}>Generic JSON API</h4>
                          <div style={{backgroundColor: 'white', padding: '12px', borderRadius: '6px', fontSize: '13px', fontFamily: 'monospace'}}>
                            <div><strong>Base URL:</strong> https://api.example.com</div>
                            <div><strong>Endpoint:</strong> /v1/documents</div>
                            <div><strong>Method:</strong> GET</div>
                            <div><strong>Custom Headers:</strong></div>
                            <pre style={{margin: '4px 0', fontSize: '12px'}}>
{`{
  "Accept": "application/json",
  "User-Agent": "RAGFactory/1.0"
}`}
                            </pre>
                            <div style={{marginTop: '8px'}}><strong>Response Path:</strong> data.results</div>
                            <div><strong>Field Mapping:</strong> Adjust based on your API's response structure</div>
                          </div>
                        </div>
                      )}
                    </details>
                  )}

                  {/* Generic SPARQL Configuration */}
                  {sourceType === 'sparql' && (
                    <>
                      <div className="form-group">
                        <label>SPARQL Endpoint URL *</label>
                        <input
                          type="url"
                          name="endpoint"
                          placeholder="https://query.wikidata.org/sparql"
                          required
                        />
                        <small>Any public SPARQL endpoint (Wikidata, DBpedia, government data, etc.)</small>
                      </div>
                      <div className="form-group">
                        <label>SPARQL Query Template *</label>
                        <textarea
                          name="query"
                          rows={10}
                          placeholder={'SELECT ?id ?title ?content ?date\nWHERE {\n  ?item wdt:P31 wd:Q5 .\n  ?item rdfs:label ?title .\n  BIND(?title AS ?content)\n  {date_filter}\n}\nOFFSET {offset}\nLIMIT {limit}'}
                          required
                        ></textarea>
                        <small>Use placeholders: &#123;limit&#125;, &#123;offset&#125;, &#123;date_filter&#125; for pagination and filtering</small>
                      </div>
                      <div className="form-row">
                        <div className="form-group">
                          <label>ID Field</label>
                          <input type="text" name="id_field" defaultValue="id" placeholder="id" />
                          <small>SPARQL variable name for document ID</small>
                        </div>
                        <div className="form-group">
                          <label>Title Field</label>
                          <input type="text" name="title_field" defaultValue="title" placeholder="title" />
                          <small>SPARQL variable name for title</small>
                        </div>
                      </div>
                      <div className="form-group">
                        <label>Content Fields (comma-separated)</label>
                        <input type="text" name="content_fields" defaultValue="content" placeholder="content,description" />
                        <small>SPARQL variables to combine for document content</small>
                      </div>
                      <div className="form-group">
                        <label>Document Limit</label>
                        <input type="number" name="limit" defaultValue="25" min="1" max="1000" />
                        <small>Maximum documents per sync</small>
                      </div>
                    </>
                  )}

                  {/* File Upload Configuration */}
                  {sourceType === 'file_upload' && (
                    <div className="form-group">
                      <label>Documents (JSON) *</label>
                      <textarea
                        name="documents"
                        rows={10}
                        placeholder={'[\n  {\n    "id": "doc1",\n    "title": "Document Title",\n    "content": "Full document content goes here..."\n  },\n  {\n    "id": "doc2",\n    "title": "Another Document",\n    "content": "More content..."\n  }\n]'}
                        required
                      ></textarea>
                      <small>Provide an array of documents with id, title, and content fields (JSON format)</small>
                    </div>
                  )}

                  {/* REST API Configuration */}
                  {sourceType === 'rest_api' && (
                    <>
                      <div className="form-group">
                        <label>Base URL *</label>
                        <input type="url" name="base_url" placeholder="https://api.example.com" required />
                        <small>Base URL of the REST API (without endpoint path)</small>
                      </div>
                      <div className="form-group">
                        <label>Endpoint Path *</label>
                        <input type="text" name="endpoint" placeholder="/v1/documents" required />
                        <small>API endpoint path (e.g., /v1/documents, /api/items)</small>
                      </div>
                      <div className="form-row">
                        <div className="form-group">
                          <label>HTTP Method</label>
                          <select name="method">
                            <option value="GET">GET</option>
                            <option value="POST">POST</option>
                          </select>
                        </div>
                        <div className="form-group">
                          <label>Authentication Type</label>
                          <select name="auth_type">
                            <option value="">None</option>
                            <option value="api_key">API Key</option>
                            <option value="bearer">Bearer Token</option>
                          </select>
                        </div>
                      </div>
                      <div className="form-group">
                        <label>API Key / Token</label>
                        <input type="text" name="api_key" placeholder="your-api-key-here" />
                        <small>Required if authentication type is selected</small>
                      </div>
                      <div className="form-group">
                        <label>Custom Headers (JSON)</label>
                        <textarea
                          name="headers"
                          rows={3}
                          placeholder={'{\n  "Accept": "application/json",\n  "User-Agent": "RAGFactory/1.0"\n}'}
                        ></textarea>
                        <small>Optional custom HTTP headers in JSON format</small>
                      </div>
                      <div className="form-row">
                        <div className="form-group">
                          <label>Limit Parameter</label>
                          <input type="text" name="limit_param" defaultValue="limit" placeholder="limit" />
                          <small>URL param for pagination limit</small>
                        </div>
                        <div className="form-group">
                          <label>Offset Parameter</label>
                          <input type="text" name="offset_param" defaultValue="offset" placeholder="offset" />
                          <small>URL param for pagination offset</small>
                        </div>
                      </div>
                      <div className="form-group">
                        <label>Date Filter Parameter</label>
                        <input type="text" name="date_param" placeholder="updated_since" />
                        <small>Optional: URL param for date filtering (ISO format)</small>
                      </div>
                      <div className="form-row">
                        <div className="form-group">
                          <label>Response Data Path</label>
                          <input type="text" name="data_path" defaultValue="data" placeholder="data.results" />
                          <small>JSON path to documents array (e.g., "data", "results", "items")</small>
                        </div>
                        <div className="form-group">
                          <label>ID Field</label>
                          <input type="text" name="id_field" defaultValue="id" placeholder="id" />
                          <small>JSON field for document ID</small>
                        </div>
                      </div>
                      <div className="form-row">
                        <div className="form-group">
                          <label>Title Field</label>
                          <input type="text" name="title_field" defaultValue="title" placeholder="title" />
                          <small>JSON field for document title</small>
                        </div>
                        <div className="form-group">
                          <label>Content Field</label>
                          <input type="text" name="content_field" defaultValue="content" placeholder="content" />
                          <small>JSON field for document content</small>
                        </div>
                      </div>
                      <div className="form-group">
                        <label>Date Field</label>
                        <input type="text" name="date_field" placeholder="updated_at" />
                        <small>Optional: JSON field for document timestamp</small>
                      </div>
                      <div className="form-group">
                        <label>Document Limit</label>
                        <input type="number" name="limit" defaultValue="25" min="1" max="1000" />
                        <small>Maximum documents per sync</small>
                      </div>
                    </>
                  )}

                  <div className="form-actions">
                    <button type="button" onClick={() => setShowCreateSource(false)} className="btn-secondary">
                      Cancel
                    </button>
                    <button type="submit" className="btn-primary">Create Source</button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {sources.length > 0 ? (
            <div className="sources-list">
              {sources.map((source) => (
                <div key={source.id} className="source-card">
                  <div className="source-header">
                    <h4>{source.name}</h4>
                    <span className={`badge ${source.is_active ? 'active' : 'inactive'}`}>
                      {source.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className="source-meta">
                    <span className="meta-text">Type: {source.source_type}</span>
                    {source.source_type === 'sparql' && source.config?.endpoint && (
                      <span className="meta-text">Endpoint: {new URL(source.config.endpoint).hostname}</span>
                    )}
                    {source.source_type === 'file_upload' && source.config?.documents && (
                      <span className="meta-text">Documents: {source.config.documents.length}</span>
                    )}
                  </div>
                  <div className="source-actions">
                    <button
                      onClick={() => runIngestionJob(source.id)}
                      className="btn-primary btn-small"
                      disabled={!source.is_active}
                    >
                      <Play size={16} weight="fill" /> Run Ingestion
                    </button>
                    <button
                      onClick={() => setConfirmDelete({type: 'source', id: source.id, name: source.name})}
                      className="btn-icon btn-danger"
                      title="Delete source"
                    >
                      <Trash size={18} weight="bold" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>No data sources configured. Create one to start ingesting documents.</p>
            </div>
          )}
        </section>
      )}

      {/* Edit Project Modal */}
      {showEditProject && editingProject && (
        <div className="modal-overlay" onClick={() => { setShowEditProject(false); setEditingProject(null); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Edit Project</h3>
            <form onSubmit={updateProject}>
              <div className="form-group">
                <label>Project Name *</label>
                <input type="text" name="name" defaultValue={editingProject.name} required />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea name="description" rows={2} defaultValue={editingProject.description}></textarea>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Host *</label>
                  <input type="text" name="target_db_host" defaultValue={editingProject.target_db_host} required />
                </div>
                <div className="form-group">
                  <label>Port *</label>
                  <input type="number" name="target_db_port" defaultValue={5432} required />
                </div>
              </div>
              <div className="form-group">
                <label>Database Name *</label>
                <input type="text" name="target_db_name" defaultValue={editingProject.target_db_name} required />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>User *</label>
                  <input type="text" name="target_db_user" defaultValue="user" required />
                </div>
                <div className="form-group">
                  <label>Password *</label>
                  <input type="password" name="target_db_password" defaultValue="password" required />
                </div>
              </div>
              <div className="form-group">
                <label>Vector Table Name *</label>
                <input type="text" name="target_table_name" defaultValue={editingProject.target_table_name} required />
              </div>
              <div className="form-group">
                <label>Model *</label>
                <select name="embedding_model" defaultValue={editingProject.embedding_model} required>
                  <option value="mxbai-embed-large">mxbai-embed-large (1024 dims)</option>
                </select>
              </div>
              <div className="form-actions">
                <button type="button" onClick={() => { setShowEditProject(false); setEditingProject(null); }} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary">Update Project</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {confirmDelete && (
        <div className="modal-overlay" onClick={() => setConfirmDelete(null)}>
          <div className="modal modal-small" onClick={(e) => e.stopPropagation()}>
            <h3><Warning size={24} weight="fill" color="#f59e0b" /> Confirm Deletion</h3>
            <p>Are you sure you want to delete <strong>{confirmDelete.name}</strong>?</p>
            {confirmDelete.type === 'project' && (
              <p className="warning-text">This will delete all associated data sources, jobs, and tracking data. This action cannot be undone.</p>
            )}
            <div className="form-actions">
              <button onClick={() => setConfirmDelete(null)} className="btn-secondary">
                Cancel
              </button>
              <button
                onClick={() => {
                  if (confirmDelete.type === 'project') {
                    deleteProject(confirmDelete.id);
                  } else {
                    deleteSource(confirmDelete.id);
                  }
                }}
                className="btn-danger"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      <footer className="footer">
        <p>
          API Documentation: <a href={`${API_URL}/docs`} target="_blank" rel="noreferrer">{API_URL}/docs</a>
        </p>
      </footer>
    </div>
  )
}

export default App
