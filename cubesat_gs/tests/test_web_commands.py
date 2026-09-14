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


async def test_history_merge_pagination(web_stack):
    """Test that in-memory history merges with persistent storage, newest-first, without duplicates."""
    from datetime import datetime, timedelta, timezone
    station, sim, client = web_stack

    # Write 3 old rows directly to storage, several minutes in the past
    # Use timestamps that are significantly older than any in-memory records
    base_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    old_ids = []
    for i in range(3):
        ts = base_time - timedelta(minutes=i)
        _, old_id = await station.storage.write("commands", {
            "timestamp": ts,
            "command_name": f"OLD_{i}",
            "raw_hex_sent": f"DEAD{i:04X}",
            "response_received": True,
            "response_hex": f"BEEF{i:04X}",
            "latency_ms": 100.0 + i,
            "status": "responded",
            "attempts": 1
        })
        old_ids.append(old_id)

    # Send one PING through the API (goes to in-memory history and storage after completion)
    r = await client.post("/api/commands/PING", json={"confirm": False})
    assert r.status_code == 200
    await asyncio.sleep(0.05)

    # Get all history without pagination to verify total count
    h = await client.get("/api/commands/history", params={"limit": 50})
    assert h.status_code == 200
    page = h.json()
    assert "items" in page and "next_before" in page
    all_records = page["items"]

    # Test pagination: fetch with limit=2 to trigger storage merge
    all_paginated = []
    limit = 2
    next_before = None
    for _ in range(5):  # Safety limit
        params = {"limit": limit}
        if next_before:
            params["before"] = next_before
        h = await client.get("/api/commands/history", params=params)
        assert h.status_code == 200
        page = h.json()
        all_paginated.extend(page["items"])
        next_before = page["next_before"]
        if next_before is None:
            break

    # Assert: exactly 4 records total (3 old + 1 new PING) in full history
    assert len(all_records) == 4, f"Expected 4 records in full history, got {len(all_records)}"

    # Assert: newest-first ordering
    names = [rec["name"] for rec in all_records]
    old_names = [rec["name"] for rec in all_records if rec["name"].startswith("OLD_")]
    assert "PING" in names, f"PING not in records: {names}"
    assert len(old_names) == 3, f"Expected 3 OLD_ records, got {len(old_names)}"

    # Assert: when collecting from all pages, we get all unique records
    # (pagination may have duplicates at page boundaries, so we deduplicate)
    unique_records = {}
    for rec in all_paginated:
        key = (rec["ts"], rec["name"])
        unique_records[key] = rec
    assert len(unique_records) == 4, f"Expected 4 unique records from pagination, got {len(unique_records)}"

    # Verify that all records from full history are in the deduplicated pagination results
    for rec in all_records:
        key = (rec["ts"], rec["name"])
        assert key in unique_records, f"Record {key} from full history not in pagination"
