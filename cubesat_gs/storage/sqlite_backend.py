"""Local SQLite store: offline fallback and sync buffer for MongoDB Atlas."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

log = logging.getLogger(__name__)

COLLECTIONS = ("raw_packets", "decoded_telemetry", "commands", "sessions", "alarms")
TIME_FIELD = {"sessions": "start_time"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS {t} (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    apid INTEGER,
    doc TEXT NOT NULL,
    synced INTEGER NOT NULL DEFAULT 0,
    mongo_id TEXT
);
CREATE INDEX IF NOT EXISTS {t}_ts ON {t}(ts);
CREATE INDEX IF NOT EXISTS {t}_apid_ts ON {t}(apid, ts);
CREATE INDEX IF NOT EXISTS {t}_synced ON {t}(synced);
"""


def _check(collection: str) -> str:
    if collection not in COLLECTIONS:
        raise ValueError(f"unknown collection {collection!r}")
    return collection


def time_field(collection: str) -> str:
    return TIME_FIELD.get(collection, "timestamp")


def _to_utc_iso(dt: datetime) -> str:
    """Convert datetime to UTC ISO string, normalizing naive or non-UTC datetimes."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def to_jsonable(value: Any) -> Any:
    """datetime -> UTC ISO string, bytes -> hex, recursively."""
    if isinstance(value, datetime):
        return _to_utc_iso(value)
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex().upper()
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return _to_utc_iso(value)
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    return str(value)


class SQLiteBackend:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._db: aiosqlite.Connection | None = None

    # ---- lifecycle
    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        for t in COLLECTIONS:
            await self._db.executescript(_SCHEMA.format(t=t))
        await self._db.commit()
        log.info("sqlite: using %s", self.path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def ping(self) -> bool:
        try:
            await self._conn.execute("SELECT 1")
            return True
        except Exception:  # noqa: BLE001
            return False

    @property
    def _conn(self) -> aiosqlite.Connection:
        assert self._db is not None, "SQLiteBackend not connected"
        return self._db

    # ---- writes
    def _row(self, collection: str, doc: dict) -> tuple[str, int | None, str]:
        doc = to_jsonable(doc)
        ts = _iso(doc.get(time_field(collection)))
        apid = doc.get("apid")
        return ts, (int(apid) if apid is not None else None), json.dumps(doc)

    async def insert(self, collection: str, doc: dict) -> str:
        t = _check(collection)
        cur = await self._conn.execute(
            f"INSERT INTO {t}(ts, apid, doc) VALUES (?, ?, ?)", self._row(t, doc))
        await self._conn.commit()
        return str(cur.lastrowid)

    async def insert_many(self, collection: str, docs: list[dict]) -> list[str]:
        t = _check(collection)
        ids = []
        for d in docs:
            cur = await self._conn.execute(
                f"INSERT INTO {t}(ts, apid, doc) VALUES (?, ?, ?)", self._row(t, d))
            ids.append(str(cur.lastrowid))
        await self._conn.commit()
        return ids

    async def update(self, collection: str, id: str, fields: dict) -> None:
        t = _check(collection)
        cur = await self._conn.execute(f"SELECT doc FROM {t} WHERE id = ?", (int(id),))
        row = await cur.fetchone()
        if row is None:
            return
        doc = json.loads(row["doc"])
        doc.update(to_jsonable(fields))
        ts, apid, text = self._row(t, doc)
        await self._conn.execute(f"UPDATE {t} SET ts = ?, apid = ?, doc = ? WHERE id = ?",
                                 (ts, apid, text, int(id)))
        await self._conn.commit()

    # ---- reads
    @staticmethod
    def _load(row: aiosqlite.Row) -> dict:
        doc = json.loads(row["doc"])
        doc["id"] = str(row["id"])
        return doc

    async def get(self, collection: str, id: str) -> dict | None:
        t = _check(collection)
        cur = await self._conn.execute(f"SELECT id, doc FROM {t} WHERE id = ?", (int(id),))
        row = await cur.fetchone()
        return self._load(row) if row else None

    @staticmethod
    def _where(start, end, apid) -> tuple[str, list]:
        clauses, params = [], []
        if start is not None:
            clauses.append("ts >= ?"); params.append(_iso(start))
        if end is not None:
            clauses.append("ts <= ?"); params.append(_iso(end))
        if apid is not None:
            clauses.append("apid = ?"); params.append(int(apid))
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    async def query(self, collection: str, *, start=None, end=None, apid=None, limit: int = 100) -> list[dict]:
        t = _check(collection)
        where, params = self._where(start, end, apid)
        cur = await self._conn.execute(
            f"SELECT id, doc FROM {t}{where} ORDER BY ts DESC, id DESC LIMIT ?", [*params, int(limit)])
        return [self._load(r) for r in await cur.fetchall()]

    async def iterate(self, collection: str, *, start=None, end=None, apid=None,
                      batch: int = 500) -> AsyncIterator[dict]:
        t = _check(collection)
        where, params = self._where(start, end, apid)
        last_id = 0
        while True:
            sep = " AND " if where else " WHERE "
            cur = await self._conn.execute(
                f"SELECT id, doc FROM {t}{where}{sep}id > ? ORDER BY id LIMIT ?", [*params, last_id, batch])
            rows = await cur.fetchall()
            if not rows:
                return
            for r in rows:
                last_id = r["id"]
                yield self._load(r)

    async def count(self, collection: str) -> int:
        t = _check(collection)
        cur = await self._conn.execute(f"SELECT COUNT(*) AS n FROM {t}")
        return (await cur.fetchone())["n"]

    # ---- sync bookkeeping
    async def unsynced(self, collection: str, limit: int) -> list[tuple[int, dict]]:
        t = _check(collection)
        cur = await self._conn.execute(
            f"SELECT id, doc FROM {t} WHERE synced = 0 ORDER BY id LIMIT ?", (int(limit),))
        return [(r["id"], json.loads(r["doc"])) for r in await cur.fetchall()]

    async def mark_synced(self, collection: str, ids: list[int], mongo_ids: list[str]) -> None:
        t = _check(collection)
        await self._conn.executemany(
            f"UPDATE {t} SET synced = 1, mongo_id = ? WHERE id = ?",
            [(m, int(i)) for i, m in zip(ids, mongo_ids)])
        await self._conn.commit()

    async def mongo_id_for(self, collection: str, id: int) -> str | None:
        t = _check(collection)
        cur = await self._conn.execute(f"SELECT mongo_id FROM {t} WHERE id = ?", (int(id),))
        row = await cur.fetchone()
        return row["mongo_id"] if row else None

    async def purge_synced_older_than(self, days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        total = 0
        for t in COLLECTIONS:
            cur = await self._conn.execute(f"DELETE FROM {t} WHERE synced = 1 AND ts < ?", (cutoff,))
            total += cur.rowcount
        await self._conn.commit()
        return total
