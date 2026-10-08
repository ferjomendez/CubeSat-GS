# GS ↔ cFS OBC integration

Target: the OBC team's cFS mission, [vaquitson/uai_obc](https://github.com/vaquitson/uai_obc) (branch `dev`,
reviewed at commit `c5c685e`), in particular `mision_doc/functionality.md` (Telecom app, LoRa implementation).

## What the GS implements

| Item | GS behaviour |
|---|---|
| Framing | cFE v1 headers. Command = primary(6) + FunctionCode(1) + Checksum(1) + payload. Telemetry = primary(6) + time(6) + spare(4) + payload. No CRC, standard CCSDS length (`ccsds.length_includes_crc: false`). |
| MsgId | Sent verbatim as the CCSDS StreamId word (cFE v1 mapping), e.g. `0x187A` → command, sec-hdr, APID 122. |
| Checksum | `CFE_MSG_GenerateChecksum` algorithm (0xFF XOR every byte); packets pass `CFE_MSG_ValidateChecksum`. |
| Sequence | Per-APID counters on both sides (`ccsds.sequence_scope: per_apid`). |
| Payload | Little-endian, layouts for the `i686-linux-gnu` build in `sample_defs/targets.cmake` (`long int` = 4 bytes). |
| `TELECOM_OPEN_TLM` | MsgId `0x187A`, FC 2, `char downlink_freq[16]`, `char uplink_freq[16]` formatted `436,000` (comma per the spec, NUL padded; empty uplink = unchanged). Expects `TELECOM_OPEN_TLM_MID` (125) with `uint32 status_code`. |
| Link following | After sending `TELECOM_OPEN_TLM` the GS listens on the new downlink and transmits every later command on the new uplink (`frequencies.tctm` = RX, `frequencies.uplink` = TX). |
| `TELECOM_SEND_HK` | MsgId 123 (`TELECOM_SEND_HK_MID`, see issue 2). Expects `TELECOM_HK_TLM_MID` (124) with the **spec** payload: `uint8 err_counter, uint8 cmd_counter, char downlink_freq[16], char uplink_freq[16]`. |
| OBC_HK | Extra: `OBC_HK_SEND_HK` (101 → 102) and `OBC_HK_SEND_*` (MsgId 100, FC 104–107 → 103–106), since TELECOM forwards their telemetry. |
| Simulator | `python cubesat_gs/main.py --sim` simulates this OBC (downlink only after OPEN_TLM, frequency switching, all replies above). |

Command and telemetry layouts live in `cubesat_gs/config/commands.yaml` and `telemetry_defs.yaml`; if the
OBC changes a struct, edit the YAML, not the code.

## Open issues to settle with the OBC team

Spec vs code mismatches (the GS follows the spec):

1. **`TELECOM_HkTlm_Payload_t`**: the code sends `command_counter, err_counter, cmd_ingest_counter, tlm_paquet_counter`
   (4 × uint8); the spec says `err_counter, cmd_counter, downlink_freq[16], uplink_freq[16]`.
2. **`TELECOM_SEND_HK_CC`** is in the spec but not defined; the code dispatches Send HK on its own MsgId
   `TELECOM_SEND_HK_MID = 123`. `msg_id_list.md` also lists `TELECOM_CMD_MID` as 122, while the code uses `0x187A`.

Bugs in the OBC code that block the link:

3. `telecom_lora_tlm.c`, `TELECOM_forward_tlm`: `lora_controller_send(..., (char *)(&sb_buf_p), sizeof(CFE_SB_Buffer_t))`
   sends the bytes of the *pointer variable* plus stack garbage instead of the message. It should send `sb_buf_p` with the length
   from `CFE_MSG_GetSize` (`TELECOM_encode_output_message` already does this). Also `bytes` is `size_t`, so `bytes < 0` never fires.
4. `TELECOM_open_tlm` swaps the fields: the uplink is set from `payload->downlink_freq` and the downlink from `payload->uplink_freq`.
5. Frequency strings: `lora_controller_set_*_freq` ignore strings of length ≤ 7 and `MAX_FRQ_LEN` is 8, so `"435,500"` (7 chars)
   is silently dropped. `LoraController` stores them in `char[10]` but copies up to 16 bytes (overflow). Also, the ESP32
   modem firmware parses `FREQ:` as a dot-decimal float, so `FREQ:435,500` would tune to 435 MHz. Proposal: agree on a fixed
   format (e.g. `435.500`, dot) for both the spec and the modem.
6. Plain-number MsgIds (`OBC_HK_CMD_MID = 100`, `TELECOM_SEND_HK_MID = 123`, ...) lack the command-type and secondary-header
   bits, so `CFE_MSG_GetFcnCode` returns 0 for them. Every `OBC_HK` function code is therefore unreachable. Use `0x18xx` IDs as
   `TELECOM_CMD_MID` (`0x187A`) and `CMD_HAND_CMD_MID` (`0x186F`) already do, and `0x08xx` for telemetry.
7. `lora_controller_downlink_freq_is_set` checks the uplink frequency.

To agree on:

8. Serial framing between the OBC and its modem: the OBC writes `TX:` + raw binary + `\n` and reads `RX:` + raw binary, but
   `cubesat_comms-main/ESP32_LoRa_Handler.ino` expects `TX:<hex>` and prints `RX:<hex>`. A raw packet can also contain `0x0A`,
   which ends the line early. Either the OBC hex-encodes (as the GS does) or the satellite modem gets a binary-safe protocol.
9. Nothing is downlinked until `TELECOM_OPEN_TLM` arrives. If the OBC reboots, the GS must send it again.
10. Struct layouts depend on the build target. The GS assumes i686 (32-bit). On a 64-bit target (e.g. a Raspberry Pi with
    aarch64), `long int ram_usage` becomes 8 bytes with 4 bytes of padding before it, and `telemetry_defs.yaml` must change.
