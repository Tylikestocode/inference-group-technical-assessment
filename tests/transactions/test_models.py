from decimal import Decimal

import pytest
from pydantic import ValidationError

from bank_ops.transactions.models import (
    RiskLevel,
    TransactionChannel,
    TransactionLookupRequest,
    TransactionResponse,
    TransactionStatus,
)


def valid_transaction_data() -> dict[str, object]:
    return {
        "transaction_id": "TXN-0212",
        "status": "held",
        "amount": "12500.00",
        "currency": "ZAR",
        "risk_level": "medium",
        "hold_reason": "Beneficiary details do not match.",
        "channel": "online_banking",
        "timestamp": "2026-08-21T09:30:00Z",
    }


def test_transaction_contract_is_strongly_typed_and_serializes_money_exactly() -> None:
    transaction = TransactionResponse.model_validate(valid_transaction_data())

    assert transaction.status is TransactionStatus.HELD
    assert transaction.amount == Decimal("12500.00")
    assert transaction.risk_level is RiskLevel.MEDIUM
    assert transaction.channel is TransactionChannel.ONLINE_BANKING
    assert transaction.timestamp.utcoffset() is not None
    assert transaction.model_dump(mode="json")["amount"] == "12500.00"


@pytest.mark.parametrize("transaction_id", ["txn-0212", "TXN-212", "TXN-99999"])
def test_lookup_request_rejects_malformed_transaction_id(transaction_id: str) -> None:
    with pytest.raises(ValidationError):
        TransactionLookupRequest(transaction_id=transaction_id)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("amount", "0.00"),
        ("amount", "10.001"),
        ("currency", "zar"),
        ("timestamp", "2026-08-21T09:30:00"),
        ("hold_reason", None),
    ],
)
def test_transaction_rejects_invalid_business_fields(field: str, value: object) -> None:
    data = valid_transaction_data()
    data[field] = value

    with pytest.raises(ValidationError):
        TransactionResponse.model_validate(data)


def test_transaction_rejects_unknown_fields() -> None:
    data = valid_transaction_data()
    data["customer_name"] = "Fictional Person"

    with pytest.raises(ValidationError):
        TransactionResponse.model_validate(data)


def test_transaction_is_immutable() -> None:
    transaction = TransactionResponse.model_validate(valid_transaction_data())

    with pytest.raises(ValidationError):
        transaction.status = TransactionStatus.COMPLETED
