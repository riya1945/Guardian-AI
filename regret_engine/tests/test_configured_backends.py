from __future__ import annotations

import pytest

from regret_engine.src.config import Settings
from regret_engine.src.embeddings import get_embedding_provider
from regret_engine.src.rag_explainer import RagExplainer


def _settings(**overrides: object) -> Settings:
    base = {
        "database_url": None,
        "auto_migrate": False,
        "storage_backend": "memory",
        "vector_backend": "memory",
        "embedding_provider": "hash",
        "embedding_dim": 768,
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


def test_explicit_supabase_vector_backend_requires_database_url() -> None:
    with pytest.raises(ValueError, match="GUARDIAN_DATABASE_URL"):
        RagExplainer(settings=_settings(vector_backend="supabase"))
