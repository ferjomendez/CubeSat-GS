"""CCSDS Space Packet (133.0-B-2) primary header + CRC-16-CCITT matching the ESP32 firmware."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

HEADER_LEN = 6
APID_BEACON = 10
APID_TELECOMMAND = 100
APID_TM_RESPONSE = 101

_MAX_APID = 0x7FF
_MAX_SEQ = 0x3FFF


class CCSDSError(ValueError):
    """Malformed packet or invalid build parameters."""


# ---------------------------------------------------------------- CRC-16-CCITT (init 0xFFFF, poly 0x1021)

def crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def crc16_append(data: bytes) -> bytes:
    return data + crc16_ccitt(data).to_bytes(2, "big")


def crc16_verify(data_with_crc: bytes) -> bool:
    if len(data_with_crc) < 2:
        return False
    body, tail = data_with_crc[:-2], data_with_crc[-2:]
    return crc16_ccitt(body) == int.from_bytes(tail, "big")


# ---------------------------------------------------------------- packet

@dataclass(frozen=True)
class CCSDSPacket:
    version: int
    packet_type: int
    sec_header_flag: bool
    apid: int
    sequence_flags: int
    sequence_count: int
    data_length: int  # raw field value as transmitted
    payload: bytes

    def to_bytes(self) -> bytes:
        return _header(
            self.apid, self.sequence_count, self.data_length,
            packet_type=self.packet_type, seq_flags=self.sequence_flags,
            sec_header_flag=self.sec_header_flag, version=self.version,
        ) + self.payload


def _header(apid: int, seq: int, data_length: int, *, packet_type: int, seq_flags: int,
            sec_header_flag: bool, version: int = 0) -> bytes:
    w0 = (version << 13) | (packet_type << 12) | (int(sec_header_flag) << 11) | apid
    w1 = (seq_flags << 14) | seq
    return w0.to_bytes(2, "big") + w1.to_bytes(2, "big") + data_length.to_bytes(2, "big")


def _expected_payload_len(data_length: int, length_includes_crc: bool) -> int:
    return data_length + 1 - (2 if length_includes_crc else 0)


def parse(raw: bytes, *, length_includes_crc: bool = True) -> CCSDSPacket:
    if len(raw) < HEADER_LEN:
        raise CCSDSError(f"packet too short: {len(raw)} bytes")
    w0 = int.from_bytes(raw[0:2], "big")
    w1 = int.from_bytes(raw[2:4], "big")
    data_length = int.from_bytes(raw[4:6], "big")
    version = w0 >> 13
    if version != 0:
        raise CCSDSError(f"unsupported version {version}")
    payload = raw[HEADER_LEN:]
    expected = _expected_payload_len(data_length, length_includes_crc)
    if len(payload) != expected:
        raise CCSDSError(
            f"data length mismatch: header declares {expected} payload bytes "
            f"(field={data_length}, includes_crc={length_includes_crc}), got {len(payload)}"
        )
    return CCSDSPacket(
        version=version,
        packet_type=(w0 >> 12) & 0x1,
        sec_header_flag=bool((w0 >> 11) & 0x1),
        apid=w0 & _MAX_APID,
        sequence_flags=w1 >> 14,
        sequence_count=w1 & _MAX_SEQ,
        data_length=data_length,
        payload=bytes(payload),
    )


def build(apid: int, payload: bytes, *, sequence_count: int, packet_type: int = 1,
          seq_flags: int = 0b11, sec_header_flag: bool = False,
          length_includes_crc: bool = True) -> bytes:
    if not 0 <= apid <= _MAX_APID:
        raise CCSDSError(f"apid out of range: {apid}")
    if not 0 <= sequence_count <= _MAX_SEQ:
        raise CCSDSError(f"sequence_count out of range: {sequence_count}")
    if packet_type not in (0, 1) or not 0 <= seq_flags <= 3:
        raise CCSDSError("invalid packet_type or seq_flags")
    data_length = len(payload) - 1 + (2 if length_includes_crc else 0)
    if not 0 <= data_length <= 0xFFFF:
        raise CCSDSError(f"payload length not encodable: {len(payload)}")
    return _header(apid, sequence_count, data_length, packet_type=packet_type,
                   seq_flags=seq_flags, sec_header_flag=sec_header_flag) + bytes(payload)


def peek_apid_seq(raw: bytes) -> tuple[int, int] | None:
    """Best-effort (apid, seq) from the header without length validation. None if too short."""
    if len(raw) < HEADER_LEN:
        return None
    w0 = int.from_bytes(raw[0:2], "big")
    w1 = int.from_bytes(raw[2:4], "big")
    return w0 & _MAX_APID, w1 & _MAX_SEQ


# ---------------------------------------------------------------- TX counters / RX gap detection

class PacketBuilder:
    """Builds packets with a per-APID 14-bit sequence counter (CCSDS standard for the GS side)."""

    def __init__(self, length_includes_crc: bool = True) -> None:
        self._length_includes_crc = length_includes_crc
        self._counters: dict[int, int] = {}

    def next_count(self, apid: int) -> int:
        return self._counters.get(apid, 0)

    def build(self, apid: int, payload: bytes, packet_type: int = 1) -> bytes:
        seq = self._counters.get(apid, 0)
        raw = build(apid, payload, sequence_count=seq, packet_type=packet_type,
                    length_includes_crc=self._length_includes_crc)
        self._counters[apid] = (seq + 1) & _MAX_SEQ
        return raw


class SequenceTracker:
    """Detects missed downlink packets. scope='global' = one counter for all APIDs (current OBC)."""

    def __init__(self, scope: Literal["global", "per_apid"] = "global") -> None:
        if scope not in ("global", "per_apid"):
            raise ValueError(f"invalid sequence scope {scope!r}")
        self._scope = scope
        self._last: dict[int | None, int] = {}

    def reset(self) -> None:
        self._last.clear()

    def observe(self, packet: CCSDSPacket) -> int | None:
        key = packet.apid if self._scope == "per_apid" else None
        last = self._last.get(key)
        self._last[key] = packet.sequence_count
        if last is None:
            return None
        delta = (packet.sequence_count - last) & _MAX_SEQ
        # delta 1 = in order; 0 = duplicate; large delta (> half range) = out of order / reset
        if delta <= 1 or delta > _MAX_SEQ // 2:
            return None
        return delta - 1
