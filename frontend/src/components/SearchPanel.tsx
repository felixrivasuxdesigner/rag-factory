import { useState } from 'react'
import { MagnifyingGlass, Sparkle, Article } from '@phosphor-icons/react'

const API_URL = 'http://localhost:8000'

interface SearchResult {
  id: string
  content: string
  metadata: any
  similarity: number
}

interface SearchResponse {
  query: string
  results: SearchResult[]
  total_results: number
  project_id: number
}

interface RAGResponse {
  question: string
  answer: string
  sources: SearchResult[]
  model: string
  project_id: number
}

interface SearchPanelProps {
  projectId: number
  projectName: string
}

export default function SearchPanel({ projectId, projectName }: SearchPanelProps) {
  const [mode, setMode] = useState<'search' | 'rag'>('rag')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [ragAnswer, setRagAnswer] = useState<string | null>(null)
  const [ragSources, setRagSources] = useState<SearchResult[]>([])
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError(null)
    setSearchResults([])
    setRagAnswer(null)
    setRagSources([])

    try {
      const endpoint = mode === 'search' ? '/search' : '/query'
      const body = mode === 'search'
        ? {
            project_id: projectId,
            query: query,
            top_k: 5,
            similarity_threshold: 0.3
          }
        : {
            project_id: projectId,
            question: query,
            top_k: 5,
            similarity_threshold: 0.3,
            model: 'gemma3:1b-it-qat',
            max_tokens: 500
          }

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })

      if (!response.ok) {
        throw new Error(`Error: ${response.statusText}`)
      }

      const data = await response.json()

      if (mode === 'search') {
        const searchData = data as SearchResponse
        setSearchResults(searchData.results)
      } else {
        const ragData = data as RAGResponse
        setRagAnswer(ragData.answer)
        setRagSources(ragData.sources)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to perform query')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="search-panel">
      <div className="panel-header">
        <h2>
          {mode === 'search' ? <MagnifyingGlass size={24} weight="fill" /> : <Sparkle size={24} weight="fill" />}
          {mode === 'search' ? 'Semantic Search' : 'RAG Query'}
        </h2>
        <div className="mode-toggle">
          <button
            className={mode === 'search' ? 'active' : ''}
            onClick={() => setMode('search')}
            title="Similarity search only"
          >
            <MagnifyingGlass size={18} />
            Search
          </button>
          <button
            className={mode === 'rag' ? 'active' : ''}
            onClick={() => setMode('rag')}
            title="RAG with AI answer generation"
          >
            <Sparkle size={18} />
            Ask AI
          </button>
        </div>
      </div>

      <div className="search-info">
        <p>
          <strong>Project:</strong> {projectName} (ID: {projectId})
        </p>
        <p className="help-text">
          {mode === 'search'
            ? '🔍 Search mode finds similar documents using semantic similarity'
            : '✨ Ask AI mode uses RAG to answer questions based on your documents'}
        </p>
      </div>

      <form onSubmit={handleSearch} className="search-form">
        <div className="input-group">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={mode === 'search'
              ? 'Enter search query (e.g., "artificial intelligence")'
              : 'Ask a question (e.g., "What is machine learning?")'}
            disabled={loading}
            className="query-input"
          />
          <button type="submit" disabled={loading || !query.trim()}>
            {loading ? '...' : mode === 'search' ? 'Search' : 'Ask'}
          </button>
        </div>
      </form>

      {error && (
        <div className="error-message">
          ❌ {error}
        </div>
      )}

      {loading && (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>{mode === 'search' ? 'Searching documents...' : 'Generating answer with AI...'}</p>
        </div>
      )}

      {/* RAG Answer */}
      {mode === 'rag' && ragAnswer && (
        <div className="rag-answer">
          <h3>
            <Sparkle size={20} weight="fill" />
            Answer
          </h3>
          <div className="answer-content">
            {ragAnswer}
          </div>
          <p className="model-info">
            <em>Generated by gemma3:1b-it-qat</em>
          </p>
        </div>
      )}

      {/* Search Results / RAG Sources */}
      {(searchResults.length > 0 || ragSources.length > 0) && (
        <div className="results-section">
          <h3>
            <Article size={20} weight="fill" />
            {mode === 'search' ? `Results (${searchResults.length})` : `Sources (${ragSources.length})`}
          </h3>
          <div className="results-list">
            {(mode === 'search' ? searchResults : ragSources).map((result, idx) => (
              <div key={result.id} className="result-card">
                <div className="result-header">
                  <span className="result-number">#{idx + 1}</span>
                  <span className="similarity-badge">
                    {(result.similarity * 100).toFixed(1)}% match
                  </span>
                </div>
                <div className="result-content">
                  {result.content.length > 300
                    ? `${result.content.substring(0, 300)}...`
                    : result.content}
                </div>
                {result.metadata && (
                  <div className="result-metadata">
                    <small>ID: {result.id}</small>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && !error && mode === 'search' && searchResults.length === 0 && query && (
        <div className="no-results">
          No documents found matching your query.
        </div>
      )}
    </div>
  )
}
