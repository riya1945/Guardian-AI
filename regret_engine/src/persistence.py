from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from regret_engine.src.config import Settings
from regret_engine.src.embeddings import EmbeddingProvider, to_pgvector
from regret_engine.src.schemas import DecisionRecord, EvidenceItem, KnowledgeChunk


try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None


BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = BASE_DIR / "db" / "schema.sql"


class PersistenceUnavailable(RuntimeError):
    pass


class InMemoryDecisionRepository:
    backend_name = "memory"

    def __init__(self):
        self.records: dict[str, DecisionRecord] = {}

    def save(self, record: DecisionRecord) -> None:
        self.records[record.decision_id] = record

    def list_records(
        self,
        limit: int = 100,
        risk_level: str | None = None,
    ) -> list[DecisionRecord]:
        records = sorted(
            self.records.values(),
            key=lambda record: record.timestamp,
            reverse=True,
        )
        if risk_level:
            records = [
                record for record in records if record.risk_level == risk_level.upper()
            ]
        return records[:limit]

    def get(self, decision_id: str) -> DecisionRecord | None:
        return self.records.get(decision_id)

    def count(self) -> int:
        return len(self.records)


class PostgresDecisionRepository:
    backend_name = "postgres"

    def __init__(self, database_url: str, auto_migrate: bool = True):
        if psycopg is None or dict_row is None:
            raise PersistenceUnavailable("psycopg is not installed.")
        self.database_url = database_url
        if auto_migrate:
            ensure_schema(database_url)
        self._conn = _connect(self.database_url)

    def save(self, record: DecisionRecord) -> None:
        payload = _model_dump(record)
        input_payload = _model_dump(record.input)
        self._conn.execute(
            """
            insert into guardian_decisions (
                decision_id,
                occurred_at,
                sku,
                price,
                risk_level,
                regret_score,
                confidence,
                input_json,
                record_json
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
            on conflict (decision_id) do update set
                occurred_at = excluded.occurred_at,
                sku = excluded.sku,
                price = excluded.price,
                risk_level = excluded.risk_level,
                regret_score = excluded.regret_score,
                confidence = excluded.confidence,
                input_json = excluded.input_json,
                record_json = excluded.record_json,
                updated_at = now()
            """,
            (
                record.decision_id,
                record.timestamp,
                record.sku,
                record.price,
                record.risk_level,
                record.regret_score,
                record.confidence,
                json.dumps(input_payload),
                json.dumps(payload),
            ),
        )

    def list_records(
        self,
        limit: int = 100,
        risk_level: str | None = None,
    ) -> list[DecisionRecord]:
        where = "where risk_level = %s" if risk_level else ""
        params: tuple[Any, ...] = (
            (risk_level.upper(), limit)
            if risk_level
            else (limit,)
        )
        rows = self._conn.execute(
            f"""
            select record_json
            from guardian_decisions
            {where}
            order by occurred_at desc
            limit %s
            """,
            params,
        ).fetchall()
        return [_record_from_json(row["record_json"]) for row in rows]

    def get(self, decision_id: str) -> DecisionRecord | None:
        row = self._conn.execute(
            """
            select record_json
            from guardian_decisions
            where decision_id = %s
            """,
            (decision_id,),
        ).fetchone()
        return _record_from_json(row["record_json"]) if row else None

    def count(self) -> int:
        row = self._conn.execute("select count(*) as count from guardian_decisions").fetchone()
        return int(row["count"])


class SupabaseVectorStore:
    backend_name = "supabase_pgvector"

    def __init__(
        self,
        database_url: str,
        embedding_provider: EmbeddingProvider,
        auto_migrate: bool = True,
    ):
        if psycopg is None or dict_row is None:
            raise PersistenceUnavailable("psycopg is not installed.")
        self.database_url = database_url
        self.embedding_provider = embedding_provider
        if auto_migrate:
            ensure_schema(database_url)
        self._conn = _connect(self.database_url)

    def ingest(self, chunks: list[KnowledgeChunk]) -> None:
        if not chunks:
            return
        embeddings = self.embedding_provider.embed([chunk.content for chunk in chunks])
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            self._conn.execute(
                """
                insert into guardian_knowledge_chunks (
                    source,
                    title,
                    content,
                    embedding,
                    metadata
                )
                values (%s, %s, %s, %s::vector, %s::jsonb)
                on conflict (source) do update set
                    title = excluded.title,
                    content = excluded.content,
                    embedding = excluded.embedding,
                    metadata = excluded.metadata,
                    updated_at = now()
                """,
                (
                    chunk.source,
                    chunk.title,
                    chunk.content,
                    to_pgvector(embedding),
                    json.dumps({"embedding_provider": self.embedding_provider.provider_name}),
                ),
            )

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        min_score: float = 0.2,
    ) -> list[EvidenceItem]:
        embedding = self.embedding_provider.embed_query(query)
        rows = self._conn.execute(
            """
            select source, title, content, relevance_score
            from match_guardian_knowledge_chunks(%s::vector, %s, %s)
            """,
            (to_pgvector(embedding), min_score, top_k),
        ).fetchall()
        return [
            EvidenceItem(
                source=row["source"],
                title=row["title"],
                content=row["content"],
                relevance_score=round(float(row["relevance_score"]), 4),
            )
            for row in rows
        ]


class InMemoryVectorStore:
    backend_name = "memory_vectors"

    def __init__(
        self,
        chunks: list[KnowledgeChunk],
        embedding_provider: EmbeddingProvider,
    ):
        if not chunks:
            raise ValueError("No knowledge chunks available for RAG retrieval.")
        self.chunks = chunks
        self.embedding_provider = embedding_provider
        self.embeddings = embedding_provider.embed([chunk.content for chunk in chunks])

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        min_score: float = 0.08,
    ) -> list[EvidenceItem]:
        query_embedding = self.embedding_provider.embed_query(query)
        scores = [
            _cosine_similarity(query_embedding, embedding)
            for embedding in self.embeddings
        ]
        ranked = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
        evidence: list[EvidenceItem] = []
        for index in ranked[:top_k]:
            score = scores[index]
            if score < min_score:
                continue
            chunk = self.chunks[index]
            evidence.append(
                EvidenceItem(
                    source=chunk.source,
                    title=chunk.title,
                    content=chunk.content,
                    relevance_score=round(score, 4),
                )
            )
        return evidence


def build_decision_repository(settings: Settings) -> InMemoryDecisionRepository | PostgresDecisionRepository:
    if settings.storage_backend == "postgres" and not settings.database_url:
        raise PersistenceUnavailable("GUARDIAN_DATABASE_URL is required for postgres storage.")
    if settings.storage_backend == "memory" or not settings.database_url:
        return InMemoryDecisionRepository()
    try:
        return PostgresDecisionRepository(
            settings.database_url,
            auto_migrate=settings.auto_migrate,
        )
    except Exception:
        if settings.storage_backend == "postgres":
            raise
        return InMemoryDecisionRepository()


def ensure_schema(database_url: str) -> None:
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    with _connect(database_url) as conn:
        conn.execute(sql)


def _connect(database_url: str):
    if psycopg is None or dict_row is None:
        raise PersistenceUnavailable("psycopg is not installed.")
    return psycopg.connect(
        database_url,
        autocommit=True,
        row_factory=dict_row,
        connect_timeout=10,
    )


def _record_from_json(value: Any) -> DecisionRecord:
    if isinstance(value, str):
        value = json.loads(value)
    return DecisionRecord.model_validate(value)


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value.dict()


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    left_arr = np.asarray(left, dtype=np.float32)
    right_arr = np.asarray(right, dtype=np.float32)
    denominator = float(np.linalg.norm(left_arr) * np.linalg.norm(right_arr))
    if denominator == 0:
        return 0.0
    return float(np.dot(left_arr, right_arr) / denominator)
