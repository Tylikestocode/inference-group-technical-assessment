"""Ollama implementation of the provider-neutral explanation boundary."""

from __future__ import annotations

import json
from typing import Final

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from bank_ops.model_serving.contracts import (
    ExplanationGenerationResult,
    ExplanationRequest,
    GeneratedExplanation,
    InvalidModelResponse,
    ModelTimedOut,
    ModelUnavailable,
)

_SYSTEM_PROMPT: Final = """\
You are a constrained writing component in a transaction investigation workflow.
Write a clear explanation using only the supplied verified transaction facts,
retrieved procedure text, and predetermined next action. Do not infer missing
facts, select or call tools, decide whether escalation is required, or change
the next action. Keep the explanation to at most three short sentences. Return
only JSON matching the supplied response schema.
"""


class _OllamaMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content: str


class _OllamaChatResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: _OllamaMessage


class OllamaExplanationGenerator:
    """Generate grounded explanations through Ollama's chat API."""

    def __init__(
        self,
        *,
        client: httpx.Client,
        model: str,
        temperature: float,
        max_tokens: int,
        seed: int,
    ) -> None:
        self._client = client
        self._model = model
        self._generation_options = {
            "temperature": temperature,
            "num_predict": max_tokens,
            "seed": seed,
        }

    def generate(self, request: ExplanationRequest) -> ExplanationGenerationResult:
        """Send approved context to Ollama and validate its structured answer."""

        try:
            response = self._client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": json.dumps(
                                self._prompt_context(request),
                                ensure_ascii=False,
                                separators=(",", ":"),
                            ),
                        },
                    ],
                    "format": GeneratedExplanation.model_json_schema(),
                    "stream": False,
                    "think": False,
                    "options": self._generation_options,
                },
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            return ModelTimedOut()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return ModelUnavailable()

        try:
            chat_response = _OllamaChatResponse.model_validate(response.json())
            return GeneratedExplanation.model_validate_json(
                chat_response.message.content
            )
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError):
            return InvalidModelResponse()

    @staticmethod
    def _prompt_context(request: ExplanationRequest) -> dict[str, object]:
        transaction = request.transaction
        return {
            "verified_transaction_facts": {
                "transaction_id": transaction.transaction_id,
                "status": transaction.status.value,
                "amount": format(transaction.amount, ".2f"),
                "currency": transaction.currency,
                "risk_level": transaction.risk_level.value,
                "hold_reason": transaction.hold_reason,
                "channel": transaction.channel.value,
                "timestamp": transaction.timestamp.isoformat(),
            },
            "retrieved_procedure_text": request.procedure_text,
            "predetermined_next_action": request.next_action,
        }
