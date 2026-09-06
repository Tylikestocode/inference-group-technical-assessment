"""Deterministic operational rules for transaction investigations."""

from __future__ import annotations

from bank_ops.investigations import (
    AllowedNextAction,
    EscalationDestination,
    InvestigationDecision,
    InvestigationOutcome,
)
from bank_ops.retrieval import ProcedureSearchResult
from bank_ops.transactions import RiskLevel, TransactionResponse

ADVISORY_ONLY_WARNING = (
    "This agent is advisory and cannot release, approve, reject, edit, or bypass "
    "the transaction."
)
BENEFICIARY_MISMATCH_HOLD_REASON = (
    "Beneficiary details do not match the payment instruction."
)


class UnsupportedInvestigationError(RuntimeError):
    """Retained for callers that distinguish unsupported policy revisions."""


def decide_next_action(
    transaction: TransactionResponse,
    procedure: ProcedureSearchResult,
) -> InvestigationDecision:
    """Select only an approved advisory action and human review destination."""

    hold_reason = (transaction.hold_reason or "").casefold()

    if "sanction" in hold_reason or procedure.procedure_id == "PROC-001":
        return _escalation_decision(
            AllowedNextAction.REFER_SANCTIONS_REVIEW,
            EscalationDestination.FINANCIAL_CRIME_OPERATIONS,
        )

    if (
        transaction.risk_level is RiskLevel.HIGH
        or procedure.procedure_id == "PROC-002"
    ):
        return _escalation_decision(
            AllowedNextAction.REFER_HIGH_RISK_REVIEW,
            EscalationDestination.TRANSACTION_MONITORING_OPERATIONS,
        )

    if (
        transaction.hold_reason == BENEFICIARY_MISMATCH_HOLD_REASON
        and procedure.procedure_id == "PROC-003"
    ):
        return _escalation_decision(
            AllowedNextAction.VERIFY_BENEFICIARY_AND_REFER,
            EscalationDestination.PAYMENTS_OPERATIONS,
        )

    # A held transaction, a general manual-review procedure, or a mismatch
    # between verified facts and the retrieved specialist procedure is uncertain.
    return manual_review_decision()


def manual_review_decision() -> InvestigationDecision:
    """Return the cautious deterministic decision for incomplete guidance."""

    return _escalation_decision(
        AllowedNextAction.REFER_MANUAL_REVIEW,
        EscalationDestination.OPERATIONS_CONTROL,
    )


def _escalation_decision(
    action: AllowedNextAction,
    destination: EscalationDestination,
) -> InvestigationDecision:
    return InvestigationDecision(
        outcome=InvestigationOutcome.ESCALATION_REQUIRED,
        recommended_next_action=action,
        human_review_required=True,
        escalation_destination=destination,
        warnings=(ADVISORY_ONLY_WARNING,),
    )
