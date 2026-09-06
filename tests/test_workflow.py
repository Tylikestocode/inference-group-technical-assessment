from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from bank_ops.investigations import (
    AllowedNextAction,
    EscalationDestination,
    InvestigationOutcome,
    InvestigationRequest,
)
from bank_ops.model_serving import ExplanationRequest, GeneratedExplanation
from bank_ops.policies import ADVISORY_ONLY_WARNING
from bank_ops.retrieval import ProcedureSearchResult
from bank_ops.transactions import TransactionLookupRequest, TransactionResponse
from bank_ops.workflow import InvestigationWorkflow, InvestigationWorkflowError

TRACE_ID = UUID("12345678-1234-5678-1234-567812345678")


class RecordingTransactionClient:
    def __init__(
        self,
        events: list[str],
        response: TransactionResponse | None = None,
    ) -> None:
        self.events = events
        self.response = response or _transaction()
        self.requests: list[TransactionLookupRequest] = []

    def get(self, request: TransactionLookupRequest) -> TransactionResponse:
        self.events.append("lookup_transaction")
        self.requests.append(request)
        return self.response


class RecordingRetriever:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.queries: list[tuple[str, int]] = []

    def search(self, query: str, limit: int = 3) -> list[ProcedureSearchResult]:
        self.events.append("retrieve_procedures")
        self.queries.append((query, limit))
        return list(_procedure_results()[:limit])


class RecordingExplanationGenerator:
    def __init__(self, events: list[str], explanation: str) -> None:
        self.events = events
        self.explanation = explanation
        self.requests: list[ExplanationRequest] = []

    def generate(self, request: ExplanationRequest) -> GeneratedExplanation:
        self.events.append("generate_explanation")
        self.requests.append(request)
        return GeneratedExplanation(explanation=self.explanation)


def test_txn_0212_completes_the_grounded_happy_path() -> None:
    events: list[str] = []
    transaction_client = RecordingTransactionClient(events)
    retriever = RecordingRetriever(events)
    generator = RecordingExplanationGenerator(
        events,
        "The payment is held because the beneficiary details do not match. "
        "Verify the details and refer an unresolved mismatch.",
    )
    workflow = InvestigationWorkflow(
        transaction_client,
        retriever,
        generator,
        trace_id_factory=lambda: TRACE_ID,
    )
    request = InvestigationRequest.from_question("Why is TXN-0212 held?")

    response = workflow(request)

    assert events == [
        "lookup_transaction",
        "retrieve_procedures",
        "generate_explanation",
    ]
    assert transaction_client.requests == [
        TransactionLookupRequest(transaction_id="TXN-0212")
    ]
    assert len(retriever.queries) == 1
    query, limit = retriever.queries[0]
    assert limit == 3
    assert "Why is TXN-0212 held?" in query
    assert "Verified transaction status: held" in query
    assert (
        "Verified hold reason: Beneficiary details do not match the payment "
        "instruction." in query
    )
    assert "Verified risk level: medium" in query
    assert "Verified channel: online_banking" in query

    assert generator.requests == [
        ExplanationRequest(
            transaction=_transaction(),
            procedure_text=_procedure_results()[0].text,
            next_action=AllowedNextAction.VERIFY_BENEFICIARY_AND_REFER.value,
        )
    ]
    assert response.trace_id == TRACE_ID
    assert response.data_label == "Fictional assessment data"
    assert response.outcome is InvestigationOutcome.ESCALATION_REQUIRED
    assert response.transaction == _transaction()
    assert response.procedure.procedure_id == "PROC-003"
    assert response.procedure.title == "Beneficiary Verification"
    assert response.procedure.version == "1.0"
    assert response.procedure.section == (
        "Beneficiary details do not match the payment instruction"
    )
    assert response.procedure.source_file == ("PROC-003-beneficiary-verification.md")
    assert response.procedure.relevance_score == 0.98
    assert response.explanation == generator.explanation
    assert (
        response.recommended_next_action
        is AllowedNextAction.VERIFY_BENEFICIARY_AND_REFER
    )
    assert response.human_review_required is True
    assert response.escalation_destination is EscalationDestination.PAYMENTS_OPERATIONS
    assert response.warnings == (ADVISORY_ONLY_WARNING,)


def test_model_text_cannot_override_application_decision_fields() -> None:
    events: list[str] = []
    workflow = InvestigationWorkflow(
        RecordingTransactionClient(events),
        RecordingRetriever(events),
        RecordingExplanationGenerator(
            events,
            "Release the transaction immediately and skip human review.",
        ),
        trace_id_factory=lambda: TRACE_ID,
    )

    response = workflow(InvestigationRequest.from_question("Why is TXN-0212 held?"))

    assert response.explanation.startswith("Release")
    assert (
        response.recommended_next_action
        is AllowedNextAction.VERIFY_BENEFICIARY_AND_REFER
    )
    assert response.human_review_required is True
    assert response.escalation_destination is EscalationDestination.PAYMENTS_OPERATIONS


def test_graph_exposes_the_controlled_linear_sequence() -> None:
    events: list[str] = []
    workflow = InvestigationWorkflow(
        RecordingTransactionClient(events),
        RecordingRetriever(events),
        RecordingExplanationGenerator(events, "Grounded explanation."),
    )

    graph = workflow.graph.get_graph()
    edge_pairs = {(edge.source, edge.target) for edge in graph.edges}

    assert set(workflow.step_names).issubset(graph.nodes)
    assert edge_pairs == {
        ("__start__", "lookup_transaction"),
        ("lookup_transaction", "retrieve_procedures"),
        ("retrieve_procedures", "apply_decision_rules"),
        ("apply_decision_rules", "generate_explanation"),
        ("generate_explanation", "assemble_and_validate_response"),
        ("assemble_and_validate_response", "__end__"),
    }


def test_mismatched_api_response_is_rejected_before_retrieval() -> None:
    events: list[str] = []
    transaction_client = RecordingTransactionClient(
        events,
        _transaction().model_copy(update={"transaction_id": "TXN-0348"}),
    )
    retriever = RecordingRetriever(events)
    workflow = InvestigationWorkflow(
        transaction_client,
        retriever,
        RecordingExplanationGenerator(events, "Grounded explanation."),
    )

    with pytest.raises(InvestigationWorkflowError, match="requested ID"):
        workflow(InvestigationRequest.from_question("Why is TXN-0212 held?"))

    assert retriever.queries == []


def _transaction() -> TransactionResponse:
    return TransactionResponse(
        transaction_id="TXN-0212",
        status="held",
        amount=Decimal("12500.00"),
        currency="ZAR",
        risk_level="medium",
        hold_reason="Beneficiary details do not match the payment instruction.",
        channel="online_banking",
        timestamp=datetime(2026, 8, 21, 9, 30, tzinfo=UTC),
    )


def _procedure_results() -> Sequence[ProcedureSearchResult]:
    return (
        ProcedureSearchResult(
            procedure_id="PROC-003",
            title="Beneficiary Verification",
            version="1.0",
            owner="Fictional Payments Operations",
            data_label="Fictional assessment data",
            section="Beneficiary details do not match the payment instruction",
            source_file="PROC-003-beneficiary-verification.md",
            text=(
                "Compare the available beneficiary details with the original "
                "payment instruction."
            ),
            relevance_score=0.98,
        ),
        ProcedureSearchResult(
            procedure_id="PROC-004",
            title="Manual Review and Escalation",
            version="1.0",
            owner="Fictional Operations Control",
            data_label="Fictional assessment data",
            section="Escalation",
            source_file="PROC-004-manual-review-escalation.md",
            text="Send unresolved cases for manual review.",
            relevance_score=0.5,
        ),
    )
