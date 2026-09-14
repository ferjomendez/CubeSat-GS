from pathlib import Path

from httpx import ASGITransport, AsyncClient

from cubesat_gs.web.app import create_app


async def test_spa_fallback_and_assets(web_stack, tmp_path):
    station, sim, client = web_stack
    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<!doctype html><title>GS</title>", encoding="utf-8")
    (static / "assets" / "app-abc123.js").write_text("console.log(1)", encoding="utf-8")
    app = create_app(station, static_dir=static)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        for path in ("/", "/telemetry", "/passes/abc"):
            r = await c.get(path)
            assert r.status_code == 200 and "<title>GS</title>" in r.text, path
        r = await c.get("/assets/app-abc123.js")
        assert r.status_code == 200 and "javascript" in r.headers["content-type"]
        assert (await c.get("/assets/missing.js")).status_code == 404
        assert (await c.get("/api/nope")).status_code == 404
        r = await c.get("/api")
        assert r.status_code == 404 and r.json()["error"] == "not_found"


async def test_missing_bundle_is_503(web_stack):
    station, sim, client = web_stack  # fixture uses a non-existent static dir
    r = await client.get("/")
    assert r.status_code == 503 and r.json()["error"] == "dashboard_not_built"
