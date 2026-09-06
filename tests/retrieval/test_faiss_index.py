from __future__ import annotations

import json
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


class DeterministicEmbedder:
    """Small semantic stand-in that keeps unit tests local and repeatable."""

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
    result = retriever.search("sanctions screening", limit=1)[0]

    assert (tmp_path / INDEX_FILENAME).read_bytes() == first_index
    assert result.procedure_id == "PROC-001"


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
