// Small geometry helpers for code-drawn illustrations.

/** Catmull-Rom spline through `pts` as an SVG path (cubic Béziers). */
export function smooth(pts, { closed = false, tension = 0.5 } = {}) {
  const n = pts.length;
  if (n < 3) return `M${pts.map((p) => p.join(' ')).join(' L')}`;
  const get = (i) => (closed ? pts[(i + n) % n] : pts[Math.min(Math.max(i, 0), n - 1)]);
  const k = tension / 3; // 1/6 for the classic uniform Catmull-Rom
  const f = (v) => v.toFixed(1);
  let d = `M${f(pts[0][0])} ${f(pts[0][1])}`;
  for (let i = 0; i < (closed ? n : n - 1); i++) {
    const p0 = get(i - 1), p1 = get(i), p2 = get(i + 1), p3 = get(i + 2);
    d += ` C${f(p1[0] + (p2[0] - p0[0]) * k)} ${f(p1[1] + (p2[1] - p0[1]) * k)} ${f(p2[0] - (p3[0] - p1[0]) * k)} ${f(p2[1] - (p3[1] - p1[1]) * k)} ${f(p2[0])} ${f(p2[1])}`;
  }
  return closed ? `${d} Z` : d;
}

/** Mirror a right-half outline (x offsets from the axis, top → bottom) into a closed symmetric polygon. */
export function mirrorHalf(half, cx) {
  const right = half.map(([dx, y]) => [cx + dx, y]);
  const left = half.filter(([dx]) => dx !== 0).reverse().map(([dx, y]) => [cx - dx, y]);
  return [...right, ...left];
}

/** Evaluate a polyline at fraction f (0..1) by arc length. */
export function pointAt(pts, f) {
  const seg = [];
  let total = 0;
  for (let i = 1; i < pts.length; i++) { const l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(l); total += l; }
  let d = f * total;
  for (let i = 0; i < seg.length; i++) {
    if (d <= seg[i] || i === seg.length - 1) {
      const u = seg[i] ? d / seg[i] : 0;
      return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u];
    }
    d -= seg[i];
  }
  return pts.at(-1);
}
