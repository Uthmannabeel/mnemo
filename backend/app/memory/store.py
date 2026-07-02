"""Storage backends for memory records.

Two interchangeable implementations behind one interface:

  InMemoryStore  numpy cosine search — zero dependencies, used for dev/CI/demo.
  PostgresStore  pgvector on Alibaba Cloud RDS for PostgreSQL — production path.

Both expose the same small surface the MemoryManager needs.
"""
from __future__ import annotations

from typing import Iterable, Protocol

import numpy as np

from .types import MemoryRecord, Tier


class MemoryStore(Protocol):
    def add(self, record: MemoryRecord) -> None: ...
    def get(self, record_id: str) -> MemoryRecord | None: ...
    def update(self, record: MemoryRecord) -> None: ...
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
    """

    def __init__(self, dsn: str, dim: int) -> None:
        import psycopg
        from pgvector.psycopg import register_vector

        self.dim = dim
        self.conn = psycopg.connect(dsn, autocommit=True)
        self.conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        self.conn.execute(
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
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS memories_user_tier ON memories (user_id, tier, active)"
        )
        register_vector(self.conn)

    def _row(self, r: MemoryRecord) -> tuple:
        from psycopg.types.json import Jsonb

        emb = np.asarray(r.embedding, dtype=np.float32) if r.embedding is not None else None
        return (
            r.id, r.user_id, r.tier.value, r.content, emb, r.created_at, r.last_used_at,
            r.use_count, r.confidence, r.importance, r.active, Jsonb(r.source_ids), Jsonb(r.attrs),
        )

    def add(self, record: MemoryRecord) -> None:
        self.conn.execute(
            """INSERT INTO memories VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (id) DO NOTHING""",
            self._row(record),
        )

    def update(self, record: MemoryRecord) -> None:
        from psycopg.types.json import Jsonb

        self.conn.execute(
            """UPDATE memories SET last_used_at=%s, use_count=%s, confidence=%s,
               importance=%s, active=%s, content=%s, attrs=%s WHERE id=%s""",
            (record.last_used_at, record.use_count, record.confidence, record.importance,
             record.active, record.content, Jsonb(record.attrs), record.id),
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

    def _dict_cursor(self):
        from psycopg.rows import dict_row

        return self.conn.cursor(row_factory=dict_row)

    def get(self, record_id: str) -> MemoryRecord | None:
        with self._dict_cursor() as cur:
            cur.execute("SELECT * FROM memories WHERE id=%s", (record_id,))
            row = cur.fetchone()
        return self._hydrate(row) if row else None

    def all(self, user_id: str, tier: Tier | None = None, active_only: bool = True) -> list[MemoryRecord]:
        q = "SELECT * FROM memories WHERE user_id=%s"
        params: list = [user_id]
        if tier is not None:
            q += " AND tier=%s"; params.append(tier.value)
        if active_only:
            q += " AND active=TRUE"
        # Chronological order matters: consolidation slices "the recent window" and
        # InMemoryStore is insertion-ordered — keep Postgres consistent with it.
        q += " ORDER BY created_at ASC"
        with self._dict_cursor() as cur:
            cur.execute(q, tuple(params))
            rows = cur.fetchall()
        return [self._hydrate(r) for r in rows]

    def search(
        self, user_id: str, embedding: list[float], tier: Tier | None, k: int, active_only: bool = True
    ) -> list[tuple[MemoryRecord, float]]:
        vec = np.asarray(embedding, dtype=np.float32)
        q = "SELECT *, 1 - (embedding <=> %s) AS sim FROM memories WHERE user_id=%s AND embedding IS NOT NULL"
        params: list = [vec, user_id]
        if tier is not None:
            q += " AND tier=%s"; params.append(tier.value)
        if active_only:
            q += " AND active=TRUE"
        q += " ORDER BY embedding <=> %s LIMIT %s"
        params += [vec, k]
        with self._dict_cursor() as cur:
            cur.execute(q, tuple(params))
            rows = cur.fetchall()
        return [(self._hydrate(r), float(r["sim"])) for r in rows]


def make_store(kind: str, dsn: str, dim: int) -> MemoryStore:
    if kind == "postgres":
        return PostgresStore(dsn, dim)
    return InMemoryStore()
