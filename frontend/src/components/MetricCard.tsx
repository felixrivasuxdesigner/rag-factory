import type { Icon } from '@phosphor-icons/react'

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: Icon
  color?: 'blue' | 'green' | 'red' | 'yellow' | 'purple'
  trend?: {
    value: number
    isPositive: boolean
  }
}

export default function MetricCard({
  title,
  value,
  subtitle,
  icon: IconComponent,
  color = 'blue',
  trend
}: MetricCardProps) {
  const colorClasses = {
    blue: 'metric-blue',
    green: 'metric-green',
    red: 'metric-red',
    yellow: 'metric-yellow',
    purple: 'metric-purple'
  }

  return (
    <div className={`metric-card ${colorClasses[color]}`}>
      <div className="metric-icon">
        <IconComponent size={24} weight="duotone" />
      </div>
      <div className="metric-content">
        <div className="metric-title">{title}</div>
        <div className="metric-value">{value}</div>
        {subtitle && <div className="metric-subtitle">{subtitle}</div>}
        {trend && (
          <div className={`metric-trend ${trend.isPositive ? 'positive' : 'negative'}`}>
            {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}%
          </div>
        )}
      </div>
    </div>
  )
}
