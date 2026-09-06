from collections.abc import AsyncIterator

import httpx
import pytest

from bank_ops.transactions.api import create_app
from bank_ops.transactions.models import (
    TransactionLookupRequest,
    TransactionLookupResult,
    TransactionResponse,
)
from bank_ops.transactions.repository import JsonTransactionRepository

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def api_client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=create_app(JsonTransactionRepository()))
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        yield client


async def test_get_txn_0212_returns_expected_transaction(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.get("/transactions/TXN-0212")

    assert response.status_code == 200
    assert response.json() == {
        "transaction_id": "TXN-0212",
        "status": "held",
        "amount": "12500.00",
        "currency": "ZAR",
        "risk_level": "medium",
        "hold_reason": "Beneficiary details do not match the payment instruction.",
        "channel": "online_banking",
        "timestamp": "2026-08-21T09:30:00Z",
    }
    assert TransactionResponse.model_validate(response.json()).transaction_id == (
        "TXN-0212"
    )


async def test_get_unknown_transaction_returns_typed_404(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.get("/transactions/TXN-9999")

    assert response.status_code == 404
    assert response.json() == {
        "error": "transaction_not_found",
        "transaction_id": "TXN-9999",
        "message": "Transaction was not found.",
    }


async def test_get_rejects_malformed_transaction_id(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.get("/transactions/txn-0212")

    assert response.status_code == 422


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
async def test_transaction_endpoint_exposes_no_write_methods(
    api_client: httpx.AsyncClient, method: str
) -> None:
    response = await api_client.request(method, "/transactions/TXN-0212", json={})

    assert response.status_code == 405


async def test_endpoint_delegates_to_injected_repository() -> None:
    class RecordingRepository:
        def __init__(self) -> None:
            self.requests: list[TransactionLookupRequest] = []

        def get(self, request: TransactionLookupRequest) -> TransactionLookupResult:
            self.requests.append(request)
            return TransactionResponse(
                transaction_id=request.transaction_id,
                status="pending",
                amount="10.00",
                currency="ZAR",
                risk_level="low",
                hold_reason=None,
                channel="mobile",
                timestamp="2026-09-06T12:00:00Z",
            )

    repository = RecordingRepository()
    transport = httpx.ASGITransport(app=create_app(repository))
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get("/transactions/TXN-4321")

    assert response.status_code == 200
    assert repository.requests == [TransactionLookupRequest(transaction_id="TXN-4321")]


async def test_openapi_documents_success_and_not_found_contracts(
    api_client: httpx.AsyncClient,
) -> None:
    operation = (await api_client.get("/openapi.json")).json()["paths"][
        "/transactions/{transaction_id}"
    ]["get"]

    assert set(operation["responses"]) >= {"200", "404"}
