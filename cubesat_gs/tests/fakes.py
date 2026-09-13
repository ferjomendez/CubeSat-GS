"""In-memory stand-in for motor's AsyncIOMotorClient covering what mongo_backend.py uses."""
from __future__ import annotations

from typing import Any

from bson import ObjectId
from pymongo.errors import AutoReconnect, BulkWriteError, DuplicateKeyError


class _Cursor:
    def __init__(self, docs: list[dict]):
        self._docs = docs
        self.batch_size_used = None

    def sort(self, key: str, direction: int):
        self._docs = sorted(self._docs, key=lambda d: d.get(key), reverse=direction < 0)
        return self

    def limit(self, n: int):
        self._docs = self._docs[:n]
        return self

    def batch_size(self, n: int):
        self.batch_size_used = n
        return self

    def __aiter__(self):
        self._it = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration

    async def to_list(self, length=None):
        return list(self._docs)


class _Result:
    def __init__(self, inserted_id=None, inserted_ids=None):
        self.inserted_id = inserted_id
        self.inserted_ids = inserted_ids or []


def _match(doc: dict, flt: dict) -> bool:
    for k, v in flt.items():
        if isinstance(v, dict):
            x = doc.get(k)
            if "$gte" in v and (x is None or x < v["$gte"]):
                return False
            if "$lte" in v and (x is None or x > v["$lte"]):
                return False
        elif doc.get(k) != v:
            return False
    return True


class FakeCollection:
    def __init__(self, client: "FakeMotorClient"):
        self._client = client
        self.docs: list[dict] = []
        self.indexes: list[tuple] = []
        self.last_cursor = None

    def _guard(self):
        if self._client.fail:
            raise AutoReconnect("fake: connection lost")

    def _unique_sync_key_index(self) -> bool:
        return any(keys == [("sync_key", 1)] and kwargs.get("unique")
                   for keys, kwargs in self.indexes)

    def _check_dup(self, doc: dict) -> None:
        # Sparse semantics: only a document entirely MISSING the field is exempt. A real
        # MongoDB sparse unique index still indexes an explicit `sync_key: None`, so that
        # must collide like any other value -- do not exempt it.
        if "sync_key" not in doc or not self._unique_sync_key_index():
            return
        key = doc["sync_key"]
        if any("sync_key" in d and d["sync_key"] == key for d in self.docs):
            raise DuplicateKeyError(f"fake: duplicate key error, sync_key={key!r}")

    async def insert_one(self, doc: dict) -> _Result:
        self._guard()
        d = dict(doc); d.setdefault("_id", ObjectId())
        self._check_dup(d)
        self.docs.append(d)
        return _Result(inserted_id=d["_id"])

    async def insert_many(self, docs: list[dict], ordered=True) -> _Result:
        self._guard()
        ids = []
        errors = []
        for idx, doc in enumerate(docs):
            d = dict(doc); d.setdefault("_id", ObjectId())
            try:
                self._check_dup(d)
            except DuplicateKeyError as e:
                if ordered:
                    raise
                errors.append({"index": idx, "code": 11000, "errmsg": str(e)})
                continue
            self.docs.append(d)
            ids.append(d["_id"])
        if errors:
            # Mirrors motor: with ordered=False, non-duplicate documents are still inserted;
            # the error is raised after, covering only the ones that failed.
            raise BulkWriteError({"writeErrors": errors, "nInserted": len(ids)})
        return _Result(inserted_ids=ids)

    async def update_one(self, flt: dict, update: dict):
        self._guard()
        for d in self.docs:
            if _match(d, flt):
                d.update(update.get("$set", {}))
                return

    async def find_one(self, flt: dict, projection: dict | None = None):
        self._guard()
        return next((dict(d) for d in self.docs if _match(d, flt)), None)

    def find(self, flt: dict | None = None) -> _Cursor:
        self._guard()
        self.last_cursor = _Cursor([dict(d) for d in self.docs if _match(d, flt or {})])
        return self.last_cursor

    async def count_documents(self, flt: dict) -> int:
        self._guard()
        return sum(1 for d in self.docs if _match(d, flt))

    async def create_index(self, keys, **kwargs):
        self._guard()
        self.indexes.append((keys, kwargs))
        return "idx"


class FakeDatabase:
    def __init__(self, client):
        self._client = client
        self._colls: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        return self._colls.setdefault(name, FakeCollection(self._client))


class _Admin:
    def __init__(self, client):
        self._client = client

    async def command(self, name: str) -> dict:
        if self._client.fail:
            raise AutoReconnect("fake: ping failed")
        return {"ok": 1}


class FakeMotorClient:
    def __init__(self, *args: Any, fail: bool = False, **kwargs: Any):
        self.fail = fail
        self.admin = _Admin(self)
        self._dbs: dict[str, FakeDatabase] = {}
        self.closed = False

    def __getitem__(self, name: str) -> FakeDatabase:
        return self._dbs.setdefault(name, FakeDatabase(self))

    def close(self):
        self.closed = True
