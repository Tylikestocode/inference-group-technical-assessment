import re
from pathlib import Path


CORPUS_DIRECTORY = (
    Path(__file__).parents[2]
    / "src"
    / "bank_ops"
    / "retrieval"
    / "data"
    / "procedures"
)

EXPECTED_PROCEDURES = {
    "PROC-001-sanctions-screening.md": ("PROC-001", "Sanctions Screening"),
    "PROC-002-high-value-unusual-activity.md": (
        "PROC-002",
        "High-Value and Unusual Activity",
    ),
    "PROC-003-beneficiary-verification.md": (
        "PROC-003",
        "Beneficiary Verification",
    ),
    "PROC-004-manual-review-escalation.md": (
        "PROC-004",
        "Manual Review and Escalation",
    ),
}

REQUIRED_SECTIONS = {
    "When this procedure applies",
    "Advisor actions",
    "Escalation",
}

TXN_0212_HOLD_REASON = "Beneficiary details do not match the payment instruction"


def metadata_value(document: str, key: str) -> str | None:
    match = re.search(rf"^- {re.escape(key)}:\s*(.+)$", document, re.MULTILINE)
    return match.group(1).strip() if match else None


def section_titles(document: str) -> set[str]:
    return set(re.findall(r"^## (.+)$", document, re.MULTILINE))


def test_corpus_contains_exactly_the_four_expected_markdown_files() -> None:
    procedure_files = {path.name for path in CORPUS_DIRECTORY.glob("*.md")}

    assert procedure_files == EXPECTED_PROCEDURES.keys()


def test_each_procedure_has_consistent_metadata_and_sections() -> None:
    observed_ids: set[str] = set()

    for filename, (expected_id, expected_title) in EXPECTED_PROCEDURES.items():
        document = (CORPUS_DIRECTORY / filename).read_text(encoding="utf-8")

        assert document.startswith(f"# {expected_title}\n")
        assert metadata_value(document, "Procedure ID") == expected_id
        assert metadata_value(document, "Version") == "1.0"

        owner = metadata_value(document, "Owner")
        assert owner
        assert owner.startswith("Fictional ")

        assert metadata_value(document, "Data label") == "Fictional assessment data"
        assert REQUIRED_SECTIONS <= section_titles(document)
        assert "must not" in document.lower()
        assert "release" in document.lower()

        observed_ids.add(expected_id)

    assert len(observed_ids) == len(EXPECTED_PROCEDURES)


def test_txn_0212_hold_reason_has_an_unambiguous_beneficiary_section() -> None:
    beneficiary_document = (
        CORPUS_DIRECTORY / "PROC-003-beneficiary-verification.md"
    ).read_text(encoding="utf-8")
    other_documents = [
        path.read_text(encoding="utf-8")
        for path in CORPUS_DIRECTORY.glob("*.md")
        if path.name != "PROC-003-beneficiary-verification.md"
    ]

    matching_heading = f"## {TXN_0212_HOLD_REASON}"
    assert matching_heading in beneficiary_document
    assert all(matching_heading not in document for document in other_documents)
