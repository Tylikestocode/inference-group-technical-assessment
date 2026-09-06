from pathlib import Path

import pytest
from pydantic import ValidationError

from bank_ops.settings import Settings


def test_settings_have_local_development_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "BANK_OPS_TRANSACTION_API_URL",
        "BANK_OPS_OLLAMA_URL",
        "BANK_OPS_GENERATION_MODEL",
        "BANK_OPS_EMBEDDING_MODEL",
        "BANK_OPS_PROCEDURE_INDEX_DIR",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert str(settings.transaction_api_url) == "http://localhost:8000/"
    assert str(settings.ollama_url) == "http://localhost:11434/"
    assert settings.generation_model == "qwen3.5:9b"
    assert settings.embedding_model == "BAAI/bge-small-en-v1.5"
    assert settings.procedure_index_dir == Path("var/retrieval")


def test_settings_load_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BANK_OPS_TRANSACTION_API_URL", "http://transactions:8000")
    monkeypatch.setenv("BANK_OPS_OLLAMA_URL", "http://ollama:11434")
    monkeypatch.setenv("BANK_OPS_GENERATION_MODEL", "local-generation-model")
    monkeypatch.setenv("BANK_OPS_EMBEDDING_MODEL", "local-embedding-model")
    monkeypatch.setenv("BANK_OPS_PROCEDURE_INDEX_DIR", "/tmp/procedure-index")

    settings = Settings(_env_file=None)

    assert str(settings.transaction_api_url) == "http://transactions:8000/"
    assert str(settings.ollama_url) == "http://ollama:11434/"
    assert settings.generation_model == "local-generation-model"
    assert settings.embedding_model == "local-embedding-model"
    assert settings.procedure_index_dir == Path("/tmp/procedure-index")


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("BANK_OPS_TRANSACTION_API_URL", "not-a-url"),
        ("BANK_OPS_OLLAMA_URL", "ftp://ollama.example"),
        ("BANK_OPS_GENERATION_MODEL", ""),
        ("BANK_OPS_EMBEDDING_MODEL", "   "),
    ],
)
def test_settings_reject_invalid_values(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
