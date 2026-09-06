import pytest

from bank_ops.investigations import InvestigationRequest, TransactionQuestionError


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
