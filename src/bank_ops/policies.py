"""Deterministic operational rules for transaction investigations."""

from __future__ import annotations

from bank_ops.investigations import (
    AllowedNextAction,
    EscalationDestination,
    InvestigationDecision,
    InvestigationOutcome,
)
from bank_ops.retrieval import ProcedureSearchResult
from bank_ops.transactions import TransactionResponse, TransactionStatus

ADVISORY_ONLY_WARNING = (
    "This agent is advisory and cannot release, approve, reject, edit, or bypass "
    "the transaction."
)
BENEFICIARY_MISMATCH_HOLD_REASON = (
    "Beneficiary details do not match the payment instruction."
)


class UnsupportedInvestigationError(RuntimeError):
    """Raised when the current slice has no approved deterministic rule."""


def decide_next_action(
    transaction: TransactionResponse,
    procedure: ProcedureSearchResult,
) -> InvestigationDecision:
    """Apply the approved TXN-0212 beneficiary-verification rule."""

    if (
        transaction.status is not TransactionStatus.HELD
        or transaction.hold_reason != BENEFICIARY_MISMATCH_HOLD_REASON
        or procedure.procedure_id != "PROC-003"
    ):
        raise UnsupportedInvestigationError(
            "No happy-path decision rule matches the verified transaction and "
            "retrieved procedure"
        )

    return InvestigationDecision(
        outcome=InvestigationOutcome.ESCALATION_REQUIRED,
        recommended_next_action=AllowedNextAction.VERIFY_BENEFICIARY_AND_REFER,
        human_review_required=True,
        escalation_destination=EscalationDestination.PAYMENTS_OPERATIONS,
        warnings=(ADVISORY_ONLY_WARNING,),
    )
