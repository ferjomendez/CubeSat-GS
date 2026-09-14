import { api } from "@/api/client";
import { useGs } from "@/store/gs";
import { cn } from "@/lib/utils";
import { fmtMhz } from "@/lib/format";

const STORAGE_TONE: Record<string, string> = { ok: "text-nominal", degraded: "text-warn", disabled: "text-dim" };

/** Top strip: serial link, frequency mode (with quick-set buttons), storage state — driven by useGs().status. */
export function StatusStrip() {
  const status = useGs((s) => s.status);

  const setMode = (mode: "tctm" | "beacon_listen") => {
    void api.put("/api/frequency", { mode });
  };

  if (!status) return null;

  return (
    <div className="flex h-8 items-center gap-6 border-b border-line px-3">
      <div className="flex items-center gap-1.5">
        <span
          className={cn("h-1.5 w-1.5 rounded-full", status.serial.connected ? "bg-nominal" : "bg-alarm")}
          aria-hidden="true"
        />
        <span className="label">{status.serial.connected ? status.serial.port ?? "serial" : "no serial"}</span>
      </div>

      <div className="flex items-center gap-2">
        <span className="label">{status.frequency.mode}</span>
        <span className="font-mono tabular-nums text-[13px]">{fmtMhz(status.frequency.mhz)}</span>
        <button type="button" className="label rounded border border-line px-1.5 hover:border-info" onClick={() => setMode("tctm")}>
          TCTM
        </button>
        <button type="button" className="label rounded border border-line px-1.5 hover:border-info" onClick={() => setMode("beacon_listen")}>
          Beacon
        </button>
      </div>

      <div className="flex items-center gap-1.5">
        <span className={cn("label", STORAGE_TONE[status.storage.mongo] ?? "text-dim")}>storage: {status.storage.mongo}</span>
      </div>
    </div>
  );
}
