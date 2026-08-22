from __future__ import annotations

import json

from regret_engine.src.config import load_settings
from regret_engine.src.embeddings import get_embedding_provider
from regret_engine.src.persistence import SupabaseVectorStore, ensure_schema
from regret_engine.src.rag_explainer import load_knowledge_chunks


def main() -> None:
    settings = load_settings()
    if not settings.database_url:
        raise SystemExit("GUARDIAN_DATABASE_URL or SUPABASE_DB_URL is required.")

    ensure_schema(settings.database_url)
    chunks = load_knowledge_chunks()
    provider = get_embedding_provider(settings)
    vector_store = SupabaseVectorStore(
        database_url=settings.database_url,
        embedding_provider=provider,
        auto_migrate=False,
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
