"""Validated runtime configuration for the application."""

from pathlib import Path
from typing import Annotated

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ModelName = Annotated[str, Field(min_length=1)]


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
    ollama_url: AnyHttpUrl = AnyHttpUrl("http://localhost:11434")
    generation_model: ModelName = "qwen3.5:9b"
    embedding_model: ModelName = "BAAI/bge-small-en-v1.5"
    procedure_index_dir: Path = Path("var/retrieval")
