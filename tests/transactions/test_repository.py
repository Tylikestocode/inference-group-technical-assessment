import json
from pathlib import Path

import pytest

from bank_ops.transactions.models import (
    ErrorCode,
    RiskLevel,
    TransactionLookupRequest,
    TransactionNotFound,
    TransactionResponse,
    TransactionStatus,
)
from bank_ops.transactions.repository import (
    JsonTransactionRepository,
    TransactionDataError,
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


def write_fixture(path: Path, records: object) -> Path:
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_repository_loads_txn_0212_as_a_typed_transaction() -> None:
    repository = JsonTransactionRepository()

    result = repository.get(TransactionLookupRequest(transaction_id="TXN-0212"))

    assert isinstance(result, TransactionResponse)
    assert result.transaction_id == "TXN-0212"
    assert result.status is TransactionStatus.HELD
    assert result.risk_level is RiskLevel.MEDIUM
    assert result.currency == "ZAR"
    assert result.hold_reason == (
        "Beneficiary details do not match the payment instruction."
    )


def test_repository_returns_specific_result_for_unknown_id() -> None:
    repository = JsonTransactionRepository()

    result = repository.get(TransactionLookupRequest(transaction_id="TXN-9999"))

    assert result == TransactionNotFound(transaction_id="TXN-9999")
    assert result.error is ErrorCode.TRANSACTION_NOT_FOUND
    assert "status" not in result.model_fields_set
    assert "hold_reason" not in result.model_fields_set


def test_repository_reports_malformed_json(tmp_path: Path) -> None:
    fixture = tmp_path / "transactions.json"
    fixture.write_text('[{"transaction_id":', encoding="utf-8")

    with pytest.raises(TransactionDataError, match=r"Invalid JSON.*line 1"):
        JsonTransactionRepository(fixture)


@pytest.mark.parametrize(
    ("field", "value", "expected_detail"),
    [
        ("currency", "zar", "currency"),
        ("timestamp", "not-a-timestamp", "timestamp"),
        ("hold_reason", None, "held transactions must include a hold reason"),
        ("customer_name", "Fictional Person", "customer_name"),
    ],
)
def test_repository_reports_invalid_fixture_fields(
    tmp_path: Path, field: str, value: object, expected_detail: str
) -> None:
    record = valid_transaction_data()
    record[field] = value
    fixture = write_fixture(tmp_path / "transactions.json", [record])

    with pytest.raises(TransactionDataError, match=expected_detail):
        JsonTransactionRepository(fixture)


def test_repository_rejects_duplicate_transaction_ids(tmp_path: Path) -> None:
    record = valid_transaction_data()
    fixture = write_fixture(tmp_path / "transactions.json", [record, record])

    with pytest.raises(TransactionDataError, match=r"duplicate transaction_id TXN-0212"):
        JsonTransactionRepository(fixture)


def test_repository_reports_missing_fixture(tmp_path: Path) -> None:
    missing_fixture = tmp_path / "missing.json"

    with pytest.raises(TransactionDataError, match=r"Unable to read transaction data"):
        JsonTransactionRepository(missing_fixture)


def test_repository_exposes_no_mutation_methods() -> None:
    repository = JsonTransactionRepository()

    assert not hasattr(repository, "add")
    assert not hasattr(repository, "update")
    assert not hasattr(repository, "delete")


def test_packaged_fixture_uses_only_approved_contract_fields() -> None:
    fixture = (
        Path(__file__).parents[2]
        / "src"
        / "bank_ops"
        / "transactions"
        / "data"
        / "transactions.json"
    )
    records = json.loads(fixture.read_text(encoding="utf-8"))
    approved_fields = {
        "transaction_id",
        "status",
        "amount",
        "currency",
        "risk_level",
        "hold_reason",
        "channel",
        "timestamp",
    }

    assert records
    assert all(set(record) == approved_fields for record in records)
