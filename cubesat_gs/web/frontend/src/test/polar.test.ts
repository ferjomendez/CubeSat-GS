import { expect, it } from "vitest";
import { azElToXY } from "@/lib/polar";
it("maps zenith to centre and horizon north to top", () => {
  expect(azElToXY(0, 90, 100)).toEqual({ x: 0, y: 0 });
  const n = azElToXY(0, 0, 100); expect(n.x).toBeCloseTo(0); expect(n.y).toBeCloseTo(-100);
  const e = azElToXY(90, 0, 100); expect(e.x).toBeCloseTo(100); expect(e.y).toBeCloseTo(0);
  const half = azElToXY(180, 45, 100); expect(half.y).toBeCloseTo(50);
});
