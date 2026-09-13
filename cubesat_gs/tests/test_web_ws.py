import asyncio
import json

from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.tests.conftest import wait_until


class WsClient:
    """Drives hub.handle() through a fake Starlette WebSocket (no network)."""

    def __init__(self):
        self.sent: list[dict] = []
        self._incoming: asyncio.Queue = asyncio.Queue()
        self.closed: int | None = None
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def send_text(self, text: str):
        self.sent.append(json.loads(text))

    async def receive_text(self) -> str:
        item = await self._incoming.get()
        if item is None:
            from starlette.websockets import WebSocketDisconnect
            raise WebSocketDisconnect(1000)
        return item

    async def close(self, code: int = 1000):
        self.closed = code
        self._incoming.put_nowait(None)

    def disconnect(self):
        self._incoming.put_nowait(None)

    def of(self, t):
        return [m for m in self.sent if m["type"] == t]


async def _connect(web_stack):
    station, sim, client = web_stack
    hub = client._transport.app.state.hub
    ws = WsClient()
    task = asyncio.create_task(hub.handle(ws))
    await wait_until(lambda: any(m["type"] == "snapshot" for m in ws.sent))
    return hub, ws, task


async def test_snapshot_on_connect(web_stack):
    station, sim, client = web_stack
    hub, ws, task = await _connect(web_stack)
    snap = ws.of("snapshot")[0]["data"]
    assert snap["status"]["serial"]["connected"] is True
    assert isinstance(snap["feed"], list) and snap["telemetry_latest"] == {}
    assert snap["pending_command"] is None and snap["next_pass"] is None
    assert hub.client_count == 1
    ws.disconnect()
    await task
    assert hub.client_count == 0


async def test_beacon_produces_packet_and_telemetry_deltas(web_stack):
    station, sim, client = web_stack
    hub, ws, task = await _connect(web_stack)
    await station.freq.set_mode(Mode.BEACON_LISTEN)
    await wait_until(lambda: len(ws.of("packet")) >= 1 and len(ws.of("telemetry")) >= 1)
    pkt = ws.of("packet")[0]["data"]
    assert pkt["direction"] == "rx" and pkt["apid"] == 10 and pkt["kind"] == "beacon"
    assert pkt["apid_name"] == "Beacon" and pkt["summary"] == "VLEO_BEACON_SYS_NOMINAL"
    assert pkt["fields"][0]["name"] == "message" and pkt["freq_mhz"] == 437.25
    assert pkt["raw_hex"] == pkt["raw_hex"].upper() and "-" in pkt["id"]
    tm = ws.of("telemetry")[0]["data"]
    assert tm["apid"] == 10 and tm["fields"][0]["value"] == "VLEO_BEACON_SYS_NOMINAL"
    assert any(m["data"]["frequency"]["mode"] == "beacon_listen" for m in ws.of("status"))
    assert len(hub.feed) >= 1 and hub.feed[-1]["kind"] == "beacon"
    ws.disconnect()
    await task


async def test_ping_pong_and_bad_message_ignored(web_stack):
    hub, ws, task = await _connect(web_stack)
    ws._incoming.put_nowait("not json")
    ws._incoming.put_nowait(json.dumps({"type": "ping"}))
    await wait_until(lambda: len(ws.of("pong")) == 1)
    ws.disconnect()
    await task


async def test_slow_client_is_dropped(web_stack):
    station, sim, client = web_stack
    hub = client._transport.app.state.hub
    hub._queue_size = 3

    class StuckWs(WsClient):
        async def send_text(self, text):
            if json.loads(text)["type"] != "snapshot":
                await asyncio.Event().wait()  # never returns → queue fills
            self.sent.append(json.loads(text))

    ws = StuckWs()
    task = asyncio.create_task(hub.handle(ws))
    await wait_until(lambda: ws.accepted)
    for _ in range(6):
        sim.inject_rx(bytes.fromhex("000AC0000018564C454F5F424541434F4E5F5359535F4E4F4D494E414C"))
        await asyncio.sleep(0.01)
    await wait_until(lambda: ws.closed == 1013, timeout=3.0)
    await task
    assert hub.client_count == 0


async def test_feed_snapshot_includes_recent(web_stack):
    station, sim, client = web_stack
    await station.freq.set_mode(Mode.BEACON_LISTEN)
    hub = client._transport.app.state.hub
    await wait_until(lambda: len(hub.feed) >= 2)
    hub2, ws, task = await _connect(web_stack)
    assert len(ws.of("snapshot")[0]["data"]["feed"]) >= 2
    ws.disconnect()
    await task


async def test_snapshot_send_failure_drops_client(web_stack):
    station, sim, client = web_stack
    hub = client._transport.app.state.hub

    class FailingSnapshotWs(WsClient):
        async def send_text(self, text):
            if json.loads(text)["type"] == "snapshot":
                raise RuntimeError("snapshot send failed")
            self.sent.append(json.loads(text))

    ws = FailingSnapshotWs()
    task = asyncio.create_task(hub.handle(ws))
    try:
        await task
    except RuntimeError:
        pass  # Expected: snapshot send fails
    assert hub.client_count == 0


async def test_pong_on_full_queue_drops_client(web_stack):
    station, sim, client = web_stack
    hub = client._transport.app.state.hub
    hub._queue_size = 2  # Very small to trigger QueueFull quickly

    class SlowSendWs(WsClient):
        async def send_text(self, text):
            if json.loads(text)["type"] != "snapshot":
                await asyncio.Event().wait()  # Block sender on all non-snapshot
            self.sent.append(json.loads(text))

    ws = SlowSendWs()
    task = asyncio.create_task(hub.handle(ws))
    await wait_until(lambda: ws.accepted)
    # Send 3 pings; first fills queue, subsequent ones hit QueueFull
    ws._incoming.put_nowait(json.dumps({"type": "ping"}))
    ws._incoming.put_nowait(json.dumps({"type": "ping"}))
    ws._incoming.put_nowait(json.dumps({"type": "ping"}))
    await wait_until(lambda: ws.closed == 1013, timeout=3.0)
    await task
    assert hub.client_count == 0
