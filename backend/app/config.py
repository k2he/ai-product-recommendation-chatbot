"""Application configuration management using Pydantic Settings."""
import os
from functools import lru_cache
from typing import Optional
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the directory where settings.py is located
BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    app_name: str = "Product Recommendation Chatbot"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = Field(default="development", pattern="^(development|staging|production)$")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # MongoDB
    mongodb_url: str = Field(default="mongodb://localhost:27017")
    mongodb_database: str = "product_chatbot"
    mongodb_user_collection: str = "users"
    mongodb_max_pool_size: int = 10
    mongodb_min_pool_size: int = 1

    # Pinecone
    pinecone_api_key: str = Field(default="", description="Pinecone API key")
    pinecone_environment: str = Field(default="gcp-starter", description="Pinecone environment")
    pinecone_index_name: str = "ai-product-recommendation-chatbot"
    pinecone_dimension: int = 1024  # Matches ollama embedding dimension
    pinecone_metric: str = "cosine"
    pinecone_namespace: str = "product-catalog"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gpt-oss:20b"
    ollama_embedding_model: str = "mxbai-embed-large"
    ollama_temperature: float = 0.7
    ollama_max_tokens: int = 2000

    # Tavily
    tavily_api_key: str = Field(default="", description="Tavily API key")
    tavily_search_depth: str = "advanced"
    tavily_max_results: int = 5

    # LangSmith
    langsmith_tracing: bool = Field(default=False, description="Enable LangSmith tracing")
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_api_key: str = Field(default="", description="LangSmith API key")
    langsmith_project: str = Field(default="ai-product-recommendation-chatbot", description="LangSmith project name")

    # Email (SMTP)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    smtp_from_email: str = Field(default="")

    # Vector Search
    vector_search_threshold: float = 0.7
    vector_search_top_k: int = 5

    # Rate Limiting
    rate_limit_requests: int = 10
    rate_limit_period: int = 60  # seconds

    # Logging
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_format: str = "json"

    model_config = SettingsConfigDict(
        env_file= BASE_DIR.parent / ".env",
        # env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
