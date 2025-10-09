"""
Pydantic models for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum


# Enums
class SourceType(str, Enum):
    SPARQL = "sparql"
    CHILE_FULLTEXT = "chile_fulltext"
    CONGRESS_API = "congress_api"
    REST_API = "rest_api"
    FILE_UPLOAD = "file_upload"
    WEB_SCRAPE = "web_scrape"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


# RAG Project Models
class RAGProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

    # Target database configuration
    target_db_host: str
    target_db_port: int = 5432
    target_db_name: str
    target_db_user: str
    target_db_password: str
    target_table_name: str

    # Embedding configuration
    embedding_model: str = "jina/jina-embeddings-v2-base-es"
    embedding_dimension: int = 768
    chunk_size: int = 1000
    chunk_overlap: int = 200


class RAGProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    target_db_host: Optional[str] = None
    target_db_port: Optional[int] = None
    target_db_name: Optional[str] = None
    target_db_user: Optional[str] = None
    target_db_password: Optional[str] = None
    target_table_name: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_dimension: Optional[int] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None


class RAGProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    target_db_host: str
    target_db_port: int
    target_db_name: str
    target_db_user: str
    target_table_name: str
    embedding_model: str
    embedding_dimension: int
    chunk_size: int
    chunk_overlap: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Data Source Models
class DataSourceCreate(BaseModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType
    config: Dict  # Flexible config based on source type
    country_code: Optional[str] = Field(None, max_length=10, description="ISO 3166-1 alpha-2 country code (e.g., 'CL', 'US')")
    region: Optional[str] = Field(None, max_length=100, description="Region/state (e.g., 'California', 'Santiago')")
    tags: Optional[Dict] = Field(None, description="Additional flexible tags (e.g., {'jurisdiction': 'federal', 'language': 'es'})")
    sync_frequency: str = "manual"
    rate_limits: Optional[Dict] = Field(None, description="Rate limiting config or preset name (e.g., {'preset': 'chile_bcn_conservative'} or full config)")


class DataSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[Dict] = None
    country_code: Optional[str] = Field(None, max_length=10)
    region: Optional[str] = Field(None, max_length=100)
    tags: Optional[Dict] = None
    sync_frequency: Optional[str] = None
    is_active: Optional[bool] = None
    rate_limits: Optional[Dict] = None


class DataSourceResponse(BaseModel):
    id: int
    project_id: int
    name: str
    source_type: str
    config: Dict
    country_code: Optional[str]
    region: Optional[str]
    tags: Optional[Dict]
    sync_frequency: str
    is_active: bool
    rate_limits: Optional[Dict]
    last_sync_at: Optional[datetime]
    next_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Ingestion Job Models
class IngestionJobCreate(BaseModel):
    project_id: int
    source_id: Optional[int] = None
    job_type: str = "full_sync"


class IngestionJobResponse(BaseModel):
    id: int
    project_id: int
    source_id: Optional[int]
    job_type: str
    status: str
    total_documents: int
    processed_documents: int
    successful_documents: int
    failed_documents: int
    error_log: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# Document Tracking Models
class DocumentTrackingResponse(BaseModel):
    id: int
    project_id: int
    source_id: Optional[int]
    document_hash: str
    external_id: Optional[str]
    title: Optional[str]
    status: str
    error_message: Optional[str]
    content_preview: Optional[str]
    metadata: Optional[Dict]
    discovered_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


# Stats and Monitoring Models
class ProjectStats(BaseModel):
    total_documents: int
    documents_pending: int
    documents_processing: int
    documents_completed: int
    documents_failed: int
    total_jobs: int
    jobs_running: int
    jobs_completed: int
    jobs_failed: int
    vector_db_stats: Optional[Dict] = None


# Connection Test Models
class DatabaseConnectionTest(BaseModel):
    host: str
    port: int = 5432
    database: str
    user: str
    password: str


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    pgvector_available: bool = False


# Search and Query Models
class SearchRequest(BaseModel):
    project_id: int
    query: str = Field(..., min_length=1, description="Search query text")
    top_k: int = Field(5, ge=1, le=50, description="Number of results to return")
    similarity_threshold: float = Field(0.0, ge=0.0, le=1.0, description="Minimum similarity score")


class SearchResult(BaseModel):
    id: str
    content: str
    metadata: Optional[Dict]
    similarity: float


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    project_id: int


class RAGQueryRequest(BaseModel):
    project_id: int
    question: str = Field(..., min_length=1, description="Question to answer using RAG")
    top_k: int = Field(5, ge=1, le=20, description="Number of context documents")
    similarity_threshold: float = Field(0.3, ge=0.0, le=1.0, description="Minimum similarity for context")
    model: str = Field("gemma3:1b-it-qat", description="LLM model to use for generation")
    max_tokens: int = Field(500, ge=50, le=2000, description="Maximum tokens in response")


class RAGQueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[SearchResult]
    model: str
    project_id: int
