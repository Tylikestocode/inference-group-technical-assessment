import json
from collections.abc import Callable
from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError

from bank_ops.model_serving import ExplanationRequest, GeneratedExplanation
from bank_ops.model_serving.ollama import OllamaExplanationGenerator
from bank_ops.transactions.models import TransactionResponse


def explanation_request() -> ExplanationRequest:
    return ExplanationRequest(
        transaction=TransactionResponse(
            transaction_id="TXN-0212",
            status="held",
            amount=Decimal("12500.00"),
            currency="ZAR",
            risk_level="medium",
            hold_reason=("Beneficiary details do not match the payment instruction."),
            channel="online_banking",
            timestamp="2026-08-21T09:30:00Z",
        ),
        procedure_text="PROC-003 says to verify the beneficiary information.",
        next_action="Keep the transaction held and refer it to Payments Operations.",
    )


def client_for(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(
        base_url="http://model-provider.test:11434",
        timeout=17.5,
        transport=httpx.MockTransport(handler),
    )


def generator(client: httpx.Client) -> OllamaExplanationGenerator:
    return OllamaExplanationGenerator(
        client=client,
        model="replaceable-model",
        temperature=0.2,
        max_tokens=96,
        seed=7,
    )


def test_adapter_sends_only_approved_context_and_structured_configuration() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["timeout"] = request.extensions["timeout"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "explanation": (
                                "TXN-0212 is held because its beneficiary details "
                                "do not match the payment instruction."
                            )
                        }
                    ),
                },
                "done": True,
            },
        )

    with client_for(handler) as client:
        result = generator(client).generate(explanation_request())

    assert result.explanation.startswith("TXN-0212 is held")
    assert captured["url"] == "http://model-provider.test:11434/api/chat"
    assert captured["timeout"] == {
        "connect": 17.5,
        "read": 17.5,
        "write": 17.5,
        "pool": 17.5,
    }

    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "replaceable-model"
    assert body["stream"] is False
    assert body["think"] is False
    assert body["format"] == GeneratedExplanation.model_json_schema()
    assert body["options"] == {
        "temperature": 0.2,
        "num_predict": 96,
        "seed": 7,
    }
    assert "tools" not in body

    messages = body["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert "do not infer missing" in messages[0]["content"].lower()
    assert "decide whether escalation" in messages[0]["content"].lower()

    supplied_context = json.loads(messages[1]["content"])
    assert supplied_context == {
        "verified_transaction_facts": {
            "transaction_id": "TXN-0212",
            "status": "held",
            "amount": "12500.00",
            "currency": "ZAR",
            "risk_level": "medium",
            "hold_reason": (
                "Beneficiary details do not match the payment instruction."
            ),
            "channel": "online_banking",
            "timestamp": "2026-08-21T09:30:00+00:00",
        },
        "retrieved_procedure_text": (
            "PROC-003 says to verify the beneficiary information."
        ),
        "predetermined_next_action": (
            "Keep the transaction held and refer it to Payments Operations."
        ),
    }


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        json.dumps({"explanation": ""}),
        json.dumps({"explanation": "Valid.", "decision": "release"}),
    ],
)
def test_adapter_rejects_invalid_structured_content(content: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": content}})

    with client_for(handler) as client, pytest.raises(ValidationError):
        generator(client).generate(explanation_request())


def test_adapter_preserves_http_failures_for_the_workflow_failure_task() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "model unavailable"})

    with client_for(handler) as client, pytest.raises(httpx.HTTPStatusError):
        generator(client).generate(explanation_request())
