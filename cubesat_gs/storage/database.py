"""Storage facade: MongoDB Atlas primary with SQLite offline fallback and background sync."""
from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Callable

from pymongo.errors import BulkWriteError, PyMongoError

from cubesat_gs.core import ccsds
from cubesat_gs.core.config import DatabaseConfig
from cubesat_gs.core.events import (AlarmRaised, CommandCompleted, EventBus, PacketDecoded,
                                    PacketReceived, PacketSent, now)
from cubesat_gs.storage.mongo_backend import MongoBackend
from cubesat_gs.storage.sqlite_backend import COLLECTIONS, SQLiteBackend

log = logging.getLogger(__name__)

Ref = tuple[str, str]  # ("mongo" | "sqlite", id)
_SYNC_ORDER = ("raw_packets", "sessions", "commands", "decoded_telemetry", "alarms")
_PACKET_REF_COLLECTIONS = ("decoded_telemetry", "alarms")
_SYNC_BATCH = 200
_TIME_KEYS = ("timestamp", "start_time", "end_time")


def _restore_datetimes(doc: dict) -> None:
    """SQLite stores datetimes as ISO strings; Mongo wants real datetimes (TTL index, range queries)."""
    for k in _TIME_KEYS:
        v = doc.get(k)
        if isinstance(v, str):
            try:
                doc[k] = datetime.fromisoformat(v)
            except ValueError:
                pass


class Storage:
    def __init__(self, bus: EventBus, cfg: DatabaseConfig, base_dir: Path, *,
                 mongo_client_factory: Callable[[str], Any] | None = None,
                 sync_interval: float = 30.0, session_flush_interval: float = 60.0) -> None:
        self._bus = bus
        self._cfg = cfg
        p = Path(cfg.local_fallback_path)
        self._sqlite = SQLiteBackend(p if p.is_absolute() else Path(base_dir) / p)
        self._mongo: MongoBackend | None = (
            MongoBackend(cfg.mongo_uri, cfg.db_name, cfg.retention_days, mongo_client_factory)
            if cfg.mongo_uri else None)
        self._degraded = False
        self._sync_interval = sync_interval
        self._flush_interval = session_flush_interval
        self._refs: OrderedDict[int, tuple[PacketReceived, asyncio.Future]] = OrderedDict()
        self._tasks: list[asyncio.Task] = []
        self._sync_lock = asyncio.Lock()
        self.session: dict[str, Any] = {}
        self._session_ref: Ref | None = None

    # ---- lifecycle
    async def start(self) -> None:
        await self._sqlite.connect()
        if self._mongo is None:
            purged = await self._sqlite.purge_older_than(self._cfg.retention_days)
            if purged:
                log.info("sqlite: purged %d rows older than %d days (mongo disabled)",
                         purged, self._cfg.retention_days)
        else:
            purged = await self._sqlite.purge_synced_older_than(self._cfg.retention_days)
            if purged:
                log.info("sqlite: purged %d synced rows older than %d days", purged, self._cfg.retention_days)
        if self._mongo is not None:
            try:
                await self._mongo.connect()
            except PyMongoError as e:
                log.warning("mongo: unreachable at startup (%s); buffering to SQLite", e)
                self._degraded = True
            self._tasks.append(asyncio.create_task(self._sync_loop(), name="storage-sync"))
        else:
            log.info("mongo: MONGO_URI not set; SQLite only")
        self.session = {"start_time": now(), "end_time": None, "pass_id": None,
                        "packets_received": 0, "packets_sent": 0, "notes": ""}
        self._session_ref = await self.write("sessions", dict(self.session))
        self._tasks.append(asyncio.create_task(self._session_flush_loop(), name="storage-session"))
        for et, h in self._handlers():
            self._bus.subscribe(et, h)

    async def stop(self) -> None:
        for et, h in self._handlers():
            self._bus.unsubscribe(et, h)
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        self._tasks.clear()
        await self._bus.drain()
        self.session["end_time"] = now()
        await self._flush_session()
        if self._mongo is not None:
            await self._mongo.close()
        await self._sqlite.close()

    def _handlers(self):
        return ((PacketReceived, self._on_packet_received), (PacketSent, self._on_packet_sent),
                (PacketDecoded, self._on_decoded), (AlarmRaised, self._on_alarm),
                (CommandCompleted, self._on_command))

    # ---- routing
    @property
    def _reads(self):
        return self._mongo if (self._mongo is not None and not self._degraded) else self._sqlite

    async def write(self, collection: str, doc: dict, *, force_sqlite: bool = False) -> Ref:
        if self._mongo is not None and not self._degraded and not force_sqlite:
            try:
                return "mongo", await self._mongo.insert(collection, doc)
            except PyMongoError as e:
                log.warning("mongo: write failed (%s); switching to SQLite buffer", e)
                self._degraded = True
        return "sqlite", await self._sqlite.insert(collection, doc)

    async def _update(self, ref: Ref, collection: str, fields: dict) -> None:
        backend, id = ref
        if backend == "mongo":
            try:
                await self._mongo.update(collection, id, fields)
            except PyMongoError as e:
                log.warning("mongo: update of %s/%s failed: %s", collection, id, e)
            return
        await self._sqlite.update(collection, id, fields)
        mongo_id = await self._sqlite.mongo_id_for(collection, int(id))
        if mongo_id and self._mongo is not None and not self._degraded:
            try:
                await self._mongo.update(collection, mongo_id, fields)
            except PyMongoError:
                pass  # the SQLite copy is authoritative until next sync anyway

    # ---- reads
    async def query(self, collection: str, *, start=None, end=None, apid=None, limit: int = 100) -> list[dict]:
        return await self._reads.query(collection, start=start, end=end, apid=apid, limit=limit)

    async def iterate(self, collection: str, *, start=None, end=None, apid=None,
                      batch: int = 500) -> AsyncIterator[dict]:
        async for d in self._reads.iterate(collection, start=start, end=end, apid=apid, batch=batch):
            yield d

    async def stats(self) -> dict[str, int]:
        return {c: await self._reads.count(c) for c in COLLECTIONS}

    async def health(self) -> dict[str, Any]:
        pending = 0
        if self._mongo is not None:
            for c in COLLECTIONS:
                pending += await self._sqlite.count_unsynced(c)
        if self._mongo is None:
            mongo = "disabled"
        else:
            mongo = "degraded" if self._degraded else "ok"
        return {"mongo": mongo, "pending_sync": pending, "sqlite_path": str(self._sqlite.path)}

    # ---- packet id correlation
    def packet_ref(self, source: PacketReceived) -> asyncio.Future:
        # Keyed on id(source): CPython can reuse the address of a freed PacketReceived, so a
        # strong reference to the source is kept alongside the future for as long as the entry
        # lives in the bounded map — that pins the object and keeps its id from being reused.
        key = id(source)
        entry = self._refs.get(key)
        if entry is not None:
            return entry[1]
        fut = asyncio.get_running_loop().create_future()
        self._refs[key] = (source, fut)
        while len(self._refs) > 1000:
            self._refs.popitem(last=False)
        return fut

    async def _ref_for(self, source: PacketReceived) -> Ref | None:
        try:
            return await asyncio.wait_for(asyncio.shield(self.packet_ref(source)), 5.0)
        except asyncio.TimeoutError:
            return None

    # ---- event handlers
    async def _on_packet_received(self, ev: PacketReceived) -> None:
        fut = self.packet_ref(ev)
        peek = ccsds.peek_apid_seq(ev.raw)
        doc = {"timestamp": ev.ts, "direction": "rx", "frequency_mhz": ev.freq_mhz,
               "raw_hex": ev.raw.hex().upper(), "rssi": ev.rssi, "snr": ev.snr, "crc_valid": True,
               "apid": peek[0] if peek else None, "sequence_count": peek[1] if peek else None}
        ref = await self.write("raw_packets", doc)
        self.session["packets_received"] += 1
        if not fut.done():
            fut.set_result(ref)

    async def _on_packet_sent(self, ev: PacketSent) -> None:
        peek = ccsds.peek_apid_seq(ev.raw)
        await self.write("raw_packets", {
            "timestamp": ev.ts, "direction": "tx", "frequency_mhz": ev.freq_mhz,
            "raw_hex": ev.raw.hex().upper(), "rssi": None, "snr": None, "crc_valid": True,
            "apid": peek[0] if peek else None, "sequence_count": peek[1] if peek else None})
        self.session["packets_sent"] += 1

    async def _on_decoded(self, ev: PacketDecoded) -> None:
        ref = await self._ref_for(ev.source)
        for f in ev.decoded.fields:
            await self.write("decoded_telemetry", {
                "packet_id": ref[1] if ref else None, "timestamp": ev.source.ts, "apid": ev.packet.apid,
                "apid_name": ev.decoded.apid_name, "field_name": f.name, "field_value": f.value,
                "unit": f.unit, "alarm_status": f.alarm,
            }, force_sqlite=bool(ref and ref[0] == "sqlite"))

    async def _on_alarm(self, ev: AlarmRaised) -> None:
        ref = await self._ref_for(ev.source)
        await self.write("alarms", {
            "timestamp": ev.ts, "packet_id": ref[1] if ref else None, "apid": ev.apid,
            "field_name": ev.field_name, "value": ev.value, "threshold": ev.threshold,
            "alarm_type": ev.alarm_type,
        }, force_sqlite=bool(ref and ref[0] == "sqlite"))

    async def _on_command(self, ev: CommandCompleted) -> None:
        r = ev.record
        await self.write("commands", {
            "timestamp": r.ts, "command_name": r.name, "raw_hex_sent": r.raw_hex,
            "response_received": r.status == "responded", "response_hex": r.response_hex,
            "latency_ms": r.latency_ms, "status": r.status, "attempts": r.attempts})

    # ---- sessions
    async def _flush_session(self) -> None:
        if self._session_ref is None:
            return
        try:
            await self._update(self._session_ref, "sessions", {
                k: self.session[k] for k in ("end_time", "packets_received", "packets_sent", "notes")})
        except Exception as e:  # noqa: BLE001
            log.warning("storage: session flush failed: %s", e)

    async def _session_flush_loop(self) -> None:
        while True:
            await asyncio.sleep(self._flush_interval)
            await self._flush_session()

    # ---- sync
    async def _sync_loop(self) -> None:
        while True:
            await asyncio.sleep(self._sync_interval)
            try:
                await self.sync_now()
            except Exception as e:  # noqa: BLE001
                log.warning("storage: sync failed: %s", e)

    async def sync_now(self) -> int:
        """Upload unsynced SQLite rows to Mongo. Returns rows uploaded; 0 if Mongo is down/disabled."""
        if self._mongo is None:
            return 0
        async with self._sync_lock:
            if not await self._mongo.ping():
                self._degraded = True
                return 0
            uploaded = 0
            try:
                if self._degraded:
                    await self._mongo.ensure_indexes()  # connect() may have failed before creating them
                for c in _SYNC_ORDER:
                    while True:
                        rows = await self._sqlite.unsynced(c, _SYNC_BATCH)
                        if not rows:
                            break
                        ids, docs, keys = [], [], []
                        for rid, doc, sync_key in rows:
                            _restore_datetimes(doc)
                            if c in _PACKET_REF_COLLECTIONS:
                                pid = doc.get("packet_id")
                                if pid is not None and str(pid).isdigit():
                                    mapped = await self._sqlite.mongo_id_for("raw_packets", int(pid))
                                    if mapped is None:
                                        continue  # raw packet not uploaded yet; retry next round
                                    doc["packet_id"] = mapped
                            doc["sync_key"] = sync_key
                            ids.append(rid)
                            docs.append(doc)
                            keys.append(sync_key)
                        if not docs:
                            break
                        try:
                            mongo_ids = await self._mongo.insert_many(c, docs, ordered=False)
                        except BulkWriteError:
                            # A previous attempt may have partially landed in Atlas; re-uploading
                            # the same batch must be a no-op for rows that already made it there.
                            mongo_ids = []
                            for doc, key in zip(docs, keys):
                                existing = await self._mongo.find_id_by_sync_key(c, key)
                                mongo_ids.append(existing if existing is not None
                                                 else await self._mongo.insert(c, doc))
                        await self._sqlite.mark_synced(c, ids, mongo_ids)
                        uploaded += len(ids)
                        if len(rows) < _SYNC_BATCH:
                            break
            except PyMongoError as e:
                log.warning("mongo: sync interrupted (%s); %d rows uploaded", e, uploaded)
                self._degraded = True
                return uploaded
            if self._degraded:
                log.info("mongo: connection restored; %d buffered rows uploaded", uploaded)
            self._degraded = False
            return uploaded
