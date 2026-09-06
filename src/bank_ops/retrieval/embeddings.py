"""Replaceable embedding interfaces and the local Hugging Face adapter."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class EmbeddingProvider(Protocol):
    """Application-owned boundary for document and query embeddings."""

    @property
    def model_name(self) -> str:
        """Return the stable model identifier used to create embeddings."""

    def embed_documents(self, texts: Sequence[str]) -> NDArray[np.float32]:
        """Embed document passages as one row per supplied text."""

    def embed_query(self, text: str) -> NDArray[np.float32]:
        """Embed one retrieval query as a single vector."""


class HuggingFaceBgeEmbedder:
    """Sentence Transformers adapter for the selected local BGE model."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        from sentence_transformers import SentenceTransformer

        self._model_name = model_name
        self._model: Any = SentenceTransformer(model_name)

    @property
    def model_name(self) -> str:
        """Return the Hugging Face model identifier used by this adapter."""

        return self._model_name

    def embed_documents(self, texts: Sequence[str]) -> NDArray[np.float32]:
        return self._encode(list(texts))

    def embed_query(self, text: str) -> NDArray[np.float32]:
        encoded = self._encode([f"{BGE_QUERY_INSTRUCTION}{text}"])
        return encoded[0]

    def _encode(self, texts: list[str]) -> NDArray[np.float32]:
        vectors = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.ascontiguousarray(vectors, dtype=np.float32)
