import os
from importlib import resources

import pytest

from bank_ops.model_serving import (
    ExplanationRequest,
    GeneratedExplanation,
    create_ollama_explanation_generator,
)
from bank_ops.settings import Settings
from bank_ops.transactions import (
    JsonTransactionRepository,
    TransactionLookupRequest,
    TransactionResponse,
)


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("BANK_OPS_RUN_MODEL_INTEGRATION") != "1",
    reason="set BANK_OPS_RUN_MODEL_INTEGRATION=1 to call the local model",
)
def test_qwen_returns_a_validated_explanation_for_txn_0212() -> None:
    transaction = JsonTransactionRepository().get(
        TransactionLookupRequest(transaction_id="TXN-0212")
    )
    assert isinstance(transaction, TransactionResponse)

    procedure = resources.files("bank_ops.retrieval.data.procedures").joinpath(
        "PROC-003-beneficiary-verification.md"
    )
    request = ExplanationRequest(
        transaction=transaction,
        procedure_text=procedure.read_text(encoding="utf-8"),
        next_action=(
            "Keep the transaction held and refer the case to Fictional Payments "
            "Operations for human review."
        ),
    )

    result = create_ollama_explanation_generator(Settings()).generate(request)

    assert isinstance(result, GeneratedExplanation)
    assert result.explanation
