import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Settings from "@/views/Settings";

const config = { config: { serial: { port: "auto", baudrate: 115200, reconnect_interval: 5, timeouts: { tx: 5, freq: 2 } },
  frequencies: { tctm: 435.5, beacon: 437.25 }, station: { name: "UAI", latitude: -33.35, longitude: -70.67, altitude: 500 },
  satellite: { name: "UAI-SAT", tle_line1: "", tle_line2: "", tle_source: "" }, passes: { min_elevation: 10, prediction_days: 7 },
  commands: { registry: "config/commands.yaml", default_timeout: 10, max_retries: 3, retry_backoff: 1.5, history_size: 500 },
  database: { db_name: "cubesat_gs", retention_days: 365, local_fallback_path: "data/gs_offline.db" },
  logging: { level: "INFO", file: "logs/gs.log" }, web: { host: "0.0.0.0", port: 8080 },
  ccsds: { length_includes_crc: true, sequence_scope: "global" }, telemetry: { definitions: "config/telemetry_defs.yaml" } },
  writable: ["serial", "frequencies", "station", "satellite", "passes", "commands"],
  applies: { "frequencies.beacon": "live", "frequencies.tctm": "live", "serial.port": "live", "serial.baudrate": "restart", "commands.max_retries": "restart" } };

function mockFetch() {
  const calls: { url: string; method: string; body?: unknown }[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: string, init?: RequestInit) => {
    const path = new URL(String(input), "http://x").pathname; const method = init?.method ?? "GET";
    calls.push({ url: path, method, body: init?.body ? JSON.parse(String(init.body)) : undefined });
    const table: Record<string, unknown> = { "/api/config": method === "PUT" ? { config: config.config, applied_live: ["frequencies.beacon"], restart_required: false } : config,
      "/api/config/serial-ports": [{ device: "COM3", description: "CP210x", vid: 4292, pid: 60000 }],
      "/api/telemetry/definitions": { yaml: "apid_10:\n  name: Beacon\n", definitions: [] },
      "/api/db/stats": { counts: { raw_packets: 12, passes: 0 }, health: { mongo: "disabled", pending_sync: 0, sqlite_path: "x" } } };
    return new Response(JSON.stringify(table[path] ?? {}), { status: 200, headers: { "content-type": "application/json" } });
  }));
  return calls;
}

describe("Settings", () => {
  it("saves a frequencies change with only the edited key", async () => {
    const calls = mockFetch();
    render(<QueryClientProvider client={new QueryClient()}><Settings /></QueryClientProvider>);
    const beacon = await screen.findByLabelText(/beacon/i);
    fireEvent.change(beacon, { target: { value: "437.3" } });
    fireEvent.click(screen.getByRole("button", { name: /save frequencies/i }));
    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ sections: { frequencies: { beacon: 437.3 } } });
    expect(await screen.findByText(/applied live/i)).toBeInTheDocument();
  });
  it("marks read-only sections and shows db stats", async () => {
    mockFetch();
    render(<QueryClientProvider client={new QueryClient()}><Settings /></QueryClientProvider>);
    expect(await screen.findByText(/edit gs_config.yaml and restart/i)).toBeInTheDocument();
    expect(await screen.findByText("12")).toBeInTheDocument();
  });
  it("disables Save and shows an inline error when a numeric field is cleared, instead of shipping 0", async () => {
    const calls = mockFetch();
    render(<QueryClientProvider client={new QueryClient()}><Settings /></QueryClientProvider>);
    const beacon = await screen.findByLabelText(/beacon/i);
    fireEvent.change(beacon, { target: { value: "" } });
    expect(screen.getByRole("button", { name: /save frequencies/i })).toBeDisabled();
    expect(screen.getByText(/enter a number/i)).toBeInTheDocument();
    fireEvent.change(beacon, { target: { value: "437.3" } });
    expect(screen.getByRole("button", { name: /save frequencies/i })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: /save frequencies/i }));
    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ sections: { frequencies: { beacon: 437.3 } } });
  });
});
