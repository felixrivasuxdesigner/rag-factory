import { useState } from 'react'
import { CaretDown, CaretRight } from '@phosphor-icons/react'

interface CollapsibleSectionProps {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
  badge?: string | number
}

export default function CollapsibleSection({
  title,
  children,
  defaultOpen = true,
  badge
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="collapsible-section">
      <button
        className="collapsible-header"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="collapsible-title">
          {isOpen ? (
            <CaretDown size={20} weight="bold" />
          ) : (
            <CaretRight size={20} weight="bold" />
          )}
          <h3>{title}</h3>
          {badge !== undefined && (
            <span className="collapsible-badge">{badge}</span>
          )}
        </div>
      </button>
      {isOpen && (
        <div className="collapsible-content">
          {children}
        </div>
      )}
    </div>
  )
}
