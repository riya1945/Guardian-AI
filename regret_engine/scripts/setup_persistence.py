from __future__ import annotations

import json

from regret_engine.src.config import load_settings
from regret_engine.src.embeddings import get_embedding_provider
from regret_engine.src.persistence import ExasolVectorStore, ensure_schema
from regret_engine.src.rag_explainer import load_knowledge_chunks


def main() -> None:
    settings = load_settings()
    if not (settings.exasol_dsn and settings.exasol_user and settings.exasol_password):
        raise SystemExit("EXASOL_DSN, EXASOL_USER, and EXASOL_PASSWORD are required.")

    ensure_schema(settings)
    chunks = load_knowledge_chunks()
    provider = get_embedding_provider(settings)
    vector_store = ExasolVectorStore(
        settings=settings,
        embedding_provider=provider,
    )
    vector_store.ingest(chunks)

    print(
        json.dumps(
            {
                "status": "ok",
                "vector_backend": vector_store.backend_name,
                "embedding_provider": provider.provider_name,
                "chunks_ingested": len(chunks),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
