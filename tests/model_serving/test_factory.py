from typing import cast

import httpx
import pytest

from bank_ops.model_serving import factory
from bank_ops.model_serving.contracts import ExplanationGenerator
from bank_ops.settings import Settings


def test_factory_maps_shared_settings_to_the_ollama_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    fake_client = cast(httpx.Client, object())
    fake_generator = cast(ExplanationGenerator, object())

    def fake_client_factory(**kwargs: object) -> httpx.Client:
        captured["client"] = kwargs
        return fake_client

    def fake_generator_factory(**kwargs: object) -> ExplanationGenerator:
        captured["generator"] = kwargs
        return fake_generator

    monkeypatch.setattr(factory.httpx, "Client", fake_client_factory)
    monkeypatch.setattr(factory, "OllamaExplanationGenerator", fake_generator_factory)
    settings = Settings(
        _env_file=None,
        ollama_url="http://ollama.internal:11434",
        generation_model="cloud-ready-model",
        generation_timeout_seconds=33,
        generation_temperature=0.1,
        generation_max_tokens=72,
        generation_seed=5,
    )

    result = factory.create_ollama_explanation_generator(settings)

    assert result is fake_generator
    assert captured["client"] == {
        "base_url": "http://ollama.internal:11434/",
        "timeout": 33.0,
    }
    assert captured["generator"] == {
        "client": fake_client,
        "model": "cloud-ready-model",
        "temperature": 0.1,
        "max_tokens": 72,
        "seed": 5,
    }
