import { cn } from "@/lib/utils";

type Tone = "nominal" | "warn" | "alarm" | "info";

const DOT_CLASS: Record<Tone, string> = {
  nominal: "bg-nominal",
  warn: "bg-warn",
  alarm: "bg-alarm",
  info: "bg-info",
};

const TEXT_CLASS: Record<Tone, string> = {
  nominal: "text-nominal",
  warn: "text-warn",
  alarm: "text-alarm",
  info: "text-info",
};

/** A dot + label indicating alarm state (nominal / low / high mapped to warn / alarm tones by the caller). */
export function AlarmBadge({ tone, text }: { tone: Tone; text: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn("h-1.5 w-1.5 rounded-full", DOT_CLASS[tone])} aria-hidden="true" />
      <span className={cn("label", TEXT_CLASS[tone])}>{text}</span>
    </span>
  );
}
