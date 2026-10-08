"""cFS OBC protocol (github.com/vaquitson/uai_obc mision_doc/functionality.md): framing, args, decoding, end to end."""
import dataclasses
import struct
from pathlib import Path

import pytest

from cubesat_gs.core import ccsds, cfs
from cubesat_gs.core.config import FrequencyConfig
from cubesat_gs.core.events import EventBus
from cubesat_gs.core.frequency_manager import FrequencyManager, Mode
from cubesat_gs.core.telecommand import load_commands
from cubesat_gs.core.telemetry import ApidDef, decode_payload, load_definitions
from cubesat_gs.tests.serial_simulator import ModemSimulator

CONFIG = Path(__file__).resolve().parents[1] / "config"
OPEN_TLM_ARGS = (cfs.ArgDef("downlink_freq", "freq", 16), cfs.ArgDef("uplink_freq", "freq", 16, optional=True))


def test_split_msg_id():
    assert cfs.split_msg_id(0x187A) == (1, True, 122)  # TELECOM_CMD_MID: command, sec hdr, APID 122
    assert cfs.split_msg_id(123) == (0, False, 123)    # plain-number MIDs keep their raw bits
    with pytest.raises(ValueError):
        cfs.split_msg_id(0x2000)


def test_build_command_header_and_checksum():
    payload = cfs.encode_args(OPEN_TLM_ARGS, {"downlink_freq": 436, "uplink_freq": "435.5"})
    raw = cfs.build_command(ccsds.PacketBuilder(length_includes_crc=False), 0x187A, 2, payload)
    assert raw[:7].hex().upper() == "187AC000002102"  # length = 40 - 7, function code 2
    assert len(raw) == 40 and cfs.checksum(raw) == 0  # CFE_MSG_ValidateChecksum
    assert raw[8:24] == b"436,000".ljust(16, b"\x00") and raw[24:40] == b"435,500".ljust(16, b"\x00")


def test_build_command_counts_sequence_per_apid():
    b = ccsds.PacketBuilder(length_includes_crc=False)
    first, second = cfs.build_command(b, 123, 0, b""), cfs.build_command(b, 123, 0, b"")
    assert first.hex().upper()[:12] == "007BC0000001" and second[2:4] == b"\xc0\x01"


def test_encode_args_errors_and_types():
    assert cfs.encode_args(OPEN_TLM_ARGS, {"downlink_freq": "437,25"})[16:] == bytes(16)  # empty uplink
    with pytest.raises(cfs.CommandArgError, match="required"):
        cfs.encode_args(OPEN_TLM_ARGS, {})
    with pytest.raises(cfs.CommandArgError, match="unknown"):
        cfs.encode_args(OPEN_TLM_ARGS, {"downlink_freq": 1, "bogus": 2})
    with pytest.raises(cfs.CommandArgError, match="frequency"):
        cfs.encode_args(OPEN_TLM_ARGS, {"downlink_freq": "abc"})
    with pytest.raises(cfs.CommandArgError, match="longer"):
        cfs.encode_args((cfs.ArgDef("s", "string", 4),), {"s": "abcd"})  # needs room for the NUL
    nums = (cfs.ArgDef("a", "uint16"), cfs.ArgDef("b", "float32"))
    assert cfs.encode_args(nums, {"a": "0x0102", "b": 1.5}) == b"\x02\x01" + struct.pack("<f", 1.5)
    with pytest.raises(cfs.CommandArgError):
        cfs.encode_args(nums, {"a": 70000, "b": 1})


def test_shipped_registry_matches_obc_ids():
    cmds = load_commands(CONFIG / "commands.yaml", default_timeout=10)
    open_tlm = cmds["TELECOM_OPEN_TLM"]
    assert (open_tlm.msg_id, open_tlm.function_code, open_tlm.response_apid) == (0x187A, 2, 125)
    assert [a.name for a in open_tlm.args] == ["downlink_freq", "uplink_freq"] and open_tlm.apid == 122
    assert open_tlm.retune == {"downlink": "downlink_freq", "uplink": "uplink_freq"}
    assert (cmds["TELECOM_SEND_HK"].msg_id, cmds["TELECOM_SEND_HK"].response_apid) == (123, 124)


def test_registry_rejects_bad_retune(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("commands:\n  - {name: X, msg_id: 0x1880, retune: {downlink: nope}}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="retune"):
        load_commands(p, default_timeout=1)


def test_decode_cfs_telemetry_skips_secondary_header():
    defs = load_definitions(CONFIG / "telemetry_defs.yaml")
    sim = ModemSimulator()
    hk = sim.cfs_tlm(124, b"\x03\x07" + b"436,000".ljust(16, b"\x00") + b"435,500".ljust(16, b"\x00"))
    pkt = ccsds.parse(hk, length_includes_crc=False)
    assert pkt.apid == 124 and len(hk) == 50  # sizeof(TELECOM_HkTlm_t), LoRa implementation
    assert decode_payload(defs[124], pkt.payload).as_dict() == {
        "err_counter": 3, "cmd_counter": 7, "downlink_freq": "436,000", "uplink_freq": "435,500"}
    assert cfs.tlm_time(pkt.payload) == pytest.approx(sim.obc_time + 0.5)
    info = ccsds.parse(sim.cfs_tlm(103, struct.pack("<ffif", 40.0, 25.0, 1234, 5.0)), length_includes_crc=False)
    assert decode_payload(defs[103], info.payload).as_dict() == {
        "cpu_temp": 40.0, "ram_usage_percent": 25.0, "ram_usage": 1234, "cpu_usage": 5.0}


def test_pad_and_short_secondary_header():
    from cubesat_gs.core.telemetry import FieldDef
    d = ApidDef(1, "x", (FieldDef("a", "uint8"), FieldDef("p", "pad", length=3), FieldDef("b", "int32")),
                byte_order="little", secondary_header="cfs_tlm")
    assert decode_payload(d, bytes(10) + b"\x01\xff\xff\xff" + struct.pack("<i", -2)).as_dict() == {"a": 1, "b": -2}
    assert decode_payload(d, b"\x00" * 4).partial


class _RecordingSerial:
    def __init__(self):
        self.lines = []

    async def set_frequency(self, mhz):
        self.lines.append(f"FREQ:{mhz:.3f}")

    async def send_tx(self, raw):
        self.lines.append("TX")


async def test_transmit_uses_uplink_then_returns_to_downlink():
    ser = _RecordingSerial()
    fm = FrequencyManager(EventBus(), ser, FrequencyConfig(tctm=436.0, beacon=437.25, uplink=435.5))
    fm._mhz = 436.0
    await fm.transmit(lambda: ser.send_tx(b""))
    assert ser.lines == ["FREQ:435.500", "TX", "FREQ:436.000"]
    ser.lines.clear()
    await fm.retune_link(437.0, None)
    assert ser.lines == ["FREQ:437.000"] and fm.mhz == 437.0 and fm.uplink_mhz == 435.5
    fm._mode = Mode.BEACON_LISTEN  # outside TCTM a TX stays on the current frequency
    ser.lines.clear()
    await fm.transmit(lambda: ser.send_tx(b""))
    assert ser.lines == ["TX"]


async def test_end_to_end_against_simulated_obc(web_stack):
    station, sim, client = web_stack
    cmds = station.telecommand.commands
    cmds["TELECOM_SEND_HK"] = dataclasses.replace(cmds["TELECOM_SEND_HK"], timeout=0.3)
    # no downlink before OPEN_TLM
    r = await client.post("/api/commands/TELECOM_SEND_HK", json={})
    assert r.json()["status"] == "timeout"

    r = await client.get("/api/commands")
    open_def = next(c for c in r.json() if c["name"] == "TELECOM_OPEN_TLM")
    assert open_def["msg_id"] == 0x187A and open_def["args"][0]["type"] == "freq"

    r = await client.post("/api/commands/TELECOM_OPEN_TLM",
                          json={"args": {"downlink_freq": 436.0, "uplink_freq": 437.0}})
    assert r.status_code == 200 and r.json()["status"] == "responded", r.json()
    assert station.decoder.last_values[125].as_dict() == {"status_code": 0}
    assert station.freq.mhz == 436.0 and station.freq.uplink_mhz == 437.0
    assert (sim.obc_downlink_mhz, sim.obc_uplink_mhz) == (436.0, 437.0)

    # next command goes out on the new uplink and the answer is heard on the new downlink
    r = await client.post("/api/commands/TELECOM_SEND_HK", json={})
    assert r.json()["status"] == "responded"
    assert station.decoder.last_values[124].as_dict()["uplink_freq"] == "437,000"
    assert sim.freq == 436.0

    r = await client.post("/api/commands/OBC_HK_SEND_OBC_INFO", json={})
    assert r.json()["status"] == "responded" and station.decoder.last_values[103].as_dict()["cpu_temp"] == 47.5


async def test_invalid_args_is_422(web_stack):
    station, sim, client = web_stack
    r = await client.post("/api/commands/TELECOM_OPEN_TLM", json={"args": {"downlink_freq": "x"}})
    assert r.status_code == 422 and r.json()["error"] == "invalid_args"
