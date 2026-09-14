import { useEffect, useState } from "react";
import { countdown } from "@/lib/time";

/** Ticks every second, rendering the time remaining until `iso`. */
export function Countdown({ iso, className }: { iso: string; className?: string }) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <span className={className ?? "font-mono tabular-nums"}>
      {countdown(iso, now)}
    </span>
  );
}
