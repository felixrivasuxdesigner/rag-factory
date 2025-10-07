import {
  Database,
  FileText,
  Globe,
  Rss,
  GithubLogo,
  GoogleLogo,
  Note,
  CloudArrowUp
} from '@phosphor-icons/react'

interface ConnectorCardProps {
  sourceType: string
  name: string
  description: string
  category: string
  isSelected: boolean
  onSelect: () => void
}

const getConnectorIcon = (sourceType: string) => {
  const iconSize = 32
  const iconWeight = "duotone"

  switch (sourceType) {
    case 'sparql':
      return <Database size={iconSize} weight={iconWeight} />
    case 'rest_api':
      return <CloudArrowUp size={iconSize} weight={iconWeight} />
    case 'file_upload':
      return <FileText size={iconSize} weight={iconWeight} />
    case 'web_scraper':
      return <Globe size={iconSize} weight={iconWeight} />
    case 'rss_feed':
      return <Rss size={iconSize} weight={iconWeight} />
    case 'github':
      return <GithubLogo size={iconSize} weight={iconWeight} />
    case 'google_drive':
      return <GoogleLogo size={iconSize} weight={iconWeight} />
    case 'notion':
      return <Note size={iconSize} weight={iconWeight} />
    default:
      return <Database size={iconSize} weight={iconWeight} />
  }
}

export default function ConnectorCard({
  sourceType,
  name,
  description,
  category,
  isSelected,
  onSelect
}: ConnectorCardProps) {
  return (
    <div
      className={`connector-card ${isSelected ? 'selected' : ''}`}
      onClick={onSelect}
    >
      <div className="connector-icon">
        {getConnectorIcon(sourceType)}
      </div>
      <div className="connector-info">
        <h4>{name}</h4>
        <p>{description}</p>
        {category === 'example' && (
          <span className="badge badge-example">Example</span>
        )}
      </div>
    </div>
  )
}
