"""NASA cFS (cFE) message framing used by the UAI OBC (github.com/vaquitson/uai_obc).

cFE v1 MsgId mapping: the 16-bit MsgId value IS the CCSDS StreamId word, so its bits carry the
packet type (0x1000), the secondary-header flag (0x0800) and the APID (0x07FF). Some OBC MIDs are
plain small numbers (e.g. 123) and therefore go out with type=TLM and no secondary-header flag;
we transmit them exactly as the OBC subscribes to them.

  command   = primary(6) | FunctionCode(1) | Checksum(1) | payload        (CFE_MSG_CommandHeader_t)
  telemetry = primary(6) | Time(6: 4 s + 2 subs, big-endian) | Spare(4) | payload
Primary header and time are big-endian; payload structs are native (little-endian on the OBC).
No CRC: the CCSDS data-length field is total_len - 7 (ccsds.length_includes_crc: false).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any

from cubesat_gs.core import ccsds

CMD_SEC_HDR_LEN = 2
TLM_SEC_HDR_LEN = 10  # 6 bytes time + 4 bytes spare
MAX_MSG_ID = 0x1FFF   # CFE_PLATFORM_SB_HIGHEST_VALID_MSGID; also keeps the CCSDS version bits 0

ARG_NUMERIC = {
    "uint8": "B", "int8": "b", "uint16": "H", "int16": "h", "uint32": "I", "int32": "i",
    "uint64": "Q", "int64": "q", "float32": "f", "float64": "d",
}
ARG_TYPES = set(ARG_NUMERIC) | {"string", "freq"}


class CommandArgError(ValueError):
    """A command argument is missing or cannot be encoded."""


def split_msg_id(msg_id: int) -> tuple[int, bool, int]:
    """MsgId value -> (packet_type, sec_header_flag, apid)."""
    if not 0 <= msg_id <= MAX_MSG_ID:
        raise ValueError(f"msg_id out of range: 0x{msg_id:04X}")
    return (msg_id >> 12) & 1, bool((msg_id >> 11) & 1), msg_id & 0x7FF


def checksum(raw: bytes) -> int:
    """CFE_MSG_ComputeCheckSum: 0xFF XOR every byte (checksum byte included, normally 0)."""
    c = 0xFF
    for b in raw:
        c ^= b
    return c


def build_command(builder: ccsds.PacketBuilder, msg_id: int, function_code: int, payload: bytes) -> bytes:
    if not 0 <= function_code <= 0x7F:
        raise ValueError(f"function_code out of range: {function_code}")
    ptype, sec, apid = split_msg_id(msg_id)
    raw = bytearray(builder.build(apid, bytes([function_code, 0]) + payload,
                                  packet_type=ptype, sec_header_flag=sec))
    raw[7] = checksum(raw)
    return bytes(raw)


def tlm_time(payload: bytes) -> float | None:
    """Spacecraft time (seconds) from the telemetry secondary header; payload excludes the primary header."""
    if len(payload) < 6:
        return None
    secs, subs = struct.unpack(">IH", payload[:6])
    return secs + subs / 65536.0


# ---------------------------------------------------------------- command arguments

@dataclass(frozen=True)
class ArgDef:
    name: str
    type: str
    length: int | None = None       # string/freq: fixed char[] size, NUL padded
    default: Any = None
    optional: bool = False          # string/freq: empty value encodes as a zero-length string
    decimals: int = 3               # freq: digits after the separator
    decimal_sep: str = ","          # freq: functionality.md asks for a comma
    description: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type, "length": self.length, "default": self.default,
                "optional": self.optional, "description": self.description}


def parse_arg(where: str, raw: Any) -> ArgDef:
    if not isinstance(raw, dict) or "name" not in raw or "type" not in raw:
        raise ValueError(f"{where}: each arg needs 'name' and 'type'")
    t = str(raw["type"])
    if t not in ARG_TYPES:
        raise ValueError(f"{where}: unknown arg type {t!r}")
    length = raw.get("length")
    if t in ("string", "freq"):
        if length is None or int(length) < 1:
            raise ValueError(f"{where}: {t} args need a positive 'length'")
        length = int(length)
    elif length is not None:
        raise ValueError(f"{where}: 'length' is only valid for string/freq")
    return ArgDef(name=str(raw["name"]), type=t, length=length, default=raw.get("default"),
                  optional=bool(raw.get("optional", False)), decimals=int(raw.get("decimals", 3)),
                  decimal_sep=str(raw.get("decimal_sep", ",")), description=str(raw.get("description", "")))


def parse_freq(value: Any) -> float:
    """Accepts 435.5, "435.5" or "435,5"."""
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError as e:
        raise CommandArgError(f"not a frequency: {value!r}") from e


def _encode_one(a: ArgDef, value: Any, byte_order: str) -> bytes:
    if a.type in ARG_NUMERIC:
        try:
            num = float(value) if a.type.startswith("float") else int(str(value), 0)
            return struct.pack(("<" if byte_order == "little" else ">") + ARG_NUMERIC[a.type], num)
        except (ValueError, struct.error) as e:
            raise CommandArgError(f"{a.name}: cannot encode {value!r} as {a.type}") from e
    if value is None or str(value).strip() == "":
        if not a.optional:
            raise CommandArgError(f"{a.name}: value required")
        text = ""
    elif a.type == "freq":
        text = f"{parse_freq(value):.{a.decimals}f}".replace(".", a.decimal_sep)
    else:
        text = str(value)
    try:
        data = text.encode("ascii")
    except UnicodeEncodeError as e:
        raise CommandArgError(f"{a.name}: only ASCII text is allowed") from e
    if len(data) >= a.length:  # the OBC treats these as C strings: keep room for the NUL
        raise CommandArgError(f"{a.name}: {text!r} is longer than {a.length - 1} characters")
    return data.ljust(a.length, b"\x00")


def encode_args(args: tuple[ArgDef, ...], values: dict[str, Any] | None, byte_order: str = "little") -> bytes:
    values = dict(values or {})
    unknown = set(values) - {a.name for a in args}
    if unknown:
        raise CommandArgError(f"unknown args: {sorted(unknown)}")
    return b"".join(_encode_one(a, values.get(a.name, a.default), byte_order) for a in args)


def resolved_args(args: tuple[ArgDef, ...], values: dict[str, Any] | None) -> dict[str, Any]:
    values = values or {}
    return {a.name: values.get(a.name, a.default) for a in args}
