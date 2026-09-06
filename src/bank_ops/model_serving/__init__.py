"""Replaceable text-generation boundary and provider composition helpers."""

from bank_ops.model_serving.contracts import (
    ExplanationGenerator,
    ExplanationRequest,
    GeneratedExplanation,
)
from bank_ops.model_serving.factory import create_ollama_explanation_generator

__all__ = [
    "ExplanationGenerator",
    "ExplanationRequest",
    "GeneratedExplanation",
    "create_ollama_explanation_generator",
]
