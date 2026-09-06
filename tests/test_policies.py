from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from bank_ops.investigations import (
    AllowedNextAction,
    EscalationDestination,
    InvestigationOutcome,
)
from bank_ops.policies import (
    ADVISORY_ONLY_WARNING,
    UnsupportedInvestigationError,
    decide_next_action,
)
from bank_ops.retrieval import ProcedureSearchResult
from bank_ops.transactions import TransactionResponse


def test_beneficiary_hold_requires_payments_operations_review() -> None:
    decision = decide_next_action(_transaction(), _procedure())

    assert decision.outcome is InvestigationOutcome.ESCALATION_REQUIRED
    assert (
        decision.recommended_next_action
        is AllowedNextAction.VERIFY_BENEFICIARY_AND_REFER
    )
    assert decision.human_review_required is True
    assert decision.escalation_destination is EscalationDestination.PAYMENTS_OPERATIONS
    assert decision.warnings == (ADVISORY_ONLY_WARNING,)


@pytest.mark.parametrize(
    ("transaction_status", "hold_reason", "procedure_id"),
    [
        ("completed", None, "PROC-003"),
        ("held", "A different hold reason.", "PROC-003"),
        (
            "held",
            "Beneficiary details do not match the payment instruction.",
            "PROC-001",
        ),
    ],
)
def test_unsupported_combinations_do_not_receive_an_invented_action(
    transaction_status: str,
    hold_reason: str | None,
    procedure_id: str,
) -> None:
    with pytest.raises(UnsupportedInvestigationError, match="No happy-path"):
        decide_next_action(
            _transaction(status=transaction_status, hold_reason=hold_reason),
            _procedure(procedure_id=procedure_id),
        )


def _transaction(
    status: str = "held",
    hold_reason: str | None = (
        "Beneficiary details do not match the payment instruction."
    ),
) -> TransactionResponse:
    return TransactionResponse(
        transaction_id="TXN-0212",
        status=status,
        amount=Decimal("12500.00"),
        currency="ZAR",
        risk_level="medium",
        hold_reason=hold_reason,
        channel="online_banking",
        timestamp=datetime(2026, 8, 21, 9, 30, tzinfo=UTC),
    )


def _procedure(procedure_id: str = "PROC-003") -> ProcedureSearchResult:
    return ProcedureSearchResult(
        procedure_id=procedure_id,
        title="Beneficiary Verification",
        version="1.0",
        owner="Fictional Payments Operations",
        data_label="Fictional assessment data",
        section="Beneficiary details do not match the payment instruction",
        source_file="PROC-003-beneficiary-verification.md",
        text="Compare the beneficiary details with the payment instruction.",
        relevance_score=0.95,
    )
