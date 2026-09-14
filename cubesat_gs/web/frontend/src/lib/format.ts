export const fmtNum = (v: number | null | undefined, digits = 2): string =>
  v == null || Number.isNaN(v) ? "—" : v.toFixed(digits);

export const fmtHz = (hz: number): string =>
  Math.abs(hz) >= 1000
    ? `${hz > 0 ? "+" : "-"}${(Math.abs(hz) / 1000).toFixed(2)} kHz`
    : `${hz > 0 ? "+" : ""}${Math.round(hz)} Hz`;

export const fmtMhz = (mhz: number): string => `${mhz.toFixed(3)} MHz`;

export const fmtDuration = (s: number): string => {
  const m = Math.floor(s / 60);
  const r = Math.round(s % 60);
  return m ? `${m}m ${String(r).padStart(2, "0")}s` : `${r}s`;
};

export const fmtBytes = (hex: string): string => `${Math.floor(hex.length / 2)} B`;

export const fmtValue = (v: unknown, digits = 3): string =>
  typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(digits)) : v == null ? "—" : String(v);
