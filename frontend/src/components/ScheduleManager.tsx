import { useState } from 'react'
import {
  Clock,
  Play,
  Pause,
  CheckCircle,
  Warning
} from '@phosphor-icons/react'

interface ScheduleManagerProps {
  sourceId: number
  sourceName: string
  currentFrequency: string
  onUpdate: () => void
}

export default function ScheduleManager({
  sourceId,
  currentFrequency,
  onUpdate
}: ScheduleManagerProps) {
  const [frequency, setFrequency] = useState(currentFrequency || 'manual')
  const [customInterval, setCustomInterval] = useState('')
  const [customCron, setCustomCron] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const API_URL = 'http://localhost:8000'

  const presets = [
    { value: 'manual', label: 'Manual Only', description: 'No automatic sync' },
    { value: 'interval:30m', label: 'Every 30 minutes', description: 'High frequency' },
    { value: 'hourly', label: 'Every Hour', description: 'Recommended for active sources' },
    { value: 'interval:6h', label: 'Every 6 Hours', description: 'Moderate frequency' },
    { value: 'daily', label: 'Daily (Midnight)', description: 'Low frequency' },
    { value: 'weekly', label: 'Weekly (Monday)', description: 'Very low frequency' },
  ]

  const handleUpdateSchedule = async () => {
    setLoading(true)
    setMessage(null)

    let finalFrequency = frequency

    // Handle custom interval
    if (frequency === 'custom_interval' && customInterval) {
      finalFrequency = `interval:${customInterval}`
    }

    // Handle custom cron
    if (frequency === 'custom_cron' && customCron) {
      finalFrequency = `cron:${customCron}`
    }

    try {
      const response = await fetch(
        `${API_URL}/sources/${sourceId}/schedule?sync_frequency=${encodeURIComponent(finalFrequency)}`,
        { method: 'POST' }
      )

      if (response.ok) {
        setMessage({ type: 'success', text: 'Schedule updated successfully!' })
        onUpdate()
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to update schedule' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Network error' })
    } finally {
      setLoading(false)
    }
  }

  const handleTriggerManual = async () => {
    setLoading(true)
    setMessage(null)

    try {
      const response = await fetch(
        `${API_URL}/sources/${sourceId}/sync/trigger`,
        { method: 'POST' }
      )

      if (response.ok) {
        setMessage({ type: 'success', text: 'Sync job triggered!' })
        onUpdate()
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to trigger sync' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Network error' })
    } finally {
      setLoading(false)
    }
  }

  const handlePause = async () => {
    try {
      await fetch(`${API_URL}/sources/${sourceId}/schedule/pause`, { method: 'POST' })
      setMessage({ type: 'success', text: 'Schedule paused' })
      onUpdate()
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to pause' })
    }
  }

  const handleResume = async () => {
    try {
      await fetch(`${API_URL}/sources/${sourceId}/schedule/resume`, { method: 'POST' })
      setMessage({ type: 'success', text: 'Schedule resumed' })
      onUpdate()
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to resume' })
    }
  }

  return (
    <div className="schedule-manager">
      <div className="schedule-header">
        <Clock size={24} weight="duotone" />
        <h4>Sync Schedule</h4>
      </div>

      {message && (
        <div className={`schedule-message ${message.type}`}>
          {message.type === 'success' ? (
            <CheckCircle size={16} weight="fill" />
          ) : (
            <Warning size={16} weight="fill" />
          )}
          {message.text}
        </div>
      )}

      <div className="schedule-presets">
        {presets.map((preset) => (
          <label key={preset.value} className="preset-option">
            <input
              type="radio"
              name="frequency"
              value={preset.value}
              checked={frequency === preset.value}
              onChange={(e) => setFrequency(e.target.value)}
            />
            <div className="preset-info">
              <span className="preset-label">{preset.label}</span>
              <span className="preset-description">{preset.description}</span>
            </div>
          </label>
        ))}

        {/* Custom Interval */}
        <label className="preset-option">
          <input
            type="radio"
            name="frequency"
            value="custom_interval"
            checked={frequency === 'custom_interval'}
            onChange={(e) => setFrequency(e.target.value)}
          />
          <div className="preset-info">
            <span className="preset-label">Custom Interval</span>
            <input
              type="text"
              placeholder="e.g., 2h, 45m, 3d"
              value={customInterval}
              onChange={(e) => setCustomInterval(e.target.value)}
              disabled={frequency !== 'custom_interval'}
              className="custom-input"
            />
          </div>
        </label>

        {/* Custom Cron */}
        <label className="preset-option">
          <input
            type="radio"
            name="frequency"
            value="custom_cron"
            checked={frequency === 'custom_cron'}
            onChange={(e) => setFrequency(e.target.value)}
          />
          <div className="preset-info">
            <span className="preset-label">Custom Cron Expression</span>
            <input
              type="text"
              placeholder="e.g., 0 */2 * * * (every 2 hours)"
              value={customCron}
              onChange={(e) => setCustomCron(e.target.value)}
              disabled={frequency !== 'custom_cron'}
              className="custom-input"
            />
          </div>
        </label>
      </div>

      <div className="schedule-actions">
        <button
          onClick={handleUpdateSchedule}
          disabled={loading}
          className="btn-primary"
        >
          {loading ? 'Updating...' : 'Update Schedule'}
        </button>

        <button
          onClick={handleTriggerManual}
          disabled={loading}
          className="btn-secondary"
        >
          <Play size={16} weight="fill" />
          Trigger Now
        </button>

        {currentFrequency !== 'manual' && (
          <>
            <button onClick={handlePause} className="btn-secondary btn-small">
              <Pause size={14} />
              Pause
            </button>
            <button onClick={handleResume} className="btn-secondary btn-small">
              <Play size={14} />
              Resume
            </button>
          </>
        )}
      </div>
    </div>
  )
}
