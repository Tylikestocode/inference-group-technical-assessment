"""Composition helpers for model-serving adapters."""

from __future__ import annotations

import httpx

from bank_ops.model_serving.contracts import ExplanationGenerator
from bank_ops.model_serving.ollama import OllamaExplanationGenerator
from bank_ops.settings import Settings


def create_ollama_explanation_generator(settings: Settings) -> ExplanationGenerator:
    """Build the local provider adapter from validated application settings."""

    client = httpx.Client(
        base_url=str(settings.ollama_url),
        timeout=httpx.Timeout(settings.generation_timeout_seconds),
    )
    return OllamaExplanationGenerator(
        client=client,
        model=settings.generation_model,
        temperature=settings.generation_temperature,
        max_tokens=settings.generation_max_tokens,
        seed=settings.generation_seed,
    )
