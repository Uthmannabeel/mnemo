"""Storage backends for memory records.

Two interchangeable implementations behind one interface:

  InMemoryStore  numpy cosine search — zero dependencies, used for dev/CI/demo.
  PostgresStore  pgvector on Alibaba Cloud RDS for PostgreSQL — production path.

Both expose the same small surface the MemoryManager needs.
"""
from __future__ import annotations

import logging
from typing import Iterable, Protocol

import numpy as np

from .types import MemoryRecord, Tier

logger = logging.getLogger(__name__)


class MemoryStore(Protocol):
    def add(self, record: MemoryRecord) -> None: ...
    def get(self, record_id: str) -> MemoryRecord | None: ...
    def update(self, record: MemoryRecord) -> None: ...
    def mark_used(self, record_ids: list[str]) -> None: ...
    def all(self, user_id: str, tier: Tier | None = None, active_only: bool = True) -> list[MemoryRecord]: ...
    def search(
        self, user_id: str, embedding: list[float], tier: Tier | None, k: int, active_only: bool = True
    ) -> list[tuple[MemoryRecord, float]]: ...


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    return float(np.dot(a, b) / denom)


class InMemoryStore:
    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}

    def add(self, record: MemoryRecord) -> None:
        self._records[record.id] = record

    def get(self, record_id: str) -> MemoryRecord | None:
        return self._records.get(record_id)

    def update(self, record: MemoryRecord) -> None:
        self._records[record.id] = record

    def mark_used(self, record_ids: list[str]) -> None:
        for rid in record_ids:
            rec = self._records.get(rid)
            if rec:
                rec.touch()

    def _filter(self, user_id: str, tier: Tier | None, active_only: bool) -> Iterable[MemoryRecord]:
        for r in self._records.values():
            if r.user_id != user_id:
                continue
            if tier is not None and r.tier != tier:
                continue
            if active_only and not r.active:
                continue
            yield r

    def all(self, user_id: str, tier: Tier | None = None, active_only: bool = True) -> list[MemoryRecord]:
        return list(self._filter(user_id, tier, active_only))

    def search(
        self, user_id: str, embedding: list[float], tier: Tier | None, k: int, active_only: bool = True
    ) -> list[tuple[MemoryRecord, float]]:
        q = np.asarray(embedding, dtype=np.float32)
        scored: list[tuple[MemoryRecord, float]] = []
        for r in self._filter(user_id, tier, active_only):
            if r.embedding is None:
                continue
            scored.append((r, _cosine(q, np.asarray(r.embedding, dtype=np.float32))))
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:k]


class PostgresStore:
    """pgvector-backed store. Schema is created on first use.

    Deployed against Alibaba Cloud RDS for PostgreSQL with the `vector` extension.
    Connections come from a pool, not a single shared connection: psycopg serializes
    concurrent use of one connection (a throughput ceiling under FastAPI's threadpool),
    and RDS drops idle connections — the pool health-checks and replaces them instead
    of leaving the API broken until a restart.
    """

    def __init__(self, dsn: str, dim: int) -> None:
        import psycopg
        from pgvector.psycopg import register_vector
        from psycopg_pool import ConnectionPool

        self.dim = dim
        # Schema first, over a plain connection: the pool's per-connection
        # `configure=register_vector` needs the vector type to already exist.
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS memories (
                    id          TEXT PRIMARY KEY,
                    user_id     TEXT NOT NULL,
                    tier        TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    embedding   vector({dim}),
                    created_at  TIMESTAMPTZ NOT NULL,
                    last_used_at TIMESTAMPTZ NOT NULL,
                    use_count   INT NOT NULL,
                    confidence  REAL NOT NULL,
                    importance  REAL NOT NULL,
                    active      BOOLEAN NOT NULL,
                    source_ids  JSONB NOT NULL,
                    attrs       JSONB NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS memories_user_tier ON memories (user_id, tier, active)"
            )
            try:
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS memories_embedding_hnsw "
                    "ON memories USING hnsw (embedding vector_cosine_ops)"
                )
            except Exception:
                # pgvector < 0.5 has no hnsw; searches fall back to a sequential
                # scan, which is fine at demo scale — but say so.
                logger.warning("hnsw index unavailable; vector searches will seq-scan")
        self.pool = ConnectionPool(
            dsn,
            min_size=1,
            max_size=8,
            kwargs={"autocommit": True},
            configure=register_vector,
            check=ConnectionPool.check_connection,
        )

    def _row(self, r: MemoryRecord) -> tuple:
        from psycopg.types.json import Jsonb

        emb = np.asarray(r.embedding, dtype=np.float32) if r.embedding is not None else None
        return (
            r.id, r.user_id, r.tier.value, r.content, emb, r.created_at, r.last_used_at,
            r.use_count, r.confidence, r.importance, r.active, Jsonb(r.source_ids), Jsonb(r.attrs),
        )

    def add(self, record: MemoryRecord) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """INSERT INTO memories VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (id) DO NOTHING""",
                self._row(record),
            )

    def update(self, record: MemoryRecord) -> None:
        from psycopg.types.json import Jsonb

        with self.pool.connection() as conn:
            conn.execute(
                """UPDATE memories SET last_used_at=%s, use_count=%s, confidence=%s,
                   importance=%s, active=%s, content=%s, attrs=%s WHERE id=%s""",
                (record.last_used_at, record.use_count, record.confidence, record.importance,
                 record.active, record.content, Jsonb(record.attrs), record.id),
            )

    def mark_used(self, record_ids: list[str]) -> None:
        # One batched write per retrieval, not a round-trip per record.
        if not record_ids:
            return
        with self.pool.connection() as conn:
            conn.execute(
                "UPDATE memories SET last_used_at=now(), use_count=use_count+1 WHERE id = ANY(%s)",
                (record_ids,),
            )

    def _hydrate(self, row: dict) -> MemoryRecord:
        rec = MemoryRecord(
            id=row["id"], user_id=row["user_id"], tier=Tier(row["tier"]), content=row["content"],
            embedding=list(row["embedding"]) if row["embedding"] is not None else None,
            created_at=row["created_at"], last_used_at=row["last_used_at"], use_count=row["use_count"],
            confidence=row["confidence"], importance=row["importance"], active=row["active"],
            source_ids=row["source_ids"], attrs=row["attrs"],
        )
        return rec

    def get(self, record_id: str) -> MemoryRecord | None:
        from psycopg.rows import dict_row

        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM memories WHERE id=%s", (record_id,))
            row = cur.fetchone()
        return self._hydrate(row) if row else None

    def all(self, user_id: str, tier: Tier | None = None, active_only: bool = True) -> list[MemoryRecord]:
        from psycopg.rows import dict_row

        q = "SELECT * FROM memories WHERE user_id=%s"
        params: list = [user_id]
        if tier is not None:
            q += " AND tier=%s"
            params.append(tier.value)
        if active_only:
            q += " AND active=TRUE"
        # Chronological order matters: consolidation slices "the recent window" and
        # InMemoryStore is insertion-ordered — keep Postgres consistent with it.
        q += " ORDER BY created_at ASC"
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(q, tuple(params))
            rows = cur.fetchall()
        return [self._hydrate(r) for r in rows]

    def search(
        self, user_id: str, embedding: list[float], tier: Tier | None, k: int, active_only: bool = True
    ) -> list[tuple[MemoryRecord, float]]:
        from psycopg.rows import dict_row

        vec = np.asarray(embedding, dtype=np.float32)
        q = "SELECT *, 1 - (embedding <=> %s) AS sim FROM memories WHERE user_id=%s AND embedding IS NOT NULL"
        params: list = [vec, user_id]
        if tier is not None:
            q += " AND tier=%s"
            params.append(tier.value)
        if active_only:
            q += " AND active=TRUE"
        q += " ORDER BY embedding <=> %s LIMIT %s"
        params += [vec, k]
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(q, tuple(params))
            rows = cur.fetchall()
        return [(self._hydrate(r), float(r["sim"])) for r in rows]


def make_store(kind: str, dsn: str, dim: int) -> MemoryStore:
    if kind == "postgres":
        return PostgresStore(dsn, dim)
    return InMemoryStore()
