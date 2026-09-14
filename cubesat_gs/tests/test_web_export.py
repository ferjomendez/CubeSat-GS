import asyncio

from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.tests.conftest import wait_until


async def test_export_csv_download(web_stack):
    station, sim, client = web_stack
    await station.freq.set_mode(Mode.BEACON_LISTEN)
    await wait_until(lambda: station.storage.session["packets_received"] >= 2)
    await asyncio.sleep(0.05)
    r = await client.post("/api/export", json={"collection": "raw_packets", "fmt": "csv"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="raw_packets-' in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("id,timestamp,direction") and len(lines) >= 3
    r = await client.post("/api/export", json={"collection": "nope"})
    assert r.status_code == 422
    r = await client.post("/api/export", json={"collection": "alarms", "fmt": "json"})
    assert r.status_code == 200 and r.json() == []
