from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    auto_migrate: bool
    storage_backend: str
    vector_backend: str
    embedding_provider: str
    embedding_dim: int
    exasol_dsn: str | None
    exasol_user: str | None
    exasol_password: str | None
    exasol_schema: str
    exasol_encryption: bool
    exasol_compression: bool
    llm_chain: tuple[str, ...]
    groq_api_key: str | None
    groq_model: str
    gemini_api_key: str | None
    gemini_chat_model: str
    gemini_embedding_model: str


def load_settings() -> Settings:
    return Settings(
        auto_migrate=_bool_env("GUARDIAN_AUTO_MIGRATE", default=True),
        storage_backend=os.getenv("GUARDIAN_STORAGE_BACKEND", "auto").lower(),
        vector_backend=os.getenv("GUARDIAN_VECTOR_BACKEND", "auto").lower(),
        embedding_provider=os.getenv("GUARDIAN_EMBEDDING_PROVIDER", "hash").lower(),
        embedding_dim=int(os.getenv("GUARDIAN_EMBEDDING_DIM", "768")),
        exasol_dsn=os.getenv("EXASOL_DSN"),
        exasol_user=os.getenv("EXASOL_USER"),
        exasol_password=os.getenv("EXASOL_PASSWORD"),
        exasol_schema=os.getenv("EXASOL_SCHEMA", "GUARDIAN_AI").upper(),
        exasol_encryption=_bool_env("EXASOL_ENCRYPTION", default=True),
        exasol_compression=_bool_env("EXASOL_COMPRESSION", default=True),
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


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}
