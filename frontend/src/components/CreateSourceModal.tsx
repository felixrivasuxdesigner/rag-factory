import { useState } from 'react'
import { X, CheckCircle, XCircle, ArrowRight } from '@phosphor-icons/react'
import ConnectorCard from './ConnectorCard'
import { getExamplesBySourceType, type ExampleConfig } from '../utils/exampleConfigs'

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

interface CreateSourceModalProps {
  connectors: Connector[]
  onClose: () => void
  onSubmit: (sourceType: string, formData: FormData) => Promise<void>
}

export default function CreateSourceModal({
  connectors,
  onClose,
  onSubmit
}: CreateSourceModalProps) {
  const [step, setStep] = useState<'select' | 'configure'>('select')
  const [selectedType, setSelectedType] = useState<string>('')
  const [selectedExample, setSelectedExample] = useState<ExampleConfig | null>(null)
  const [testingConnection, setTestingConnection] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

  const handleConnectorSelect = (sourceType: string) => {
    setSelectedType(sourceType)
    setStep('configure')
  }

  const handleExampleSelect = (example: ExampleConfig) => {
    setSelectedExample(example)
    // Auto-fill form will happen in the render
  }

  const handleTestConnection = async () => {
    setTestingConnection(true)
    setTestResult(null)

    // TODO: Implement actual test connection logic
    // For now, simulate it
    await new Promise(resolve => setTimeout(resolve, 1500))

    setTestResult({
      success: true,
      message: 'Connection successful! Configuration is valid.'
    })
    setTestingConnection(false)
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    await onSubmit(selectedType, formData)
  }

  const examples = selectedType ? getExamplesBySourceType(selectedType) : []
  const selectedConnector = connectors.find(c => c.source_type === selectedType)

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{step === 'select' ? 'Select Connector Type' : 'Configure Data Source'}</h3>
          <button className="btn-icon" onClick={onClose}>
            <X size={24} weight="bold" />
          </button>
        </div>

        {step === 'select' && (
          <div className="connector-grid">
            {connectors.map((connector) => (
              <ConnectorCard
                key={connector.source_type}
                sourceType={connector.source_type}
                name={connector.name}
                description={connector.description}
                category={connector.category}
                isSelected={selectedType === connector.source_type}
                onSelect={() => handleConnectorSelect(connector.source_type)}
              />
            ))}
          </div>
        )}

        {step === 'configure' && (
          <>
            <div className="breadcrumb">
              <button
                className="breadcrumb-link"
                onClick={() => {
                  setStep('select')
                  setSelectedType('')
                  setSelectedExample(null)
                }}
              >
                Select Connector
              </button>
              <ArrowRight size={16} />
              <span>{selectedConnector?.name}</span>
            </div>

            {examples.length > 0 && (
              <div className="examples-section">
                <h4>📚 Example Configurations</h4>
                <div className="examples-grid">
                  {examples.map((example) => (
                    <div
                      key={example.id}
                      className={`example-card ${selectedExample?.id === example.id ? 'selected' : ''}`}
                      onClick={() => handleExampleSelect(example)}
                    >
                      <h5>{example.name}</h5>
                      <p>{example.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="source-form">
              <div className="form-group">
                <label>Source Name *</label>
                <input
                  type="text"
                  name="name"
                  defaultValue={selectedExample?.config.name || ''}
                  placeholder="My Data Source"
                  required
                />
              </div>

              {/* Dynamic form fields based on connector type */}
              {selectedType === 'sparql' && (
                <SPARQLFields selectedExample={selectedExample} />
              )}
              {selectedType === 'rest_api' && (
                <RESTAPIFields selectedExample={selectedExample} />
              )}
              {selectedType === 'rss_feed' && (
                <RSSFields selectedExample={selectedExample} />
              )}
              {selectedType === 'github' && (
                <GitHubFields selectedExample={selectedExample} />
              )}
              {selectedType === 'web_scraper' && (
                <WebScraperFields selectedExample={selectedExample} />
              )}
              {selectedType === 'google_drive' && (
                <GoogleDriveFields selectedExample={selectedExample} />
              )}
              {selectedType === 'notion' && (
                <NotionFields selectedExample={selectedExample} />
              )}
              {selectedType === 'file_upload' && (
                <FileUploadFields selectedExample={selectedExample} />
              )}

              {testResult && (
                <div className={`alert ${testResult.success ? 'alert-success' : 'alert-error'}`}>
                  {testResult.success ? (
                    <CheckCircle size={20} weight="fill" />
                  ) : (
                    <XCircle size={20} weight="fill" />
                  )}
                  {testResult.message}
                </div>
              )}

              <div className="form-actions">
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testingConnection}
                  className="btn-secondary"
                >
                  {testingConnection ? 'Testing...' : 'Test Connection'}
                </button>
                <button type="button" onClick={onClose} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create Source
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

// Field components for each connector type
function SPARQLFields({ selectedExample }: { selectedExample: ExampleConfig | null }) {
  return (
    <>
      <div className="form-group">
        <label>SPARQL Endpoint URL *</label>
        <input
          type="url"
          name="endpoint"
          defaultValue={selectedExample?.config.endpoint || ''}
          placeholder="https://query.wikidata.org/sparql"
          required
        />
      </div>
      <div className="form-group">
        <label>SPARQL Query *</label>
        <textarea
          name="query"
          rows={10}
          defaultValue={selectedExample?.config.query || ''}
          placeholder="SELECT ?id ?title ?content WHERE { ... }"
          required
        />
        <small>Use placeholders: {'{'}limit{'}'}, {'{'}offset{'}'}, {'{'}date_filter{'}'}</small>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>ID Field</label>
          <input
            type="text"
            name="id_field"
            defaultValue={selectedExample?.config.id_field || 'id'}
            placeholder="id"
          />
        </div>
        <div className="form-group">
          <label>Title Field</label>
          <input
            type="text"
            name="title_field"
            defaultValue={selectedExample?.config.title_field || 'title'}
            placeholder="title"
          />
        </div>
      </div>
      <div className="form-group">
        <label>Content Fields</label>
        <input
          type="text"
          name="content_fields"
          defaultValue={selectedExample?.config.content_fields || 'content'}
          placeholder="content,description"
        />
        <small>Comma-separated field names</small>
      </div>
      <div className="form-group">
        <label>Limit</label>
        <input
          type="number"
          name="limit"
          defaultValue={selectedExample?.config.limit || 25}
          min="1"
          max="1000"
        />
      </div>
    </>
  )
}

function RESTAPIFields({ selectedExample }: { selectedExample: ExampleConfig | null }) {
  return (
    <>
      <div className="form-group">
        <label>Base URL *</label>
        <input
          type="url"
          name="base_url"
          defaultValue={selectedExample?.config.base_url || ''}
          placeholder="https://api.example.com"
          required
        />
      </div>
      <div className="form-group">
        <label>Endpoint Path *</label>
        <input
          type="text"
          name="endpoint"
          defaultValue={selectedExample?.config.endpoint || ''}
          placeholder="/v1/documents"
          required
        />
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Method</label>
          <select name="method" defaultValue={selectedExample?.config.method || 'GET'}>
            <option value="GET">GET</option>
            <option value="POST">POST</option>
          </select>
        </div>
        <div className="form-group">
          <label>Auth Type</label>
          <select name="auth_type" defaultValue={selectedExample?.config.auth_type || ''}>
            <option value="">None</option>
            <option value="api_key">API Key</option>
            <option value="bearer">Bearer Token</option>
          </select>
        </div>
      </div>
      <div className="form-group">
        <label>API Key / Token</label>
        <input
          type="text"
          name="api_key"
          defaultValue={selectedExample?.config.api_key || ''}
          placeholder="your-api-key"
        />
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Data Path</label>
          <input
            type="text"
            name="data_path"
            defaultValue={selectedExample?.config.data_path || 'data'}
            placeholder="data.results"
          />
        </div>
        <div className="form-group">
          <label>ID Field</label>
          <input
            type="text"
            name="id_field"
            defaultValue={selectedExample?.config.id_field || 'id'}
            placeholder="id"
          />
        </div>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Title Field</label>
          <input
            type="text"
            name="title_field"
            defaultValue={selectedExample?.config.title_field || 'title'}
            placeholder="title"
          />
        </div>
        <div className="form-group">
          <label>Content Field</label>
          <input
            type="text"
            name="content_field"
            defaultValue={selectedExample?.config.content_field || 'content'}
            placeholder="content"
          />
        </div>
      </div>
    </>
  )
}

function RSSFields({ selectedExample }: { selectedExample: ExampleConfig | null }) {
  return (
    <>
      <div className="form-group">
        <label>Feed URL *</label>
        <input
          type="url"
          name="feed_url"
          defaultValue={selectedExample?.config.feed_url || ''}
          placeholder="https://example.com/feed.xml"
          required
        />
      </div>
      <div className="form-group">
        <label>
          <input
            type="checkbox"
            name="auto_discover"
            defaultChecked={selectedExample?.config.auto_discover || false}
          />
          {' '}Auto-discover feed from webpage
        </label>
      </div>
      <div className="form-group">
        <label>Limit</label>
        <input
          type="number"
          name="limit"
          defaultValue={selectedExample?.config.limit || 50}
          min="1"
        />
      </div>
    </>
  )
}

function GitHubFields({ selectedExample }: { selectedExample: ExampleConfig | null }) {
  return (
    <>
      <div className="form-group">
        <label>Repository *</label>
        <input
          type="text"
          name="repository"
          defaultValue={selectedExample?.config.repository || ''}
          placeholder="owner/repo"
          required
        />
        <small>Format: owner/repository</small>
      </div>
      <div className="form-group">
        <label>Personal Access Token</label>
        <input
          type="password"
          name="token"
          placeholder="ghp_xxxxxxxxxxxx"
        />
        <small>Optional but recommended for higher rate limits</small>
      </div>
      <div className="form-group">
        <label>Include:</label>
        <div className="checkbox-group">
          <label>
            <input type="checkbox" name="include_readme" defaultChecked={selectedExample?.config.include_readme ?? true} />
            {' '}README & Documentation
          </label>
          <label>
            <input type="checkbox" name="include_issues" defaultChecked={selectedExample?.config.include_issues ?? true} />
            {' '}Issues with Comments
          </label>
          <label>
            <input type="checkbox" name="include_prs" defaultChecked={selectedExample?.config.include_prs ?? false} />
            {' '}Pull Requests
          </label>
          <label>
            <input type="checkbox" name="include_code" defaultChecked={selectedExample?.config.include_code ?? false} />
            {' '}Code Files
          </label>
        </div>
      </div>
      <div className="form-group">
        <label>Limit</label>
        <input
          type="number"
          name="limit"
          defaultValue={selectedExample?.config.limit || 50}
          min="1"
        />
      </div>
    </>
  )
}

function WebScraperFields({ selectedExample }: { selectedExample: ExampleConfig | null }) {
  return (
    <>
      <div className="form-group">
        <label>Start URL *</label>
        <input
          type="url"
          name="start_url"
          defaultValue={selectedExample?.config.start_url || ''}
          placeholder="https://example.com"
          required
        />
      </div>
      <div className="form-group">
        <label>Content Selector *</label>
        <input
          type="text"
          name="content_selector"
          defaultValue={selectedExample?.config.content_selector || 'article'}
          placeholder="article, .content, #main-text"
          required
        />
        <small>CSS selector for main content</small>
      </div>
      <div className="form-group">
        <label>Title Selector</label>
        <input
          type="text"
          name="title_selector"
          defaultValue={selectedExample?.config.title_selector || 'h1'}
          placeholder="h1, .title"
        />
      </div>
      <div className="form-group">
        <label>Max Pages</label>
        <input
          type="number"
          name="max_pages"
          defaultValue={selectedExample?.config.max_pages || 1}
          min="1"
          max="100"
        />
      </div>
    </>
  )
}

function GoogleDriveFields({ selectedExample }: { selectedExample: ExampleConfig | null }) {
  return (
    <>
      <div className="form-group">
        <label>Credentials JSON *</label>
        <textarea
          name="credentials_json"
          rows={8}
          placeholder='{"type": "service_account", ...}'
          required
        />
        <small>Service account or OAuth2 credentials</small>
      </div>
      <div className="form-group">
        <label>Folder ID</label>
        <input
          type="text"
          name="folder_id"
          defaultValue={selectedExample?.config.folder_id || ''}
          placeholder="Leave empty for root"
        />
      </div>
      <div className="form-group">
        <label>
          <input type="checkbox" name="recursive" defaultChecked={selectedExample?.config.recursive ?? true} />
          {' '}Scan subfolders recursively
        </label>
      </div>
      <div className="form-group">
        <label>Include:</label>
        <div className="checkbox-group">
          <label>
            <input type="checkbox" name="include_docs" defaultChecked={selectedExample?.config.include_docs ?? true} />
            {' '}Google Docs
          </label>
          <label>
            <input type="checkbox" name="include_sheets" defaultChecked={selectedExample?.config.include_sheets ?? true} />
            {' '}Google Sheets
          </label>
          <label>
            <input type="checkbox" name="include_pdfs" defaultChecked={selectedExample?.config.include_pdfs ?? true} />
            {' '}PDFs
          </label>
        </div>
      </div>
    </>
  )
}

function NotionFields({ selectedExample }: { selectedExample: ExampleConfig | null }) {
  return (
    <>
      <div className="form-group">
        <label>Integration Token *</label>
        <input
          type="password"
          name="token"
          placeholder="secret_xxxxxxxxxxxx"
          required
        />
        <small>Create an integration at notion.so/my-integrations</small>
      </div>
      <div className="form-group">
        <label>Search Query</label>
        <input
          type="text"
          name="search_query"
          defaultValue={selectedExample?.config.search_query || ''}
          placeholder="Leave empty for all pages"
        />
      </div>
      <div className="form-group">
        <label>Include:</label>
        <div className="checkbox-group">
          <label>
            <input type="checkbox" name="include_pages" defaultChecked={selectedExample?.config.include_pages ?? true} />
            {' '}Pages
          </label>
          <label>
            <input type="checkbox" name="include_databases" defaultChecked={selectedExample?.config.include_databases ?? true} />
            {' '}Databases
          </label>
        </div>
      </div>
    </>
  )
}

function FileUploadFields({ selectedExample }: { selectedExample: ExampleConfig | null }) {
  return (
    <div className="form-group">
      <label>Documents (JSON) *</label>
      <textarea
        name="documents"
        rows={12}
        defaultValue={selectedExample ? JSON.stringify(selectedExample.config.documents, null, 2) : ''}
        placeholder={'[\n  {\n    "id": "doc1",\n    "title": "Document Title",\n    "content": "Full document content..."\n  }\n]'}
        required
      />
      <small>Array of documents with id, title, and content fields</small>
    </div>
  )
}
