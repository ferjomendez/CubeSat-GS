import asyncio
import struct
from pathlib import Path

import pytest

from cubesat_gs.core import ccsds
from cubesat_gs.core.config import CCSDSConfig
from cubesat_gs.core.events import (AlarmRaised, EventBus, PacketDecoded, PacketMalformed,
                                    PacketReceived, SequenceGap)
from cubesat_gs.core.telemetry import TelemetryDecoder, TelemetryDefError, load_definitions

DEFS = Path(__file__).resolve().parents[1] / "config" / "telemetry_defs.yaml"

EPS_YAML = """
apid_50:
  name: "EPS"
  fields:
    - {name: v_bat, type: float32, unit: V, alarm_low: 3.3, alarm_high: 4.2}
    - {name: t_bat, type: int16, scale: 0.1, unit: "°C", alarm_low: -10, alarm_high: 50}
    - {name: mode, type: uint8}
    - {name: uptime, type: uint32, unit: s}
    - {name: tag, type: string, length: 3}
    - {name: rest, type: bytes}
"""


def _pkt(apid, payload, seq=0):
    return ccsds.parse(ccsds.build(apid, payload, sequence_count=seq, packet_type=0))


def _decoder(tmp_path, text=None, scope="global"):
    path = DEFS
    if text is not None:
        path = tmp_path / "defs.yaml"
        path.write_text(text, encoding="utf-8")
    return TelemetryDecoder(EventBus(), path, CCSDSConfig(sequence_scope=scope))


def test_load_shipped_definitions():
    defs = load_definitions(DEFS)
    assert defs[10].name == "Beacon" and defs[101].name == "TM Response"
    assert defs[10].fields[0].type == "string"


def test_decode_beacon_string(tmp_path):
    d = _decoder(tmp_path)
    out = d.decode(_pkt(10, b"VLEO_BEACON_SYS_NOMINAL"))
    assert out.apid_name == "Beacon" and not out.unknown_apid and not out.partial
    assert out.fields[0].name == "message" and out.fields[0].value == "VLEO_BEACON_SYS_NOMINAL"
    assert out.fields[0].alarm is None
    assert out.as_dict() == {"message": "VLEO_BEACON_SYS_NOMINAL"}


def test_decode_structured_types_scale_alarms(tmp_path):
    d = _decoder(tmp_path, EPS_YAML)
    payload = struct.pack(">fhBI", 3.0, 555, 2, 123456) + b"abcXYZ"
    out = d.decode(_pkt(50, payload))
    f = {x.name: x for x in out.fields}
    assert f["v_bat"].value == pytest.approx(3.0) and f["v_bat"].alarm == "low" and f["v_bat"].unit == "V"
    assert f["t_bat"].value == pytest.approx(55.5) and f["t_bat"].alarm == "high"
    assert f["mode"].value == 2 and f["mode"].alarm is None
    assert f["uptime"].value == 123456
    assert f["tag"].value == "abc"
    assert f["rest"].value == b"XYZ"
    out2 = d.decode(_pkt(50, struct.pack(">fhBI", 3.8, 250, 0, 0) + b"abc"))
    f2 = {x.name: x for x in out2.fields}
    assert f2["v_bat"].alarm == "nominal" and f2["t_bat"].alarm == "nominal"
    assert f2["rest"].value == b""


def test_unknown_apid(tmp_path):
    d = _decoder(tmp_path)
    out = d.decode(_pkt(999, b"\x01\x02"))
    assert out.unknown_apid and out.apid_name == "UNKNOWN"
    assert out.fields[0].name == "raw_hex" and out.fields[0].value == "0102"


def test_truncated_payload_is_partial(tmp_path):
    d = _decoder(tmp_path, EPS_YAML)
    out = d.decode(_pkt(50, struct.pack(">f", 3.9) + b"\x00"))  # t_bat needs 2 bytes, only 1 left
    assert out.partial and "t_bat" in out.error
    assert [x.name for x in out.fields] == ["v_bat"]


def test_invalid_definitions_rejected(tmp_path):
    with pytest.raises(TelemetryDefError, match="type"):
        _decoder(tmp_path, "apid_1:\n  name: x\n  fields:\n    - {name: a, type: float64}\n")
    with pytest.raises(TelemetryDefError, match="length"):
        _decoder(tmp_path, "apid_1:\n  name: x\n  fields:\n    - {name: a, type: uint8, length: 2}\n")
    with pytest.raises(TelemetryDefError, match="scale"):
        _decoder(tmp_path, "apid_1:\n  name: x\n  fields:\n    - {name: a, type: string, scale: 2}\n")
    with pytest.raises(TelemetryDefError, match="apid"):
        _decoder(tmp_path, "beacon:\n  name: x\n  fields: []\n")


async def test_bus_flow_decoded_alarm_gap_malformed(tmp_path):
    bus = EventBus()
    path = tmp_path / "defs.yaml"
    path.write_text(EPS_YAML, encoding="utf-8")
    d = TelemetryDecoder(bus, path, CCSDSConfig())
    d.start()
    got = []

    async def on(ev):
        got.append(ev)

    for t in (PacketDecoded, AlarmRaised, SequenceGap, PacketMalformed):
        bus.subscribe(t, on)

    def rx(raw):
        bus.publish(PacketReceived(raw=raw, rssi=None, snr=None, freq_mhz=435.5))

    good = ccsds.build(50, struct.pack(">fhBI", 2.0, 0, 0, 0) + b"abc", sequence_count=0, packet_type=0)
    rx(good)
    rx(ccsds.build(50, struct.pack(">fhBI", 3.8, 0, 0, 0) + b"abc", sequence_count=3, packet_type=0))
    rx(b"\x00\x32\xc0")  # malformed
    await asyncio.sleep(0.02)

    decoded = [e for e in got if isinstance(e, PacketDecoded)]
    assert len(decoded) == 2 and decoded[0].source.raw == good
    alarms = [e for e in got if isinstance(e, AlarmRaised)]
    assert len(alarms) == 1 and alarms[0].field_name == "v_bat" and alarms[0].alarm_type == "low"
    assert alarms[0].threshold == 3.3
    gaps = [e for e in got if isinstance(e, SequenceGap)]
    assert len(gaps) == 1 and gaps[0].missed == 2 and gaps[0].apid == 50
    bad = [e for e in got if isinstance(e, PacketMalformed)]
    assert len(bad) == 1 and "short" in bad[0].reason
    assert d.last_values[50].as_dict()["v_bat"] == pytest.approx(3.8)
    d.stop()
