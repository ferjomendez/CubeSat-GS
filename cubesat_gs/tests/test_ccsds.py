import pytest

from cubesat_gs.core import ccsds
from cubesat_gs.core.ccsds import CCSDSError, CCSDSPacket, build, parse

BEACON_HEX = "000AC0000018564C454F5F424541434F4E5F5359535F4E4F4D494E414C"
PONG_HEX = "0065C001000F504F4E475F444154415F362E3238"
PING_HEX = "1064C000000550494E47"


# ---- CRC

def test_crc_standard_vector():
    assert ccsds.crc16_ccitt(b"123456789") == 0x29B1


def test_crc_append_and_verify():
    framed = ccsds.crc16_append(b"abc")
    assert len(framed) == 5
    assert ccsds.crc16_verify(framed)
    assert not ccsds.crc16_verify(framed[:-1] + b"\x00")
    assert not ccsds.crc16_verify(b"\x01")  # too short


# ---- parse

def test_parse_obc_beacon():
    p = parse(bytes.fromhex(BEACON_HEX))
    assert p.version == 0
    assert p.packet_type == 0
    assert p.sec_header_flag is False
    assert p.apid == 10
    assert p.sequence_flags == 0b11
    assert p.sequence_count == 0
    assert p.data_length == 24
    assert p.payload == b"VLEO_BEACON_SYS_NOMINAL"


def test_parse_pong():
    p = parse(bytes.fromhex(PONG_HEX))
    assert p.apid == 101 and p.sequence_count == 1
    assert p.payload == b"PONG_DATA_6.28"


def test_parse_strict_standard_convention():
    # data_length = len(payload) - 1 = 2 for b"abc"
    raw = bytes([0x00, 0x05, 0xC0, 0x00, 0x00, 0x02]) + b"abc"
    p = parse(raw, length_includes_crc=False)
    assert p.payload == b"abc"
    with pytest.raises(CCSDSError, match="length"):
        parse(raw, length_includes_crc=True)


def test_parse_rejects_short():
    with pytest.raises(CCSDSError, match="short"):
        parse(b"\x00\x0A\xC0")


def test_parse_rejects_bad_version():
    raw = bytearray(bytes.fromhex(BEACON_HEX))
    raw[0] |= 0x20  # version bits = 001
    with pytest.raises(CCSDSError, match="version"):
        parse(bytes(raw))


def test_parse_rejects_length_mismatch():
    raw = bytes.fromhex(BEACON_HEX)[:-1]  # truncated payload
    with pytest.raises(CCSDSError, match="length"):
        parse(raw)


def test_parse_type_and_secheader_bits():
    raw = bytes([0x18, 0x05, 0xC0, 0x00, 0x00, 0x01]) + b""  # type=1, sec hdr=1, apid=5
    p = parse(raw)
    assert p.packet_type == 1 and p.sec_header_flag is True and p.apid == 5
    assert p.payload == b""


# ---- build

def test_build_ping_matches_vector():
    raw = build(100, b"PING", sequence_count=0)
    assert raw.hex().upper() == PING_HEX


def test_build_roundtrip_both_conventions():
    for conv in (True, False):
        raw = build(2047, b"\x01\x02\x03", sequence_count=0x3FFF, packet_type=0,
                    length_includes_crc=conv)
        p = parse(raw, length_includes_crc=conv)
        assert p.apid == 2047 and p.sequence_count == 0x3FFF and p.payload == b"\x01\x02\x03"
        assert p.to_bytes() == raw


def test_build_rejects_out_of_range():
    with pytest.raises(CCSDSError):
        build(2048, b"", sequence_count=0)
    with pytest.raises(CCSDSError):
        build(1, b"", sequence_count=0x4000)
    with pytest.raises(CCSDSError):
        build(1, b"x" * 65536, sequence_count=0)


def test_peek_apid_seq():
    assert ccsds.peek_apid_seq(bytes.fromhex(PONG_HEX)) == (101, 1)
    assert ccsds.peek_apid_seq(b"\x00") is None


# ---- Task 4: PacketBuilder and SequenceTracker

from cubesat_gs.core.ccsds import PacketBuilder, SequenceTracker


def _pkt(apid, seq):
    return parse(build(apid, b"x", sequence_count=seq, packet_type=0))


def test_packet_builder_counts_per_apid_and_wraps():
    b = PacketBuilder(length_includes_crc=True)
    assert parse(b.build(100, b"a")).sequence_count == 0
    assert parse(b.build(100, b"a")).sequence_count == 1
    assert parse(b.build(7, b"a")).sequence_count == 0  # independent counter
    b._counters[100] = 0x3FFF
    assert parse(b.build(100, b"a")).sequence_count == 0x3FFF
    assert parse(b.build(100, b"a")).sequence_count == 0
    assert b.next_count(7) == 1


def test_tracker_global_scope_obc_interleaving():
    t = SequenceTracker("global")
    assert t.observe(_pkt(10, 0)) is None
    assert t.observe(_pkt(101, 1)) is None   # different APID, same global counter: no gap
    assert t.observe(_pkt(10, 2)) is None
    assert t.observe(_pkt(10, 5)) == 2       # 3 and 4 missed


def test_tracker_per_apid_scope():
    t = SequenceTracker("per_apid")
    assert t.observe(_pkt(10, 0)) is None
    assert t.observe(_pkt(101, 0)) is None
    assert t.observe(_pkt(10, 1)) is None
    assert t.observe(_pkt(101, 3)) == 2


def test_tracker_wraparound():
    t = SequenceTracker("global")
    t.observe(_pkt(10, 0x3FFE))
    assert t.observe(_pkt(10, 0x3FFF)) is None
    assert t.observe(_pkt(10, 0)) is None
    assert t.observe(_pkt(10, 2)) == 1


def test_tracker_duplicate_or_backwards_is_not_a_gap():
    t = SequenceTracker("global")
    t.observe(_pkt(10, 5))
    assert t.observe(_pkt(10, 5)) is None
    assert t.observe(_pkt(10, 3)) is None
    t.reset()
    assert t.observe(_pkt(10, 9)) is None
