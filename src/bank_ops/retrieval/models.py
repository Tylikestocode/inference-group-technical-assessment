"""Validated records stored alongside and returned from the FAISS index."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

NonEmptyText = Annotated[str, Field(min_length=1)]


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


class ProcedureIndexManifest(RetrievalModel):
    """Ordered chunk details whose positions correspond to FAISS row IDs."""

    schema_version: Literal[1] = 1
    chunks: tuple[ProcedureChunk, ...]
