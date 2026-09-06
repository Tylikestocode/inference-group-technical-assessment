from __future__ import annotations

import os

import pytest

from bank_ops.retrieval.embeddings import HuggingFaceBgeEmbedder
from bank_ops.retrieval.index import FaissProcedureRetriever, build_procedure_index
from bank_ops.retrieval.models import NoRelevantProcedureResult

pytestmark = [
    pytest.mark.retrieval_integration,
    pytest.mark.skipif(
        os.environ.get("RUN_RETRIEVAL_INTEGRATION") != "1",
        reason="set RUN_RETRIEVAL_INTEGRATION=1 to load the real embedding model",
    ),
]


@pytest.fixture(scope="module")
def retriever(tmp_path_factory: pytest.TempPathFactory) -> FaissProcedureRetriever:
    index_directory = tmp_path_factory.mktemp("bge-procedure-index")
    embedder = HuggingFaceBgeEmbedder("BAAI/bge-small-en-v1.5")
    build_procedure_index(embedder, index_directory)
    return FaissProcedureRetriever.load(
        embedder, index_directory, minimum_relevance_score=0.6
    )


@pytest.mark.parametrize(
    ("query", "expected_procedure_id"),
    [
        (
            (
                "A transaction screening result identified a possible sanctions match "
                "to a restricted party."
            ),
            "PROC-001",
        ),
        (
            (
                "A transaction is held because its high-value unusual activity and "
                "high risk require review."
            ),
            "PROC-002",
        ),
        (
            "Beneficiary details do not match the payment instruction.",
            "PROC-003",
        ),
        (
            (
                "Verified information is incomplete and conflicting, so the correct "
                "next step is uncertain and needs manual review."
            ),
            "PROC-004",
        ),
    ],
)
def test_expected_query_returns_intended_procedure_first(
    retriever: FaissProcedureRetriever,
    query: str,
    expected_procedure_id: str,
) -> None:
    results = retriever.search(query, limit=3)

    assert isinstance(results, list)
    assert results[0].procedure_id == expected_procedure_id


def test_txn_0212_hold_reason_returns_complete_beneficiary_citation(
    retriever: FaissProcedureRetriever,
) -> None:
    results = retriever.search(
        "Beneficiary details do not match the payment instruction", limit=1
    )

    assert isinstance(results, list)
    result = results[0]

    assert result.procedure_id == "PROC-003"
    assert result.title == "Beneficiary Verification"
    assert result.version == "1.0"
    assert result.section == (
        "Beneficiary details do not match the payment instruction"
    )
    assert result.source_file == "PROC-003-beneficiary-verification.md"


def test_unrelated_query_returns_no_relevant_procedure(
    retriever: FaissProcedureRetriever,
) -> None:
    result = retriever.search("How do I reset my online banking password?")

    assert isinstance(result, NoRelevantProcedureResult)
    assert result.highest_relevance_score is not None
    assert result.highest_relevance_score < result.minimum_relevance_score
