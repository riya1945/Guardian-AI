from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    auto_migrate: bool
    storage_backend: str
    vector_backend: str
    embedding_provider: str
    embedding_dim: int
    llm_chain: tuple[str, ...]
    groq_api_key: str | None
    groq_model: str
    gemini_api_key: str | None
    gemini_chat_model: str
    gemini_embedding_model: str


def load_settings() -> Settings:
    return Settings(
        database_url=_first_env(
            "GUARDIAN_DATABASE_URL",
            "DATABASE_URL",
            "SUPABASE_DB_URL",
        ),
        auto_migrate=_bool_env("GUARDIAN_AUTO_MIGRATE", default=True),
        storage_backend=os.getenv("GUARDIAN_STORAGE_BACKEND", "auto").lower(),
        vector_backend=os.getenv("GUARDIAN_VECTOR_BACKEND", "auto").lower(),
        embedding_provider=os.getenv("GUARDIAN_EMBEDDING_PROVIDER", "hash").lower(),
        embedding_dim=int(os.getenv("GUARDIAN_EMBEDDING_DIM", "768")),
        llm_chain=tuple(
            item.strip().lower()
            for item in os.getenv("LLM_CHAIN", "groq,gemini,deterministic").split(",")
            if item.strip()
        ),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_chat_model=os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash-lite"),
        gemini_embedding_model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
    )


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}
