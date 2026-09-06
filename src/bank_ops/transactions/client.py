"""Application-owned client boundary for transaction lookup."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self, runtime_checkable

import httpx

from bank_ops.transactions.models import (
    TransactionClientResult,
    TransactionLookupRequest,
    TransactionNotFound,
    TransactionResponse,
    TransactionServiceUnavailable,
)


@runtime_checkable
class TransactionClient(Protocol):
    """Read-only transaction lookup capability used by the agent."""

    def get(self, request: TransactionLookupRequest) -> TransactionClientResult:
        """Return a transaction or a typed safe-failure result."""


class HttpTransactionClient:
    """HTTP adapter for the transaction lookup API."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._owns_client = client is None

    def get(self, request: TransactionLookupRequest) -> TransactionClientResult:
        """Look up a transaction and validate the API response contract."""

        try:
            response = self._client.get(
                f"{self._base_url}/transactions/{request.transaction_id}",
                timeout=self._timeout_seconds,
            )
        except httpx.RequestError:
            return TransactionServiceUnavailable(transaction_id=request.transaction_id)

        if response.status_code == 200:
            return TransactionResponse.model_validate_json(response.content)
        if response.status_code == 404:
            return TransactionNotFound.model_validate_json(response.content)
        if response.status_code >= 500:
            return TransactionServiceUnavailable(transaction_id=request.transaction_id)

        response.raise_for_status()
        raise AssertionError("unreachable")

    def close(self) -> None:
        """Close an internally managed HTTP connection pool."""

        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
