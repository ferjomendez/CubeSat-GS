"""Guard: every Pydantic model + field name in web/schemas.py must appear in frontend/src/api/types.ts."""
import inspect
import re
from pathlib import Path

from pydantic import BaseModel

from cubesat_gs.web import schemas

TYPES_TS = Path(__file__).resolve().parents[1] / "web" / "frontend" / "src" / "api" / "types.ts"


def test_types_ts_mirrors_schemas():
    text = TYPES_TS.read_text(encoding="utf-8")
    missing = []
    for name, cls in inspect.getmembers(schemas, inspect.isclass):
        if not issubclass(cls, BaseModel) or cls is BaseModel or name == "WsMessage":
            continue
        if not re.search(rf"\b(interface|type)\s+{name}\b", text):
            missing.append(name)
            continue
        for field in cls.model_fields:
            if not re.search(rf"\b{field}\??:", text):
                missing.append(f"{name}.{field}")
    assert not missing, f"types.ts is missing: {missing}"


async def test_schema_endpoint(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/schema.json")
    assert r.status_code == 200 and "StatusOut" in r.json() and "FeedEntry" in r.json()
