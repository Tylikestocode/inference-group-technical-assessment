import pytest
from pydantic import ValidationError

from bank_ops.investigations import (
    AllowedNextAction,
    EscalationDestination,
    InvestigationOutcome,
    InvestigationRequest,
    InvestigationResponse,
    TransactionQuestionError,
)

TRACE_ID = "12345678-1234-5678-1234-567812345678"


def test_extracts_one_transaction_id_and_preserves_the_question() -> None:
    question = "Why is TXN-0212 held?"

    request = InvestigationRequest.from_question(question)

    assert request.question == question
    assert request.transaction_id == "TXN-0212"


@pytest.mark.parametrize(
    ("question", "message"),
    [
        ("Why is this transaction held?", "Include exactly one transaction ID"),
        ("Why is txn-0212 held?", "exact format TXN-0000"),
        ("Why is TXN-212 held?", "exact format TXN-0000"),
        ("Why is TXN-02120 held?", "exact format TXN-0000"),
        ("Why is TXN-0212-extra held?", "exact format TXN-0000"),
        (
            "Compare TXN-0212 with TXN-9999.",
            "multiple IDs were found",
        ),
        (
            "Compare TXN-0212 with TXN-0212.",
            "multiple IDs were found",
        ),
    ],
)
def test_rejects_questions_without_exactly_one_valid_id(
    question: str, message: str
) -> None:
    with pytest.raises(TransactionQuestionError, match=message):
        InvestigationRequest.from_question(question)


def test_lookup_failure_contract_rejects_invented_evidence() -> None:
    with pytest.raises(ValidationError, match="must not contain invented evidence"):
        InvestigationResponse(
            trace_id=TRACE_ID,
            requested_transaction_id="TXN-9999",
            outcome=InvestigationOutcome.TRANSACTION_NOT_FOUND,
            transaction={
                "transaction_id": "TXN-9999",
                "status": "held",
                "amount": "10.00",
                "currency": "ZAR",
                "risk_level": "low",
                "hold_reason": "Invented reason.",
                "channel": "mobile",
                "timestamp": "2026-08-20T14:05:00Z",
            },
            procedure=None,
            explanation="Transaction was not found.",
            recommended_next_action=(
                AllowedNextAction.CONFIRM_TRANSACTION_ID_AND_REFER
            ),
            human_review_required=True,
            escalation_destination=EscalationDestination.OPERATIONS_CONTROL,
            warnings=("No facts were inferred.",),
        )


def test_failure_outcome_rejects_a_different_permitted_action() -> None:
    with pytest.raises(ValidationError, match="unsupported recommended action"):
        InvestigationResponse(
            trace_id=TRACE_ID,
            requested_transaction_id="TXN-9999",
            outcome=InvestigationOutcome.TRANSACTION_NOT_FOUND,
            transaction=None,
            procedure=None,
            explanation="Transaction was not found.",
            recommended_next_action=AllowedNextAction.REFER_SANCTIONS_REVIEW,
            human_review_required=True,
            escalation_destination=EscalationDestination.OPERATIONS_CONTROL,
            warnings=("No facts were inferred.",),
        )


def test_recommendation_outside_the_permitted_action_list_is_rejected() -> None:
    with pytest.raises(ValidationError, match="recommended_next_action"):
        InvestigationResponse(
            trace_id=TRACE_ID,
            requested_transaction_id="TXN-9999",
            outcome=InvestigationOutcome.TRANSACTION_NOT_FOUND,
            transaction=None,
            procedure=None,
            explanation="Transaction was not found.",
            recommended_next_action="Release the transaction.",
            human_review_required=True,
            escalation_destination=EscalationDestination.OPERATIONS_CONTROL,
            warnings=("No facts were inferred.",),
        )
