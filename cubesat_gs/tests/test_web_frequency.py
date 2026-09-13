async def test_get_and_put_frequency(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/frequency")
    assert r.json()["mode"] == "tctm" and r.json()["presets"] == {"tctm": 435.5, "beacon": 437.25}
    r = await client.put("/api/frequency", json={"mode": "beacon_listen"})
    assert r.status_code == 200 and r.json()["mhz"] == 437.25 and sim.freq == 437.25
    assert r.json()["history"][-1]["mode"] == "beacon_listen"
    r = await client.put("/api/frequency", json={"mode": "custom"})
    assert r.status_code == 422
    r = await client.put("/api/frequency", json={"mode": "custom", "mhz": 436.0})
    assert r.status_code == 200 and sim.freq == 436.0
    sim.silent = True
    r = await client.put("/api/frequency", json={"mode": "tctm"})
    assert r.status_code == 504 and r.json()["error"] == "modem_timeout"
    sim.silent = False
    r = await client.put("/api/frequency", json={"mode": "tctm"})
    assert r.status_code == 200
