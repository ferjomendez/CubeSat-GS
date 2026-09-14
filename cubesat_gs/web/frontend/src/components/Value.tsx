import { fmtNum } from "@/lib/format";
import { cn } from "@/lib/utils";

type Tone = "nominal" | "warn" | "alarm" | "info" | "default";

const TONE_CLASS: Record<Tone, string> = {
  nominal: "text-nominal",
  warn: "text-warn",
  alarm: "text-alarm",
  info: "text-info",
  default: "text-fg",
};

/** A mono numeric value with a dim unit suffix, coloured by semantic tone. */
export function Value({
  v,
  unit,
  digits = 2,
  tone = "default",
  className,
}: {
  v: number | null | undefined;
  unit?: string;
  digits?: number;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span className={cn("font-mono tabular-nums", TONE_CLASS[tone], className)}>
      {fmtNum(v, digits)}
      {unit ? <span className="text-dim ml-1">{unit}</span> : null}
    </span>
  );
}
