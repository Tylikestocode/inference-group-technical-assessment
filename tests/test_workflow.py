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
from bank_ops.model_serving import (
    ExplanationGenerationFailure,
    ExplanationRequest,
    GeneratedExplanation,
    InvalidModelResponse,
    ModelTimedOut,
    ModelUnavailable,
)
from bank_ops.policies import ADVISORY_ONLY_WARNING
from bank_ops.retrieval import NoRelevantProcedureResult, ProcedureSearchResult
from bank_ops.transactions import (
    TransactionClientResult,
    TransactionLookupRequest,
    TransactionNotFound,
    TransactionResponse,
    TransactionServiceUnavailable,
)
from bank_ops.workflow import (
    MODEL_FALLBACK_WARNING,
    NO_RELEVANT_PROCEDURE_WARNING,
    TRANSACTION_NOT_FOUND_WARNING,
    TRANSACTION_SERVICE_WARNING,
    UNSAFE_MODEL_OUTPUT_WARNING,
    InvestigationWorkflow,
)

TRACE_ID = UUID("12345678-1234-5678-1234-567812345678")


class RecordingTransactionClient:
    def __init__(
        self,
        events: list[str],
        response: TransactionClientResult | None = None,
    ) -> None:
        self.events = events
        self.response = response or _transaction()
        self.requests: list[TransactionLookupRequest] = []

    def get(self, request: TransactionLookupRequest) -> TransactionClientResult:
        self.events.append("lookup_transaction")
        self.requests.append(request)
        return self.response


class RecordingRetriever:
    def __init__(
        self,
        events: list[str],
        response: list[ProcedureSearchResult] | NoRelevantProcedureResult | None = None,
    ) -> None:
        self.events = events
        self.response = response
        self.queries: list[tuple[str, int]] = []

    def search(
        self, query: str, limit: int = 3
    ) -> list[ProcedureSearchResult] | NoRelevantProcedureResult:
        self.events.append("retrieve_procedures")
        self.queries.append((query, limit))
        if self.response is not None:
            return self.response
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


class FailingExplanationGenerator:
    def __init__(
        self,
        events: list[str],
        failure: ExplanationGenerationFailure,
    ) -> None:
        self.events = events
        self.failure = failure
        self.requests: list[ExplanationRequest] = []

    def generate(self, request: ExplanationRequest) -> ExplanationGenerationFailure:
        self.events.append("generate_explanation")
        self.requests.append(request)
        return self.failure


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


def test_model_text_with_unpermitted_action_is_rejected() -> None:
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

    assert "Release" not in response.explanation
    assert response.outcome is InvestigationOutcome.MODEL_FALLBACK_USED
    assert (
        response.recommended_next_action
        is AllowedNextAction.VERIFY_BENEFICIARY_AND_REFER
    )
    assert response.human_review_required is True
    assert response.escalation_destination is EscalationDestination.PAYMENTS_OPERATIONS
    assert response.warnings == (
        ADVISORY_ONLY_WARNING,
        MODEL_FALLBACK_WARNING,
        UNSAFE_MODEL_OUTPUT_WARNING,
    )


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
        ("lookup_transaction", "__end__"),
        ("retrieve_procedures", "apply_decision_rules"),
        ("retrieve_procedures", "__end__"),
        ("apply_decision_rules", "generate_explanation"),
        ("generate_explanation", "assemble_and_validate_response"),
        ("generate_explanation", "build_model_fallback"),
        ("build_model_fallback", "assemble_and_validate_response"),
        ("assemble_and_validate_response", "__end__"),
    }


@pytest.mark.parametrize(
    "failure",
    [ModelUnavailable(), ModelTimedOut(), InvalidModelResponse()],
    ids=lambda failure: failure.failure_type,
)
def test_model_failure_uses_the_deterministic_fallback_route(
    failure: ExplanationGenerationFailure,
) -> None:
    events: list[str] = []
    generator = FailingExplanationGenerator(events, failure)
    workflow = InvestigationWorkflow(
        RecordingTransactionClient(events),
        RecordingRetriever(events),
        generator,
        trace_id_factory=lambda: TRACE_ID,
    )

    response = workflow(InvestigationRequest.from_question("Why is TXN-0212 held?"))

    assert events == [
        "lookup_transaction",
        "retrieve_procedures",
        "generate_explanation",
    ]
    assert len(generator.requests) == 1
    assert response.explanation == (
        "TXN-0212 has verified status held. Model-generated wording is "
        "unavailable; use the cited procedure and predetermined next action "
        "shown below."
    )
    assert response.transaction == _transaction()
    assert response.outcome is InvestigationOutcome.MODEL_FALLBACK_USED
    assert response.procedure.procedure_id == "PROC-003"
    assert (
        response.recommended_next_action
        is AllowedNextAction.VERIFY_BENEFICIARY_AND_REFER
    )
    assert response.human_review_required is True
    assert response.escalation_destination is EscalationDestination.PAYMENTS_OPERATIONS
    assert response.warnings == (ADVISORY_ONLY_WARNING, MODEL_FALLBACK_WARNING)


@pytest.mark.parametrize(
    ("client_result", "expected_outcome", "expected_action", "expected_warning"),
    [
        (
            TransactionNotFound(transaction_id="TXN-0212"),
            InvestigationOutcome.TRANSACTION_NOT_FOUND,
            AllowedNextAction.CONFIRM_TRANSACTION_ID_AND_REFER,
            TRANSACTION_NOT_FOUND_WARNING,
        ),
        (
            TransactionServiceUnavailable(transaction_id="TXN-0212"),
            InvestigationOutcome.TRANSACTION_SERVICE_UNAVAILABLE,
            AllowedNextAction.RETRY_LOOKUP_OR_REFER,
            TRANSACTION_SERVICE_WARNING,
        ),
    ],
)
def test_lookup_failures_return_named_outcomes_without_calling_other_services(
    client_result: TransactionClientResult,
    expected_outcome: InvestigationOutcome,
    expected_action: AllowedNextAction,
    expected_warning: str,
) -> None:
    events: list[str] = []
    retriever = RecordingRetriever(events)
    generator = RecordingExplanationGenerator(events, "Must not be called.")
    workflow = InvestigationWorkflow(
        RecordingTransactionClient(events, client_result),
        retriever,
        generator,
        trace_id_factory=lambda: TRACE_ID,
    )

    response = workflow(InvestigationRequest.from_question("Why is TXN-0212 held?"))

    assert events == ["lookup_transaction"]
    assert response.outcome is expected_outcome
    assert response.requested_transaction_id == "TXN-0212"
    assert response.transaction is None
    assert response.procedure is None
    assert response.recommended_next_action is expected_action
    assert response.human_review_required is True
    assert response.escalation_destination is EscalationDestination.OPERATIONS_CONTROL
    assert response.warnings == (ADVISORY_ONLY_WARNING, expected_warning)
    assert retriever.queries == []
    assert generator.requests == []


def test_no_relevant_procedure_preserves_facts_and_skips_the_model() -> None:
    events: list[str] = []
    retriever = RecordingRetriever(
        events,
        NoRelevantProcedureResult(
            minimum_relevance_score=0.6,
            highest_relevance_score=0.2,
        ),
    )
    generator = RecordingExplanationGenerator(events, "Must not be called.")
    workflow = InvestigationWorkflow(
        RecordingTransactionClient(events),
        retriever,
        generator,
        trace_id_factory=lambda: TRACE_ID,
    )

    response = workflow(InvestigationRequest.from_question("Why is TXN-0212 held?"))

    assert events == ["lookup_transaction", "retrieve_procedures"]
    assert response.outcome is InvestigationOutcome.NO_RELEVANT_PROCEDURE
    assert response.transaction == _transaction()
    assert response.procedure is None
    assert response.recommended_next_action is AllowedNextAction.REFER_MANUAL_REVIEW
    assert response.human_review_required is True
    assert response.escalation_destination is EscalationDestination.OPERATIONS_CONTROL
    assert response.warnings == (
        ADVISORY_ONLY_WARNING,
        NO_RELEVANT_PROCEDURE_WARNING,
    )
    assert generator.requests == []


def test_mismatched_api_response_returns_safe_failure_before_retrieval() -> None:
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

    response = workflow(InvestigationRequest.from_question("Why is TXN-0212 held?"))

    assert response.outcome is InvestigationOutcome.TRANSACTION_SERVICE_UNAVAILABLE
    assert response.transaction is None
    assert response.procedure is None
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
