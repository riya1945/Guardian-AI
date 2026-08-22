from __future__ import annotations

import pytest

from regret_engine.src.config import Settings
from regret_engine.src.embeddings import get_embedding_provider
from regret_engine.src.rag_explainer import RagExplainer


def _settings(**overrides: object) -> Settings:
    base = {
        "auto_migrate": False,
        "storage_backend": "memory",
        "vector_backend": "memory",
        "embedding_provider": "hash",
        "embedding_dim": 768,
        "exasol_dsn": None,
        "exasol_user": None,
        "exasol_password": None,
        "exasol_schema": "GUARDIAN_AI",
        "exasol_encryption": True,
        "exasol_compression": True,
        "llm_chain": ("deterministic",),
        "groq_api_key": None,
        "groq_model": "llama-3.1-8b-instant",
        "gemini_api_key": None,
        "gemini_chat_model": "gemini-2.5-flash-lite",
        "gemini_embedding_model": "gemini-embedding-001",
    }
    base.update(overrides)
    return Settings(**base)


def test_explicit_gemini_embeddings_require_key() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        get_embedding_provider(_settings(embedding_provider="gemini"))


def test_explicit_exasol_vector_backend_requires_credentials() -> None:
    with pytest.raises(ValueError, match="EXASOL_DSN"):
        RagExplainer(settings=_settings(vector_backend="exasol"))
