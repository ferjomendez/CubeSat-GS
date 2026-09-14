import { useMemo, useRef, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { useVirtualizer } from "@tanstack/react-virtual";

import { api } from "@/api/client";
import type { Direction, FeedEntry, Kind, PacketsPageOut } from "@/api/types";
import { FeedRow } from "@/components/FeedRow";
import { Panel } from "@/components/Panel";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { useGs } from "@/store/gs";

type DirFilter = "all" | Direction;
type KindFilter = "all" | Kind;
type RangeFilter = "all" | "10m" | "1h";

const KINDS: Kind[] = ["beacon", "telemetry", "command", "malformed", "unknown"];
const RANGE_MS: Record<RangeFilter, number | null> = { all: null, "10m": 10 * 60_000, "1h": 60 * 60_000 };

/** Backend cursor format (`feed.py`'s `_parse_cursor`): `<iso ts>|<row id>`. */
const cursorOf = (e: FeedEntry): string => `${e.ts}|${e.id}`;

/** Live packet feed: toolbar filters, a virtualised scroll body, and a "Load older" page fetch. */
export default function LiveFeed() {
  const feed = useGs((s) => s.feed);
  const paused = useGs((s) => s.paused);
  const pausedCount = useGs((s) => s.pausedBuffer.length);
  const telemetryLatest = useGs((s) => s.telemetryLatest);
  const setPaused = useGs((s) => s.setPaused);
  const flushPaused = useGs((s) => s.flushPaused);

  const [direction, setDirection] = useState<DirFilter>("all");
  const [kind, setKind] = useState<KindFilter>("all");
  const [range, setRange] = useState<RangeFilter>("all");
  const [apids, setApids] = useState<Set<number>>(new Set());
  const [expanded, setExpanded] = useState<string | null>(null);

  const singleApid = apids.size === 1 ? [...apids][0] : undefined;

  const infinite = useInfiniteQuery({
    queryKey: ["packets", direction, kind, singleApid],
    queryFn: ({ pageParam }: { pageParam: string | undefined }) => {
      // The first page has no cursor from the backend yet. Without one, `/api/packets` would
      // return the newest persisted packets — the same ones already in `feed` (the hub snapshot
      // hydrates from that same storage) — duplicating the live rows. Seed the first page from the
      // oldest *currently* live entry instead, read at fetch time so a feed that's grown or
      // trimmed since render doesn't shift the anchor.
      const before = pageParam ?? (feed.length > 0 ? cursorOf(feed[feed.length - 1]) : undefined);
      return api.get<PacketsPageOut>("/api/packets", {
        limit: 50,
        before,
        direction: direction === "all" ? undefined : direction,
        kind: kind === "all" ? undefined : kind,
        apid: singleApid,
      });
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last: PacketsPageOut) => last.next_before ?? undefined,
    enabled: false,
  });

  const older = useMemo(() => infinite.data?.pages.flatMap((p) => p.items) ?? [], [infinite.data]);

  const seenApids = useMemo(() => {
    const s = new Set<number>(Object.keys(telemetryLatest).map(Number));
    for (const e of feed) if (e.apid != null) s.add(e.apid);
    for (const e of older) if (e.apid != null) s.add(e.apid);
    return [...s].sort((a, b) => a - b);
  }, [feed, older, telemetryLatest]);

  const passesFilters = useMemo(() => {
    const rangeMs = RANGE_MS[range];
    return (e: FeedEntry) => {
      if (direction !== "all" && e.direction !== direction) return false;
      if (kind !== "all" && e.kind !== kind) return false;
      if (apids.size > 0 && (e.apid == null || !apids.has(e.apid))) return false;
      if (rangeMs != null && Date.now() - Date.parse(e.ts) > rangeMs) return false;
      return true;
    };
  }, [direction, kind, apids, range]);

  const rows = useMemo(() => {
    const seen = new Set<string>();
    const combined: FeedEntry[] = [];
    // Live rows take priority over older/paginated ones sharing the same id (defensive: keeps a
    // single copy even if a fetched page happens to overlap the live feed).
    for (const e of [...feed.filter(passesFilters), ...older.filter(passesFilters)]) {
      if (seen.has(e.id)) continue;
      seen.add(e.id);
      combined.push(e);
    }
    return combined;
  }, [feed, older, passesFilters]);

  const loadOlder = () => void infinite.fetchNextPage();
  const canLoadOlder = !infinite.data || infinite.hasNextPage;

  const scrollRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 28,
    overscan: 8,
    initialRect: { width: 800, height: 600 },
  });

  const toggleApid = (apid: number) => {
    setApids((s) => {
      const next = new Set(s);
      if (next.has(apid)) next.delete(apid);
      else next.add(apid);
      return next;
    });
  };

  return (
    <Panel title="Live feed" className="h-full" bodyClassName="flex flex-col">
      <div className="flex flex-wrap items-center gap-3 border-b border-line px-3 py-2">
        <div className="flex gap-1" role="group" aria-label="Direction">
          {(["all", "rx", "tx"] as const).map((d) => (
            <button
              key={d}
              type="button"
              aria-pressed={direction === d}
              onClick={() => setDirection(d)}
              className={cn(
                "label rounded border border-line px-2 py-0.5",
                direction === d && "border-info text-info",
              )}
            >
              {d === "all" ? "All" : d.toUpperCase()}
            </button>
          ))}
        </div>

        <Select value={kind} onValueChange={(v) => setKind(v as KindFilter)}>
          <SelectTrigger className="label h-7 w-32 border-line bg-bg">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All kinds</SelectItem>
            {KINDS.map((k) => (
              <SelectItem key={k} value={k}>
                {k}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={range} onValueChange={(v) => setRange(v as RangeFilter)}>
          <SelectTrigger className="label h-7 w-36 border-line bg-bg">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All time</SelectItem>
            <SelectItem value="10m">Last 10 min</SelectItem>
            <SelectItem value="1h">Last 1 h</SelectItem>
          </SelectContent>
        </Select>

        {seenApids.length > 0 && (
          <div className="flex max-w-xs flex-wrap items-center gap-2">
            {seenApids.map((apid) => (
              <label key={apid} className="label flex items-center gap-1">
                <Checkbox checked={apids.has(apid)} onCheckedChange={() => toggleApid(apid)} />
                {apid}
              </label>
            ))}
          </div>
        )}

        <div className="ml-auto flex items-center gap-2">
          {paused && pausedCount > 0 && <span className="label text-info">{pausedCount} new</span>}
          <button
            type="button"
            aria-pressed={paused}
            onClick={() => (paused ? flushPaused() : setPaused(true))}
            className="label rounded border border-line px-2 py-0.5 hover:border-info"
          >
            {paused ? "Resume" : "Pause"}
          </button>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
          <p className="text-dim">No packets yet — switch to Beacon to listen on 437.250 MHz</p>
          <button
            type="button"
            className="label rounded border border-line px-2 py-1 hover:border-info"
            onClick={() => void api.put("/api/frequency", { mode: "beacon_listen" })}
          >
            Listen for beacon
          </button>
        </div>
      ) : (
        <div ref={scrollRef} className="min-h-0 flex-1 overflow-auto">
          <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
            {virtualizer.getVirtualItems().map((vi) => {
              const row = rows[vi.index];
              return (
                <div
                  key={row.id}
                  data-index={vi.index}
                  ref={virtualizer.measureElement}
                  style={{ position: "absolute", top: 0, left: 0, width: "100%", transform: `translateY(${vi.start}px)` }}
                >
                  <FeedRow entry={row} expanded={expanded === row.id} onToggle={() => setExpanded((e) => (e === row.id ? null : row.id))} />
                </div>
              );
            })}
          </div>
          {canLoadOlder && (
            <div className="flex justify-center border-t border-line/60 p-2">
              <button
                type="button"
                className="label rounded border border-line px-2 py-1 hover:border-info"
                disabled={infinite.isFetching}
                onClick={loadOlder}
              >
                {infinite.isFetching ? "Loading…" : "Load older"}
              </button>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
