"""Build src/ua_alert_forecast/web/ukraine.json (SVG paths + label points) from geoBoundaries UKR ADM1.

Usage: python scripts/make_map.py geoBoundaries-UKR-ADM1_simplified.geojson
Source: https://www.geoboundaries.org (OpenStreetMap contributors, ODbL 1.0).
Projection: equirectangular scaled by cos(48.5°), which is close enough at this size.
"""

import json
import math
import sys
from pathlib import Path

ISO = {
    "UA-05": "vinnytska", "UA-07": "volynska", "UA-09": "luhanska", "UA-12": "dnipropetrovska", "UA-14": "donetska",
    "UA-18": "zhytomyrska", "UA-21": "zakarpatska", "UA-23": "zaporizka", "UA-26": "ivano_frankivska", "UA-30": "kyiv",
    "UA-32": "kyivska", "UA-35": "kirovohradska", "UA-46": "lvivska", "UA-48": "mykolaivska", "UA-51": "odeska",
    "UA-53": "poltavska", "UA-56": "rivnenska", "UA-59": "sumska", "UA-61": "ternopilska", "UA-63": "kharkivska",
    "UA-65": "khersonska", "UA-68": "khmelnytska", "UA-71": "cherkaska", "UA-74": "chernihivska", "UA-77": "chernivetska",
}  # UA-43 Crimea and UA-40 Sevastopol: drawn as land without data
WIDTH, TOLERANCE = 1000, 0.6  # viewBox width; simplification tolerance in viewBox units
OUT = Path(__file__).resolve().parents[1] / "src" / "ua_alert_forecast" / "web" / "ukraine.json"


def polygons(geom):
    return geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]


def simplify(pts, tol):
    """Douglas-Peucker on a closed ring (first point == last): split at the point farthest from the start."""
    if len(pts) < 4:
        return pts
    far = max(range(len(pts)), key=lambda i: math.hypot(pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]))
    return _dp(pts[: far + 1], tol)[:-1] + _dp(pts[far:], tol)


def _dp(pts, tol):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1e-9
        best, idx = 0.0, None
        for i in range(a + 1, b):
            d = abs(dy * (pts[i][0] - x1) - dx * (pts[i][1] - y1)) / norm
            if d > best:
                best, idx = d, i
        if idx is not None and best > tol:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep) if k]


def inside(x, y, rings):
    hit = False
    for ring in rings:
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                hit = not hit
    return hit


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy or 1e-9)))
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy)


def label_point(rings, obstacles):
    """Grid search for the inside point farthest from any edge (and from `obstacles`, e.g. Kyiv city)."""
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    edges = [(a, b) for r in rings + obstacles for a, b in zip(r, r[1:] + r[:1])]
    best, point = -1.0, None
    step = max(max(xs) - min(xs), max(ys) - min(ys)) / 40
    y = min(ys)
    while y <= max(ys):
        x = min(xs)
        while x <= max(xs):
            if inside(x, y, rings) and not any(inside(x, y, [o]) for o in obstacles):
                d = min(seg_dist(x, y, *a, *b) for a, b in edges)
                if d > best:
                    best, point = d, (x, y)
            x += step
        y += step
    return [round(point[0], 1), round(point[1], 1)]


def main(path: str) -> None:
    features = json.load(open(path))["features"]
    k = math.cos(math.radians(48.5))
    allpts = [(lon * k, lat) for f in features for poly in polygons(f["geometry"]) for ring in poly for lon, lat in ring]
    minx, maxx = min(p[0] for p in allpts), max(p[0] for p in allpts)
    miny, maxy = min(p[1] for p in allpts), max(p[1] for p in allpts)
    scale = WIDTH / (maxx - minx)
    height = round((maxy - miny) * scale)

    def project(ring):
        return [((lon * k - minx) * scale, (maxy - lat) * scale) for lon, lat in ring[:-1]]

    shapes = {}
    for f in features:
        rings = [simplify(project(r) + [project(r)[0]], TOLERANCE)[:-1] for poly in polygons(f["geometry"]) for r in poly]
        shapes[f["properties"]["shapeISO"]] = [r for r in rings if len(r) >= 3]

    def path_d(rings):
        return "".join("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in r) + "Z" for r in rings)

    regions = {}
    for iso, rid in ISO.items():
        rings = shapes[iso]
        outer = [max(rings, key=len)]  # label goes in the main part (Kyiv oblast also has the Slavutych exclave)
        obstacles = shapes["UA-30"] if rid == "kyivska" else []
        regions[rid] = {"d": path_d(rings), "label": label_point(outer, obstacles)}
    other = [path_d(shapes[iso]) for iso in ("UA-43", "UA-40")]
    OUT.write_text(json.dumps({"viewBox": f"0 0 {WIDTH} {height}", "regions": regions, "other": other}, separators=(",", ":")))
    print(f"{OUT} {OUT.stat().st_size / 1024:.0f} KB, viewBox 0 0 {WIDTH} {height}")


if __name__ == "__main__":
    main(sys.argv[1])
