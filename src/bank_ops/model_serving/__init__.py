"""Replaceable text-generation boundary and provider composition helpers."""

from bank_ops.model_serving.contracts import (
    ExplanationGenerationFailure,
    ExplanationGenerationResult,
    ExplanationGenerator,
    ExplanationRequest,
    GeneratedExplanation,
    InvalidModelResponse,
    ModelTimedOut,
    ModelUnavailable,
)
from bank_ops.model_serving.factory import create_ollama_explanation_generator

__all__ = [
    "ExplanationGenerationFailure",
    "ExplanationGenerationResult",
    "ExplanationGenerator",
    "ExplanationRequest",
    "GeneratedExplanation",
    "InvalidModelResponse",
    "ModelTimedOut",
    "ModelUnavailable",
    "create_ollama_explanation_generator",
]
