import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.tests.conftest import wait_until
from cubesat_gs.web.lttb import lttb


def test_lttb_keeps_endpoints_and_caps():
    pts = [(float(i), float((i * 7919) % 101)) for i in range(1000)]
    out = lttb(pts, 50)
    assert len(out) == 50 and out[0] == pts[0] and out[-1] == pts[-1]
    assert lttb(pts, 5000) == pts and lttb(pts[:2], 1) == pts[:2] and lttb([], 10) == []


async def _seed(station, n=5):
    await station.freq.set_mode(Mode.BEACON_LISTEN)
    await wait_until(lambda: len(station.decoder.last_values) >= 1)
    sim_wait = 0.12 * n
    await asyncio.sleep(sim_wait)
    await station.freq.set_mode(Mode.TCTM)
    await station.bus.drain()


async def test_packets_paging_and_filters(web_stack):
    station, sim, client = web_stack
    await _seed(station, 6)
    await asyncio.sleep(0.1)
    r = await client.get("/api/packets", params={"limit": 3})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 3 and body["next_before"]
    first = body["items"][0]
    assert first["direction"] == "rx" and first["kind"] == "beacon" and first["fields"][0]["name"] == "message"
    assert first["summary"] == "VLEO_BEACON_SYS_NOMINAL" and first["apid_name"] == "Beacon"
    r2 = await client.get("/api/packets", params={"limit": 3, "before": body["next_before"]})
    ids1 = {i["id"] for i in body["items"]}
    assert all(i["id"] not in ids1 for i in r2.json()["items"])
    assert all(i["ts"] <= body["items"][-1]["ts"] for i in r2.json()["items"])
    r3 = await client.get("/api/packets", params={"apid": 999})
    assert r3.json()["items"] == [] and r3.json()["next_before"] is None
    r4 = await client.get("/api/packets", params={"direction": "tx"})
    assert r4.json()["items"] == []
    r5 = await client.get("/api/packets", params={"limit": 9999})
    assert r5.status_code == 422


async def test_telemetry_latest_and_definitions(web_stack):
    station, sim, client = web_stack
    await _seed(station, 2)
    r = await client.get("/api/telemetry/latest")
    body = r.json()
    assert body["latest"]["10"]["fields"][0]["value"] == "VLEO_BEACON_SYS_NOMINAL"
    defs = {d["apid"]: d for d in body["definitions"]}
    assert defs[10]["name"] == "Beacon" and defs[101]["fields"][0]["name"] == "response_data"
    r = await client.get("/api/telemetry/definitions")
    assert "apid_10" in r.json()["yaml"] and len(r.json()["definitions"]) == 2


async def test_telemetry_history_downsamples(web_stack, tmp_path):
    station, sim, client = web_stack
    base = datetime(2026, 9, 13, 0, 0, tzinfo=timezone.utc)
    for i in range(300):
        await station.storage.write("decoded_telemetry", {
            "packet_id": None, "timestamp": base + timedelta(seconds=i), "apid": 50, "apid_name": "EPS",
            "field_name": "v_bat", "field_value": 3.0 + (i % 10) / 10, "unit": "V", "alarm_status": "nominal"})
    r = await client.get("/api/telemetry/history", params={"apid": 50, "field": "v_bat", "max_points": 40,
                                                            "start": base.isoformat(),
                                                            "end": (base + timedelta(seconds=400)).isoformat()})
    assert r.status_code == 200
    body = r.json()
    assert body["apid"] == 50 and body["field"] == "v_bat" and body["unit"] == "V"
    assert body["total_rows"] == 300 and len(body["points"]) == 40
    assert body["points"][0]["t"] < body["points"][-1]["t"]
    r = await client.get("/api/telemetry/history", params={"apid": 50, "field": "nope"})
    assert r.json()["points"] == [] and r.json()["total_rows"] == 0
    r = await client.get("/api/telemetry/history", params={"apid": 10, "field": "message"})
    assert r.status_code == 422  # non-numeric field


async def test_cursor_pagination_identical_timestamps(web_stack):
    """Verify no duplicate rows when multiple rows share identical timestamps."""
    station, sim, client = web_stack
    base = datetime(2026, 9, 13, 0, 0, tzinfo=timezone.utc)
    # Write >=3 rows with identical timestamp
    for i in range(5):
        await station.storage.write("raw_packets", {
            "timestamp": base, "apid": 10, "direction": "rx", "raw_hex": f"0A{i:02X}" + "00" * 10,
            "sequence_count": i, "rssi": -100.0, "snr": 5.0, "frequency_mhz": 437.0})
    # Page with limit=2, verify no duplicates in multi-page fetch
    r1 = await client.get("/api/packets", params={"limit": 2})
    assert r1.status_code == 200
    body1 = r1.json()
    ids1 = {item["id"] for item in body1["items"]}
    assert len(ids1) == 2 and body1["next_before"]
    r2 = await client.get("/api/packets", params={"limit": 2, "before": body1["next_before"]})
    assert r2.status_code == 200
    body2 = r2.json()
    ids2 = {item["id"] for item in body2["items"]}
    assert len(ids2) == 2 and body2["next_before"]
    # Verify no overlap between pages
    assert len(ids1 & ids2) == 0, f"Duplicate IDs across pages: {ids1 & ids2}"


async def test_telemetry_field_order(web_stack):
    """Verify decoded fields appear in definition order for multi-field packets."""
    station, sim, client = web_stack
    await _seed(station, 2)
    # Get beacon packets (APID 10) which have fields
    r = await client.get("/api/packets", params={"limit": 100, "apid": 10})
    assert r.status_code == 200
    items = r.json()["items"]
    beacon = next((i for i in items if i["apid"] == 10 and i["fields"]), None)
    assert beacon is not None, "No Beacon packet with fields found"
    # Verify field order matches definition
    defs = station.decoder.definitions[10]
    expected_order = [f.name for f in defs.fields]
    actual_order = [f["name"] for f in beacon["fields"]]
    assert actual_order == expected_order, f"Field order mismatch: expected {expected_order}, got {actual_order}"
