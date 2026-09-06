"""Load the packaged Markdown procedures into section-level search chunks."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Protocol

from bank_ops.retrieval.models import ProcedureChunk

_TITLE = re.compile(r"\A#\s+(.+?)\s*$", re.MULTILINE)
_METADATA = re.compile(r"^-\s+([^:]+):\s*(.+?)\s*$", re.MULTILINE)
_SECTION = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_REQUIRED_METADATA = ("Procedure ID", "Version", "Owner", "Data label")


class _Digest(Protocol):
    def update(self, data: bytes) -> None:
        """Add bytes to the digest state."""


class ProcedureCorpusError(RuntimeError):
    """Raised when a procedure document cannot produce trustworthy chunks."""


@dataclass(frozen=True)
class ProcedureCorpusSnapshot:
    """Validated chunks and the fingerprint of their exact source documents."""

    chunks: tuple[ProcedureChunk, ...]
    source_fingerprint: str


def load_procedure_chunks(
    corpus_directory: str | Path | None = None,
) -> tuple[ProcedureChunk, ...]:
    """Load every Markdown procedure in deterministic filename order."""

    return load_procedure_corpus(corpus_directory).chunks


def load_procedure_corpus(
    corpus_directory: str | Path | None = None,
) -> ProcedureCorpusSnapshot:
    """Load and fingerprint every procedure from one consistent source snapshot."""

    directory: Traversable
    if corpus_directory is None:
        directory = resources.files("bank_ops").joinpath(
            "retrieval", "data", "procedures"
        )
    else:
        directory = Path(corpus_directory)

    try:
        procedure_files = sorted(
            (
                entry
                for entry in directory.iterdir()
                if entry.is_file() and entry.name.endswith(".md")
            ),
            key=lambda entry: entry.name,
        )
    except OSError as error:
        raise ProcedureCorpusError(
            f"Unable to inspect procedure corpus at {directory}: {error}"
        ) from error

    if not procedure_files:
        raise ProcedureCorpusError(f"No Markdown procedures found at {directory}")

    chunks: list[ProcedureChunk] = []
    fingerprint = hashlib.sha256()
    observed_ids: dict[str, str] = {}
    for procedure_file in procedure_files:
        try:
            source = procedure_file.read_bytes()
            document = source.decode("utf-8")
        except (OSError, UnicodeError) as error:
            raise ProcedureCorpusError(
                f"Unable to read procedure {procedure_file.name}: {error}"
            ) from error

        _add_fingerprint_entry(fingerprint, procedure_file.name, source)

        file_chunks = _parse_procedure(document, procedure_file.name)
        procedure_id = file_chunks[0].procedure_id
        if procedure_id in observed_ids:
            raise ProcedureCorpusError(
                f"Duplicate procedure ID {procedure_id} in {observed_ids[procedure_id]} "
                f"and {procedure_file.name}"
            )
        observed_ids[procedure_id] = procedure_file.name
        chunks.extend(file_chunks)

    return ProcedureCorpusSnapshot(
        chunks=tuple(chunks), source_fingerprint=fingerprint.hexdigest()
    )


def _add_fingerprint_entry(
    fingerprint: _Digest, source_file: str, source: bytes
) -> None:
    """Add one length-delimited filename and document to a corpus digest."""

    filename = source_file.encode("utf-8")
    fingerprint.update(len(filename).to_bytes(8, "big"))
    fingerprint.update(filename)
    fingerprint.update(len(source).to_bytes(8, "big"))
    fingerprint.update(source)


def _parse_procedure(document: str, source_file: str) -> tuple[ProcedureChunk, ...]:
    title_match = _TITLE.search(document)
    if title_match is None:
        raise ProcedureCorpusError(f"Procedure {source_file} has no level-one title")

    section_matches = list(_SECTION.finditer(document))
    if not section_matches:
        raise ProcedureCorpusError(f"Procedure {source_file} has no level-two sections")

    metadata_region = document[title_match.end() : section_matches[0].start()]
    metadata = {
        match.group(1).strip(): match.group(2).strip()
        for match in _METADATA.finditer(metadata_region)
    }
    missing = [key for key in _REQUIRED_METADATA if not metadata.get(key)]
    if missing:
        raise ProcedureCorpusError(
            f"Procedure {source_file} is missing metadata: {', '.join(missing)}"
        )

    chunks: list[ProcedureChunk] = []
    for position, section_match in enumerate(section_matches):
        next_start = (
            section_matches[position + 1].start()
            if position + 1 < len(section_matches)
            else len(document)
        )
        section_text = document[section_match.end() : next_start].strip()
        if not section_text:
            raise ProcedureCorpusError(
                f"Procedure {source_file} has an empty section "
                f"{section_match.group(1).strip()!r}"
            )

        chunks.append(
            ProcedureChunk(
                procedure_id=metadata["Procedure ID"],
                title=title_match.group(1).strip(),
                version=metadata["Version"],
                owner=metadata["Owner"],
                data_label=metadata["Data label"],
                section=section_match.group(1).strip(),
                source_file=source_file,
                text=section_text,
            )
        )

    return tuple(chunks)
