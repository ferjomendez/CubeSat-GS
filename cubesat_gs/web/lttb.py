"""Largest-Triangle-Three-Buckets downsampling (Steinarsson 2013) for time series."""
from __future__ import annotations


def lttb(points: list[tuple[float, float]], threshold: int) -> list[tuple[float, float]]:
    n = len(points)
    if threshold >= n or threshold < 3 or n < 3:
        return list(points)
    sampled = [points[0]]
    bucket = (n - 2) / (threshold - 2)
    a = 0
    for i in range(threshold - 2):
        r0 = int((i + 1) * bucket) + 1
        r1 = min(int((i + 2) * bucket) + 1, n)
        avg_x = sum(p[0] for p in points[r0:r1]) / max(r1 - r0, 1)
        avg_y = sum(p[1] for p in points[r0:r1]) / max(r1 - r0, 1)
        s0 = int(i * bucket) + 1
        s1 = int((i + 1) * bucket) + 1
        ax, ay = points[a]
        best, best_area = s0, -1.0
        for j in range(s0, s1):
            area = abs((ax - avg_x) * (points[j][1] - ay) - (ax - points[j][0]) * (avg_y - ay)) * 0.5
            if area > best_area:
                best, best_area = j, area
        sampled.append(points[best])
        a = best
    sampled.append(points[-1])
    return sampled
