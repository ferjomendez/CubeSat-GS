import type { FeedEntry, Kind } from "@/api/types";
import { HexView } from "@/components/HexView";
import { fmtNum, fmtValue } from "@/lib/format";
import { local, utcTime } from "@/lib/time";
import { cn } from "@/lib/utils";

export const KIND_TONE: Record<Kind, string> = {
  beacon: "text-info",
  telemetry: "text-nominal",
  command: "text-warn",
  malformed: "text-alarm",
  unknown: "text-dim",
};

/** One row of the live feed table: summary line (colour by kind) plus an expandable fields table + hex dump. */
export function FeedRow({
  entry,
  expanded,
  onToggle,
}: {
  entry: FeedEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="border-b border-line/60">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        className="grid h-7 w-full grid-cols-[112px_28px_56px_48px_1fr_56px_56px] items-center gap-2 px-2 text-left text-[13px] hover:bg-raised"
      >
        <span className="font-mono tabular-nums text-dim" title={local(entry.ts)}>
          {utcTime(entry.ts)}
        </span>
        <span className="label uppercase">{entry.direction}</span>
        <span className="font-mono tabular-nums">{entry.apid ?? "—"}</span>
        <span className="font-mono tabular-nums text-dim">{entry.seq ?? "—"}</span>
        <span className={cn("truncate", KIND_TONE[entry.kind])}>{entry.summary}</span>
        <span className="font-mono tabular-nums text-dim">{fmtNum(entry.rssi, 1)}</span>
        <span className="font-mono tabular-nums text-dim">{fmtNum(entry.snr, 1)}</span>
      </button>
      {expanded && (
        <div className="space-y-2 border-t border-line/60 bg-raised/60 px-3 py-2">
          {entry.fields && entry.fields.length > 0 && (
            <table className="w-full text-left text-[12px]">
              <thead>
                <tr className="label">
                  <th className="py-0.5 pr-3">Field</th>
                  <th className="pr-3">Value</th>
                  <th>Unit</th>
                </tr>
              </thead>
              <tbody>
                {entry.fields.map((f) => (
                  <tr key={f.name}>
                    <td className="py-0.5 pr-3 text-dim">{f.name}</td>
                    <td className={cn("font-mono tabular-nums pr-3", (f.alarm === "low" || f.alarm === "high") && "text-alarm")}>
                      {fmtValue(f.value)}
                    </td>
                    <td className="text-dim">{f.unit ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <HexView hex={entry.raw_hex} />
        </div>
      )}
    </div>
  );
}
