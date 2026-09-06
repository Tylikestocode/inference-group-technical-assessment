from decimal import Decimal

import pytest
from pydantic import ValidationError

from bank_ops.model_serving import (
    ExplanationGenerator,
    ExplanationRequest,
    GeneratedExplanation,
)
from bank_ops.transactions.models import TransactionResponse


def transaction() -> TransactionResponse:
    return TransactionResponse(
        transaction_id="TXN-0212",
        status="held",
        amount=Decimal("12500.00"),
        currency="ZAR",
        risk_level="medium",
        hold_reason="Beneficiary details do not match the payment instruction.",
        channel="online_banking",
        timestamp="2026-08-21T09:30:00Z",
    )


def request() -> ExplanationRequest:
    return ExplanationRequest(
        transaction=transaction(),
        procedure_text="Verify the beneficiary details against the instruction.",
        next_action="Keep the transaction held and refer it to Payments Operations.",
    )


def test_explanation_request_accepts_only_grounded_inputs() -> None:
    explanation_request = request()

    assert explanation_request.transaction.transaction_id == "TXN-0212"
    assert explanation_request.procedure_text.startswith("Verify")
    assert explanation_request.next_action.startswith("Keep")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("procedure_text", "  "),
        ("next_action", ""),
    ],
)
def test_explanation_request_rejects_blank_grounding(field: str, value: str) -> None:
    data = request().model_dump()
    data[field] = value

    with pytest.raises(ValidationError):
        ExplanationRequest.model_validate(data)


def test_generated_explanation_is_small_strict_and_immutable() -> None:
    explanation = GeneratedExplanation(explanation="  The mismatch must be reviewed. ")

    assert explanation.explanation == "The mismatch must be reviewed."

    with pytest.raises(ValidationError):
        GeneratedExplanation(explanation="x" * 601)

    with pytest.raises(ValidationError):
        GeneratedExplanation.model_validate(
            {"explanation": "Valid text.", "next_action": "Release it."}
        )

    with pytest.raises(ValidationError):
        explanation.explanation = "Changed."


def test_stand_in_can_replace_a_model_provider() -> None:
    class StandInExplanationGenerator:
        def generate(self, value: ExplanationRequest) -> GeneratedExplanation:
            assert value.transaction.transaction_id == "TXN-0212"
            return GeneratedExplanation(explanation="A predictable explanation.")

    generator: ExplanationGenerator = StandInExplanationGenerator()

    assert generator.generate(request()) == GeneratedExplanation(
        explanation="A predictable explanation."
    )
