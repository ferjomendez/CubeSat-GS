import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { connectWs } from "@/api/ws";

/** Minimal WebSocket stub: records every instance constructed, and `close()` fires `onclose` like a real socket. */
class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  send(): void {
    /* no-op */
  }

  close(): void {
    this.onclose?.();
  }
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  vi.useFakeTimers();
  vi.stubGlobal("WebSocket", FakeWebSocket);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

it("cancels a pending reconnect timer when close() runs before it fires", () => {
  const conn = connectWs(
    () => {},
    () => {},
  );
  expect(FakeWebSocket.instances.length).toBe(1);

  // The socket drops (server restart, network blip): onclose schedules a reconnect up to 10s out.
  FakeWebSocket.instances[0]!.onclose?.();

  // The caller (e.g. a component unmounting) closes before that reconnect timer fires.
  conn.close();

  // Advance well past the max 10s backoff.
  vi.advanceTimersByTime(15000);

  expect(FakeWebSocket.instances.length).toBe(1);
});
