"""Configuration and client initialization for JRE Quote Search."""

from functools import lru_cache

import cohere
from pinecone import Pinecone
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Pinecone
    pinecone_api_key: str
    pinecone_index_name: str = "jre-quotes"
    pinecone_environment: str = "us-east-1"

    # Cohere
    cohere_api_key: str
    cohere_embed_model: str = "embed-english-v3.0"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Search
    default_top_k: int = 10
    max_top_k: int = 50

    # Data paths
    data_dir: str = "./data"
    transcripts_dir: str = "./data/transcripts"
    chunks_dir: str = "./data/chunks"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_pinecone_client() -> Pinecone:
    """Initialize and return Pinecone client."""
    settings = get_settings()
    return Pinecone(api_key=settings.pinecone_api_key)


def get_pinecone_index():
    """Get the Pinecone index for JRE quotes."""
    settings = get_settings()
    pc = get_pinecone_client()
    return pc.Index(settings.pinecone_index_name)


def get_cohere_client() -> cohere.Client:
    """Initialize and return Cohere client."""
    settings = get_settings()
    return cohere.Client(api_key=settings.cohere_api_key)
