"""Pydantic models for JRE Quote Search API."""

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Request model for search endpoint."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    episode_filter: list[int] | None = Field(
        default=None, description="Optional list of episode numbers to filter by"
    )
    guest_filter: str | None = Field(default=None, description="Optional guest name to filter by")


class QuoteResult(BaseModel):
    """A single quote result from search."""

    text: str = Field(..., description="The full context text")
    highlight: str | None = Field(default=None, description="Key quote/excerpt from the text")
    episode_number: int = Field(..., description="JRE episode number (0 if unknown)")
    episode_title: str = Field(..., description="Episode title")
    guest: str = Field(..., description="Guest name(s)")
    youtube_id: str | None = Field(default=None, description="YouTube video ID")
    timestamp: str | None = Field(default=None, description="Timestamp in episode if available")
    score: float = Field(..., ge=0, le=1, description="Relevance score")
    chunk_id: str = Field(..., description="Unique identifier for this chunk")


class SearchResponse(BaseModel):
    """Response model for search endpoint."""

    query: str = Field(..., description="Original search query")
    results: list[QuoteResult] = Field(default_factory=list, description="Search results")
    total_results: int = Field(..., description="Number of results returned")
    search_time_ms: float = Field(..., description="Search latency in milliseconds")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Service status")
    pinecone_connected: bool = Field(..., description="Pinecone connection status")
    cohere_connected: bool = Field(..., description="Cohere connection status")


class StatsResponse(BaseModel):
    """Response model for stats endpoint."""

    total_vectors: int = Field(..., description="Total vectors in index")
    index_dimension: int = Field(..., description="Vector dimension")
    index_name: str = Field(..., description="Pinecone index name")
    total_episodes: int | None = Field(default=None, description="Total episodes indexed")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: str = Field(..., description="Error message")
    error_code: str | None = Field(default=None, description="Error code for client handling")
