"""Validated runtime configuration for the application."""

from pathlib import Path
from typing import Annotated

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ModelName = Annotated[str, Field(min_length=1)]
TimeoutSeconds = Annotated[float, Field(gt=0, le=600)]
Temperature = Annotated[float, Field(ge=0, le=2)]
MaxGenerationTokens = Annotated[int, Field(gt=0, le=512)]
GenerationSeed = Annotated[int, Field(ge=0)]
MinimumRelevanceScore = Annotated[float, Field(ge=0, le=1)]


class Settings(BaseSettings):
    """Settings shared by the CLI and its downstream service adapters."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="BANK_OPS_",
        extra="ignore",
        frozen=True,
        str_strip_whitespace=True,
    )

    transaction_api_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    transaction_timeout_seconds: TimeoutSeconds = 5
    ollama_url: AnyHttpUrl = AnyHttpUrl("http://localhost:11434")
    generation_model: ModelName = "qwen3.5:9b"
    generation_timeout_seconds: TimeoutSeconds = 120
    generation_temperature: Temperature = 0
    generation_max_tokens: MaxGenerationTokens = 160
    generation_seed: GenerationSeed = 42
    embedding_model: ModelName = "BAAI/bge-small-en-v1.5"
    procedure_index_dir: Path = Path("var/retrieval")
    minimum_relevance_score: MinimumRelevanceScore = 0.6
