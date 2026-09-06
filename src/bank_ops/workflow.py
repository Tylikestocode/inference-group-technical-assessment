"""Controlled LangGraph workflow for grounded transaction investigations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict
from uuid import UUID, uuid4

from langgraph.graph import END, START, StateGraph

from bank_ops.investigations import (
    InvestigationDecision,
    InvestigationRequest,
    InvestigationResponse,
    ProcedureReference,
)
from bank_ops.model_serving import (
    ExplanationGenerator,
    ExplanationRequest,
    GeneratedExplanation,
    create_ollama_explanation_generator,
)
from bank_ops.policies import decide_next_action
from bank_ops.retrieval import (
    FaissProcedureRetriever,
    HuggingFaceBgeEmbedder,
    ProcedureRetriever,
    ProcedureSearchResult,
)
from bank_ops.settings import Settings
from bank_ops.transactions import (
    HttpTransactionClient,
    TransactionClient,
    TransactionLookupRequest,
    TransactionNotFound,
    TransactionResponse,
)

DEFAULT_RETRIEVAL_LIMIT = 3


class InvestigationWorkflowError(RuntimeError):
    """Raised when the slice-two happy path cannot be completed."""


class InvestigationState(TypedDict, total=False):
    """Validated values passed between named workflow steps."""

    request: InvestigationRequest
    trace_id: UUID
    transaction: TransactionResponse
    search_query: str
    procedure_results: tuple[ProcedureSearchResult, ...]
    selected_procedure: ProcedureSearchResult
    decision: InvestigationDecision
    generated_explanation: GeneratedExplanation
    response: InvestigationResponse


TraceIdFactory = Callable[[], UUID]


def build_procedure_search_query(
    request: InvestigationRequest,
    transaction: TransactionResponse,
) -> str:
    """Combine the advisor question with only verified transaction facts."""

    return "\n".join(
        (
            f"Advisor question: {request.question}",
            f"Verified transaction status: {transaction.status.value}",
            f"Verified hold reason: {transaction.hold_reason or 'None'}",
            f"Verified risk level: {transaction.risk_level.value}",
            f"Verified channel: {transaction.channel.value}",
        )
    )


class InvestigationWorkflow:
    """Run one explicit, non-agentic investigation graph."""

    step_names = (
        "lookup_transaction",
        "retrieve_procedures",
        "apply_decision_rules",
        "generate_explanation",
        "assemble_and_validate_response",
    )

    def __init__(
        self,
        transaction_client: TransactionClient,
        procedure_retriever: ProcedureRetriever,
        explanation_generator: ExplanationGenerator,
        *,
        trace_id_factory: TraceIdFactory = uuid4,
        retrieval_limit: int = DEFAULT_RETRIEVAL_LIMIT,
    ) -> None:
        if retrieval_limit < 1:
            raise ValueError("retrieval_limit must be at least 1")
        self._transaction_client = transaction_client
        self._procedure_retriever = procedure_retriever
        self._explanation_generator = explanation_generator
        self._trace_id_factory = trace_id_factory
        self._retrieval_limit = retrieval_limit
        self._graph = self._build_graph()

    @property
    def graph(self) -> Any:
        """Expose the compiled graph for inspection and visualization."""

        return self._graph

    def __call__(self, request: InvestigationRequest) -> InvestigationResponse:
        """Run the graph for an already validated investigation request."""

        result = self._graph.invoke(
            {"request": request, "trace_id": self._trace_id_factory()}
        )
        response = result.get("response")
        if not isinstance(response, InvestigationResponse):
            raise InvestigationWorkflowError(
                "The investigation ended without a validated response"
            )
        return response

    def _build_graph(self) -> Any:
        graph = StateGraph(InvestigationState)
        graph.add_node("lookup_transaction", self._lookup_transaction)
        graph.add_node("retrieve_procedures", self._retrieve_procedures)
        graph.add_node("apply_decision_rules", self._apply_decision_rules)
        graph.add_node("generate_explanation", self._generate_explanation)
        graph.add_node(
            "assemble_and_validate_response",
            self._assemble_and_validate_response,
        )
        graph.add_edge(START, "lookup_transaction")
        graph.add_edge("lookup_transaction", "retrieve_procedures")
        graph.add_edge("retrieve_procedures", "apply_decision_rules")
        graph.add_edge("apply_decision_rules", "generate_explanation")
        graph.add_edge("generate_explanation", "assemble_and_validate_response")
        graph.add_edge("assemble_and_validate_response", END)
        return graph.compile()

    def _lookup_transaction(self, state: InvestigationState) -> InvestigationState:
        request = state["request"]
        result = self._transaction_client.get(
            TransactionLookupRequest(transaction_id=request.transaction_id)
        )
        if isinstance(result, TransactionNotFound):
            raise InvestigationWorkflowError(
                f"Transaction {request.transaction_id} was not found"
            )
        if result.transaction_id != request.transaction_id:
            raise InvestigationWorkflowError(
                "The transaction API response does not match the requested ID"
            )
        return {"transaction": result}

    def _retrieve_procedures(self, state: InvestigationState) -> InvestigationState:
        query = build_procedure_search_query(state["request"], state["transaction"])
        results = tuple(
            self._procedure_retriever.search(query, limit=self._retrieval_limit)
        )
        if not results:
            raise InvestigationWorkflowError("No procedure references were retrieved")
        return {
            "search_query": query,
            "procedure_results": results,
            "selected_procedure": results[0],
        }

    @staticmethod
    def _apply_decision_rules(state: InvestigationState) -> InvestigationState:
        return {
            "decision": decide_next_action(
                state["transaction"], state["selected_procedure"]
            )
        }

    def _generate_explanation(self, state: InvestigationState) -> InvestigationState:
        generated = self._explanation_generator.generate(
            ExplanationRequest(
                transaction=state["transaction"],
                procedure_text=state["selected_procedure"].text,
                next_action=state["decision"].recommended_next_action.value,
            )
        )
        return {"generated_explanation": generated}

    @staticmethod
    def _assemble_and_validate_response(
        state: InvestigationState,
    ) -> InvestigationState:
        decision = state["decision"]
        return {
            "response": InvestigationResponse(
                trace_id=state["trace_id"],
                outcome=decision.outcome,
                transaction=state["transaction"],
                procedure=ProcedureReference.from_search_result(
                    state["selected_procedure"]
                ),
                explanation=state["generated_explanation"].explanation,
                recommended_next_action=decision.recommended_next_action,
                human_review_required=decision.human_review_required,
                escalation_destination=decision.escalation_destination,
                warnings=decision.warnings,
            )
        }


def create_investigation_workflow(settings: Settings) -> InvestigationWorkflow:
    """Compose the happy-path workflow from configured service adapters."""

    transaction_client = HttpTransactionClient(str(settings.transaction_api_url))
    embedder = HuggingFaceBgeEmbedder(settings.embedding_model)
    procedure_retriever = FaissProcedureRetriever.load(
        embedder, settings.procedure_index_dir
    )
    explanation_generator = create_ollama_explanation_generator(settings)
    return InvestigationWorkflow(
        transaction_client,
        procedure_retriever,
        explanation_generator,
    )
