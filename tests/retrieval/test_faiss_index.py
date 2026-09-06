from __future__ import annotations

import json
import shutil
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

from bank_ops.retrieval.index import (
    INDEX_FILENAME,
    MANIFEST_FILENAME,
    FaissProcedureRetriever,
    ProcedureIndexError,
    build_procedure_index,
)
from bank_ops.retrieval.models import NoRelevantProcedureResult

CORPUS_DIRECTORY = (
    Path(__file__).parents[2] / "src" / "bank_ops" / "retrieval" / "data" / "procedures"
)


class DeterministicEmbedder:
    """Small semantic stand-in that keeps unit tests local and repeatable."""

    def __init__(self, model_name: str = "deterministic-test-embedder") -> None:
        self.model_name = model_name

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        return np.stack([self._vector(text) for text in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self._vector(text)

    @staticmethod
    def _vector(text: str) -> np.ndarray:
        lowered = text.lower()
        return np.asarray(
            [
                float("beneficiary" in lowered or "payment instruction" in lowered),
                float("sanction" in lowered),
                float("high-value" in lowered or "unusual" in lowered),
                float("manual review" in lowered),
                0.1,
            ],
            dtype=np.float32,
        )


def test_build_load_and_search_returns_complete_ranked_citation(
    tmp_path: Path,
) -> None:
    embedder = DeterministicEmbedder()

    chunk_count = build_procedure_index(embedder, tmp_path)
    retriever = FaissProcedureRetriever.load(embedder, tmp_path)
    results = retriever.search(
        "Beneficiary details do not match the payment instruction", limit=2
    )

    assert isinstance(results, list)
    assert chunk_count == 13
    assert (tmp_path / INDEX_FILENAME).is_file()
    assert (tmp_path / MANIFEST_FILENAME).is_file()
    assert len(results) == 2
    assert results[0].procedure_id == "PROC-003"
    assert results[0].title == "Beneficiary Verification"
    assert results[0].version == "1.0"
    assert results[0].section == (
        "Beneficiary details do not match the payment instruction"
    )
    assert results[0].source_file == "PROC-003-beneficiary-verification.md"
    assert "direct match" in results[0].text
    assert results[0].relevance_score >= results[1].relevance_score


def test_rebuild_replaces_artifacts_with_an_immediately_usable_index(
    tmp_path: Path,
) -> None:
    embedder = DeterministicEmbedder()

    build_procedure_index(embedder, tmp_path)
    first_index = (tmp_path / INDEX_FILENAME).read_bytes()
    build_procedure_index(embedder, tmp_path)

    retriever = FaissProcedureRetriever.load(embedder, tmp_path)
    results = retriever.search("sanctions screening", limit=1)

    assert (tmp_path / INDEX_FILENAME).read_bytes() == first_index
    assert isinstance(results, list)
    assert results[0].procedure_id == "PROC-001"


@pytest.mark.parametrize(("query", "limit"), [("", 1), ("   ", 1), ("valid", 0)])
def test_search_rejects_invalid_inputs(tmp_path: Path, query: str, limit: int) -> None:
    embedder = DeterministicEmbedder()
    build_procedure_index(embedder, tmp_path)
    retriever = FaissProcedureRetriever.load(embedder, tmp_path)

    with pytest.raises(ValueError):
        retriever.search(query, limit)


def test_load_rejects_index_and_manifest_row_mismatch(tmp_path: Path) -> None:
    embedder = DeterministicEmbedder()
    build_procedure_index(embedder, tmp_path)
    manifest_path = tmp_path / MANIFEST_FILENAME
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["chunks"].pop()
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ProcedureIndexError, match="row count"):
        FaissProcedureRetriever.load(embedder, tmp_path)


def test_manifest_records_embedding_model_and_source_fingerprint(
    tmp_path: Path,
) -> None:
    embedder = DeterministicEmbedder()

    build_procedure_index(embedder, tmp_path)
    payload = json.loads((tmp_path / MANIFEST_FILENAME).read_text(encoding="utf-8"))

    assert payload["schema_version"] == 2
    assert payload["embedding_model"] == embedder.model_name
    assert len(payload["source_fingerprint"]) == 64
    assert set(payload["source_fingerprint"]) <= set("0123456789abcdef")


def test_search_returns_explicit_no_relevant_procedure_result(
    tmp_path: Path,
) -> None:
    embedder = DeterministicEmbedder()
    build_procedure_index(embedder, tmp_path)
    retriever = FaissProcedureRetriever.load(
        embedder, tmp_path, minimum_relevance_score=0.6
    )

    result = retriever.search("How do I reset my online banking password?")

    assert isinstance(result, NoRelevantProcedureResult)
    assert result == NoRelevantProcedureResult(
        minimum_relevance_score=0.6,
        highest_relevance_score=result.highest_relevance_score,
    )
    assert result.highest_relevance_score is not None
    assert result.highest_relevance_score < result.minimum_relevance_score
    assert "human review" in result.message


def test_search_includes_results_at_the_minimum_relevance_boundary(
    tmp_path: Path,
) -> None:
    embedder = DeterministicEmbedder()
    build_procedure_index(embedder, tmp_path)
    unrestricted = FaissProcedureRetriever.load(
        embedder, tmp_path, minimum_relevance_score=0
    ).search("sanctions screening", limit=1)
    assert isinstance(unrestricted, list)

    result = FaissProcedureRetriever.load(
        embedder,
        tmp_path,
        minimum_relevance_score=unrestricted[0].relevance_score,
    ).search("sanctions screening", limit=1)

    assert isinstance(result, list)
    assert result[0].procedure_id == "PROC-001"


def test_load_rejects_an_incompatible_embedding_model(tmp_path: Path) -> None:
    build_procedure_index(DeterministicEmbedder("model-a"), tmp_path)

    with pytest.raises(
        ProcedureIndexError, match=r"incompatible.*model-a.*model-b.*build-index"
    ):
        FaissProcedureRetriever.load(DeterministicEmbedder("model-b"), tmp_path)


def test_load_rejects_an_index_when_source_documents_changed(
    tmp_path: Path,
) -> None:
    corpus_directory = tmp_path / "corpus"
    index_directory = tmp_path / "index"
    shutil.copytree(CORPUS_DIRECTORY, corpus_directory)
    embedder = DeterministicEmbedder()
    build_procedure_index(embedder, index_directory, corpus_directory)
    changed_procedure = corpus_directory / "PROC-001-sanctions-screening.md"
    changed_procedure.write_text(
        changed_procedure.read_text(encoding="utf-8") + "\nChanged.\n",
        encoding="utf-8",
    )

    with pytest.raises(ProcedureIndexError, match=r"stale.*build-index"):
        FaissProcedureRetriever.load(
            embedder, index_directory, corpus_directory=corpus_directory
        )


def test_load_reports_missing_artifacts_with_recovery_instruction(
    tmp_path: Path,
) -> None:
    with pytest.raises(ProcedureIndexError, match=r"missing.*build-index"):
        FaissProcedureRetriever.load(DeterministicEmbedder(), tmp_path)


def test_load_rejects_legacy_manifest_with_recovery_instruction(
    tmp_path: Path,
) -> None:
    embedder = DeterministicEmbedder()
    build_procedure_index(embedder, tmp_path)
    manifest_path = tmp_path / MANIFEST_FILENAME
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["schema_version"] = 1
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ProcedureIndexError) as raised:
        FaissProcedureRetriever.load(embedder, tmp_path)

    assert "invalid or incompatible" in str(raised.value)
    assert "build-index" in str(raised.value)


@pytest.mark.parametrize("minimum_relevance_score", [-0.01, 1.01, float("nan")])
def test_retriever_rejects_invalid_minimum_relevance_score(
    tmp_path: Path, minimum_relevance_score: float
) -> None:
    embedder = DeterministicEmbedder()
    build_procedure_index(embedder, tmp_path)

    with pytest.raises(ValueError, match="between 0 and 1"):
        FaissProcedureRetriever.load(
            embedder,
            tmp_path,
            minimum_relevance_score=minimum_relevance_score,
        )
