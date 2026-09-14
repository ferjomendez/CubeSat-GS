import { describe, expect, it, beforeEach } from "vitest";
import { useGs } from "@/store/gs";
import type { WsMessage } from "@/api/types";

const snapshot: WsMessage = { type: "snapshot", ts: "2026-09-13T12:00:00Z", data: {
  status: { station: "UAI", serial: { connected: true, port: "COM3" }, frequency: { mode: "tctm", mhz: 435.5 },
    pending_command: null, storage: { mongo: "disabled" }, passes: { enabled: false, reason: "TLE not configured", next: null, current: null },
    session: { start_time: "2026-09-13T11:00:00Z", end_time: null, pass_id: null, packets_received: 0, packets_sent: 0, notes: "" } },
  feed: [], telemetry_latest: {}, pending_command: null, next_pass: null, current_pass: null, alarms_active: [] } };

const pkt = (i: number): WsMessage => ({ type: "packet", ts: "2026-09-13T12:00:01Z", data: {
  id: `1-${i}`, ts: "2026-09-13T12:00:01Z", direction: "rx", apid: 10, apid_name: "Beacon", seq: i, raw_hex: "00",
  rssi: null, snr: null, freq_mhz: 437.25, kind: "beacon", summary: "ok", fields: null } });

describe("gs store", () => {
  beforeEach(() => useGs.getState().reset());

  it("hydrates from snapshot", () => {
    useGs.getState().applyMessage(snapshot);
    expect(useGs.getState().status?.frequency.mhz).toBe(435.5);
    expect(useGs.getState().feed).toEqual([]);
  });

  it("appends packets, caps at 2000, and buffers while paused", () => {
    const s = useGs.getState();
    s.applyMessage(snapshot);
    for (let i = 0; i < 2100; i++) s.applyMessage(pkt(i));
    expect(useGs.getState().feed.length).toBe(2000);
    expect(useGs.getState().feed[0].id).toBe("1-2099");
    s.setPaused(true);
    s.applyMessage(pkt(5000));
    expect(useGs.getState().feed[0].id).toBe("1-2099");
    expect(useGs.getState().pausedBuffer.length).toBe(1);
    s.flushPaused();
    expect(useGs.getState().feed[0].id).toBe("1-5000");
    expect(useGs.getState().paused).toBe(false);
  });

  it("tracks telemetry latest, series and alarms", () => {
    const s = useGs.getState();
    s.applyMessage(snapshot);
    s.applyMessage({ type: "telemetry", ts: "t", data: { apid: 50, apid_name: "EPS", ts: "2026-09-13T12:00:02Z",
      fields: [{ name: "v_bat", value: 3.1, unit: "V", alarm: "low" }, { name: "tag", value: "x", unit: null, alarm: null }] } });
    expect(useGs.getState().telemetryLatest[50].fields[0].value).toBe(3.1);
    expect(useGs.getState().series["50:v_bat"]).toEqual([[Date.parse("2026-09-13T12:00:02Z"), 3.1]]);
    expect(useGs.getState().series["50:tag"]).toBeUndefined();
    expect(useGs.getState().alarmsActive).toEqual([{ apid: 50, field_name: "v_bat", value: 3.1, alarm: "low" }]);
    s.applyMessage({ type: "telemetry", ts: "t", data: { apid: 50, apid_name: "EPS", ts: "2026-09-13T12:00:03Z",
      fields: [{ name: "v_bat", value: 3.8, unit: "V", alarm: "nominal" }] } });
    expect(useGs.getState().alarmsActive).toEqual([]);
  });

  it("caps series at 5000 points", () => {
    const s = useGs.getState();
    s.applyMessage(snapshot);
    for (let i = 0; i < 5010; i++)
      s.applyMessage({ type: "telemetry", ts: "t", data: { apid: 1, apid_name: "A", ts: new Date(i * 1000).toISOString(),
        fields: [{ name: "x", value: i, unit: null, alarm: null }] } });
    expect(useGs.getState().series["1:x"].length).toBe(5000);
  });

  it("pending command lifecycle and history", () => {
    const s = useGs.getState();
    s.applyMessage(snapshot);
    s.applyMessage({ type: "command", ts: "t", data: { ts: "t", name: "PING", raw_hex: "10", status: "acked",
      response_hex: null, latency_ms: null, attempts: 0, error: null, pending: true } });
    expect(useGs.getState().pendingCommand?.name).toBe("PING");
    s.applyMessage({ type: "command", ts: "t", data: { ts: "t", name: "PING", raw_hex: "10", status: "responded",
      response_hex: "0065", latency_ms: 12, attempts: 1, error: null, pending: false } });
    expect(useGs.getState().pendingCommand).toBeNull();
    expect(useGs.getState().commandHistory[0].status).toBe("responded");
  });

  it("status and pass messages", () => {
    const s = useGs.getState();
    s.applyMessage(snapshot);
    s.applyMessage({ type: "status", ts: "t", data: { ...snapshot.data.status, frequency: { mode: "beacon_listen", mhz: 437.25 } } });
    expect(useGs.getState().status?.frequency.mode).toBe("beacon_listen");
    s.applyMessage({ type: "pass", ts: "t", data: { pass_id: "p1", t: "t", az: 1, el: 2, range_km: 3, doppler_hz: 4, progress: 0.5 } });
    expect(useGs.getState().currentPass?.pass_id).toBe("p1");
    s.applyMessage({ type: "pass", ts: "t", data: { event: "los", pass: { id: "p1", aos: "a", los: "b", tca: "c", max_el: 1, aos_az: 0, los_az: 0, duration_s: 1 } } });
    expect(useGs.getState().currentPass).toBeNull();
  });
});
