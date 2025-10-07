import { CheckCircle, XCircle, Clock } from '@phosphor-icons/react'

interface SyncEvent {
  id: number
  source_name: string
  status: string
  documents_count: number
  created_at: string
  completed_at: string | null
}

interface SyncTimelineProps {
  events: SyncEvent[]
  maxEvents?: number
}

export default function SyncTimeline({ events, maxEvents = 10 }: SyncTimelineProps) {
  const displayEvents = events.slice(0, maxEvents)

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={20} weight="fill" className="timeline-icon success" />
      case 'failed':
        return <XCircle size={20} weight="fill" className="timeline-icon error" />
      default:
        return <Clock size={20} weight="fill" className="timeline-icon pending" />
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (displayEvents.length === 0) {
    return (
      <div className="timeline-empty">
        <Clock size={48} weight="duotone" />
        <p>No recent sync activity</p>
      </div>
    )
  }

  return (
    <div className="sync-timeline">
      {displayEvents.map((event, index) => (
        <div key={event.id} className="timeline-event">
          <div className="timeline-marker">
            {getStatusIcon(event.status)}
            {index < displayEvents.length - 1 && <div className="timeline-line" />}
          </div>
          <div className="timeline-content">
            <div className="timeline-header">
              <span className="timeline-source">{event.source_name}</span>
              <span className="timeline-date">{formatDate(event.created_at)}</span>
            </div>
            <div className="timeline-details">
              <span className={`timeline-status status-${event.status}`}>
                {event.status}
              </span>
              <span className="timeline-docs">
                {event.documents_count} documents
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
