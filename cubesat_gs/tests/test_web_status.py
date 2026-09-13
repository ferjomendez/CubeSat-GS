async def test_status_shape(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["serial"]["connected"] is True
    assert body["frequency"] == {"mode": "tctm", "mhz": 435.5}
    assert body["storage"]["mongo"] == "disabled"
    assert body["passes"]["enabled"] is False
    assert body["pending_command"] is None
    assert "packets_received" in body["session"]


async def test_health_shape(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["mongo"] == "disabled" and body["pending_sync"] == 0
    assert body["web"] == {"clients": 0}


async def test_unknown_api_path_is_json_404(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/nope")
    assert r.status_code == 404 and r.json()["error"] == "not_found"
