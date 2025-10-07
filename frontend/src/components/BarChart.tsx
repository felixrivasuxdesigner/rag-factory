interface BarChartProps {
  data: Array<{
    label: string
    value: number
    color?: string
  }>
  height?: number
  showValues?: boolean
}

export default function BarChart({ data, height = 200, showValues = true }: BarChartProps) {
  const maxValue = Math.max(...data.map(d => d.value), 1)

  return (
    <div className="bar-chart" style={{ height: `${height}px` }}>
      {data.map((item, index) => {
        const percentage = (item.value / maxValue) * 100
        const barColor = item.color || '#667eea'

        return (
          <div key={index} className="bar-item">
            <div className="bar-container">
              <div
                className="bar"
                style={{
                  height: `${percentage}%`,
                  backgroundColor: barColor
                }}
              >
                {showValues && item.value > 0 && (
                  <span className="bar-value">{item.value}</span>
                )}
              </div>
            </div>
            <div className="bar-label">{item.label}</div>
          </div>
        )
      })}
    </div>
  )
}
