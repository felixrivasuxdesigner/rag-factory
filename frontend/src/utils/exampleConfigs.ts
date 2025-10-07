export interface ExampleConfig {
  id: string
  name: string
  description: string
  sourceType: string
  config: Record<string, any>
}

export const exampleConfigs: ExampleConfig[] = [
  // SPARQL Examples
  {
    id: 'chile_bcn',
    name: 'Chile BCN Legal Norms',
    description: 'Chilean legal norms from Biblioteca del Congreso Nacional',
    sourceType: 'sparql',
    config: {
      name: 'Chile BCN Legal Norms',
      endpoint: 'https://datos.bcn.cl/sparql',
      query: `PREFIX bcnnorms: <http://datos.bcn.cl/ontologies/bcn-norms#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>

SELECT DISTINCT ?id ?title ?date
WHERE {
  ?norma dc:identifier ?id .
  ?norma dc:title ?title .
  ?norma bcnnorms:publishDate ?date .
  {date_filter}
}
ORDER BY DESC(?date)
OFFSET {offset}
LIMIT {limit}`,
      id_field: 'id',
      title_field: 'title',
      content_fields: 'title',
      limit: 25
    }
  },
  {
    id: 'wikidata_people',
    name: 'Wikidata: Notable People',
    description: 'Get biographies of notable people from Wikidata',
    sourceType: 'sparql',
    config: {
      name: 'Wikidata Notable People',
      endpoint: 'https://query.wikidata.org/sparql',
      query: `SELECT ?id ?title ?description
WHERE {
  ?id wdt:P31 wd:Q5 .
  ?id rdfs:label ?title .
  ?id schema:description ?description .
  FILTER(LANG(?title) = "en")
  FILTER(LANG(?description) = "en")
}
OFFSET {offset}
LIMIT {limit}`,
      id_field: 'id',
      title_field: 'title',
      content_fields: 'description',
      limit: 50
    }
  },
  {
    id: 'dbpedia_books',
    name: 'DBpedia: Books',
    description: 'Book information from DBpedia',
    sourceType: 'sparql',
    config: {
      name: 'DBpedia Books',
      endpoint: 'https://dbpedia.org/sparql',
      query: `PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbp: <http://dbpedia.org/property/>

SELECT ?id ?title ?abstract
WHERE {
  ?id a dbo:Book .
  ?id rdfs:label ?title .
  ?id dbo:abstract ?abstract .
  FILTER(LANG(?title) = "en")
  FILTER(LANG(?abstract) = "en")
}
OFFSET {offset}
LIMIT {limit}`,
      id_field: 'id',
      title_field: 'title',
      content_fields: 'abstract',
      limit: 25
    }
  },

  // REST API Examples
  {
    id: 'us_congress',
    name: 'US Congress Bills',
    description: 'Congressional bills from Congress.gov API',
    sourceType: 'rest_api',
    config: {
      name: 'US Congress Bills',
      base_url: 'https://api.congress.gov/v3',
      endpoint: '/bill/119',
      method: 'GET',
      auth_type: 'api_key',
      api_key: 'DEMO_KEY',
      limit_param: 'limit',
      offset_param: 'offset',
      data_path: 'bills',
      id_field: 'number',
      title_field: 'title',
      content_field: 'title',
      limit: 25
    }
  },
  {
    id: 'jsonplaceholder',
    name: 'JSONPlaceholder Posts',
    description: 'Demo API for testing (fake blog posts)',
    sourceType: 'rest_api',
    config: {
      name: 'JSONPlaceholder Demo',
      base_url: 'https://jsonplaceholder.typicode.com',
      endpoint: '/posts',
      method: 'GET',
      auth_type: '',
      limit_param: '_limit',
      offset_param: '_start',
      data_path: '',
      id_field: 'id',
      title_field: 'title',
      content_field: 'body',
      limit: 10
    }
  },

  // RSS Examples
  {
    id: 'techcrunch',
    name: 'TechCrunch RSS',
    description: 'Latest tech news from TechCrunch',
    sourceType: 'rss_feed',
    config: {
      name: 'TechCrunch News',
      feed_url: 'https://techcrunch.com/feed/',
      auto_discover: false,
      limit: 50
    }
  },
  {
    id: 'hn_rss',
    name: 'Hacker News RSS',
    description: 'Top stories from Hacker News',
    sourceType: 'rss_feed',
    config: {
      name: 'Hacker News',
      feed_url: 'https://news.ycombinator.com/rss',
      auto_discover: false,
      limit: 30
    }
  },

  // GitHub Examples
  {
    id: 'github_pytorch',
    name: 'PyTorch Repository',
    description: 'PyTorch GitHub repo (docs, issues, PRs)',
    sourceType: 'github',
    config: {
      name: 'PyTorch Repo',
      repository: 'pytorch/pytorch',
      include_readme: true,
      include_issues: true,
      include_prs: false,
      include_code: false,
      limit: 50
    }
  },

  // Web Scraper Examples
  {
    id: 'wikipedia',
    name: 'Wikipedia Article',
    description: 'Scrape content from a Wikipedia page',
    sourceType: 'web_scraper',
    config: {
      name: 'Wikipedia Example',
      start_url: 'https://en.wikipedia.org/wiki/Artificial_intelligence',
      content_selector: '#mw-content-text p',
      title_selector: '#firstHeading',
      max_pages: 1
    }
  },

  // Google Drive Examples
  {
    id: 'gdrive_folder',
    name: 'Google Drive Folder',
    description: 'Sync documents from a Google Drive folder',
    sourceType: 'google_drive',
    config: {
      name: 'My Drive Docs',
      folder_id: '',
      recursive: true,
      include_docs: true,
      include_sheets: true,
      include_pdfs: true
    }
  },

  // Notion Examples
  {
    id: 'notion_workspace',
    name: 'Notion Workspace',
    description: 'Sync pages and databases from Notion',
    sourceType: 'notion',
    config: {
      name: 'My Notion Workspace',
      search_query: '',
      include_pages: true,
      include_databases: true
    }
  },

  // File Upload Example
  {
    id: 'file_upload_demo',
    name: 'Sample Documents',
    description: 'Upload your own documents (PDF, DOCX, TXT, etc.)',
    sourceType: 'file_upload',
    config: {
      name: 'My Documents',
      documents: [
        {
          id: 'doc1',
          title: 'Sample Document 1',
          content: 'This is the content of the first document. Add your own content here.'
        },
        {
          id: 'doc2',
          title: 'Sample Document 2',
          content: 'This is the content of the second document. You can add as many as you need.'
        }
      ]
    }
  }
]

export function getExamplesBySourceType(sourceType: string): ExampleConfig[] {
  return exampleConfigs.filter(config => config.sourceType === sourceType)
}
