"""HTTP API for read-only transaction lookup."""

from __future__ import annotations

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

from bank_ops.transactions.models import (
    TransactionId,
    TransactionLookupRequest,
    TransactionNotFound,
    TransactionResponse,
)
from bank_ops.transactions.repository import (
    JsonTransactionRepository,
    TransactionRepository,
)


def create_app(repository: TransactionRepository | None = None) -> FastAPI:
    """Create the transaction API with an injectable read-only repository."""

    transaction_repository = repository or JsonTransactionRepository()
    app = FastAPI(title="Transaction Lookup API", version="0.1.0")

    @app.get(
        "/transactions/{transaction_id}",
        response_model=TransactionResponse,
        responses={
            404: {
                "model": TransactionNotFound,
                "description": "Transaction not found",
            }
        },
    )
    def get_transaction(
        transaction_id: TransactionId,
    ) -> TransactionResponse | Response:
        """Return a synthetic transaction or the typed not-found response."""

        request = TransactionLookupRequest(transaction_id=transaction_id)
        result = transaction_repository.get(request)
        if isinstance(result, TransactionNotFound):
            return JSONResponse(
                status_code=404,
                content=result.model_dump(mode="json"),
            )
        return result

    return app


app = create_app()
