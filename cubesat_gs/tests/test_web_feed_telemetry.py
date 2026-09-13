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
    """Verify no duplicate rows when multiple rows share identical timestamps.

    Tests cursor pagination with >=12 rows to verify correct handling when ids
    cross digit boundaries (e.g., 9 vs 11) where lexicographic comparison fails.
    """
    station, sim, client = web_stack
    base = datetime(2026, 9, 13, 0, 0, tzinfo=timezone.utc)
    # Write 12 rows with identical timestamp (ids will span 1..12)
    for i in range(12):
        await station.storage.write("raw_packets", {
            "timestamp": base, "apid": 10, "direction": "rx", "raw_hex": f"0A{i:02X}" + "00" * 10,
            "sequence_count": i, "rssi": -100.0, "snr": 5.0, "frequency_mhz": 437.0})

    # Paginate with limit=5 through all rows
    all_ids = []
    next_before = None
    page_count = 0
    while True:
        params = {"limit": 5}
        if next_before:
            params["before"] = next_before
        r = await client.get("/api/packets", params=params)
        assert r.status_code == 200
        body = r.json()
        page_ids = [item["id"] for item in body["items"]]
        all_ids.extend(page_ids)
        next_before = body["next_before"]
        page_count += 1
        if not next_before:
            break
        assert page_count < 10, "Infinite loop detected in pagination"

    # Verify no duplicates and full coverage
    assert len(all_ids) == len(set(all_ids)), f"Duplicate IDs found: {[id for id in all_ids if all_ids.count(id) > 1]}"
    assert len(all_ids) == 12, f"Expected 12 rows, got {len(all_ids)}: {all_ids}"


async def test_cursor_pagination_many_identical_timestamps(web_stack):
    """Test bounded refetch loop with many rows sharing identical timestamp.

    Verifies that when many rows (>limit) share a cursor timestamp, the refetch
    loop correctly fetches more rows until a full page is available.
    """
    station, sim, client = web_stack
    base = datetime(2026, 9, 13, 0, 0, tzinfo=timezone.utc)
    # Write 20 rows with identical timestamp
    for i in range(20):
        await station.storage.write("raw_packets", {
            "timestamp": base, "apid": 10, "direction": "rx", "raw_hex": f"0A{i:02X}" + "00" * 10,
            "sequence_count": i, "rssi": -100.0, "snr": 5.0, "frequency_mhz": 437.0})

    # Paginate to the end with limit=3
    all_ids = []
    next_before = None
    page_count = 0
    while True:
        params = {"limit": 3}
        if next_before:
            params["before"] = next_before
        r = await client.get("/api/packets", params=params)
        assert r.status_code == 200
        body = r.json()
        page_ids = [item["id"] for item in body["items"]]
        all_ids.extend(page_ids)
        next_before = body["next_before"]
        page_count += 1
        if not next_before:
            break
        assert page_count < 20, "Too many pages for 20 rows with limit=3"

    # Verify no duplicates and full coverage
    assert len(all_ids) == len(set(all_ids)), f"Duplicate IDs found"
    assert len(all_ids) == 20, f"Expected 20 rows, got {len(all_ids)}"


async def test_telemetry_field_order(web_stack):
    """Verify decoded fields appear in definition order for multi-field packets."""
    station, sim, client = web_stack
    base = datetime(2026, 9, 13, 0, 0, tzinfo=timezone.utc)

    # Write a raw packet
    ref = await station.storage.write("raw_packets", {
        "timestamp": base, "apid": 50, "direction": "rx",
        "raw_hex": "3200" + "00" * 10, "sequence_count": 0,
        "rssi": -100.0, "snr": 5.0, "frequency_mhz": 437.0})

    # Extract packet_id from the ref (Ref is ("sqlite"|"mongo", id_string))
    packet_id = ref[1]

    # Write three decoded_telemetry rows with fields in order a, b, c
    for i, field_name in enumerate(["a", "b", "c"]):
        await station.storage.write("decoded_telemetry", {
            "packet_id": packet_id, "timestamp": base, "apid": 50,
            "apid_name": "Test", "field_name": field_name,
            "field_value": float(i), "unit": "V", "alarm_status": "nominal"})

    # Fetch the packet and verify field order
    r = await client.get("/api/packets", params={"limit": 10, "apid": 50})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) > 0, "No packets found"
    item = items[0]
    assert item["apid"] == 50 and item["fields"]
    actual_order = [f["name"] for f in item["fields"]]
    assert actual_order == ["a", "b", "c"], f"Field order mismatch: expected ['a', 'b', 'c'], got {actual_order}"


async def test_cursor_pagination_refetch_loop_exhaustion(web_stack):
    """Test refetch loop exhaustion: forces multiple refetch iterations without early break.

    This tests the critical fix: rows = filtered assignment must happen after the loop,
    not just on break. Ensures that if the loop exhausts all 4 iterations without
    breaking early, unfiltered rows don't leak through to pagination.
    """
    station, sim, client = web_stack
    base = datetime(2026, 9, 13, 0, 0, tzinfo=timezone.utc)
    # Write 30 rows with identical timestamp at a unique APID to avoid test data mixing
    num_rows = 30
    unique_apid = 77  # Use a unique APID to avoid interference with other test rows
    for i in range(num_rows):
        await station.storage.write("raw_packets", {
            "timestamp": base, "apid": unique_apid, "direction": "rx",
            "raw_hex": f"{unique_apid:02X}{i:02X}" + "00" * 10,
            "sequence_count": i, "rssi": -100.0, "snr": 5.0, "frequency_mhz": 437.0})

    # Paginate to the end with limit=2
    all_ids = []
    next_before = None
    page_count = 0
    while True:
        params = {"limit": 2, "apid": unique_apid}
        if next_before:
            params["before"] = next_before
        r = await client.get("/api/packets", params=params)
        assert r.status_code == 200
        body = r.json()
        page_ids = [item["id"] for item in body["items"]]
        all_ids.extend(page_ids)
        next_before = body["next_before"]
        page_count += 1
        if not next_before:
            break
        assert page_count <= 20, f"Too many pages ({page_count})"

    # Critical test: verify no duplicates across pages (main defect from loop exhaustion bug)
    # This catches the bug where rows = filtered wasn't set after loop exhaustion,
    # which would cause unfiltered rows to leak through and create duplicates
    assert len(all_ids) > 0, "No rows returned from pagination"
    assert len(all_ids) == len(set(all_ids)), f"Duplicate IDs found: pagination returned same row twice. IDs: {all_ids}"
