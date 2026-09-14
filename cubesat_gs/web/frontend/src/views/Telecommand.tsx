import { useEffect, useMemo, useState } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, ApiError } from "@/api/client";
import type { CommandDefOut, CommandHistoryOut, CommandRecordOut, CommandStatus } from "@/api/types";
import { AlarmBadge } from "@/components/AlarmBadge";
import { CommandDialog } from "@/components/CommandDialog";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { MutationButton } from "@/components/MutationButton";
import { Panel } from "@/components/Panel";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fmtBytes } from "@/lib/format";
import { age, local, utc } from "@/lib/time";
import { useGs } from "@/store/gs";

const STATUS_TONE: Record<CommandStatus, "nominal" | "info" | "warn" | "alarm"> = {
  responded: "nominal",
  acked: "info",
  timeout: "warn",
  failed: "alarm",
  refused: "alarm",
};

function validateRawHex(raw: string): { clean: string; error: string | null; bytes: string | null } {
  const clean = raw.replace(/\s+/g, "").toUpperCase();
  if (!clean) return { clean, error: null, bytes: null };
  if (!/^[0-9A-F]+$/.test(clean)) return { clean, error: "Only 0–9 A–F allowed", bytes: null };
  if (clean.length % 2 !== 0) return { clean, error: "Odd number of hex digits", bytes: null };
  return { clean, error: null, bytes: fmtBytes(clean) };
}

/** Reports an `ApiError` as a human toast — a 403 `confirm_required`'s `detail` is a JSON record dump, not for display. */
function toastError(err: unknown, name: string) {
  if (err instanceof ApiError) {
    toast.error(err.error === "confirm_required" ? `${name} needs confirmation` : err.detail ?? err.error);
  } else {
    toast.error(`Failed to send ${name}`);
  }
}

/** Ticks every second while a command is pending, showing elapsed time since it was sent. */
function PendingStrip({ pending }: { pending: CommandRecordOut }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);
  return (
    <div className="flex items-center gap-3 border-b border-line px-3 py-2">
      <span className="bg-warn h-1.5 w-1.5 shrink-0 animate-pulse rounded-full" aria-hidden="true" />
      <span className="label text-warn">Waiting for response to {pending.name}</span>
      <span className="font-mono tabular-nums text-dim">{age(pending.ts, now)}</span>
      <span className="label text-dim">attempts {pending.attempts}</span>
    </div>
  );
}

/** Backend cursor format for command history (`commands.py`'s `before` query param): an ISO timestamp. */
const cursorOf = (r: CommandRecordOut): string => r.ts;
const rowKey = (r: CommandRecordOut): string => `${r.ts}|${r.name}`;

/** Commands console: a definitions table with send confirmation, a raw-hex sender, and paginated history. */
export default function Telecommand() {
  const connected = useGs((s) => s.connected);
  const pendingCommand = useGs((s) => s.pendingCommand);
  const commandHistory = useGs((s) => s.commandHistory);

  const { data: defs } = useQuery({
    queryKey: ["commands"],
    queryFn: () => api.get<CommandDefOut[]>("/api/commands"),
  });

  const [selectedCmd, setSelectedCmd] = useState<CommandDefOut | null>(null);
  const [rawHex, setRawHex] = useState("");
  const [rawDialogOpen, setRawDialogOpen] = useState(false);

  const infinite = useInfiniteQuery({
    queryKey: ["commands-history"],
    queryFn: ({ pageParam }: { pageParam: string | undefined }) => {
      // Seed the first page from the oldest *currently live* history entry (same reasoning as
      // LiveFeed's "Load older": without a cursor the backend would return the newest persisted
      // records, duplicating what applyMessage already put in commandHistory).
      const before = pageParam ?? (commandHistory.length > 0 ? cursorOf(commandHistory[commandHistory.length - 1]) : undefined);
      return api.get<CommandHistoryOut>("/api/commands/history", { limit: 50, before });
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last: CommandHistoryOut) => last.next_before ?? undefined,
    enabled: false,
  });

  const older = useMemo(() => infinite.data?.pages.flatMap((p) => p.items) ?? [], [infinite.data]);

  const rows = useMemo(() => {
    const seen = new Set<string>();
    const combined: CommandRecordOut[] = [];
    for (const r of [...commandHistory, ...older]) {
      const key = rowKey(r);
      if (seen.has(key)) continue;
      seen.add(key);
      combined.push(r);
    }
    return combined;
  }, [commandHistory, older]);

  const loadOlder = () => void infinite.fetchNextPage();
  // `commandHistory` only fills from live WS events, so on a fresh session it's empty and this
  // button is the only way to reach persisted history — it must stay usable even when
  // rows.length === 0. Disable only while a page is in flight or once the backend has said
  // there's nothing more (hasNextPage === false); before the first fetch, data is undefined and
  // hasNextPage is unset, so the button starts out enabled.
  const loadOlderDisabled = infinite.isFetching || (infinite.data != null && infinite.hasNextPage === false);

  const sendCommand = async (cmd: CommandDefOut, payloadHex: string | null) => {
    try {
      const rec = await api.post<CommandRecordOut>(`/api/commands/${cmd.name}`, { confirm: cmd.critical, payload_hex: payloadHex });
      toast(`Sent ${cmd.name} — ${rec.status}`);
    } catch (err) {
      toastError(err, cmd.name);
    }
  };

  const sendRaw = async (hex: string) => {
    try {
      const rec = await api.post<CommandRecordOut>("/api/commands/raw", { hex, confirm: true });
      toast(`Sent raw — ${rec.status}`);
    } catch (err) {
      toastError(err, "Raw command");
    }
  };

  const { clean: rawClean, error: rawError, bytes: rawBytes } = validateRawHex(rawHex);

  return (
    <div className="flex flex-col gap-2">
      <Panel title="Commands" bodyClassName="overflow-auto">
        <table className="w-full text-left text-[13px]">
          <thead>
            <tr className="label">
              <th className="px-2 py-1">Name</th>
              <th className="px-2 py-1">Description</th>
              <th className="px-2 py-1">APID</th>
              <th className="px-2 py-1">Response APID</th>
              <th className="px-2 py-1">Timeout</th>
              <th className="px-2 py-1">Critical</th>
              <th className="px-2 py-1" />
            </tr>
          </thead>
          <tbody>
            {(defs ?? []).map((c) => (
              <tr key={c.name} className="row">
                <td className="px-2 font-mono">{c.name}</td>
                <td className="text-dim px-2">{c.description}</td>
                <td className="px-2 font-mono tabular-nums">{c.apid}</td>
                <td className="px-2 font-mono tabular-nums">{c.response_apid ?? "—"}</td>
                <td className="px-2 font-mono tabular-nums">{c.timeout}s</td>
                <td className="px-2">{c.critical ? <AlarmBadge tone="alarm" text="critical" /> : null}</td>
                <td className="px-2 py-1 text-right">
                  <MutationButton
                    connected={connected}
                    onClick={() => setSelectedCmd(c)}
                    className="label rounded border border-line px-2 py-0.5 hover:border-info disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Send
                  </MutationButton>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      {pendingCommand && <PendingStrip pending={pendingCommand} />}

      <Panel title="Raw command" bodyClassName="flex flex-col gap-2 p-3">
        <div className="max-w-xs space-y-1">
          <Label htmlFor="raw-hex">Raw hex</Label>
          <Input
            id="raw-hex"
            aria-label="Raw hex"
            className="font-mono"
            placeholder="DEADBEEF"
            value={rawHex}
            onChange={(e) => setRawHex(e.target.value)}
          />
          {rawError ? (
            <p className="label text-alarm">{rawError}</p>
          ) : rawBytes ? (
            <p className="label text-dim">{rawBytes}</p>
          ) : null}
        </div>
        <div>
          <MutationButton
            connected={connected}
            disabled={!rawClean || !!rawError}
            onClick={() => setRawDialogOpen(true)}
            className="label rounded border border-line px-2 py-1 hover:border-info disabled:cursor-not-allowed disabled:opacity-40"
          >
            Send raw
          </MutationButton>
        </div>
      </Panel>

      <Panel title="History" bodyClassName="overflow-auto">
        <table className="w-full text-left text-[13px]">
          <thead>
            <tr className="label">
              <th className="px-2 py-1">Time</th>
              <th className="px-2 py-1">Name</th>
              <th className="px-2 py-1">Status</th>
              <th className="px-2 py-1">Response</th>
              <th className="px-2 py-1">Latency</th>
              <th className="px-2 py-1">Attempts</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-dim px-2 py-6 text-center">
                  No commands sent yet — send one above
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={rowKey(r)} className="row">
                  <td className="text-dim px-2 font-mono tabular-nums" title={local(r.ts)}>
                    {utc(r.ts)}
                  </td>
                  <td className="px-2 font-mono">{r.name}</td>
                  <td className="px-2">
                    <AlarmBadge tone={STATUS_TONE[r.status]} text={r.status} />
                  </td>
                  <td className="text-dim px-2 font-mono">
                    {r.response_hex ? `${r.response_hex.slice(0, 16)}${r.response_hex.length > 16 ? "…" : ""}` : "—"}
                  </td>
                  <td className="px-2 font-mono tabular-nums">{r.latency_ms != null ? `${r.latency_ms.toFixed(1)} ms` : "—"}</td>
                  <td className="px-2 font-mono tabular-nums">{r.attempts}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        <div className="flex justify-center border-t border-line/60 p-2">
          <button
            type="button"
            className="label rounded border border-line px-2 py-1 hover:border-info disabled:cursor-not-allowed disabled:opacity-40"
            disabled={loadOlderDisabled}
            onClick={loadOlder}
          >
            {infinite.isFetching ? "Loading…" : "Load older"}
          </button>
        </div>
      </Panel>

      {selectedCmd && (
        <CommandDialog
          cmd={selectedCmd}
          open
          onOpenChange={(open) => {
            if (!open) setSelectedCmd(null);
          }}
          onConfirm={(payloadHex) => void sendCommand(selectedCmd, payloadHex)}
        />
      )}

      <ConfirmDialog
        open={rawDialogOpen}
        onOpenChange={setRawDialogOpen}
        title="Send raw command"
        body={`Send ${rawBytes ?? "0 B"} of raw hex exactly once: ${rawClean || "—"}`}
        critical
        confirmLabel="Send raw"
        onConfirm={() => void sendRaw(rawClean)}
      />
    </div>
  );
}
