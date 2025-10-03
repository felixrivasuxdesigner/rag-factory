"""
Models for vector similarity search with country/region filtering.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class SimilaritySearchRequest(BaseModel):
    """Request model for similarity search."""
    query: str = Field(..., min_length=1, description="Search query text")
    limit: int = Field(5, ge=1, le=100, description="Maximum results to return")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score (0-1)")

    # Filtering options
    country_code: Optional[str] = Field(None, description="Filter by country code (e.g., 'CL', 'US')")
    region: Optional[str] = Field(None, description="Filter by region")
    tags: Optional[Dict] = Field(None, description="Filter by tags (must match all)")


class SimilaritySearchResult(BaseModel):
    """Single search result."""
    id: str
    content: str
    similarity: float
    metadata: Dict


class SimilaritySearchResponse(BaseModel):
    """Response model for similarity search."""
    query: str
    results: List[SimilaritySearchResult]
    count: int
    filters_applied: Dict
