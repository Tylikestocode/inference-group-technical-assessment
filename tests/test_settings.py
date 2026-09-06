from pathlib import Path

import pytest
from pydantic import ValidationError

from bank_ops.settings import Settings


def test_settings_have_local_development_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "BANK_OPS_TRANSACTION_API_URL",
        "BANK_OPS_TRANSACTION_TIMEOUT_SECONDS",
        "BANK_OPS_OLLAMA_URL",
        "BANK_OPS_GENERATION_MODEL",
        "BANK_OPS_GENERATION_TIMEOUT_SECONDS",
        "BANK_OPS_GENERATION_TEMPERATURE",
        "BANK_OPS_GENERATION_MAX_TOKENS",
        "BANK_OPS_GENERATION_SEED",
        "BANK_OPS_EMBEDDING_MODEL",
        "BANK_OPS_PROCEDURE_INDEX_DIR",
        "BANK_OPS_MINIMUM_RELEVANCE_SCORE",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert str(settings.transaction_api_url) == "http://localhost:8000/"
    assert settings.transaction_timeout_seconds == 5
    assert str(settings.ollama_url) == "http://localhost:11434/"
    assert settings.generation_model == "qwen3.5:9b"
    assert settings.generation_timeout_seconds == 120
    assert settings.generation_temperature == 0
    assert settings.generation_max_tokens == 160
    assert settings.generation_seed == 42
    assert settings.embedding_model == "BAAI/bge-small-en-v1.5"
    assert settings.procedure_index_dir == Path("var/retrieval")
    assert settings.minimum_relevance_score == 0.6


def test_settings_load_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BANK_OPS_TRANSACTION_API_URL", "http://transactions:8000")
    monkeypatch.setenv("BANK_OPS_TRANSACTION_TIMEOUT_SECONDS", "3.5")
    monkeypatch.setenv("BANK_OPS_OLLAMA_URL", "http://ollama:11434")
    monkeypatch.setenv("BANK_OPS_GENERATION_MODEL", "local-generation-model")
    monkeypatch.setenv("BANK_OPS_GENERATION_TIMEOUT_SECONDS", "45.5")
    monkeypatch.setenv("BANK_OPS_GENERATION_TEMPERATURE", "0.25")
    monkeypatch.setenv("BANK_OPS_GENERATION_MAX_TOKENS", "80")
    monkeypatch.setenv("BANK_OPS_GENERATION_SEED", "11")
    monkeypatch.setenv("BANK_OPS_EMBEDDING_MODEL", "local-embedding-model")
    monkeypatch.setenv("BANK_OPS_PROCEDURE_INDEX_DIR", "/tmp/procedure-index")
    monkeypatch.setenv("BANK_OPS_MINIMUM_RELEVANCE_SCORE", "0.72")

    settings = Settings(_env_file=None)

    assert str(settings.transaction_api_url) == "http://transactions:8000/"
    assert settings.transaction_timeout_seconds == 3.5
    assert str(settings.ollama_url) == "http://ollama:11434/"
    assert settings.generation_model == "local-generation-model"
    assert settings.generation_timeout_seconds == 45.5
    assert settings.generation_temperature == 0.25
    assert settings.generation_max_tokens == 80
    assert settings.generation_seed == 11
    assert settings.embedding_model == "local-embedding-model"
    assert settings.procedure_index_dir == Path("/tmp/procedure-index")
    assert settings.minimum_relevance_score == 0.72


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("BANK_OPS_TRANSACTION_API_URL", "not-a-url"),
        ("BANK_OPS_TRANSACTION_TIMEOUT_SECONDS", "0"),
        ("BANK_OPS_OLLAMA_URL", "ftp://ollama.example"),
        ("BANK_OPS_GENERATION_MODEL", ""),
        ("BANK_OPS_GENERATION_TIMEOUT_SECONDS", "0"),
        ("BANK_OPS_GENERATION_TEMPERATURE", "2.1"),
        ("BANK_OPS_GENERATION_MAX_TOKENS", "0"),
        ("BANK_OPS_GENERATION_SEED", "-1"),
        ("BANK_OPS_EMBEDDING_MODEL", "   "),
        ("BANK_OPS_MINIMUM_RELEVANCE_SCORE", "-0.01"),
        ("BANK_OPS_MINIMUM_RELEVANCE_SCORE", "1.01"),
    ],
)
def test_settings_reject_invalid_values(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
