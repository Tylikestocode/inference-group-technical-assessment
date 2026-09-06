from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError

from bank_ops.transactions.client import HttpTransactionClient, TransactionClient
from bank_ops.transactions.models import (
    TransactionLookupRequest,
    TransactionNotFound,
    TransactionResponse,
)


def transaction_payload() -> dict[str, object]:
    return {
        "transaction_id": "TXN-0212",
        "status": "held",
        "amount": "12500.00",
        "currency": "ZAR",
        "risk_level": "medium",
        "hold_reason": "Beneficiary details do not match the payment instruction.",
        "channel": "online_banking",
        "timestamp": "2026-08-21T09:30:00Z",
    }


def test_http_client_returns_typed_transaction_and_uses_get_route() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url == "https://transactions.test/transactions/TXN-0212"
        return httpx.Response(200, json=transaction_payload())

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = HttpTransactionClient(
            "https://transactions.test/", client=http_client
        )
        result = client.get(TransactionLookupRequest(transaction_id="TXN-0212"))

    assert isinstance(result, TransactionResponse)
    assert result.amount == Decimal("12500.00")


def test_http_client_returns_typed_not_found_without_invented_details() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                "error": "transaction_not_found",
                "transaction_id": "TXN-9999",
                "message": "Transaction was not found.",
            },
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = HttpTransactionClient(
            "https://transactions.test", client=http_client
        )
        result = client.get(TransactionLookupRequest(transaction_id="TXN-9999"))

    assert result == TransactionNotFound(transaction_id="TXN-9999")
    assert "status" not in result.model_fields_set
    assert "hold_reason" not in result.model_fields_set


def test_http_client_raises_for_unexpected_http_status() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    with httpx.Client(transport=transport) as http_client:
        client = HttpTransactionClient(
            "https://transactions.test", client=http_client
        )
        with pytest.raises(httpx.HTTPStatusError):
            client.get(TransactionLookupRequest(transaction_id="TXN-0212"))


def test_http_client_rejects_invalid_success_payload() -> None:
    invalid_payload = transaction_payload()
    invalid_payload["currency"] = "zar"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=invalid_payload)
    )
    with httpx.Client(transport=transport) as http_client:
        client = HttpTransactionClient(
            "https://transactions.test", client=http_client
        )
        with pytest.raises(ValidationError):
            client.get(TransactionLookupRequest(transaction_id="TXN-0212"))


def test_transaction_client_protocol_accepts_a_framework_free_stand_in() -> None:
    class StandInClient:
        def get(self, request: TransactionLookupRequest) -> TransactionNotFound:
            return TransactionNotFound(transaction_id=request.transaction_id)

    client = StandInClient()

    assert isinstance(client, TransactionClient)
    assert client.get(TransactionLookupRequest(transaction_id="TXN-9999")) == (
        TransactionNotFound(transaction_id="TXN-9999")
    )
