from datetime import datetime, timezone

import httpx

from cubesat_gs.tests.test_pass_predictor import L1, L2, NOW


async def test_disabled_state(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/passes")
    assert r.json() == {"enabled": False, "reason": "TLE not configured", "passes": []}
    assert (await client.get("/api/passes/current")).json() is None
    assert (await client.get("/api/passes/nope/track")).status_code == 404
    r = await client.post("/api/passes/refresh-tle")
    assert r.status_code == 400 and r.json()["error"] == "no_tle_source"


async def test_enabled_passes_and_track(web_stack):
    station, sim, client = web_stack
    station.passes._clock = lambda: NOW
    await station.passes.set_tle(L1, L2)
    r = await client.get("/api/passes", params={"days": 1})
    body = r.json()
    assert body["enabled"] and len(body["passes"]) == 4
    p = body["passes"][0]
    assert p["aos"].startswith("2024-01-08T00:08:54") and abs(p["max_el"] - 21.3) < 0.2
    r = await client.get(f"/api/passes/{p['id']}/track", params={"step_s": 30})
    pts = r.json()
    assert 9 <= len(pts) <= 13 and set(pts[0]) == {"t", "az", "el", "range_km", "doppler_hz"}
    station.passes._clock = lambda: datetime.fromisoformat(p["tca"])
    cur = (await client.get("/api/passes/current")).json()
    assert cur["pass_id"] == p["id"] and abs(cur["el"] - p["max_el"]) < 0.3
    st = (await client.get("/api/status")).json()
    assert st["passes"]["current"]["pass_id"] == p["id"]


async def test_refresh_tle_via_api(web_stack, monkeypatch):
    station, sim, client = web_stack
    station.passes._tle_source = "https://tle.example/x.txt"
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, text=f"ISS\n{L1}\n{L2}\n")

    station.passes._http_factory = lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    r = await client.post("/api/passes/refresh-tle")
    assert r.status_code == 502 and r.json()["error"] == "tle_fetch_failed"
    r = await client.post("/api/passes/refresh-tle")
    assert r.status_code == 200 and r.json() == {"line1": L1, "line2": L2}
    assert station.passes.enabled


async def test_pass_history_empty(web_stack):
    station, sim, client = web_stack
    assert (await client.get("/api/passes/history")).json() == {"items": []}
