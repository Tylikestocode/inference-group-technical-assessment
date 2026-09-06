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
def test_uncertain_combinations_receive_only_the_manual_review_action(
    transaction_status: str,
    hold_reason: str | None,
    procedure_id: str,
) -> None:
    decision = decide_next_action(
        _transaction(status=transaction_status, hold_reason=hold_reason),
        _procedure(procedure_id=procedure_id),
    )

    if procedure_id == "PROC-001":
        assert (
            decision.recommended_next_action
            is AllowedNextAction.REFER_SANCTIONS_REVIEW
        )
        assert (
            decision.escalation_destination
            is EscalationDestination.FINANCIAL_CRIME_OPERATIONS
        )
    else:
        assert decision.recommended_next_action is AllowedNextAction.REFER_MANUAL_REVIEW
        assert (
            decision.escalation_destination
            is EscalationDestination.OPERATIONS_CONTROL
        )
    assert decision.human_review_required is True


def test_high_risk_transaction_requires_transaction_monitoring_review() -> None:
    transaction = _transaction(
        status="held", hold_reason="Activity requires enhanced review."
    ).model_copy(update={"risk_level": "high"})

    decision = decide_next_action(transaction, _procedure(procedure_id="PROC-002"))

    assert decision.recommended_next_action is AllowedNextAction.REFER_HIGH_RISK_REVIEW
    assert (
        decision.escalation_destination
        is EscalationDestination.TRANSACTION_MONITORING_OPERATIONS
    )
    assert decision.human_review_required is True


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
