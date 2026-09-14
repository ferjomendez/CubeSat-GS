/** Polar sky plot: zenith at centre, horizon at `radius`, north up, east right. */
export function azElToXY(az: number, el: number, radius: number): { x: number; y: number } {
  const r = ((90 - Math.max(0, Math.min(90, el))) / 90) * radius;
  const a = (az * Math.PI) / 180;
  return { x: r * Math.sin(a) + 0, y: -r * Math.cos(a) + 0 };
}
