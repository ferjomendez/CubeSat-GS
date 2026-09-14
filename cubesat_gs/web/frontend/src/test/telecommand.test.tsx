import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, beforeEach, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useGs } from "@/store/gs";
import Telecommand from "@/views/Telecommand";

const defs = [
  { name: "PING", description: "Liveness check", apid: 100, payload_hex: "50494E47", payload_text: "PING", response_apid: 101, timeout: 10, critical: false },
  { name: "REBOOT", description: "Reboot OBC", apid: 100, payload_hex: "01FF", payload_text: null, response_apid: null, timeout: 5, critical: true },
];

function mockFetch(routes: Record<string, unknown>) {
  const calls: { url: string; body?: unknown }[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: string, init?: RequestInit) => {
    const url = String(input); const path = new URL(url, "http://x").pathname;
    calls.push({ url: path, body: init?.body ? JSON.parse(String(init.body)) : undefined });
    const hit = routes[path];
    return new Response(JSON.stringify(hit ?? { error: "not_found", detail: null }), { status: hit ? 200 : 404, headers: { "content-type": "application/json" } });
  }));
  return calls;
}

describe("Telecommand", () => {
  beforeEach(() => { useGs.getState().reset(); useGs.setState({ connected: true }); });

  it("lists commands and sends PING after confirmation", async () => {
    const calls = mockFetch({ "/api/commands": defs, "/api/commands/history": { items: [], next_before: null },
      "/api/commands/PING": { ts: "t", name: "PING", raw_hex: "10", status: "responded", response_hex: "0065", latency_ms: 12.5, attempts: 1, error: null, pending: false } });
    render(<QueryClientProvider client={new QueryClient()}><Telecommand /></QueryClientProvider>);
    await screen.findByText("Liveness check");
    fireEvent.click(screen.getAllByRole("button", { name: /send/i })[0]);
    fireEvent.click(await screen.findByRole("button", { name: /send ping/i }));
    await waitFor(() => expect(calls.some((c) => c.url === "/api/commands/PING")).toBe(true));
    expect(calls.find((c) => c.url === "/api/commands/PING")?.body).toEqual({ confirm: false, payload_hex: null });
  });

  it("critical command requires the checkbox", async () => {
    mockFetch({ "/api/commands": defs, "/api/commands/history": { items: [], next_before: null } });
    render(<QueryClientProvider client={new QueryClient()}><Telecommand /></QueryClientProvider>);
    await screen.findByText("Reboot OBC");
    fireEvent.click(screen.getAllByRole("button", { name: /send/i })[1]);
    const confirm = await screen.findByRole("button", { name: /send reboot/i });
    expect(confirm).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox"));
    expect(confirm).toBeEnabled();
  });

  it("raw hex input validates", async () => {
    mockFetch({ "/api/commands": defs, "/api/commands/history": { items: [], next_before: null } });
    render(<QueryClientProvider client={new QueryClient()}><Telecommand /></QueryClientProvider>);
    const input = await screen.findByLabelText(/raw hex/i);
    fireEvent.change(input, { target: { value: "DEAD BEE" } });
    expect(screen.getByText(/odd number of hex digits/i)).toBeInTheDocument();
    fireEvent.change(input, { target: { value: "DEAD BEEF" } });
    expect(screen.getByText("4 B")).toBeInTheDocument();
  });

  it("shows the pending indicator", () => {
    mockFetch({ "/api/commands": defs, "/api/commands/history": { items: [], next_before: null } });
    useGs.getState().applyMessage({ type: "command", ts: "t", data: { ts: new Date().toISOString(), name: "PING", raw_hex: "10", status: "acked", response_hex: null, latency_ms: null, attempts: 0, error: null, pending: true } });
    render(<QueryClientProvider client={new QueryClient()}><Telecommand /></QueryClientProvider>);
    expect(screen.getByText(/waiting for response/i)).toBeInTheDocument();
  });
});
