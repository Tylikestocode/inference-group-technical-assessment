"""Local procedure corpus and vector-retrieval implementations."""

from bank_ops.retrieval.corpus import (
    ProcedureCorpusError,
    ProcedureCorpusSnapshot,
    load_procedure_chunks,
    load_procedure_corpus,
)
from bank_ops.retrieval.embeddings import (
    BGE_QUERY_INSTRUCTION,
    EmbeddingProvider,
    HuggingFaceBgeEmbedder,
)
from bank_ops.retrieval.index import (
    DEFAULT_MINIMUM_RELEVANCE_SCORE,
    FaissProcedureRetriever,
    ProcedureIndexError,
    ProcedureRetriever,
    build_procedure_index,
)
from bank_ops.retrieval.models import (
    NoRelevantProcedureResult,
    ProcedureChunk,
    ProcedureSearchOutcome,
    ProcedureSearchResult,
    RetrievalErrorCode,
)

__all__ = [
    "BGE_QUERY_INSTRUCTION",
    "DEFAULT_MINIMUM_RELEVANCE_SCORE",
    "EmbeddingProvider",
    "FaissProcedureRetriever",
    "HuggingFaceBgeEmbedder",
    "NoRelevantProcedureResult",
    "ProcedureChunk",
    "ProcedureCorpusError",
    "ProcedureCorpusSnapshot",
    "ProcedureIndexError",
    "ProcedureRetriever",
    "ProcedureSearchOutcome",
    "ProcedureSearchResult",
    "RetrievalErrorCode",
    "build_procedure_index",
    "load_procedure_chunks",
    "load_procedure_corpus",
]
