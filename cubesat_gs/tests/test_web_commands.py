import asyncio

from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.tests.conftest import wait_until


async def test_registry_lists_ping(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/commands")
    assert r.status_code == 200
    ping = next(c for c in r.json() if c["name"] == "PING")
    assert ping["apid"] == 100 and ping["response_apid"] == 101 and ping["critical"] is False
    assert ping["payload_hex"] == "50494E47" and ping["payload_text"] == "PING"


async def test_send_ping_ok_and_history(web_stack):
    station, sim, client = web_stack
    r = await client.post("/api/commands/PING", json={"confirm": False})
    assert r.status_code == 200
    rec = r.json()
    assert rec["status"] == "responded" and rec["response_hex"].startswith("0065") and rec["pending"] is False
    await asyncio.sleep(0.05)
    h = await client.get("/api/commands/history")
    assert h.json()["items"][0]["name"] == "PING" and h.json()["items"][0]["status"] == "responded"
    r = await client.post("/api/commands/NOPE", json={})
    assert r.status_code == 404 and r.json()["error"] == "unknown_command"


async def test_critical_and_raw_require_confirm(web_stack, tmp_path):
    station, sim, client = web_stack
    from cubesat_gs.core.telecommand import CommandDef
    station.telecommand.commands["REBOOT"] = CommandDef("REBOOT", "reboot", 100, b"\x01\xff", None, 1.0, True)
    r = await client.post("/api/commands/REBOOT", json={"confirm": False})
    assert r.status_code == 403 and r.json()["error"] == "confirm_required"
    r = await client.post("/api/commands/REBOOT", json={"confirm": True})
    assert r.status_code == 200 and r.json()["status"] == "acked"
    r = await client.post("/api/commands/raw", json={"hex": "DEADBEEF"})
    assert r.status_code == 403
    r = await client.post("/api/commands/raw", json={"hex": "XYZ", "confirm": True})
    assert r.status_code == 422
    r = await client.post("/api/commands/raw", json={"hex": "DE AD BE EF", "confirm": True})
    assert r.status_code == 200 and r.json()["name"] == "RAW" and sim.received_tx[-1] == b"\xde\xad\xbe\xef"


async def test_busy_wrong_mode_disconnected(web_stack):
    station, sim, client = web_stack
    sim.silent = True
    t = asyncio.create_task(client.post("/api/commands/PING", json={}))
    await wait_until(lambda: station.telecommand.pending is not None)
    r = await client.post("/api/commands/PING", json={})
    assert r.status_code == 409 and r.json()["error"] == "command_busy"
    sim.silent = False
    first = await t
    assert first.status_code == 200 and first.json()["status"] in ("timeout", "failed")
    await station.freq.set_mode(Mode.BEACON_LISTEN)
    r = await client.post("/api/commands/PING", json={})
    assert r.status_code == 400 and r.json()["error"] == "wrong_mode"
    await station.freq.set_mode(Mode.TCTM)
    await station.serial.stop()
    r = await client.post("/api/commands/PING", json={})
    assert r.status_code == 503
    await station.serial.start()
    await wait_until(lambda: station.serial.connected)


async def test_command_started_event_is_published(web_stack):
    from cubesat_gs.core.events import CommandStarted
    station, sim, client = web_stack
    got = []
    station.bus.subscribe(CommandStarted, lambda e: _push(got, e))
    await client.post("/api/commands/PING", json={})
    await wait_until(lambda: len(got) == 1)
    assert got[0].name == "PING" and got[0].raw_hex.endswith("50494E47")


async def _push(lst, e):
    lst.append(e)
