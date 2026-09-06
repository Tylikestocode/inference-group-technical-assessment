"""Provider-neutral contracts for grounded investigation explanations."""

from __future__ import annotations

from typing import Annotated, Literal, Protocol, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from bank_ops.transactions.models import TransactionResponse

GroundedText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
ShortExplanation = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=600),
]


class ModelServingContract(BaseModel):
    """Base contract that rejects drift and cannot be mutated after validation."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ExplanationRequest(ModelServingContract):
    """Grounded information from which a provider may write an explanation."""

    transaction: TransactionResponse
    procedure_text: GroundedText
    next_action: Annotated[GroundedText, Field(max_length=1000)]


class GeneratedExplanation(ModelServingContract):
    """The complete structured contribution expected from a text model."""

    explanation: ShortExplanation


class ExplanationGenerationFailure(ModelServingContract):
    """Base type for safe failures returned across the provider boundary."""


class ModelUnavailable(ExplanationGenerationFailure):
    """The configured model service could not complete a request."""

    failure_type: Literal["model_unavailable"] = "model_unavailable"


class ModelTimedOut(ExplanationGenerationFailure):
    """The configured model service exceeded the allowed request time."""

    failure_type: Literal["model_timed_out"] = "model_timed_out"


class InvalidModelResponse(ExplanationGenerationFailure):
    """The provider returned content outside the validated response contract."""

    failure_type: Literal["invalid_model_response"] = "invalid_model_response"


ExplanationGenerationResult: TypeAlias = (
    GeneratedExplanation | ModelUnavailable | ModelTimedOut | InvalidModelResponse
)


class ExplanationGenerator(Protocol):
    """Application-owned boundary implemented by local or cloud providers."""

    def generate(self, request: ExplanationRequest) -> ExplanationGenerationResult:
        """Write a short explanation without making operational decisions."""
