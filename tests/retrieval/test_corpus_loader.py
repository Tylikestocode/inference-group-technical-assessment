from pathlib import Path

import pytest

from bank_ops.retrieval.corpus import ProcedureCorpusError, load_procedure_chunks


def test_packaged_corpus_is_split_into_stable_section_chunks() -> None:
    chunks = load_procedure_chunks()

    assert len(chunks) == 13
    assert chunks[0].procedure_id == "PROC-001"
    assert chunks[0].section == "When this procedure applies"
    assert chunks[-1].procedure_id == "PROC-004"
    assert chunks[-1].section == "Escalation"

    beneficiary_match = next(
        chunk
        for chunk in chunks
        if chunk.section == "Beneficiary details do not match the payment instruction"
    )
    assert beneficiary_match.title == "Beneficiary Verification"
    assert beneficiary_match.version == "1.0"
    assert beneficiary_match.owner == "Fictional Payments Operations"
    assert beneficiary_match.source_file == "PROC-003-beneficiary-verification.md"
    assert "direct match" in beneficiary_match.text
    assert beneficiary_match.section in beneficiary_match.embedding_text


def test_missing_document_metadata_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "incomplete.md").write_text(
        "# Incomplete\n\n- Procedure ID: PROC-999\n\n## Actions\n\nDo something.\n",
        encoding="utf-8",
    )

    with pytest.raises(ProcedureCorpusError, match="missing metadata"):
        load_procedure_chunks(tmp_path)


def test_duplicate_procedure_ids_are_rejected(tmp_path: Path) -> None:
    template = """# {title}

- Procedure ID: PROC-999
- Version: 1.0
- Owner: Fictional Operations
- Data label: Fictional assessment data

## Actions

Keep the transaction held.
"""
    (tmp_path / "first.md").write_text(template.format(title="First"), encoding="utf-8")
    (tmp_path / "second.md").write_text(
        template.format(title="Second"), encoding="utf-8"
    )

    with pytest.raises(ProcedureCorpusError, match="Duplicate procedure ID"):
        load_procedure_chunks(tmp_path)
