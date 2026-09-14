import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";
import { describe, expect, it, beforeEach, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useGs } from "@/store/gs";
import { api } from "@/api/client";
import LiveFeed from "@/views/LiveFeed";

vi.mock("@/api/client", () => ({ api: { get: vi.fn(), put: vi.fn() } }));

const entry = (i: number, kind = "beacon") => ({ id: `1-${i}`, ts: "2026-09-13T12:00:01Z", direction: "rx" as const, apid: kind === "command" ? 100 : 10,
  apid_name: "Beacon", seq: i, raw_hex: "000AC000", rssi: -97.5, snr: 8.2, freq_mhz: 437.25, kind: kind as never, summary: `msg ${i}`, fields: null });

describe("LiveFeed", () => {
  beforeEach(() => {
    useGs.getState().reset();
    vi.mocked(api.get).mockReset();
    vi.mocked(api.put).mockReset();
  });
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
  it("seeds 'Load older' from the oldest live entry and doesn't duplicate it", async () => {
    const s = useGs.getState();
    // feed ends up [entry(2), entry(1)] (newest first) — entry(1) is the oldest live row.
    s.applyMessage({ type: "packet", ts: "t", data: entry(1) });
    s.applyMessage({ type: "packet", ts: "t", data: entry(2) });
    vi.mocked(api.get).mockResolvedValue({
      // The backend returning the oldest live entry again (no cursor) is exactly the bug: a page
      // that overlaps `feed` must not render a second copy of it.
      items: [entry(1), entry(0)],
      next_before: null,
    });
    render(<QueryClientProvider client={new QueryClient()}><LiveFeed /></QueryClientProvider>);
    fireEvent.click(screen.getByRole("button", { name: /load older/i }));
    await waitFor(() => expect(screen.getByText("msg 0")).toBeInTheDocument());
    expect(api.get).toHaveBeenCalledWith(
      "/api/packets",
      expect.objectContaining({ before: "2026-09-13T12:00:01Z|1-1" }),
    );
    expect(screen.getAllByText("msg 1")).toHaveLength(1);
  });
});
