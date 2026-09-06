"""Read-only access to validated synthetic transaction data."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Protocol

from pydantic import TypeAdapter, ValidationError

from bank_ops.transactions.models import (
    TransactionLookupRequest,
    TransactionLookupResult,
    TransactionNotFound,
    TransactionResponse,
)

_TRANSACTION_LIST = TypeAdapter(list[TransactionResponse])


class TransactionDataError(RuntimeError):
    """Raised when the synthetic transaction source cannot be safely loaded."""


class TransactionRepository(Protocol):
    """Application-owned boundary for read-only transaction lookup."""

    def get(self, request: TransactionLookupRequest) -> TransactionLookupResult:
        """Return a transaction or a specific not-found result."""


class JsonTransactionRepository:
    """Repository backed by an eagerly validated local JSON document."""

    def __init__(self, fixture_path: str | Path | None = None) -> None:
        source, source_name = self._read_source(fixture_path)
        transactions = self._validate_source(source, source_name)

        indexed: dict[str, TransactionResponse] = {}
        for transaction in transactions:
            if transaction.transaction_id in indexed:
                raise TransactionDataError(
                    f"Invalid transaction data in {source_name}: duplicate "
                    f"transaction_id {transaction.transaction_id}"
                )
            indexed[transaction.transaction_id] = transaction

        self._transactions: Mapping[str, TransactionResponse] = MappingProxyType(indexed)

    def get(self, request: TransactionLookupRequest) -> TransactionLookupResult:
        """Look up a validated ID without modifying the fixture data."""

        transaction = self._transactions.get(request.transaction_id)
        if transaction is None:
            return TransactionNotFound(transaction_id=request.transaction_id)
        return transaction

    @staticmethod
    def _read_source(fixture_path: str | Path | None) -> tuple[str, str]:
        if fixture_path is None:
            fixture = resources.files("bank_ops.transactions.data").joinpath(
                "transactions.json"
            )
            source_name = str(fixture)
            try:
                return fixture.read_text(encoding="utf-8"), source_name
            except OSError as error:
                raise TransactionDataError(
                    f"Unable to read transaction data from {source_name}: {error}"
                ) from error

        path = Path(fixture_path)
        source_name = str(path)
        try:
            return path.read_text(encoding="utf-8"), source_name
        except OSError as error:
            raise TransactionDataError(
                f"Unable to read transaction data from {source_name}: {error}"
            ) from error

    @staticmethod
    def _validate_source(source: str, source_name: str) -> list[TransactionResponse]:
        try:
            raw_transactions = json.loads(source)
        except json.JSONDecodeError as error:
            raise TransactionDataError(
                f"Invalid JSON in transaction data {source_name} at "
                f"line {error.lineno}, column {error.colno}: {error.msg}"
            ) from error

        try:
            return _TRANSACTION_LIST.validate_python(raw_transactions)
        except ValidationError as error:
            raise TransactionDataError(
                f"Invalid transaction data in {source_name}: {error}"
            ) from error
