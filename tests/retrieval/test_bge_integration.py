from __future__ import annotations

import os
from pathlib import Path

import pytest

from bank_ops.retrieval.embeddings import HuggingFaceBgeEmbedder
from bank_ops.retrieval.index import FaissProcedureRetriever, build_procedure_index

pytestmark = [
    pytest.mark.retrieval_integration,
    pytest.mark.skipif(
        os.environ.get("RUN_RETRIEVAL_INTEGRATION") != "1",
        reason="set RUN_RETRIEVAL_INTEGRATION=1 to load the real embedding model",
    ),
]


def test_txn_0212_hold_reason_returns_beneficiary_procedure_first(
    tmp_path: Path,
) -> None:
    embedder = HuggingFaceBgeEmbedder("BAAI/bge-small-en-v1.5")
    build_procedure_index(embedder, tmp_path)

    result = FaissProcedureRetriever.load(embedder, tmp_path).search(
        "Beneficiary details do not match the payment instruction", limit=1
    )[0]

    assert result.procedure_id == "PROC-003"
    assert result.title == "Beneficiary Verification"
    assert result.version == "1.0"
    assert result.section == (
        "Beneficiary details do not match the payment instruction"
    )
    assert result.source_file == "PROC-003-beneficiary-verification.md"
