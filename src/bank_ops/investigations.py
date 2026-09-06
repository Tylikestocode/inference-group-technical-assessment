"""Validated inputs for transaction investigations."""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import Field

from bank_ops.transactions.models import ContractModel, TransactionId

_TRANSACTION_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])(?i:TXN)[A-Za-z0-9_-]*(?![A-Za-z0-9_])"
)
_VALID_TRANSACTION_ID = re.compile(r"TXN-\d{4}")


class TransactionQuestionError(ValueError):
    """Raised when a question does not contain exactly one valid transaction ID."""


class InvestigationRequest(ContractModel):
    """Question and transaction ID accepted by the agent boundary."""

    question: Annotated[str, Field(min_length=1)]
    transaction_id: TransactionId

    @classmethod
    def from_question(cls, question: str) -> InvestigationRequest:
        """Extract exactly one standalone, correctly formatted transaction ID."""

        candidates = _TRANSACTION_TOKEN.findall(question)
        if not candidates:
            raise TransactionQuestionError(
                "Include exactly one transaction ID in the form TXN-0000."
            )

        if any(
            _VALID_TRANSACTION_ID.fullmatch(candidate) is None
            for candidate in candidates
        ):
            raise TransactionQuestionError(
                "Transaction IDs must use the exact format TXN-0000 "
                "(uppercase TXN and four digits)."
            )

        if len(candidates) != 1:
            raise TransactionQuestionError(
                "Include exactly one transaction ID; multiple IDs were found."
            )

        return cls(question=question, transaction_id=candidates[0])
