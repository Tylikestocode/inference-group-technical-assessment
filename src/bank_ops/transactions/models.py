"""Pydantic contracts for the read-only transaction service."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    model_validator,
)

TransactionId = Annotated[str, Field(pattern=r"^TXN-\d{4}$")]
Money = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class ContractModel(BaseModel):
    """Base contract that rejects drift and cannot be mutated after validation."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class TransactionStatus(StrEnum):
    """Statuses represented by the synthetic transaction service."""

    HELD = "held"
    PENDING = "pending"
    COMPLETED = "completed"


class RiskLevel(StrEnum):
    """Risk classifications represented by the synthetic records."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TransactionChannel(StrEnum):
    """Channels represented by the synthetic records."""

    BRANCH = "branch"
    MOBILE = "mobile"
    ONLINE_BANKING = "online_banking"


class ErrorCode(StrEnum):
    """Stable error codes exposed by the transaction contract."""

    TRANSACTION_NOT_FOUND = "transaction_not_found"
    TRANSACTION_SERVICE_UNAVAILABLE = "transaction_service_unavailable"


class TransactionLookupRequest(ContractModel):
    """Validated input to a transaction lookup."""

    transaction_id: TransactionId


class TransactionResponse(ContractModel):
    """A validated fictional transaction returned by the service."""

    transaction_id: TransactionId
    status: TransactionStatus
    amount: Money
    currency: CurrencyCode
    risk_level: RiskLevel
    hold_reason: Annotated[str, Field(min_length=1)] | None
    channel: TransactionChannel
    timestamp: AwareDatetime

    @model_validator(mode="after")
    def held_transaction_has_reason(self) -> TransactionResponse:
        """Reject held transactions that have no meaningful hold reason."""

        if self.status is TransactionStatus.HELD and (
            self.hold_reason is None or not self.hold_reason.strip()
        ):
            raise ValueError("held transactions must include a hold reason")
        return self

    @field_serializer("amount", when_used="json")
    def serialize_amount(self, value: Decimal) -> str:
        """Preserve the exact financial value in JSON representations."""

        return format(value, ".2f")


class TransactionNotFound(ContractModel):
    """Specific result returned when no fixture matches a valid ID."""

    error: Literal[ErrorCode.TRANSACTION_NOT_FOUND] = ErrorCode.TRANSACTION_NOT_FOUND
    transaction_id: TransactionId
    message: Literal["Transaction was not found."] = "Transaction was not found."


class TransactionServiceUnavailable(ContractModel):
    """Safe result returned when the transaction API cannot answer reliably."""

    error: Literal[ErrorCode.TRANSACTION_SERVICE_UNAVAILABLE] = (
        ErrorCode.TRANSACTION_SERVICE_UNAVAILABLE
    )
    transaction_id: TransactionId
    message: Literal["Transaction service is unavailable."] = (
        "Transaction service is unavailable."
    )


class HealthResponse(ContractModel):
    """Lightweight service health contract used by Docker Compose."""

    status: Literal["ok"] = "ok"


type TransactionLookupResult = TransactionResponse | TransactionNotFound
type TransactionClientResult = TransactionLookupResult | TransactionServiceUnavailable
