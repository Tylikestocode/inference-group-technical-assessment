"""Controlled LangGraph workflow for grounded transaction investigations."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, Literal, TypedDict
from uuid import UUID, uuid4

from langgraph.graph import END, START, StateGraph

from bank_ops.investigations import (
    AllowedNextAction,
    EscalationDestination,
    InvestigationDecision,
    InvestigationOutcome,
    InvestigationRequest,
    InvestigationResponse,
    ProcedureReference,
)
from bank_ops.model_serving import (
    ExplanationGenerationFailure,
    ExplanationGenerator,
    ExplanationRequest,
    GeneratedExplanation,
    InvalidModelResponse,
    ModelUnavailable,
    create_ollama_explanation_generator,
)
from bank_ops.policies import (
    ADVISORY_ONLY_WARNING,
    decide_next_action,
    manual_review_decision,
)
from bank_ops.retrieval import (
    FaissProcedureRetriever,
    HuggingFaceBgeEmbedder,
    NoRelevantProcedureResult,
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
    TransactionServiceUnavailable,
)

DEFAULT_RETRIEVAL_LIMIT = 3
MODEL_FALLBACK_WARNING = (
    "The model explanation was unavailable, so deterministic wording was used."
)
TRANSACTION_NOT_FOUND_WARNING = (
    "No transaction facts were available, so no status or reason was inferred."
)
TRANSACTION_SERVICE_WARNING = (
    "The transaction service did not provide verified facts; retry once or refer "
    "the case for human review."
)
NO_RELEVANT_PROCEDURE_WARNING = (
    "No procedure met the relevance requirement, so no specialist guidance was "
    "inferred."
)
UNSAFE_MODEL_OUTPUT_WARNING = (
    "The model output contained an unpermitted transaction action and was rejected; "
    "deterministic wording was used."
)
_PROHIBITED_MODEL_ACTIONS = re.compile(
    r"\b(?:release(?:d|s|ing)?|approv(?:e|ed|es|ing)|"
    r"reject(?:ed|s|ing)?|alter(?:ed|s|ing)?|edit(?:ed|s|ing)?|"
    r"bypass(?:ed|es|ing)?)\b",
    re.IGNORECASE,
)


class InvestigationWorkflowError(RuntimeError):
    """Raised when the workflow itself violates its validated contract."""


class InvestigationState(TypedDict, total=False):
    """Validated values passed between named workflow steps."""

    request: InvestigationRequest
    trace_id: UUID
    transaction: TransactionResponse
    search_query: str
    procedure_results: tuple[ProcedureSearchResult, ...]
    selected_procedure: ProcedureSearchResult
    decision: InvestigationDecision
    generation_failure: ExplanationGenerationFailure
    generated_explanation: GeneratedExplanation
    unsafe_model_output: bool
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
        "build_model_fallback",
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
        graph.add_node("build_model_fallback", self._build_model_fallback)
        graph.add_node(
            "assemble_and_validate_response",
            self._assemble_and_validate_response,
        )
        graph.add_edge(START, "lookup_transaction")
        graph.add_conditional_edges(
            "lookup_transaction",
            self._route_after_service_step,
            {"continue": "retrieve_procedures", "failure": END},
        )
        graph.add_conditional_edges(
            "retrieve_procedures",
            self._route_after_service_step,
            {"continue": "apply_decision_rules", "failure": END},
        )
        graph.add_edge("apply_decision_rules", "generate_explanation")
        graph.add_conditional_edges(
            "generate_explanation",
            self._route_after_generation,
            {
                "success": "assemble_and_validate_response",
                "fallback": "build_model_fallback",
            },
        )
        graph.add_edge("build_model_fallback", "assemble_and_validate_response")
        graph.add_edge("assemble_and_validate_response", END)
        return graph.compile()

    @staticmethod
    def _route_after_service_step(
        state: InvestigationState,
    ) -> Literal["continue", "failure"]:
        """Stop once a service step has produced a validated failure response."""

        if "response" in state:
            return "failure"
        return "continue"

    def _lookup_transaction(self, state: InvestigationState) -> InvestigationState:
        request = state["request"]
        try:
            result = self._transaction_client.get(
                TransactionLookupRequest(transaction_id=request.transaction_id)
            )
        except Exception:
            result = TransactionServiceUnavailable(
                transaction_id=request.transaction_id
            )
        if isinstance(result, TransactionNotFound):
            return {
                "response": self._lookup_failure_response(
                    state,
                    InvestigationOutcome.TRANSACTION_NOT_FOUND,
                    (
                        f"Transaction {request.transaction_id} was not found. No "
                        "transaction status, hold reason, or other facts were inferred."
                    ),
                    AllowedNextAction.CONFIRM_TRANSACTION_ID_AND_REFER,
                    TRANSACTION_NOT_FOUND_WARNING,
                )
            }
        if isinstance(result, TransactionServiceUnavailable):
            return {
                "response": self._lookup_failure_response(
                    state,
                    InvestigationOutcome.TRANSACTION_SERVICE_UNAVAILABLE,
                    (
                        f"Verified facts for {request.transaction_id} are unavailable "
                        "because the transaction service could not complete the lookup."
                    ),
                    AllowedNextAction.RETRY_LOOKUP_OR_REFER,
                    TRANSACTION_SERVICE_WARNING,
                )
            }
        if not isinstance(result, TransactionResponse):
            return {
                "response": self._lookup_failure_response(
                    state,
                    InvestigationOutcome.TRANSACTION_SERVICE_UNAVAILABLE,
                    (
                        f"Verified facts for {request.transaction_id} are unavailable "
                        "because the transaction service returned an invalid result."
                    ),
                    AllowedNextAction.RETRY_LOOKUP_OR_REFER,
                    TRANSACTION_SERVICE_WARNING,
                )
            }
        if result.transaction_id != request.transaction_id:
            return {
                "response": self._lookup_failure_response(
                    state,
                    InvestigationOutcome.TRANSACTION_SERVICE_UNAVAILABLE,
                    (
                        f"Verified facts for {request.transaction_id} are unavailable "
                        "because the transaction service returned a mismatched record."
                    ),
                    AllowedNextAction.RETRY_LOOKUP_OR_REFER,
                    TRANSACTION_SERVICE_WARNING,
                )
            }
        return {"transaction": result}

    def _retrieve_procedures(self, state: InvestigationState) -> InvestigationState:
        if "response" in state:
            return {}
        query = build_procedure_search_query(state["request"], state["transaction"])
        try:
            result = self._procedure_retriever.search(
                query, limit=self._retrieval_limit
            )
        except Exception:
            result = NoRelevantProcedureResult(
                minimum_relevance_score=0,
                highest_relevance_score=None,
            )
        if isinstance(result, NoRelevantProcedureResult) or not result:
            decision = manual_review_decision()
            return {
                "search_query": query,
                "response": InvestigationResponse(
                    trace_id=state["trace_id"],
                    requested_transaction_id=state["request"].transaction_id,
                    outcome=InvestigationOutcome.NO_RELEVANT_PROCEDURE,
                    transaction=state["transaction"],
                    procedure=None,
                    explanation=(
                        "Verified transaction facts are available, but no relevant "
                        "procedure was found. No procedure guidance was inferred."
                    ),
                    recommended_next_action=decision.recommended_next_action,
                    human_review_required=decision.human_review_required,
                    escalation_destination=decision.escalation_destination,
                    warnings=decision.warnings + (NO_RELEVANT_PROCEDURE_WARNING,),
                ),
            }
        results = tuple(result)
        return {
            "search_query": query,
            "procedure_results": results,
            "selected_procedure": results[0],
        }

    @staticmethod
    def _apply_decision_rules(state: InvestigationState) -> InvestigationState:
        if "response" in state:
            return {}
        return {
            "decision": decide_next_action(
                state["transaction"], state["selected_procedure"]
            )
        }

    def _generate_explanation(self, state: InvestigationState) -> InvestigationState:
        if "response" in state:
            return {}
        try:
            generated = self._explanation_generator.generate(
                ExplanationRequest(
                    transaction=state["transaction"],
                    procedure_text=state["selected_procedure"].text,
                    next_action=state["decision"].recommended_next_action.value,
                )
            )
        except Exception:
            generated = ModelUnavailable()
        if isinstance(generated, GeneratedExplanation):
            if _PROHIBITED_MODEL_ACTIONS.search(generated.explanation):
                return {
                    "generation_failure": InvalidModelResponse(),
                    "unsafe_model_output": True,
                }
            return {"generated_explanation": generated}
        if not isinstance(generated, ExplanationGenerationFailure):
            generated = InvalidModelResponse()
        return {"generation_failure": generated}

    @staticmethod
    def _route_after_generation(
        state: InvestigationState,
    ) -> Literal["success", "fallback"]:
        if "response" in state:
            return "success"
        if "generation_failure" in state:
            return "fallback"
        return "success"

    @staticmethod
    def _build_model_fallback(state: InvestigationState) -> InvestigationState:
        transaction = state["transaction"]
        explanation = (
            f"{transaction.transaction_id} has verified status "
            f"{transaction.status.value}. Model-generated wording is unavailable; "
            "use the cited procedure and predetermined next action shown below."
        )
        return {"generated_explanation": GeneratedExplanation(explanation=explanation)}

    @staticmethod
    def _assemble_and_validate_response(
        state: InvestigationState,
    ) -> InvestigationState:
        if "response" in state:
            return {}
        decision = state["decision"]
        warnings = decision.warnings
        if "generation_failure" in state:
            warnings += (MODEL_FALLBACK_WARNING,)
        if state.get("unsafe_model_output"):
            warnings += (UNSAFE_MODEL_OUTPUT_WARNING,)
        return {
            "response": InvestigationResponse(
                trace_id=state["trace_id"],
                requested_transaction_id=state["request"].transaction_id,
                outcome=(
                    InvestigationOutcome.MODEL_FALLBACK_USED
                    if "generation_failure" in state
                    else decision.outcome
                ),
                transaction=state["transaction"],
                procedure=ProcedureReference.from_search_result(
                    state["selected_procedure"]
                ),
                explanation=state["generated_explanation"].explanation,
                recommended_next_action=decision.recommended_next_action,
                human_review_required=decision.human_review_required,
                escalation_destination=decision.escalation_destination,
                warnings=warnings,
            )
        }

    @staticmethod
    def _lookup_failure_response(
        state: InvestigationState,
        outcome: InvestigationOutcome,
        explanation: str,
        action: AllowedNextAction,
        warning: str,
    ) -> InvestigationResponse:
        return InvestigationResponse(
            trace_id=state["trace_id"],
            requested_transaction_id=state["request"].transaction_id,
            outcome=outcome,
            transaction=None,
            procedure=None,
            explanation=explanation,
            recommended_next_action=action,
            human_review_required=True,
            escalation_destination=EscalationDestination.OPERATIONS_CONTROL,
            warnings=(ADVISORY_ONLY_WARNING, warning),
        )


def create_investigation_workflow(settings: Settings) -> InvestigationWorkflow:
    """Compose the controlled workflow from configured service adapters."""

    transaction_client = HttpTransactionClient(str(settings.transaction_api_url))
    embedder = HuggingFaceBgeEmbedder(settings.embedding_model)
    procedure_retriever = FaissProcedureRetriever.load(
        embedder,
        settings.procedure_index_dir,
        minimum_relevance_score=settings.minimum_relevance_score,
    )
    explanation_generator = create_ollama_explanation_generator(settings)
    return InvestigationWorkflow(
        transaction_client,
        procedure_retriever,
        explanation_generator,
    )
