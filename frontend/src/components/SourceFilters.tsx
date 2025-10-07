import { MagnifyingGlass, Funnel } from '@phosphor-icons/react'

interface SourceFiltersProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  typeFilter: string
  onTypeFilterChange: (type: string) => void
  availableTypes: string[]
  statusFilter: string
  onStatusFilterChange: (status: string) => void
}

export default function SourceFilters({
  searchQuery,
  onSearchChange,
  typeFilter,
  onTypeFilterChange,
  availableTypes,
  statusFilter,
  onStatusFilterChange
}: SourceFiltersProps) {
  return (
    <div className="source-filters">
      <div className="filter-group">
        <div className="search-box">
          <MagnifyingGlass size={18} weight="bold" />
          <input
            type="text"
            placeholder="Search sources..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="filter-input"
          />
        </div>
      </div>

      <div className="filter-group">
        <Funnel size={18} weight="bold" />
        <select
          value={typeFilter}
          onChange={(e) => onTypeFilterChange(e.target.value)}
          className="filter-select"
        >
          <option value="">All Types</option>
          {availableTypes.map(type => (
            <option key={type} value={type}>{type}</option>
          ))}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => onStatusFilterChange(e.target.value)}
          className="filter-select"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>
    </div>
  )
}
