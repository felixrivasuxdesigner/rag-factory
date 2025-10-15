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
  Warning,
  Clock
} from '@phosphor-icons/react'
import SearchPanel from './components/SearchPanel'
import CreateSourceModal from './components/CreateSourceModal'
import JobMonitor from './components/JobMonitor'
import TabNavigation from './components/TabNavigation'
import type { TabType } from './components/TabNavigation'
import SourceFilters from './components/SourceFilters'
import ProjectInsights from './components/ProjectInsights'
import ScheduleManager from './components/ScheduleManager'
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

interface DataSource {
  id: number
  project_id: number
  name: string
  source_type: string
  is_active: boolean
  config: any
  sync_frequency?: string
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
  const [sources, setSources] = useState<DataSource[]>([])
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [loading, setLoading] = useState(false)
  const [showCreateProject, setShowCreateProject] = useState(false)
  const [showEditProject, setShowEditProject] = useState(false)
  const [editingProject, setEditingProject] = useState<Project | null>(null)
  const [showCreateSource, setShowCreateSource] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<{type: 'project' | 'source', id: number, name: string} | null>(null)

  // Phase 4.3: Tab and Filter states
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [sourceSearchQuery, setSourceSearchQuery] = useState('')
  const [sourceTypeFilter, setSourceTypeFilter] = useState('')
  const [sourceStatusFilter, setSourceStatusFilter] = useState('')

  // Phase 5: Scheduling state
  const [scheduleOpen, setScheduleOpen] = useState<number | null>(null)

  useEffect(() => {
    checkHealth()
    loadProjects()
    loadConnectors()
  }, [])

  useEffect(() => {
    if (selectedProject) {
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

  const createSource = async (sourceType: string, formData: FormData) => {
    if (!selectedProject) return

    let config: Record<string, any> = {}

    // Build config based on source type
    if (sourceType === 'sparql') {
      config = {
        endpoint: formData.get('endpoint'),
        query: formData.get('query'),
        id_field: formData.get('id_field') || 'id',
        title_field: formData.get('title_field') || 'title',
        content_fields: formData.get('content_fields') || 'content',
        limit: parseInt(formData.get('limit') as string) || 25
      }
    } else if (sourceType === 'rest_api') {
      const headersStr = formData.get('headers')
      config = {
        base_url: formData.get('base_url'),
        endpoint: formData.get('endpoint'),
        method: formData.get('method') || 'GET',
        auth_type: formData.get('auth_type') || '',
        api_key: formData.get('api_key') || '',
        headers: headersStr ? JSON.parse(headersStr as string) : {},
        limit_param: formData.get('limit_param') || 'limit',
        offset_param: formData.get('offset_param') || 'offset',
        date_param: formData.get('date_param') || '',
        data_path: formData.get('data_path') || 'data',
        id_field: formData.get('id_field') || 'id',
        title_field: formData.get('title_field') || 'title',
        content_field: formData.get('content_field') || 'content',
        date_field: formData.get('date_field') || '',
        limit: parseInt(formData.get('limit') as string) || 25
      }
    } else if (sourceType === 'rss_feed') {
      config = {
        feed_url: formData.get('feed_url'),
        auto_discover: formData.get('auto_discover') === 'on',
        limit: parseInt(formData.get('limit') as string) || 50
      }
    } else if (sourceType === 'github') {
      config = {
        repository: formData.get('repository'),
        token: formData.get('token') || '',
        include_readme: formData.get('include_readme') === 'on',
        include_issues: formData.get('include_issues') === 'on',
        include_prs: formData.get('include_prs') === 'on',
        include_code: formData.get('include_code') === 'on',
        limit: parseInt(formData.get('limit') as string) || 50
      }
    } else if (sourceType === 'web_scraper') {
      config = {
        start_url: formData.get('start_url'),
        content_selector: formData.get('content_selector'),
        title_selector: formData.get('title_selector') || 'h1',
        max_pages: parseInt(formData.get('max_pages') as string) || 1
      }
    } else if (sourceType === 'google_drive') {
      config = {
        credentials_json: formData.get('credentials_json'),
        folder_id: formData.get('folder_id') || '',
        recursive: formData.get('recursive') === 'on',
        include_docs: formData.get('include_docs') === 'on',
        include_sheets: formData.get('include_sheets') === 'on',
        include_pdfs: formData.get('include_pdfs') === 'on'
      }
    } else if (sourceType === 'notion') {
      config = {
        token: formData.get('token'),
        search_query: formData.get('search_query') || '',
        include_pages: formData.get('include_pages') === 'on',
        include_databases: formData.get('include_databases') === 'on'
      }
    } else if (sourceType === 'file_upload') {
      const documents = formData.get('documents')
      config = {
        documents: documents ? JSON.parse(documents as string) : []
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
        throw new Error(errorData.detail || 'Failed to create source')
      }
    } catch (error) {
      setError('Failed to create source')
      throw error
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

  // Phase 4.3: Filter sources based on search and filters
  const filteredSources = sources.filter(source => {
    // Search filter
    if (sourceSearchQuery && !source.name.toLowerCase().includes(sourceSearchQuery.toLowerCase())) {
      return false
    }

    // Type filter
    if (sourceTypeFilter && source.source_type !== sourceTypeFilter) {
      return false
    }

    // Status filter
    if (sourceStatusFilter === 'active' && !source.is_active) {
      return false
    }
    if (sourceStatusFilter === 'inactive' && source.is_active) {
      return false
    }

    return true
  })

  // Get unique source types for filter dropdown
  const availableSourceTypes = Array.from(new Set(sources.map(s => s.source_type)))

  return (
    <div className="app">
      <header className="header">
        <h1><Factory size={32} weight="duotone" /> RAG Factory</h1>
        <p className="subtitle">Multi-Project RAG Management System</p>
      </header>

      {error && <div className="alert alert-error">{error} <button onClick={() => setError(null)}>×</button></div>}
      {success && <div className="alert alert-success">{success}</div>}

      {/* Tab Navigation */}
      <TabNavigation
        activeTab={activeTab}
        onTabChange={setActiveTab}
        projectSelected={!!selectedProject}
      />

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="tab-content">

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
                    <option value="jina/jina-embeddings-v2-base-es">jina/jina-embeddings-v2-base-es (768 dims) - Bilingual ES/EN</option>
                    <option value="embeddinggemma">embeddinggemma (768 dims) - Multilingual (100+ languages)</option>
                  </select>
                  <small>Jina ES recommended for Spanish-English bilingual content</small>
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

      {/* Project Insights & Visualizations */}
      {selectedProject && (
        <ProjectInsights projectId={selectedProject} />
      )}
        </div>
      )}

      {/* Jobs Tab */}
      {activeTab === 'jobs' && selectedProject && (
        <div className="tab-content">
          <JobMonitor
            projectId={selectedProject}
            onJobComplete={() => {}}
          />
        </div>
      )}

      {/* Search & Query Tab */}
      {activeTab === 'search' && selectedProject && projects.find(p => p.id === selectedProject) && (
        <div className="tab-content">
          <SearchPanel
            projectId={selectedProject}
            projectName={projects.find(p => p.id === selectedProject)!.name}
          />
        </div>
      )}

      {/* Data Sources Tab */}
      {activeTab === 'sources' && selectedProject && (
        <div className="tab-content">
        <section className="sources-section">
          <div className="section-header">
            <h2>Data Sources</h2>
            <button onClick={() => setShowCreateSource(true)} className="btn-primary">
              <Plus size={18} weight="bold" /> New Source
            </button>
          </div>

          {showCreateSource && (
            <CreateSourceModal
              connectors={connectors}
              onClose={() => setShowCreateSource(false)}
              onSubmit={createSource}
            />
          )}

          {/* Source Filters */}
          {sources.length > 0 && (
            <SourceFilters
              searchQuery={sourceSearchQuery}
              onSearchChange={setSourceSearchQuery}
              typeFilter={sourceTypeFilter}
              onTypeFilterChange={setSourceTypeFilter}
              availableTypes={availableSourceTypes}
              statusFilter={sourceStatusFilter}
              onStatusFilterChange={setSourceStatusFilter}
            />
          )}

          {filteredSources.length > 0 ? (
            <div className="sources-list">
              {filteredSources.map((source) => (
                <div key={source.id} className="source-card">
                  <div className="source-header">
                    <h4>{source.name}</h4>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      <span className={`badge ${source.is_active ? 'active' : 'inactive'}`}>
                        {source.is_active ? 'Active' : 'Inactive'}
                      </span>
                      {source.sync_frequency && source.sync_frequency !== 'manual' && (
                        <span className="schedule-badge">
                          <Clock size={12} weight="fill" />
                          {source.sync_frequency}
                        </span>
                      )}
                    </div>
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
                      <Play size={16} weight="fill" /> Run Now
                    </button>
                    <button
                      onClick={() => setScheduleOpen(scheduleOpen === source.id ? null : source.id)}
                      className="btn-secondary btn-small"
                    >
                      <Clock size={16} weight="bold" /> Schedule
                    </button>
                    <button
                      onClick={() => setConfirmDelete({type: 'source', id: source.id, name: source.name})}
                      className="btn-icon btn-danger"
                      title="Delete source"
                    >
                      <Trash size={18} weight="bold" />
                    </button>
                  </div>

                  {/* Schedule Manager */}
                  {scheduleOpen === source.id && (
                    <ScheduleManager
                      sourceId={source.id}
                      sourceName={source.name}
                      currentFrequency={source.sync_frequency || 'manual'}
                      onUpdate={() => loadProjectSources(selectedProject!)}
                    />
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>No data sources configured. Create one to start ingesting documents.</p>
            </div>
          )}
        </section>
        </div>
      )}

      {/* Modals - Always available */}

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
                  <option value="jina/jina-embeddings-v2-base-es">jina/jina-embeddings-v2-base-es (768 dims) - Bilingual ES/EN</option>
                  <option value="embeddinggemma">embeddinggemma (768 dims) - Multilingual (100+ languages)</option>
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
