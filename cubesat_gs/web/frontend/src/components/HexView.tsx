/** Renders a hex string as a classic hex dump: offset, 16 bytes per row, uppercase pairs. */
export function HexView({ hex, className }: { hex: string; className?: string }) {
  const clean = hex.replace(/\s+/g, "").toUpperCase();
  const bytes: string[] = [];
  for (let i = 0; i + 1 < clean.length; i += 2) bytes.push(clean.slice(i, i + 2));

  const rows: string[][] = [];
  for (let i = 0; i < bytes.length; i += 16) rows.push(bytes.slice(i, i + 16));

  return (
    <div className={className ?? "font-mono text-[13px] tabular-nums"}>
      {rows.length === 0 ? (
        <div className="text-dim">—</div>
      ) : (
        rows.map((row, i) => (
          <div key={i} className="flex gap-3">
            <span className="text-dim">{(i * 16).toString(16).padStart(4, "0").toUpperCase()}</span>
            <span>{row.join(" ")}</span>
          </div>
        ))
      )}
    </div>
  );
}
