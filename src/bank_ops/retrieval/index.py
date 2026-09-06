"""Build, persist, load, and query the local FAISS procedure index."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Protocol

import faiss
import numpy as np
from pydantic import ValidationError

from bank_ops.retrieval.corpus import ProcedureCorpusError, load_procedure_corpus
from bank_ops.retrieval.embeddings import EmbeddingProvider
from bank_ops.retrieval.models import (
    NoRelevantProcedureResult,
    ProcedureChunk,
    ProcedureIndexManifest,
    ProcedureSearchOutcome,
    ProcedureSearchResult,
)

INDEX_FILENAME = "procedures.faiss"
MANIFEST_FILENAME = "procedure-chunks.json"
DEFAULT_MINIMUM_RELEVANCE_SCORE = 0.6
_RECOVERY_INSTRUCTION = "Run `bank-ops build-index` to rebuild it."


class ProcedureIndexError(RuntimeError):
    """Raised when an index cannot be safely built, loaded, or queried."""


class ProcedureRetriever(Protocol):
    """Application-owned interface for ranked procedure retrieval."""

    def search(self, query: str, limit: int = 3) -> ProcedureSearchOutcome:
        """Return relevant procedure sections or an explicit no-match result."""


def build_procedure_index(
    embedding_provider: EmbeddingProvider,
    output_directory: str | Path,
    corpus_directory: str | Path | None = None,
) -> int:
    """Build and atomically replace a local index and its chunk metadata."""

    corpus = load_procedure_corpus(corpus_directory)
    vectors = _document_vectors(embedding_provider, corpus.chunks)

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    index_path = output / INDEX_FILENAME
    manifest_path = output / MANIFEST_FILENAME
    manifest = ProcedureIndexManifest(
        embedding_model=embedding_provider.model_name,
        source_fingerprint=corpus.source_fingerprint,
        chunks=corpus.chunks,
    )

    temporary_index = _temporary_path(output, INDEX_FILENAME)
    temporary_manifest = _temporary_path(output, MANIFEST_FILENAME)
    try:
        faiss.write_index(index, str(temporary_index))
        temporary_manifest.write_text(
            manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary_manifest, manifest_path)
        os.replace(temporary_index, index_path)
    except (OSError, RuntimeError) as error:
        raise ProcedureIndexError(f"Unable to save procedure index: {error}") from error
    finally:
        temporary_index.unlink(missing_ok=True)
        temporary_manifest.unlink(missing_ok=True)

    return len(corpus.chunks)


class FaissProcedureRetriever:
    """Query a persisted FAISS index and return validated citation records."""

    def __init__(
        self,
        index: faiss.Index,
        chunks: tuple[ProcedureChunk, ...],
        embedding_provider: EmbeddingProvider,
        *,
        minimum_relevance_score: float = DEFAULT_MINIMUM_RELEVANCE_SCORE,
    ) -> None:
        if (
            not np.isfinite(minimum_relevance_score)
            or minimum_relevance_score < 0
            or minimum_relevance_score > 1
        ):
            raise ValueError("minimum_relevance_score must be between 0 and 1")
        if index.ntotal != len(chunks):
            raise ProcedureIndexError(
                "Procedure index row count does not match its chunk metadata. "
                f"{_RECOVERY_INSTRUCTION}"
            )
        self._index = index
        self._chunks = chunks
        self._embedding_provider = embedding_provider
        self._minimum_relevance_score = minimum_relevance_score

    @classmethod
    def load(
        cls,
        embedding_provider: EmbeddingProvider,
        index_directory: str | Path,
        *,
        minimum_relevance_score: float = DEFAULT_MINIMUM_RELEVANCE_SCORE,
        corpus_directory: str | Path | None = None,
    ) -> FaissProcedureRetriever:
        """Load an index only when its model and source corpus remain compatible."""

        directory = Path(index_directory)
        index_path = directory / INDEX_FILENAME
        manifest_path = directory / MANIFEST_FILENAME
        missing_artifacts = [
            path.name for path in (index_path, manifest_path) if not path.is_file()
        ]
        if missing_artifacts:
            missing = ", ".join(missing_artifacts)
            raise ProcedureIndexError(
                f"Procedure index is missing required artifacts in {directory}: "
                f"{missing}. {_RECOVERY_INSTRUCTION}"
            )

        try:
            manifest = ProcedureIndexManifest.model_validate_json(
                manifest_path.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError, json.JSONDecodeError) as error:
            raise ProcedureIndexError(
                "Procedure index metadata is invalid or incompatible: "
                f"{error}. {_RECOVERY_INSTRUCTION}"
            ) from error

        if manifest.embedding_model != embedding_provider.model_name:
            raise ProcedureIndexError(
                "Procedure index is incompatible with the configured embedding "
                f"model: built with {manifest.embedding_model!r}, configured with "
                f"{embedding_provider.model_name!r}. {_RECOVERY_INSTRUCTION}"
            )

        try:
            corpus = load_procedure_corpus(corpus_directory)
        except ProcedureCorpusError as error:
            raise ProcedureIndexError(
                "Unable to validate the procedure index against its source documents: "
                f"{error}. Restore the procedure corpus, then {_RECOVERY_INSTRUCTION}"
            ) from error
        if manifest.source_fingerprint != corpus.source_fingerprint:
            raise ProcedureIndexError(
                "Procedure index is stale because the source documents have changed. "
                f"{_RECOVERY_INSTRUCTION}"
            )

        try:
            index = faiss.read_index(str(index_path))
        except (OSError, RuntimeError) as error:
            raise ProcedureIndexError(
                f"Unable to read the procedure index from {directory}: {error}. "
                f"{_RECOVERY_INSTRUCTION}"
            ) from error

        return cls(
            index,
            manifest.chunks,
            embedding_provider,
            minimum_relevance_score=minimum_relevance_score,
        )

    def search(self, query: str, limit: int = 3) -> ProcedureSearchOutcome:
        """Return cosine-ranked sections that clear the configured safety threshold."""

        if not query.strip():
            raise ValueError("query must not be empty")
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if self._index.ntotal == 0:
            return self._no_relevant_procedure(None)

        vector = np.asarray(
            self._embedding_provider.embed_query(query), dtype=np.float32
        )
        if vector.ndim != 1 or vector.shape[0] != self._index.d:
            raise ProcedureIndexError(
                "Query embedding dimension does not match the procedure index. "
                f"{_RECOVERY_INSTRUCTION}"
            )
        if not np.isfinite(vector).all() or np.linalg.norm(vector) == 0:
            raise ProcedureIndexError("Query embedding must contain finite values")

        query_vector = np.ascontiguousarray(vector.reshape(1, -1))
        faiss.normalize_L2(query_vector)
        result_count = min(limit, self._index.ntotal)
        scores, row_ids = self._index.search(query_vector, result_count)

        results = [
            ProcedureSearchResult(
                **self._chunks[int(row_id)].model_dump(),
                relevance_score=float(score),
            )
            for score, row_id in zip(scores[0], row_ids[0], strict=True)
            if score >= self._minimum_relevance_score
        ]
        if results:
            return results
        return self._no_relevant_procedure(float(scores[0][0]))

    def _no_relevant_procedure(
        self, highest_relevance_score: float | None
    ) -> NoRelevantProcedureResult:
        return NoRelevantProcedureResult(
            minimum_relevance_score=self._minimum_relevance_score,
            highest_relevance_score=highest_relevance_score,
        )


def _document_vectors(
    embedding_provider: EmbeddingProvider,
    chunks: tuple[ProcedureChunk, ...],
) -> np.ndarray:
    vectors = np.asarray(
        embedding_provider.embed_documents([chunk.embedding_text for chunk in chunks]),
        dtype=np.float32,
    )
    if vectors.ndim != 2 or vectors.shape[0] != len(chunks) or vectors.shape[1] < 1:
        raise ProcedureIndexError(
            "Document embedding provider returned an unexpected matrix shape"
        )
    if not np.isfinite(vectors).all():
        raise ProcedureIndexError("Document embeddings must contain finite values")
    if np.any(np.linalg.norm(vectors, axis=1) == 0):
        raise ProcedureIndexError("Document embeddings must not contain zero vectors")

    normalized = np.ascontiguousarray(vectors)
    faiss.normalize_L2(normalized)
    return normalized


def _temporary_path(directory: Path, filename: str) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=f".{filename}.", dir=directory)
    os.close(descriptor)
    return Path(name)
