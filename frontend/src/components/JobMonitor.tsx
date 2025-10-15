import { useState, useEffect } from 'react'
import {
  CheckCircle,
  XCircle,
  Clock,
  ArrowsClockwise,
  Warning,
  Pause,
  Play,
  StopCircle,
  Trash,
  ArrowClockwise,
  PlayCircle
} from '@phosphor-icons/react'
import { useToast } from '../hooks/useToast'
import ConfirmDialog from './ConfirmDialog'
import Pagination from './Pagination'

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

interface ConfirmDialogState {
  isOpen: boolean
  title: string
  message: string
  confirmText: string
  variant: 'danger' | 'primary' | 'warning'
  onConfirm: () => void
}

export default function JobMonitor({ projectId, onJobComplete }: JobMonitorProps) {
  const [jobs, setJobs] = useState<IngestionJob[]>([])
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [totalCount, setTotalCount] = useState(0)
  const [totalPages, setTotalPages] = useState(0)

  const { showToast, ToastContainer } = useToast()
  const API_URL = 'http://localhost:8000'

  useEffect(() => {
    fetchJobs()
  }, [projectId, currentPage, pageSize])

  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      fetchJobs(true) // Silent refresh
    }, 3000) // Poll every 3 seconds

    return () => clearInterval(interval)
  }, [projectId, autoRefresh, currentPage, pageSize])

  const fetchJobs = async (silent = false) => {
    if (!silent) setLoading(true)

    try {
      const response = await fetch(
        `${API_URL}/projects/${projectId}/jobs?page=${currentPage}&page_size=${pageSize}`
      )
      const data = await response.json()

      // Check if any job completed since last fetch
      if (jobs.length > 0 && data.jobs && data.jobs.length > 0) {
        const previousRunningJobs = jobs.filter(j => j.status === 'running')
        const currentCompletedJobs = data.jobs.filter((j: IngestionJob) =>
          j.status === 'completed' || j.status === 'failed'
        )

        if (previousRunningJobs.some(oldJob =>
          currentCompletedJobs.some((newJob: IngestionJob) => newJob.id === oldJob.id)
        )) {
          onJobComplete?.()
        }
      }

      setJobs(data.jobs || [])
      setTotalCount(data.pagination?.total_count || 0)
      setTotalPages(data.pagination?.total_pages || 0)
    } catch (error) {
      console.error('Failed to fetch jobs:', error)
    } finally {
      if (!silent) setLoading(false)
    }
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
    setAutoRefresh(false) // Pause auto-refresh when manually navigating
  }

  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize)
    setCurrentPage(1) // Reset to first page when changing page size
    setAutoRefresh(false) // Pause auto-refresh when changing page size
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
      case 'paused':
        return `${baseClasses} badge-paused`
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

  const handleCancelJob = (jobId: number) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Cancel Job',
      message: `Are you sure you want to cancel Job #${jobId}? This will stop the processing immediately.`,
      confirmText: 'Cancel Job',
      variant: 'danger',
      onConfirm: async () => {
        setConfirmDialog(null)
        try {
          const response = await fetch(`${API_URL}/jobs/${jobId}/cancel`, {
            method: 'POST'
          })

          if (response.ok) {
            showToast('Job cancelled successfully!', 'success')
            fetchJobs() // Refresh jobs list
          } else {
            const error = await response.json()
            showToast(`Failed to cancel job: ${error.detail}`, 'error')
          }
        } catch (error) {
          console.error('Failed to cancel job:', error)
          showToast('Failed to cancel job. Please try again.', 'error')
        }
      }
    })
  }

  const handleRestartJob = (jobId: number) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Restart Job',
      message: `Restart Job #${jobId}? This will create a new job and skip already processed documents.`,
      confirmText: 'Restart Job',
      variant: 'primary',
      onConfirm: async () => {
        setConfirmDialog(null)
        try {
          const response = await fetch(`${API_URL}/jobs/${jobId}/restart`, {
            method: 'POST'
          })

          if (response.ok) {
            const data = await response.json()
            showToast(`Job restarted successfully! New Job ID: #${data.new_job_id}`, 'success')
            fetchJobs() // Refresh jobs list
          } else {
            const error = await response.json()
            showToast(`Failed to restart job: ${error.detail}`, 'error')
          }
        } catch (error) {
          console.error('Failed to restart job:', error)
          showToast('Failed to restart job. Please try again.', 'error')
        }
      }
    })
  }

  const handleDeleteJob = (jobId: number) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Delete Job',
      message: `Are you sure you want to delete Job #${jobId}? This action cannot be undone.`,
      confirmText: 'Delete Job',
      variant: 'danger',
      onConfirm: async () => {
        setConfirmDialog(null)
        try {
          const response = await fetch(`${API_URL}/jobs/${jobId}`, {
            method: 'DELETE'
          })

          if (response.ok) {
            showToast('Job deleted successfully!', 'success')
            fetchJobs() // Refresh jobs list
          } else {
            const error = await response.json()
            showToast(`Failed to delete job: ${error.detail}`, 'error')
          }
        } catch (error) {
          console.error('Failed to delete job:', error)
          showToast('Failed to delete job. Please try again.', 'error')
        }
      }
    })
  }

  const handlePauseJob = (jobId: number) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Pause Job',
      message: `Are you sure you want to pause Job #${jobId}? You can resume it later.`,
      confirmText: 'Pause Job',
      variant: 'warning',
      onConfirm: async () => {
        setConfirmDialog(null)
        try {
          const response = await fetch(`${API_URL}/jobs/${jobId}/pause`, {
            method: 'POST'
          })

          if (response.ok) {
            showToast('Job paused successfully!', 'success')
            fetchJobs()
          } else {
            const error = await response.json()
            showToast(`Failed to pause job: ${error.detail}`, 'error')
          }
        } catch (error) {
          console.error('Failed to pause job:', error)
          showToast('Failed to pause job. Please try again.', 'error')
        }
      }
    })
  }

  const handleResumeJob = (jobId: number) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Resume Job',
      message: `Resume Job #${jobId}? It will continue from where it was paused.`,
      confirmText: 'Resume Job',
      variant: 'primary',
      onConfirm: async () => {
        setConfirmDialog(null)
        try {
          const response = await fetch(`${API_URL}/jobs/${jobId}/resume`, {
            method: 'POST'
          })

          if (response.ok) {
            showToast('Job resumed successfully!', 'success')
            fetchJobs()
          } else {
            const error = await response.json()
            showToast(`Failed to resume job: ${error.detail}`, 'error')
          }
        } catch (error) {
          console.error('Failed to resume job:', error)
          showToast('Failed to resume job. Please try again.', 'error')
        }
      }
    })
  }

  const handleStartJob = (jobId: number) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Start Job',
      message: `Start Job #${jobId}? It will be queued for processing.`,
      confirmText: 'Start Job',
      variant: 'primary',
      onConfirm: async () => {
        setConfirmDialog(null)
        try {
          const response = await fetch(`${API_URL}/jobs/${jobId}/start`, {
            method: 'POST'
          })

          if (response.ok) {
            showToast('Job started successfully!', 'success')
            fetchJobs()
          } else {
            const error = await response.json()
            showToast(`Failed to start job: ${error.detail}`, 'error')
          }
        } catch (error) {
          console.error('Failed to start job:', error)
          showToast('Failed to start job. Please try again.', 'error')
        }
      }
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
                  <div className="job-actions">
                    {/* Start button for pending jobs */}
                    {job.status === 'pending' && (
                      <button
                        className="btn-icon btn-start"
                        onClick={() => handleStartJob(job.id)}
                        title="Start job"
                      >
                        <PlayCircle size={18} weight="fill" />
                      </button>
                    )}

                    {/* Pause button for running jobs */}
                    {job.status === 'running' && (
                      <button
                        className="btn-icon btn-pause"
                        onClick={() => handlePauseJob(job.id)}
                        title="Pause job"
                      >
                        <Pause size={18} weight="fill" />
                      </button>
                    )}

                    {/* Resume button for paused jobs */}
                    {job.status === 'paused' && (
                      <button
                        className="btn-icon btn-resume"
                        onClick={() => handleResumeJob(job.id)}
                        title="Resume job"
                      >
                        <Play size={18} weight="fill" />
                      </button>
                    )}

                    {/* Cancel button for active jobs */}
                    {(job.status === 'running' || job.status === 'pending' || job.status === 'queued' || job.status === 'paused') && (
                      <button
                        className="btn-icon btn-cancel"
                        onClick={() => handleCancelJob(job.id)}
                        title="Cancel job"
                      >
                        <StopCircle size={18} weight="fill" />
                      </button>
                    )}

                    {/* Restart button for failed/cancelled jobs */}
                    {(job.status === 'failed' || job.status === 'cancelled') && (
                      <button
                        className="btn-icon btn-restart"
                        onClick={() => handleRestartJob(job.id)}
                        title="Restart job"
                      >
                        <ArrowClockwise size={18} weight="bold" />
                      </button>
                    )}

                    {/* Delete button for finished jobs */}
                    {(job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled' || job.status === 'paused') && (
                      <button
                        className="btn-icon btn-delete"
                        onClick={() => handleDeleteJob(job.id)}
                        title="Delete job"
                      >
                        <Trash size={18} weight="fill" />
                      </button>
                    )}
                  </div>
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

      {/* Pagination */}
      {totalPages > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalCount={totalCount}
          pageSize={pageSize}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
        />
      )}

      {/* Toast Notifications */}
      <ToastContainer />

      {/* Confirmation Dialog */}
      {confirmDialog && (
        <ConfirmDialog
          title={confirmDialog.title}
          message={confirmDialog.message}
          confirmText={confirmDialog.confirmText}
          variant={confirmDialog.variant}
          onConfirm={confirmDialog.onConfirm}
          onCancel={() => setConfirmDialog(null)}
        />
      )}
    </div>
  )
}
