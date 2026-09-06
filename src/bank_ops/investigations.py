"""Validated contracts for controlled transaction investigations."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field, StringConstraints, model_validator

from bank_ops.retrieval.models import ProcedureSearchResult
from bank_ops.transactions.models import (
    ContractModel,
    RiskLevel,
    TransactionId,
    TransactionResponse,
    TransactionStatus,
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
    """Named outcomes produced by the controlled investigation workflow."""

    ESCALATION_REQUIRED = "escalation_required"
    TRANSACTION_NOT_FOUND = "transaction_not_found"
    TRANSACTION_SERVICE_UNAVAILABLE = "transaction_service_unavailable"
    NO_RELEVANT_PROCEDURE = "no_relevant_procedure"
    MODEL_FALLBACK_USED = "model_fallback_used"


class AllowedNextAction(StrEnum):
    """Closed set of advisory-only actions the application may return."""

    VERIFY_BENEFICIARY_AND_REFER = (
        "Compare the available beneficiary details with the original payment "
        "instruction, keep the transaction held, and refer any unresolved "
        "mismatch to Fictional Payments Operations."
    )
    REFER_SANCTIONS_REVIEW = (
        "Keep the transaction in its current state and refer the verified screening "
        "facts to Fictional Financial Crime Operations for human review."
    )
    REFER_HIGH_RISK_REVIEW = (
        "Keep the transaction in its current state and refer the verified facts to "
        "Fictional Transaction Monitoring Operations for human review."
    )
    REFER_MANUAL_REVIEW = (
        "Preserve the transaction's current state and refer the available verified "
        "facts to Fictional Operations Control for manual review."
    )
    CONFIRM_TRANSACTION_ID_AND_REFER = (
        "Confirm the transaction ID and retry the lookup; if it still cannot be "
        "found, refer the case to Fictional Operations Control."
    )
    RETRY_LOOKUP_OR_REFER = (
        "Retry the transaction lookup once the service is available or refer the "
        "case to Fictional Operations Control."
    )


class EscalationDestination(StrEnum):
    """Human teams the deterministic policy may select."""

    PAYMENTS_OPERATIONS = "Fictional Payments Operations"
    FINANCIAL_CRIME_OPERATIONS = "Fictional Financial Crime Operations"
    TRANSACTION_MONITORING_OPERATIONS = (
        "Fictional Transaction Monitoring Operations"
    )
    OPERATIONS_CONTROL = "Fictional Operations Control"


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

        if (
            self.outcome is InvestigationOutcome.ESCALATION_REQUIRED
            and not self.human_review_required
        ):
            raise ValueError("an escalation outcome requires human review")
        return self


class InvestigationResponse(ContractModel):
    """Complete grounded response returned by the investigation workflow."""

    trace_id: UUID
    data_label: Literal["Fictional assessment data"] = FICTIONAL_DATA_LABEL
    requested_transaction_id: TransactionId
    outcome: InvestigationOutcome
    transaction: TransactionResponse | None
    procedure: ProcedureReference | None
    explanation: Annotated[RequiredText, Field(max_length=600)]
    recommended_next_action: AllowedNextAction
    human_review_required: bool
    escalation_destination: EscalationDestination | None
    warnings: tuple[RequiredText, ...]

    @model_validator(mode="before")
    @classmethod
    def default_requested_transaction_id(cls, data: Any) -> Any:
        """Keep older successful callers compatible while making failures traceable."""

        if isinstance(data, dict) and "requested_transaction_id" not in data:
            transaction = data.get("transaction")
            if isinstance(transaction, TransactionResponse):
                data = {**data, "requested_transaction_id": transaction.transaction_id}
            elif isinstance(transaction, dict) and "transaction_id" in transaction:
                data = {
                    **data,
                    "requested_transaction_id": transaction["transaction_id"],
                }
        return data

    @model_validator(mode="after")
    def escalation_matches_human_review(self) -> InvestigationResponse:
        """Keep the public response internally consistent."""

        if self.human_review_required != (self.escalation_destination is not None):
            raise ValueError(
                "human review and escalation destination must be set together"
            )

        uncertain_outcomes = {
            InvestigationOutcome.TRANSACTION_NOT_FOUND,
            InvestigationOutcome.TRANSACTION_SERVICE_UNAVAILABLE,
            InvestigationOutcome.NO_RELEVANT_PROCEDURE,
            InvestigationOutcome.MODEL_FALLBACK_USED,
        }
        sensitive_transaction = self.transaction is not None and (
            self.transaction.status is TransactionStatus.HELD
            or self.transaction.risk_level is RiskLevel.HIGH
            or "sanction" in (self.transaction.hold_reason or "").casefold()
        )
        if (
            self.outcome is InvestigationOutcome.ESCALATION_REQUIRED
            or self.outcome in uncertain_outcomes
            or sensitive_transaction
        ) and not self.human_review_required:
            raise ValueError(
                "held, high-risk, sanctions-related, escalated, or uncertain cases "
                "require human review"
            )

        lookup_failures = {
            InvestigationOutcome.TRANSACTION_NOT_FOUND,
            InvestigationOutcome.TRANSACTION_SERVICE_UNAVAILABLE,
        }
        if self.outcome in lookup_failures:
            if self.transaction is not None or self.procedure is not None:
                raise ValueError(
                    "transaction lookup failures must not contain invented evidence"
                )
        elif self.transaction is None:
            raise ValueError("this outcome requires verified transaction facts")

        if (
            self.transaction is not None
            and self.transaction.transaction_id != self.requested_transaction_id
        ):
            raise ValueError("verified transaction does not match the requested ID")

        if self.outcome is InvestigationOutcome.NO_RELEVANT_PROCEDURE:
            if self.procedure is not None:
                raise ValueError(
                    "a no-relevant-procedure outcome cannot cite a procedure"
                )
        elif self.outcome not in lookup_failures and self.procedure is None:
            raise ValueError("this outcome requires a verified procedure reference")

        expected_failure_actions = {
            InvestigationOutcome.TRANSACTION_NOT_FOUND: (
                AllowedNextAction.CONFIRM_TRANSACTION_ID_AND_REFER
            ),
            InvestigationOutcome.TRANSACTION_SERVICE_UNAVAILABLE: (
                AllowedNextAction.RETRY_LOOKUP_OR_REFER
            ),
            InvestigationOutcome.NO_RELEVANT_PROCEDURE: (
                AllowedNextAction.REFER_MANUAL_REVIEW
            ),
        }
        expected_action = expected_failure_actions.get(self.outcome)
        if (
            expected_action is not None
            and self.recommended_next_action is not expected_action
        ):
            raise ValueError("failure outcome has an unsupported recommended action")
        return self
