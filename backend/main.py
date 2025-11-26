"""FastAPI application for JRE Quote Search."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_cohere_client, get_pinecone_index, get_settings
from backend.models import (
    ErrorResponse,
    HealthResponse,
    SearchRequest,
    SearchResponse,
    StatsResponse,
)
from backend.search import get_index_stats, search_quotes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup: verify connections
    settings = get_settings()
    print(f"Starting JRE Quote Search API on {settings.api_host}:{settings.api_port}")
    yield
    # Shutdown
    print("Shutting down JRE Quote Search API")


app = FastAPI(
    title="JRE Quote Search API",
    description="Semantic search for Joe Rogan Experience podcast transcripts",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Check service health and external connections."""
    pinecone_ok = False
    cohere_ok = False

    # Test Pinecone connection
    try:
        index = get_pinecone_index()
        index.describe_index_stats()
        pinecone_ok = True
    except Exception:
        pass

    # Test Cohere connection
    try:
        client = get_cohere_client()
        # Simple API check - embed a short test string
        client.embed(texts=["test"], model="embed-english-v3.0", input_type="search_query")
        cohere_ok = True
    except Exception:
        pass

    status = "healthy" if (pinecone_ok and cohere_ok) else "degraded"

    return HealthResponse(
        status=status,
        pinecone_connected=pinecone_ok,
        cohere_connected=cohere_ok,
    )


@app.post(
    "/api/search",
    response_model=SearchResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    tags=["Search"],
)
async def search(request: SearchRequest) -> SearchResponse:
    """Search for quotes matching the query.

    Uses semantic search with Cohere embeddings and Pinecone vector database.
    """
    try:
        return search_quotes(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get(
    "/api/stats",
    response_model=StatsResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["Stats"],
)
async def get_stats() -> StatsResponse:
    """Get statistics about the search index."""
    try:
        settings = get_settings()
        stats = get_index_stats()

        return StatsResponse(
            total_vectors=stats["total_vectors"],
            index_dimension=stats["dimension"],
            index_name=settings.pinecone_index_name,
            total_episodes=None,  # Would need to query metadata for this
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
