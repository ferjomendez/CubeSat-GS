import { expect, it } from "vitest";
import { lttb } from "@/lib/lttb";
it("lttb keeps endpoints and caps", () => {
  const pts: [number, number][] = Array.from({ length: 1000 }, (_, i) => [i, (i * 7919) % 101]);
  const out = lttb(pts, 50);
  expect(out.length).toBe(50); expect(out[0]).toEqual(pts[0]); expect(out[49]).toEqual(pts[999]);
  expect(lttb(pts, 5000)).toEqual(pts); expect(lttb([], 10)).toEqual([]);
});
