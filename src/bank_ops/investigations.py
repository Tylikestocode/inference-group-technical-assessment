"""Validated contracts for controlled transaction investigations."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints, model_validator

from bank_ops.retrieval.models import ProcedureSearchResult
from bank_ops.transactions.models import (
    ContractModel,
    TransactionId,
    TransactionResponse,
)

_TRANSACTION_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])(?i:TXN)[A-Za-z0-9_-]*(?![A-Za-z0-9_])"
)
_VALID_TRANSACTION_ID = re.compile(r"TXN-\d{4}")

RequiredText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]

FICTIONAL_DATA_LABEL = "Fictional assessment data"


class TransactionQuestionError(ValueError):
    """Raised when a question does not contain exactly one valid transaction ID."""


class InvestigationRequest(ContractModel):
    """Question and transaction ID accepted by the agent boundary."""

    question: Annotated[str, Field(min_length=1)]
    transaction_id: TransactionId

    @classmethod
    def from_question(cls, question: str) -> InvestigationRequest:
        """Extract exactly one standalone, correctly formatted transaction ID."""

        candidates = _TRANSACTION_TOKEN.findall(question)
        if not candidates:
            raise TransactionQuestionError(
                "Include exactly one transaction ID in the form TXN-0000."
            )

        if any(
            _VALID_TRANSACTION_ID.fullmatch(candidate) is None
            for candidate in candidates
        ):
            raise TransactionQuestionError(
                "Transaction IDs must use the exact format TXN-0000 "
                "(uppercase TXN and four digits)."
            )

        if len(candidates) != 1:
            raise TransactionQuestionError(
                "Include exactly one transaction ID; multiple IDs were found."
            )

        return cls(question=question, transaction_id=candidates[0])


class InvestigationOutcome(StrEnum):
    """Successful operational outcomes produced by application rules."""

    ESCALATION_REQUIRED = "escalation_required"


class AllowedNextAction(StrEnum):
    """Closed set of advisory actions the happy-path workflow may return."""

    VERIFY_BENEFICIARY_AND_REFER = (
        "Compare the available beneficiary details with the original payment "
        "instruction, keep the transaction held, and refer any unresolved "
        "mismatch to Fictional Payments Operations."
    )


class EscalationDestination(StrEnum):
    """Human teams the application may select for the happy path."""

    PAYMENTS_OPERATIONS = "Fictional Payments Operations"


class ProcedureReference(ContractModel):
    """Traceable details for the procedure section used in the response."""

    procedure_id: Annotated[str, Field(pattern=r"^PROC-\d{3}$")]
    title: RequiredText
    version: RequiredText
    section: RequiredText
    source_file: Annotated[str, Field(pattern=r"^[^/\\]+\.md$")]
    relevance_score: Annotated[float, Field(ge=-1, le=1)]

    @classmethod
    def from_search_result(cls, result: ProcedureSearchResult) -> ProcedureReference:
        """Keep citation metadata while excluding internal procedure text."""

        return cls(
            procedure_id=result.procedure_id,
            title=result.title,
            version=result.version,
            section=result.section,
            source_file=result.source_file,
            relevance_score=result.relevance_score,
        )


class InvestigationDecision(ContractModel):
    """Operational decision made by deterministic application policy."""

    outcome: InvestigationOutcome
    recommended_next_action: AllowedNextAction
    human_review_required: bool
    escalation_destination: EscalationDestination | None
    warnings: tuple[RequiredText, ...]

    @model_validator(mode="after")
    def escalation_matches_human_review(self) -> InvestigationDecision:
        """Require a destination exactly when a human review is required."""

        if self.human_review_required != (self.escalation_destination is not None):
            raise ValueError(
                "human review and escalation destination must be set together"
            )
        return self


class InvestigationResponse(ContractModel):
    """Complete grounded response returned by the investigation workflow."""

    trace_id: UUID
    data_label: Literal["Fictional assessment data"] = FICTIONAL_DATA_LABEL
    outcome: InvestigationOutcome
    transaction: TransactionResponse
    procedure: ProcedureReference
    explanation: Annotated[RequiredText, Field(max_length=600)]
    recommended_next_action: AllowedNextAction
    human_review_required: bool
    escalation_destination: EscalationDestination | None
    warnings: tuple[RequiredText, ...]

    @model_validator(mode="after")
    def escalation_matches_human_review(self) -> InvestigationResponse:
        """Keep the public response internally consistent."""

        if self.human_review_required != (self.escalation_destination is not None):
            raise ValueError(
                "human review and escalation destination must be set together"
            )
        return self
