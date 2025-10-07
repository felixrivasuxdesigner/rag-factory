import { useState, useEffect } from 'react'
import {
  CheckCircle,
  XCircle,
  Clock,
  ArrowsClockwise,
  Warning,
  Pause,
  Play
} from '@phosphor-icons/react'

interface IngestionJob {
  id: number
  project_id: number
  source_id: number | null
  job_type: string
  status: string
  total_documents: number
  processed_documents: number
  successful_documents: number
  failed_documents: number
  error_log: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

interface JobMonitorProps {
  projectId: number
  onJobComplete?: () => void
}

export default function JobMonitor({ projectId, onJobComplete }: JobMonitorProps) {
  const [jobs, setJobs] = useState<IngestionJob[]>([])
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const API_URL = 'http://localhost:8000'

  useEffect(() => {
    fetchJobs()
  }, [projectId])

  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      fetchJobs(true) // Silent refresh
    }, 3000) // Poll every 3 seconds

    return () => clearInterval(interval)
  }, [projectId, autoRefresh])

  const fetchJobs = async (silent = false) => {
    if (!silent) setLoading(true)

    try {
      const response = await fetch(`${API_URL}/projects/${projectId}/jobs?limit=10`)
      const data = await response.json()

      // Check if any job completed since last fetch
      if (jobs.length > 0 && data.length > 0) {
        const previousRunningJobs = jobs.filter(j => j.status === 'running')
        const currentCompletedJobs = data.filter((j: IngestionJob) =>
          j.status === 'completed' || j.status === 'failed'
        )

        if (previousRunningJobs.some(oldJob =>
          currentCompletedJobs.some((newJob: IngestionJob) => newJob.id === oldJob.id)
        )) {
          onJobComplete?.()
        }
      }

      setJobs(data)
    } catch (error) {
      console.error('Failed to fetch jobs:', error)
    } finally {
      if (!silent) setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={20} weight="fill" className="text-green-500" />
      case 'failed':
        return <XCircle size={20} weight="fill" className="text-red-500" />
      case 'running':
        return <ArrowsClockwise size={20} weight="bold" className="text-blue-500 animate-spin" />
      case 'pending':
        return <Clock size={20} weight="fill" className="text-yellow-500" />
      default:
        return <Clock size={20} weight="fill" className="text-gray-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    const baseClasses = "badge"
    switch (status) {
      case 'completed':
        return `${baseClasses} badge-success`
      case 'failed':
        return `${baseClasses} badge-error`
      case 'running':
        return `${baseClasses} badge-running`
      case 'pending':
        return `${baseClasses} badge-pending`
      default:
        return baseClasses
    }
  }

  const calculateProgress = (job: IngestionJob) => {
    if (job.total_documents === 0) return 0
    return Math.round((job.processed_documents / job.total_documents) * 100)
  }

  const formatDuration = (start: string | null, end: string | null) => {
    if (!start) return 'Not started'

    const startTime = new Date(start).getTime()
    const endTime = end ? new Date(end).getTime() : Date.now()
    const duration = Math.floor((endTime - startTime) / 1000)

    if (duration < 60) return `${duration}s`
    if (duration < 3600) return `${Math.floor(duration / 60)}m ${duration % 60}s`
    return `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`
  }

  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div className="job-monitor loading">
        <div className="spinner"></div>
        <p>Loading jobs...</p>
      </div>
    )
  }

  if (jobs.length === 0) {
    return (
      <div className="job-monitor empty">
        <Clock size={48} weight="duotone" className="empty-icon" />
        <p>No ingestion jobs yet</p>
        <small>Run an ingestion from a data source to see jobs here</small>
      </div>
    )
  }

  return (
    <div className="job-monitor">
      <div className="job-monitor-header">
        <h3>Recent Jobs</h3>
        <div className="job-monitor-controls">
          <button
            className={`btn-icon ${autoRefresh ? 'active' : ''}`}
            onClick={() => setAutoRefresh(!autoRefresh)}
            title={autoRefresh ? 'Disable auto-refresh' : 'Enable auto-refresh'}
          >
            {autoRefresh ? <Pause size={18} /> : <Play size={18} />}
          </button>
          <button
            className="btn-icon"
            onClick={() => fetchJobs()}
            title="Refresh now"
          >
            <ArrowsClockwise size={18} weight="bold" />
          </button>
        </div>
      </div>

      <div className="jobs-list">
        {jobs.map((job) => {
          const progress = calculateProgress(job)
          const isActive = job.status === 'running' || job.status === 'pending'

          return (
            <div key={job.id} className={`job-card ${isActive ? 'active' : ''}`}>
              <div className="job-header">
                <div className="job-title">
                  {getStatusIcon(job.status)}
                  <span className="job-id">Job #{job.id}</span>
                  <span className={getStatusBadge(job.status)}>{job.status}</span>
                </div>
                <div className="job-meta">
                  <span className="job-date">{formatDateTime(job.created_at)}</span>
                </div>
              </div>

              {/* Progress Bar */}
              {job.total_documents > 0 && (
                <div className="progress-section">
                  <div className="progress-bar-container">
                    <div
                      className={`progress-bar ${job.status === 'failed' ? 'error' : 'success'}`}
                      style={{ width: `${progress}%` }}
                    >
                      <span className="progress-label">{progress}%</span>
                    </div>
                  </div>
                  <div className="progress-stats">
                    <span>{job.processed_documents} / {job.total_documents} documents</span>
                    {job.status === 'running' && (
                      <span className="duration">{formatDuration(job.started_at, null)}</span>
                    )}
                  </div>
                </div>
              )}

              {/* Stats Grid */}
              <div className="job-stats-grid">
                <div className="stat">
                  <span className="stat-label">Total</span>
                  <span className="stat-value">{job.total_documents}</span>
                </div>
                <div className="stat success">
                  <span className="stat-label">Success</span>
                  <span className="stat-value">{job.successful_documents}</span>
                </div>
                <div className="stat error">
                  <span className="stat-label">Failed</span>
                  <span className="stat-value">{job.failed_documents}</span>
                </div>
                {job.completed_at && (
                  <div className="stat">
                    <span className="stat-label">Duration</span>
                    <span className="stat-value">
                      {formatDuration(job.started_at, job.completed_at)}
                    </span>
                  </div>
                )}
              </div>

              {/* Error Log */}
              {job.error_log && (
                <div className="job-error">
                  <div className="error-header">
                    <Warning size={16} weight="fill" />
                    <span>Error Details</span>
                  </div>
                  <pre className="error-log">{job.error_log}</pre>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
