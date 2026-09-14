/** Largest-Triangle-Three-Buckets downsampling (Steinarsson 2013) for time series. Mirrors cubesat_gs/web/lttb.py. */
export function lttb(points: [number, number][], threshold: number): [number, number][] {
  const n = points.length;
  if (threshold >= n || threshold < 3 || n < 3) return points.slice();

  const sampled: [number, number][] = [points[0]];
  const bucket = (n - 2) / (threshold - 2);
  let a = 0;
  for (let i = 0; i < threshold - 2; i++) {
    const r0 = Math.floor((i + 1) * bucket) + 1;
    const r1 = Math.min(Math.floor((i + 2) * bucket) + 1, n);
    let sumX = 0, sumY = 0;
    for (let k = r0; k < r1; k++) { sumX += points[k][0]; sumY += points[k][1]; }
    const count = Math.max(r1 - r0, 1);
    const avgX = sumX / count, avgY = sumY / count;

    const s0 = Math.floor(i * bucket) + 1;
    const s1 = Math.floor((i + 1) * bucket) + 1;
    const [ax, ay] = points[a];
    let best = s0, bestArea = -1;
    for (let j = s0; j < s1; j++) {
      const area = Math.abs((ax - avgX) * (points[j][1] - ay) - (ax - points[j][0]) * (avgY - ay)) * 0.5;
      if (area > bestArea) { best = j; bestArea = area; }
    }
    sampled.push(points[best]);
    a = best;
  }
  sampled.push(points[n - 1]);
  return sampled;
}
