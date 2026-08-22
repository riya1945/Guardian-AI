from __future__ import annotations

import hashlib
import re
from typing import Protocol

import httpx
import numpy as np

from regret_engine.src.config import Settings


class EmbeddingProvider(Protocol):
    provider_name: str
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


class HashEmbeddingProvider:
    provider_name = "hash"

    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    def _embed_one(self, text: str) -> list[float]:
        vector = np.zeros(self.dimension, dtype=np.float32)
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.astype(float).tolist()


class GeminiEmbeddingProvider:
    provider_name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        dimension: int = 768,
        timeout: float = 20.0,
    ):
        self.api_key = api_key
        self.model = model
        self.dimension = dimension
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text, task_type="RETRIEVAL_QUERY")

    def _embed_one(
        self,
        text: str,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> list[float]:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model}:embedContent"
        )
        payload = {
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
            "outputDimensionality": self.dimension,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                url,
                params={"key": self.api_key},
                json=payload,
            )
        response.raise_for_status()
        values = response.json()["embedding"]["values"]
        if len(values) != self.dimension:
            raise ValueError(
                f"Gemini returned {len(values)} dimensions; expected {self.dimension}."
            )
        return [float(value) for value in values]


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for Gemini embeddings.")
        return GeminiEmbeddingProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_embedding_model,
            dimension=settings.embedding_dim,
        )
    return HashEmbeddingProvider(dimension=settings.embedding_dim)


def to_pgvector(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
