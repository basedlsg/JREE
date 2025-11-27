"""FastAPI application for JRE Quote Search."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.models import (
    ErrorResponse,
    HealthResponse,
    SearchRequest,
    SearchResponse,
    StatsResponse,
)

# Determine which backend to use
USE_LOCAL = os.getenv("USE_LOCAL_SEARCH", "true").lower() == "true"

if USE_LOCAL:
    from backend.search_local import (
        search_quotes_local as search_quotes,
        get_local_index_stats as get_index_stats,
        check_local_health,
    )
else:
    from backend.search import search_quotes, get_index_stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    settings = get_settings()
    backend_type = "ChromaDB (local)" if USE_LOCAL else "Pinecone (cloud)"
    print(f"Starting JRE Quote Search API on {settings.api_host}:{settings.api_port}")
    print(f"Using backend: {backend_type}")
    yield
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
    """Check service health and connections."""
    if USE_LOCAL:
        # Local mode - check ChromaDB
        local_ok = check_local_health()
        return HealthResponse(
            status="healthy" if local_ok else "degraded",
            pinecone_connected=False,
            cohere_connected=False,
        )
    else:
        # Cloud mode - check Pinecone and Cohere
        from backend.config import get_cohere_client, get_pinecone_index

        pinecone_ok = False
        cohere_ok = False

        try:
            index = get_pinecone_index()
            index.describe_index_stats()
            pinecone_ok = True
        except Exception:
            pass

        try:
            client = get_cohere_client()
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

    Uses semantic search with local ChromaDB or cloud Pinecone.
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
        stats = get_index_stats()
        index_name = stats.get("backend", "chromadb") if USE_LOCAL else get_settings().pinecone_index_name

        return StatsResponse(
            total_vectors=stats["total_vectors"],
            index_dimension=stats["dimension"],
            index_name=index_name,
            total_episodes=None,
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
