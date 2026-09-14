import { useMemo, useRef, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { observeElementRect, useVirtualizer } from "@tanstack/react-virtual";

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

/**
 * Wraps the default rect observer to ignore a degenerate 0x0 report — jsdom has no layout engine, so
 * `element.offsetWidth/offsetHeight` are always 0, and the default observer would otherwise clobber
 * `initialRect` with that on mount before any real measurement exists.
 */
const safeObserveElementRect: typeof observeElementRect = (instance, cb) =>
  observeElementRect(instance, (rect) => {
    if (rect.width === 0 && rect.height === 0) return;
    cb(rect);
  });

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
    queryFn: ({ pageParam }: { pageParam: string | undefined }) =>
      api.get<PacketsPageOut>("/api/packets", {
        limit: 50,
        before: pageParam,
        direction: direction === "all" ? undefined : direction,
        kind: kind === "all" ? undefined : kind,
        apid: singleApid,
      }),
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

  const rows = useMemo(
    () => [...feed.filter(passesFilters), ...older.filter(passesFilters)],
    [feed, older, passesFilters],
  );

  const loadOlder = () => void infinite.fetchNextPage();
  const canLoadOlder = !infinite.data || infinite.hasNextPage;

  const scrollRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 28,
    overscan: 8,
    initialRect: { width: 800, height: 600 },
    observeElementRect: safeObserveElementRect,
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
                  ref={(node) => {
                    // Guard against jsdom (no real layout: offsetHeight is always 0), which would
                    // otherwise overwrite the estimated row height with a bogus zero.
                    if (node && node.offsetHeight > 0) virtualizer.measureElement(node);
                  }}
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
