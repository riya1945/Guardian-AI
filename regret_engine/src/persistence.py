from __future__ import annotations

import json
import re
import ssl
from pathlib import Path
from typing import Any

import numpy as np

from regret_engine.src.config import Settings
from regret_engine.src.embeddings import EmbeddingProvider
from regret_engine.src.schemas import DecisionRecord, EvidenceItem, KnowledgeChunk


try:
    import pyexasol
except ImportError:
    pyexasol = None


BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = BASE_DIR / "db" / "exasol_schema.sql"


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


class ExasolDecisionRepository:
    backend_name = "exasol"

    def __init__(self, settings: Settings):
        self.settings = settings
        if settings.auto_migrate:
            ensure_schema(settings)
        self._conn = _connect(settings)

    def save(self, record: DecisionRecord) -> None:
        payload = _model_dump(record)
        input_payload = _model_dump(record.input)
        self._conn.execute(
            """
            DELETE FROM {schema!i}.DECISIONS
            WHERE DECISION_ID={decision_id!s}
            """,
            {
                "schema": self.settings.exasol_schema,
                "decision_id": record.decision_id,
            },
        )
        self._conn.execute(
            """
            INSERT INTO {schema!i}.DECISIONS (
                DECISION_ID,
                OCCURRED_AT,
                SKU,
                PRICE_INR,
                RISK_LEVEL,
                REGRET_SCORE_INR,
                CONFIDENCE,
                INPUT_JSON,
                RECORD_JSON
            )
            VALUES (
                {decision_id!s},
                TO_TIMESTAMP({occurred_at!s}, 'YYYY-MM-DD HH24:MI:SS'),
                {sku!s},
                {price!f},
                {risk_level!s},
                {regret_score!f},
                {confidence!f},
                {input_json!s},
                {record_json!s}
            )
            """,
            {
                "schema": self.settings.exasol_schema,
                "decision_id": record.decision_id,
                "occurred_at": _timestamp_for_exasol(record.timestamp),
                "sku": record.sku,
                "price": record.price,
                "risk_level": record.risk_level,
                "regret_score": record.regret_score,
                "confidence": record.confidence,
                "input_json": json.dumps(input_payload),
                "record_json": json.dumps(payload),
            },
        )

    def list_records(
        self,
        limit: int = 100,
        risk_level: str | None = None,
    ) -> list[DecisionRecord]:
        if risk_level:
            stmt = self._conn.execute(
                """
                SELECT RECORD_JSON
                FROM {schema!i}.DECISIONS
                WHERE RISK_LEVEL={risk_level!s}
                ORDER BY OCCURRED_AT DESC
                LIMIT {limit!d}
                """,
                {
                    "schema": self.settings.exasol_schema,
                    "risk_level": risk_level.upper(),
                    "limit": limit,
                },
            )
        else:
            stmt = self._conn.execute(
                """
                SELECT RECORD_JSON
                FROM {schema!i}.DECISIONS
                ORDER BY OCCURRED_AT DESC
                LIMIT {limit!d}
                """,
                {
                    "schema": self.settings.exasol_schema,
                    "limit": limit,
                },
            )
        return [_record_from_json(row["RECORD_JSON"]) for row in stmt.fetchall()]

    def get(self, decision_id: str) -> DecisionRecord | None:
        stmt = self._conn.execute(
            """
            SELECT RECORD_JSON
            FROM {schema!i}.DECISIONS
            WHERE DECISION_ID={decision_id!s}
            """,
            {
                "schema": self.settings.exasol_schema,
                "decision_id": decision_id,
            },
        )
        row = stmt.fetchone()
        return _record_from_json(row["RECORD_JSON"]) if row else None

    def count(self) -> int:
        stmt = self._conn.execute(
            """
            SELECT COUNT(*) AS RECORD_COUNT
            FROM {schema!i}.DECISIONS
            """,
            {"schema": self.settings.exasol_schema},
        )
        row = stmt.fetchone()
        return int(row["RECORD_COUNT"])


class ExasolVectorStore:
    backend_name = "exasol_python_vectors"

    def __init__(
        self,
        settings: Settings,
        embedding_provider: EmbeddingProvider,
    ):
        self.settings = settings
        self.embedding_provider = embedding_provider
        if settings.auto_migrate:
            ensure_schema(settings)
        self._conn = _connect(settings)

    def ingest(self, chunks: list[KnowledgeChunk]) -> None:
        if not chunks:
            return
        current_ids = {chunk.source for chunk in chunks}
        existing = self._existing_chunks()
        stale_ids = set(existing) - current_ids
        for chunk_id in stale_ids:
            self._conn.execute(
                """
                DELETE FROM {schema!i}.KNOWLEDGE_CHUNKS
                WHERE CHUNK_ID={chunk_id!s}
                """,
                {
                    "schema": self.settings.exasol_schema,
                    "chunk_id": chunk_id,
                },
            )

        chunks_to_write = [
            chunk
            for chunk in chunks
            if existing.get(chunk.source) != chunk.content
        ]
        if not chunks_to_write:
            return

        embeddings = self.embedding_provider.embed(
            [chunk.content for chunk in chunks_to_write]
        )
        for chunk, embedding in zip(chunks_to_write, embeddings, strict=True):
            self._conn.execute(
                """
                DELETE FROM {schema!i}.KNOWLEDGE_CHUNKS
                WHERE CHUNK_ID={chunk_id!s}
                """,
                {
                    "schema": self.settings.exasol_schema,
                    "chunk_id": chunk.source,
                },
            )
            self._conn.execute(
                """
                INSERT INTO {schema!i}.KNOWLEDGE_CHUNKS (
                    CHUNK_ID,
                    SOURCE_ID,
                    TITLE,
                    CONTENT,
                    EMBEDDING_MODEL,
                    EMBEDDING_JSON
                )
                VALUES (
                    {chunk_id!s},
                    {source!s},
                    {title!s},
                    {content!s},
                    {embedding_model!s},
                    {embedding_json!s}
                )
                """,
                {
                    "schema": self.settings.exasol_schema,
                    "chunk_id": chunk.source,
                    "source": chunk.source,
                    "title": chunk.title,
                    "content": chunk.content,
                    "embedding_model": self.embedding_provider.provider_name,
                    "embedding_json": json.dumps(embedding),
                },
            )

    def _existing_chunks(self) -> dict[str, str]:
        rows = self._conn.execute(
            """
            SELECT CHUNK_ID, CONTENT
            FROM {schema!i}.KNOWLEDGE_CHUNKS
            WHERE EMBEDDING_MODEL={embedding_model!s}
            """,
            {
                "schema": self.settings.exasol_schema,
                "embedding_model": self.embedding_provider.provider_name,
            },
        ).fetchall()
        return {str(row["CHUNK_ID"]): str(row["CONTENT"]) for row in rows}

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        min_score: float = 0.08,
    ) -> list[EvidenceItem]:
        query_embedding = self.embedding_provider.embed_query(query)
        rows = self._conn.execute(
            """
            SELECT SOURCE_ID, TITLE, CONTENT, EMBEDDING_JSON
            FROM {schema!i}.KNOWLEDGE_CHUNKS
            WHERE EMBEDDING_MODEL={embedding_model!s}
            """,
            {
                "schema": self.settings.exasol_schema,
                "embedding_model": self.embedding_provider.provider_name,
            },
        ).fetchall()
        scored: list[tuple[float, Any]] = []
        for row in rows:
            score = _cosine_similarity(query_embedding, json.loads(row["EMBEDDING_JSON"]))
            if score >= min_score:
                scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            EvidenceItem(
                source=row["SOURCE_ID"],
                title=row["TITLE"],
                content=row["CONTENT"],
                relevance_score=round(score, 4),
            )
            for score, row in scored[:top_k]
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


def build_decision_repository(settings: Settings) -> InMemoryDecisionRepository | ExasolDecisionRepository:
    if settings.storage_backend == "exasol" and not _has_exasol_settings(settings):
        raise PersistenceUnavailable("EXASOL_DSN, EXASOL_USER, and EXASOL_PASSWORD are required.")
    if settings.storage_backend == "memory" or not _has_exasol_settings(settings):
        return InMemoryDecisionRepository()
    try:
        return ExasolDecisionRepository(settings)
    except Exception:
        if settings.storage_backend == "exasol":
            raise
        return InMemoryDecisionRepository()


def ensure_schema(settings: Settings) -> None:
    schema = _safe_ident(settings.exasol_schema)
    sql = SCHEMA_FILE.read_text(encoding="utf-8").replace("GUARDIAN_AI", schema)
    conn = _connect(settings, use_schema=False)
    try:
        for statement in _split_sql(sql):
            conn.execute(statement)
    finally:
        conn.close()


def _connect(settings: Settings, use_schema: bool = True):
    if pyexasol is None:
        raise PersistenceUnavailable("pyexasol is not installed.")
    if not _has_exasol_settings(settings):
        raise PersistenceUnavailable("EXASOL_DSN, EXASOL_USER, and EXASOL_PASSWORD are required.")
    kwargs: dict[str, Any] = {
        "dsn": settings.exasol_dsn,
        "user": settings.exasol_user,
        "password": settings.exasol_password,
        "encryption": settings.exasol_encryption,
        "compression": settings.exasol_compression,
        "fetch_dict": True,
    }
    if use_schema:
        kwargs["schema"] = settings.exasol_schema
    if settings.exasol_encryption and not settings.exasol_certificate_validation:
        kwargs["websocket_sslopt"] = {
            "cert_reqs": ssl.CERT_NONE,
            "check_hostname": False,
        }
    return pyexasol.connect(**kwargs)


def _has_exasol_settings(settings: Settings) -> bool:
    return bool(settings.exasol_dsn and settings.exasol_user and settings.exasol_password)


def _record_from_json(value: Any) -> DecisionRecord:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        value = json.loads(value)
    return DecisionRecord.model_validate(value)


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value.dict()


def _timestamp_for_exasol(value: str) -> str:
    return value.replace("+05:30", "").replace("+00:00", "").replace("T", " ").split(".")[0]


def _split_sql(sql: str) -> list[str]:
    return [
        statement.strip()
        for statement in sql.split(";")
        if statement.strip()
    ]


def _safe_ident(value: str) -> str:
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
        raise ValueError(f"Unsafe Exasol identifier: {value}")
    return value


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    left_arr = np.asarray(left, dtype=np.float32)
    right_arr = np.asarray(right, dtype=np.float32)
    denominator = float(np.linalg.norm(left_arr) * np.linalg.norm(right_arr))
    if denominator == 0:
        return 0.0
    return float(np.dot(left_arr, right_arr) / denominator)
