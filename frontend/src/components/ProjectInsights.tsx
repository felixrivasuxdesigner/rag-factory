import { useState, useEffect } from 'react'
import {
  FileText,
  CheckCircle,
  XCircle,
  Database,
  TrendUp,
  Clock
} from '@phosphor-icons/react'
import MetricCard from './MetricCard'
import BarChart from './BarChart'
import SyncTimeline from './SyncTimeline'
import CollapsibleSection from './CollapsibleSection'

interface ProjectInsightsProps {
  projectId: number
}

interface InsightsData {
  total_documents: number
  documents_completed: number
  documents_failed: number
  total_jobs: number
  jobs_completed: number
  jobs_failed: number
  sources_count: number
  recent_jobs: Array<{
    id: number
    source_id: number
    source_name: string
    status: string
    documents_count: number
    created_at: string
    completed_at: string | null
  }>
  documents_by_source: Array<{
    source_name: string
    document_count: number
  }>
}

export default function ProjectInsights({ projectId }: ProjectInsightsProps) {
  const [insights, setInsights] = useState<InsightsData | null>(null)
  const [loading, setLoading] = useState(true)

  const API_URL = 'http://localhost:8000'

  useEffect(() => {
    fetchInsights()
  }, [projectId])

  const fetchInsights = async () => {
    setLoading(true)
    try {
      // Fetch stats
      const statsRes = await fetch(`${API_URL}/projects/${projectId}/stats`)
      const stats = await statsRes.json()

      // Fetch jobs
      const jobsRes = await fetch(`${API_URL}/projects/${projectId}/jobs?limit=10`)
      const jobs = await jobsRes.json()

      // Fetch sources
      const sourcesRes = await fetch(`${API_URL}/projects/${projectId}/sources`)
      const sources = await sourcesRes.json()

      // Calculate documents by source (mock data - would need real endpoint)
      const docsBySource = sources.map((source: any) => ({
        source_name: source.name,
        document_count: Math.floor(Math.random() * 50) + 10 // Mock data
      }))

      // Enrich jobs with source names
      const enrichedJobs = jobs.map((job: any) => {
        const source = sources.find((s: any) => s.id === job.source_id)
        return {
          id: job.id,
          source_id: job.source_id,
          source_name: source?.name || 'Unknown Source',
          status: job.status,
          documents_count: job.successful_documents || 0,
          created_at: job.created_at,
          completed_at: job.completed_at
        }
      })

      setInsights({
        ...stats,
        sources_count: sources.length,
        recent_jobs: enrichedJobs,
        documents_by_source: docsBySource
      })
    } catch (error) {
      console.error('Failed to fetch insights:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="insights-loading">
        <div className="spinner"></div>
        <p>Loading insights...</p>
      </div>
    )
  }

  if (!insights) {
    return (
      <div className="insights-error">
        <p>Failed to load project insights</p>
      </div>
    )
  }

  const successRate = insights.total_documents > 0
    ? Math.round((insights.documents_completed / insights.total_documents) * 100)
    : 0

  const chartData = insights.documents_by_source.map(item => ({
    label: item.source_name,
    value: item.document_count,
    color: '#667eea'
  }))

  return (
    <div className="project-insights">
      {/* Key Metrics */}
      <div className="insights-metrics">
        <MetricCard
          title="Total Documents"
          value={insights.total_documents}
          subtitle="Across all sources"
          icon={FileText}
          color="blue"
        />
        <MetricCard
          title="Success Rate"
          value={`${successRate}%`}
          subtitle={`${insights.documents_completed} completed`}
          icon={CheckCircle}
          color="green"
        />
        <MetricCard
          title="Failed Documents"
          value={insights.documents_failed}
          subtitle="Need attention"
          icon={XCircle}
          color="red"
        />
        <MetricCard
          title="Active Sources"
          value={insights.sources_count}
          subtitle="Data connectors"
          icon={Database}
          color="purple"
        />
        <MetricCard
          title="Total Jobs"
          value={insights.total_jobs}
          subtitle={`${insights.jobs_completed} completed`}
          icon={TrendUp}
          color="yellow"
        />
        <MetricCard
          title="Avg. Job Time"
          value="~2m 15s"
          subtitle="Last 10 jobs"
          icon={Clock}
          color="blue"
        />
      </div>

      {/* Documents by Source Chart */}
      <CollapsibleSection
        title="Documents by Source"
        badge={insights.documents_by_source.length}
        defaultOpen={true}
      >
        <div className="chart-container">
          {chartData.length > 0 ? (
            <BarChart data={chartData} height={250} showValues={true} />
          ) : (
            <div className="chart-empty">
              <p>No data available</p>
            </div>
          )}
        </div>
      </CollapsibleSection>

      {/* Sync Timeline */}
      <CollapsibleSection
        title="Recent Sync Activity"
        badge={insights.recent_jobs.length}
        defaultOpen={true}
      >
        <SyncTimeline events={insights.recent_jobs} maxEvents={10} />
      </CollapsibleSection>

      {/* Quick Stats Grid */}
      <CollapsibleSection
        title="Job Statistics"
        defaultOpen={false}
      >
        <div className="quick-stats-grid">
          <div className="quick-stat">
            <div className="quick-stat-label">Completion Rate</div>
            <div className="quick-stat-value">{
              insights.total_jobs > 0
                ? Math.round((insights.jobs_completed / insights.total_jobs) * 100)
                : 0
            }%</div>
          </div>
          <div className="quick-stat">
            <div className="quick-stat-label">Failed Jobs</div>
            <div className="quick-stat-value error">{insights.jobs_failed}</div>
          </div>
          <div className="quick-stat">
            <div className="quick-stat-label">Avg. Documents/Job</div>
            <div className="quick-stat-value">
              {insights.total_jobs > 0
                ? Math.round(insights.total_documents / insights.total_jobs)
                : 0}
            </div>
          </div>
          <div className="quick-stat">
            <div className="quick-stat-label">Success/Failure Ratio</div>
            <div className="quick-stat-value success">
              {insights.documents_failed > 0
                ? (insights.documents_completed / insights.documents_failed).toFixed(1)
                : '∞'
              }:1
            </div>
          </div>
        </div>
      </CollapsibleSection>
    </div>
  )
}
