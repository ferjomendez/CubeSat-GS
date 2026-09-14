import { useEffect, useMemo, useState } from "react";

import { api } from "@/api/client";
import { KIND_TONE } from "@/components/FeedRow";
import { Panel } from "@/components/Panel";
import { PassInstrument } from "@/components/PassInstrument";
import { Sparkline } from "@/components/Sparkline";
import { Value } from "@/components/Value";
import { age, local, utc } from "@/lib/time";
import { cn } from "@/lib/utils";
import { useGs } from "@/store/gs";

const BUCKETS = 15;

/** Ticks every second, rendering the elapsed time since `iso`. */
function Age({ iso, className }: { iso: string; className?: string }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);
  return <span className={className}>{age(iso, now)}</span>;
}

export function Overview() {
  const status = useGs((s) => s.status);
  const feed = useGs((s) => s.feed);
  const nextPass = useGs((s) => s.nextPass);
  const currentPass = useGs((s) => s.currentPass);
  const commandHistory = useGs((s) => s.commandHistory);
  const gaps = useGs((s) => s.gaps);

  const last = feed[0] ?? null;

  const perMinute = useMemo(() => {
    const now = Date.now();
    const counts = new Array(BUCKETS).fill(0);
    for (const e of feed) {
      const diffMin = Math.floor((now - Date.parse(e.ts)) / 60_000);
      if (diffMin >= 0 && diffMin < BUCKETS) counts[BUCKETS - 1 - diffMin]++;
    }
    return counts;
  }, [feed]);

  const commandRate = useMemo(() => {
    const responded = commandHistory.filter((c) => c.status === "responded").length;
    const timeout = commandHistory.filter((c) => c.status === "timeout").length;
    const failed = commandHistory.filter((c) => c.status === "failed").length;
    const denom = responded + timeout + failed;
    return denom > 0 ? (responded / denom) * 100 : null;
  }, [commandHistory]);

  return (
    <div className="grid grid-cols-12 gap-2">
      <Panel title="Next pass" className="col-span-7" bodyClassName="p-3">
        <PassInstrument next={nextPass} current={currentPass} size={260} />
      </Panel>

      <Panel title="Last packet" className="col-span-5" bodyClassName="p-3">
        {last ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className={cn("label", KIND_TONE[last.kind])}>{last.kind}</span>
              <span className="font-mono tabular-nums">{last.apid ?? "—"}</span>
              <span className="text-dim">{last.apid_name ?? ""}</span>
            </div>
            <p className="truncate">{last.summary}</p>
            <div className="label flex items-center gap-2">
              <span className="font-mono tabular-nums" title={local(last.ts)}>
                {utc(last.ts)}
              </span>
              <span className="text-dim">
                (<Age iso={last.ts} />
                ago)
              </span>
            </div>
            {(last.rssi != null || last.snr != null) && (
              <div className="flex items-center gap-3">
                {last.rssi != null && <Value v={last.rssi} unit="dBm" digits={1} />}
                {last.snr != null && <Value v={last.snr} unit="dB" digits={1} />}
              </div>
            )}
          </div>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <p className="text-dim">No packets yet — switch to Beacon to listen on 437.250 MHz</p>
            <button
              type="button"
              className="label rounded border border-line px-2 py-1 hover:border-info"
              onClick={() => void api.put("/api/frequency", { mode: "beacon_listen" })}
            >
              Listen for beacon
            </button>
          </div>
        )}
      </Panel>

      <Panel title="Today" className="col-span-7" bodyClassName="grid grid-cols-5 gap-3 p-3">
        <div>
          <div className="label">RX packets</div>
          <Value v={status?.session.packets_received} digits={0} />
        </div>
        <div>
          <div className="label">TX packets</div>
          <Value v={status?.session.packets_sent} digits={0} />
        </div>
        <div>
          <div className="label">Command success</div>
          <Value v={commandRate} unit="%" digits={0} />
        </div>
        <div>
          <div className="label">Uptime</div>
          {status ? <Age iso={status.session.start_time} className="font-mono tabular-nums" /> : <span className="text-dim">—</span>}
        </div>
        <div>
          <div className="label">Sequence gaps</div>
          <Value v={gaps} digits={0} tone={gaps > 0 ? "warn" : "default"} />
        </div>
      </Panel>

      <Panel title="Packets per minute" className="col-span-5" bodyClassName="flex flex-col items-start gap-2 p-3">
        <Sparkline data={perMinute} width={200} height={40} />
        <div className="label">
          <span className="font-mono tabular-nums text-fg">{perMinute[perMinute.length - 1]}</span> pkt/min
        </div>
      </Panel>
    </div>
  );
}
