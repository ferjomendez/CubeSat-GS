"""MongoDB Atlas backend (motor). Errors propagate as pymongo.errors.PyMongoError."""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Callable

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from cubesat_gs.storage.sqlite_backend import COLLECTIONS, time_field

log = logging.getLogger(__name__)

_TTL_COLLECTIONS = ("raw_packets", "decoded_telemetry")
_APID_COLLECTIONS = ("raw_packets", "decoded_telemetry")


def to_bsonable(value: Any) -> Any:
    """bytes -> hex string, recursively; datetimes are kept (BSON native)."""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex().upper()
    if isinstance(value, dict):
        return {k: to_bsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_bsonable(v) for v in value]
    return value


def _check(collection: str) -> str:
    if collection not in COLLECTIONS:
        raise ValueError(f"unknown collection {collection!r}")
    return collection


def _public(doc: dict) -> dict:
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    return d


class MongoBackend:
    def __init__(self, uri: str, db_name: str, retention_days: int,
                 client_factory: Callable[[str], Any] | None = None) -> None:
        self._uri = uri
        self._db_name = db_name
        self._retention_days = retention_days
        self._factory = client_factory or self._default_factory
        self._client: Any = None
        self._db: Any = None

    @staticmethod
    def _default_factory(uri: str) -> Any:
        from motor.motor_asyncio import AsyncIOMotorClient
        return AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)

    # ---- lifecycle
    async def connect(self) -> None:
        self._client = self._factory(self._uri)
        self._db = self._client[self._db_name]
        await self._client.admin.command("ping")
        await self.ensure_indexes()
        log.info("mongo: connected to database %s", self._db_name)

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    async def ping(self) -> bool:
        try:
            await self._client.admin.command("ping")
            return True
        except (PyMongoError, AttributeError):
            return False

    async def ensure_indexes(self) -> None:
        for c in COLLECTIONS:
            await self._db[c].create_index([(time_field(c), DESCENDING)])
        for c in _APID_COLLECTIONS:
            await self._db[c].create_index([("apid", ASCENDING)])
            await self._db[c].create_index([("apid", ASCENDING), ("timestamp", ASCENDING)])
        for c in _TTL_COLLECTIONS:
            await self._db[c].create_index(
                [("timestamp", ASCENDING)], name="ttl_timestamp",
                expireAfterSeconds=int(self._retention_days) * 86400)

    # ---- writes
    async def insert(self, collection: str, doc: dict) -> str:
        res = await self._db[_check(collection)].insert_one(to_bsonable(doc))
        return str(res.inserted_id)

    async def insert_many(self, collection: str, docs: list[dict]) -> list[str]:
        if not docs:
            return []
        res = await self._db[_check(collection)].insert_many([to_bsonable(d) for d in docs], ordered=True)
        return [str(i) for i in res.inserted_ids]

    async def update(self, collection: str, id: str, fields: dict) -> None:
        await self._db[_check(collection)].update_one({"_id": ObjectId(id)}, {"$set": to_bsonable(fields)})

    # ---- reads
    @staticmethod
    def _filter(collection: str, start, end, apid) -> dict:
        flt: dict = {}
        tf = time_field(collection)
        if start is not None or end is not None:
            rng = {}
            if start is not None:
                rng["$gte"] = start
            if end is not None:
                rng["$lte"] = end
            flt[tf] = rng
        if apid is not None:
            flt["apid"] = int(apid)
        return flt

    async def get(self, collection: str, id: str) -> dict | None:
        doc = await self._db[_check(collection)].find_one({"_id": ObjectId(id)})
        return _public(doc) if doc else None

    async def query(self, collection: str, *, start=None, end=None, apid=None, limit: int = 100) -> list[dict]:
        c = _check(collection)
        cur = self._db[c].find(self._filter(c, start, end, apid)).sort(time_field(c), DESCENDING).limit(int(limit))
        return [_public(d) async for d in cur]

    async def iterate(self, collection: str, *, start=None, end=None, apid=None,
                      batch: int = 500) -> AsyncIterator[dict]:
        c = _check(collection)
        cur = self._db[c].find(self._filter(c, start, end, apid)).sort(time_field(c), ASCENDING).batch_size(int(batch))
        async for d in cur:
            yield _public(d)

    async def count(self, collection: str) -> int:
        return await self._db[_check(collection)].count_documents({})
