import type { PassOut, PassStateOut, TrackPoint } from "@/api/types";
import { Countdown } from "@/components/Countdown";
import { Value } from "@/components/Value";
import { fmtDuration, fmtHz } from "@/lib/format";
import { azElToXY } from "@/lib/polar";

const RINGS = [100, 66.7, 33.3];
const CARDINALS: { label: string; az: number }[] = [
  { label: "N", az: 0 },
  { label: "E", az: 90 },
  { label: "S", az: 180 },
  { label: "W", az: 270 },
];

/**
 * Polar sky plot (rings at 0/30/60° elevation, N/E/S/W, ground track, current position dot) with a right
 * column showing either live pass telemetry (progress bar + az/el/range/doppler) or a countdown to the next
 * pass. Reused unchanged by the Pass Tracker view.
 */
export function PassInstrument({
  next,
  current,
  track,
  size = 200,
}: {
  next: PassOut | null;
  current: PassStateOut | null;
  track?: TrackPoint[];
  size?: number;
}) {
  const trackPoints = (track ?? []).map((p) => azElToXY(p.az, p.el, 100));
  const dot = current ? azElToXY(current.az, current.el, 100) : null;

  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} viewBox="-110 -110 220 220" role="img" aria-label="Sky plot">
        {RINGS.map((r) => (
          <circle key={r} cx={0} cy={0} r={r} fill="none" stroke="hsl(var(--line))" strokeWidth={1} />
        ))}
        {CARDINALS.map(({ label, az }) => {
          const { x, y } = azElToXY(az, 0, 108);
          return (
            <text
              key={label}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="font-label"
              fontSize={11}
              fill="hsl(var(--text-dim))"
            >
              {label}
            </text>
          );
        })}
        {trackPoints.length > 1 && (
          <polyline
            points={trackPoints.map((p) => `${p.x},${p.y}`).join(" ")}
            fill="none"
            stroke="hsl(var(--info))"
            strokeWidth={1.5}
            opacity={0.6}
          />
        )}
        {dot && (
          <>
            <circle cx={dot.x} cy={dot.y} r={9} fill="hsl(var(--info) / 0.25)" className="transition-all duration-300" />
            <circle cx={dot.x} cy={dot.y} r={4} fill="hsl(var(--info))" className="transition-all duration-300" />
          </>
        )}
      </svg>

      <div className="min-w-0 flex-1">
        {current ? (
          <div className="space-y-2">
            <div className="h-1 rounded bg-line">
              <div className="h-1 rounded bg-info" style={{ width: `${Math.round(current.progress * 100)}%` }} />
            </div>
            <div className="label grid grid-cols-2 gap-1">
              <span>
                Az <Value v={current.az} unit="°" digits={0} />
              </span>
              <span>
                El <Value v={current.el} unit="°" digits={0} />
              </span>
              <span>
                Range <Value v={current.range_km} unit="km" digits={0} />
              </span>
              <span>Doppler <span className="font-mono tabular-nums">{fmtHz(current.doppler_hz)}</span></span>
            </div>
          </div>
        ) : next ? (
          <div className="space-y-1">
            <div className="label">AOS in</div>
            <Countdown iso={next.aos} className="text-2xl font-mono tabular-nums" />
            <div className="label grid grid-cols-2 gap-1">
              <span>
                Max el <Value v={next.max_el} unit="°" digits={0} />
              </span>
              <span>Duration {fmtDuration(next.duration_s)}</span>
              <span>
                AOS az <Value v={next.aos_az} unit="°" digits={0} />
              </span>
              <span>
                LOS az <Value v={next.los_az} unit="°" digits={0} />
              </span>
            </div>
          </div>
        ) : (
          <p className="text-dim">Add a TLE in Settings to predict passes</p>
        )}
      </div>
    </div>
  );
}
