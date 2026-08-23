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
    batch_size = 32

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
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            embeddings.extend(self._embed_batch(batch, task_type="RETRIEVAL_DOCUMENT"))
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text, task_type="RETRIEVAL_QUERY")

    def _embed_batch(
        self,
        texts: list[str],
        task_type: str,
    ) -> list[list[float]]:
        if not texts:
            return []
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model}:batchEmbedContents"
        )
        payload = {
            "requests": [
                {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": task_type,
                    "outputDimensionality": self.dimension,
                }
                for text in texts
            ]
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                url,
                params={"key": self.api_key},
                json=payload,
            )
        _raise_gemini_error(response)
        embeddings = response.json()["embeddings"]
        vectors = [[float(value) for value in item["values"]] for item in embeddings]
        for vector in vectors:
            self._validate_dimension(vector)
        return vectors

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
        _raise_gemini_error(response)
        values = response.json()["embedding"]["values"]
        vector = [float(value) for value in values]
        self._validate_dimension(vector)
        return vector

    def _validate_dimension(self, vector: list[float]) -> None:
        if len(vector) != self.dimension:
            raise ValueError(
                f"Gemini returned {len(vector)} dimensions; expected {self.dimension}."
            )


def _raise_gemini_error(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    detail = ""
    try:
        payload = response.json()
        detail = payload.get("error", {}).get("message", "")
    except (ValueError, AttributeError):
        detail = "non-JSON error response"
    raise RuntimeError(
        f"Gemini embedding request failed with status {response.status_code}: {detail}"
    )


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
