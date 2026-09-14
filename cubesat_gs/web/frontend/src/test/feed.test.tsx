import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useGs } from "@/store/gs";
import LiveFeed from "@/views/LiveFeed";

const entry = (i: number, kind = "beacon") => ({ id: `1-${i}`, ts: "2026-09-13T12:00:01Z", direction: "rx" as const, apid: kind === "command" ? 100 : 10,
  apid_name: "Beacon", seq: i, raw_hex: "000AC000", rssi: -97.5, snr: 8.2, freq_mhz: 437.25, kind: kind as never, summary: `msg ${i}`, fields: null });

describe("LiveFeed", () => {
  beforeEach(() => { useGs.getState().reset(); });
  it("renders entries, pauses and shows the new-count chip", () => {
    const s = useGs.getState();
    s.applyMessage({ type: "packet", ts: "t", data: entry(1) });
    render(<QueryClientProvider client={new QueryClient()}><LiveFeed /></QueryClientProvider>);
    expect(screen.getByText("msg 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /pause/i }));
    // The store notifies subscribers synchronously, but React 19 schedules the resulting re-render
    // on a microtask; act() flushes it immediately so the assertions below see it right away.
    act(() => { s.applyMessage({ type: "packet", ts: "t", data: entry(2) }); });
    expect(screen.queryByText("msg 2")).not.toBeInTheDocument();
    expect(screen.getByText(/1 new/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /resume/i }));
    expect(screen.getByText("msg 2")).toBeInTheDocument();
  });
  it("filters by direction", () => {
    const s = useGs.getState();
    s.applyMessage({ type: "packet", ts: "t", data: entry(1) });
    s.applyMessage({ type: "packet", ts: "t", data: { ...entry(2, "command"), direction: "tx" } });
    render(<QueryClientProvider client={new QueryClient()}><LiveFeed /></QueryClientProvider>);
    fireEvent.click(screen.getByRole("button", { name: /^tx$/i }));
    expect(screen.queryByText("msg 1")).not.toBeInTheDocument();
    expect(screen.getByText("msg 2")).toBeInTheDocument();
  });
});
