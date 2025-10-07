import {
  House,
  Database,
  Clock,
  MagnifyingGlass
} from '@phosphor-icons/react'

export type TabType = 'overview' | 'sources' | 'jobs' | 'search'

interface TabNavigationProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
  projectSelected: boolean
}

export default function TabNavigation({ activeTab, onTabChange, projectSelected }: TabNavigationProps) {
  const tabs = [
    { id: 'overview' as TabType, label: 'Overview', icon: House, disabled: false },
    { id: 'sources' as TabType, label: 'Data Sources', icon: Database, disabled: !projectSelected },
    { id: 'jobs' as TabType, label: 'Jobs', icon: Clock, disabled: !projectSelected },
    { id: 'search' as TabType, label: 'Search & Query', icon: MagnifyingGlass, disabled: !projectSelected }
  ]

  return (
    <nav className="tab-navigation">
      {tabs.map((tab) => {
        const Icon = tab.icon
        return (
          <button
            key={tab.id}
            className={`tab ${activeTab === tab.id ? 'active' : ''} ${tab.disabled ? 'disabled' : ''}`}
            onClick={() => !tab.disabled && onTabChange(tab.id)}
            disabled={tab.disabled}
          >
            <Icon size={20} weight={activeTab === tab.id ? 'fill' : 'regular'} />
            <span>{tab.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
