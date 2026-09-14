const pad = (n: number): string => String(n).padStart(2, "0");

export const utc = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}Z`;
};

export const utcTime = (iso: string): string => utc(iso).slice(11);

export const local = (iso: string): string => new Date(iso).toLocaleString();

export const age = (iso: string, now = Date.now()): string => {
  const s = Math.max(0, Math.round((now - Date.parse(iso)) / 1000));
  return s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m ${pad(s % 60)}s` : `${Math.floor(s / 3600)}h ${pad(Math.floor((s % 3600) / 60))}m`;
};

export const countdown = (iso: string, now = Date.now()): string => {
  const s = Math.max(0, Math.round((Date.parse(iso) - now) / 1000));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60;
  return h ? `${h}h ${pad(m)}m ${pad(r)}s` : m ? `${m}m ${pad(r)}s` : `${r}s`;
};
