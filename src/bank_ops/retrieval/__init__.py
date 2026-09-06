"""Local procedure corpus and vector-retrieval implementations."""

from bank_ops.retrieval.corpus import ProcedureCorpusError, load_procedure_chunks
from bank_ops.retrieval.embeddings import (
    BGE_QUERY_INSTRUCTION,
    EmbeddingProvider,
    HuggingFaceBgeEmbedder,
)
from bank_ops.retrieval.index import (
    FaissProcedureRetriever,
    ProcedureIndexError,
    ProcedureRetriever,
    build_procedure_index,
)
from bank_ops.retrieval.models import ProcedureChunk, ProcedureSearchResult

__all__ = [
    "BGE_QUERY_INSTRUCTION",
    "EmbeddingProvider",
    "FaissProcedureRetriever",
    "HuggingFaceBgeEmbedder",
    "ProcedureChunk",
    "ProcedureCorpusError",
    "ProcedureIndexError",
    "ProcedureRetriever",
    "ProcedureSearchResult",
    "build_procedure_index",
    "load_procedure_chunks",
]
