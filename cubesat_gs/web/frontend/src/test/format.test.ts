import { expect, it } from "vitest";
import { fmtDuration, fmtHz, fmtMhz, fmtNum } from "@/lib/format";
import { age, countdown } from "@/lib/time";
it("formats", () => {
  expect(fmtNum(3.14159, 2)).toBe("3.14"); expect(fmtNum(null, 2)).toBe("—");
  expect(fmtHz(4008.4)).toBe("+4.01 kHz"); expect(fmtHz(-120)).toBe("-120 Hz");
  expect(fmtMhz(437.25)).toBe("437.250 MHz"); expect(fmtDuration(318)).toBe("5m 18s");
  const now = Date.parse("2026-09-13T12:00:10Z");
  expect(age("2026-09-13T12:00:00Z", now)).toBe("10s"); expect(countdown("2026-09-13T13:01:05Z", now)).toBe("1h 00m 55s");
});
