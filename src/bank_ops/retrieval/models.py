"""Validated records stored alongside and returned from the FAISS index."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

NonEmptyText = Annotated[str, Field(min_length=1)]
RelevanceThreshold = Annotated[float, Field(ge=0, le=1)]


class RetrievalModel(BaseModel):
    """Immutable retrieval contract that rejects unexpected fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ProcedureChunk(RetrievalModel):
    """One independently searchable procedure section and its citation details."""

    procedure_id: Annotated[str, Field(pattern=r"^PROC-\d{3}$")]
    title: NonEmptyText
    version: NonEmptyText
    owner: NonEmptyText
    data_label: NonEmptyText
    section: NonEmptyText
    source_file: Annotated[str, Field(pattern=r"^[^/\\]+\.md$")]
    text: NonEmptyText

    @property
    def embedding_text(self) -> str:
        """Return self-contained text that carries context into the embedding."""

        return f"{self.title}\n\n{self.section}\n\n{self.text}"


class ProcedureSearchResult(ProcedureChunk):
    """A matched procedure section with its cosine-similarity score."""

    relevance_score: float


class RetrievalErrorCode(StrEnum):
    """Stable error codes returned by the retrieval boundary."""

    NO_RELEVANT_PROCEDURE = "no_relevant_procedure"


class NoRelevantProcedureResult(RetrievalModel):
    """Specific result returned when no procedure clears the safety threshold."""

    error: Literal[RetrievalErrorCode.NO_RELEVANT_PROCEDURE] = (
        RetrievalErrorCode.NO_RELEVANT_PROCEDURE
    )
    message: Literal[
        "No procedure met the minimum relevance score. Escalate for human review."
    ] = "No procedure met the minimum relevance score. Escalate for human review."
    minimum_relevance_score: RelevanceThreshold
    highest_relevance_score: float | None


type ProcedureSearchOutcome = list[ProcedureSearchResult] | NoRelevantProcedureResult


class ProcedureIndexManifest(RetrievalModel):
    """Ordered chunk details whose positions correspond to FAISS row IDs."""

    schema_version: Literal[2] = 2
    embedding_model: NonEmptyText
    source_fingerprint: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    chunks: tuple[ProcedureChunk, ...]
