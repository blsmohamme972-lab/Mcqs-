// Layered (top-down) layout for small flow charts and trees. Pure: no DOM, unit-tested in Node.
//
//   layered(nodes, edges, opts) → { [id]: { x, y, rank } }   (x, y are node centres)
//
// nodes: [{ id, w, h, rank? }]   edges: [[from, to], …]   (graph must be acyclic)
// Ranks come from the longest path from the sources unless a node sets `rank`. Inside a rank nodes are ordered by the
// barycentre of their neighbours, then pulled under their parents (and over their children) without overlapping.

export function layered(nodes, edges, { gapX = 36, gapY = 120, x0 = 540, y0 = 0, sweeps = 4 } = {}) {
  const byId = new Map(nodes.map((n, i) => [n.id, { ...n, i }]));
  const parents = new Map(nodes.map((n) => [n.id, []]));
  const kids = new Map(nodes.map((n) => [n.id, []]));
  for (const [a, b] of edges) {
    if (!byId.has(a) || !byId.has(b)) throw new Error(`layered: unknown node in edge ${a} → ${b}`);
    parents.get(b).push(a);
    kids.get(a).push(b);
  }

  // longest-path ranks (iterative; detects cycles)
  const rank = new Map();
  const visiting = new Set();
  const rankOf = (id) => {
    if (rank.has(id)) return rank.get(id);
    if (visiting.has(id)) throw new Error(`layered: cycle through ${id}`);
    visiting.add(id);
    const n = byId.get(id);
    const r = n.rank ?? (parents.get(id).length ? Math.max(...parents.get(id).map(rankOf)) + 1 : 0);
    visiting.delete(id);
    rank.set(id, r);
    return r;
  };
  nodes.forEach((n) => rankOf(n.id));

  const R = Math.max(...rank.values()) + 1;
  const rows = Array.from({ length: R }, () => []);
  nodes.forEach((n) => rows[rank.get(n.id)].push(n.id));

  const x = new Map();
  const place = (row) => { // left-to-right packing, centred on x0
    const total = row.reduce((s, id) => s + byId.get(id).w, 0) + gapX * (row.length - 1);
    let cur = x0 - total / 2;
    for (const id of row) { const w = byId.get(id).w; x.set(id, cur + w / 2); cur += w + gapX; }
  };
  rows.forEach(place);

  const mean = (ids) => ids.reduce((s, id) => s + x.get(id), 0) / ids.length;

  const relax = (row, want) => {
    // Order by desired x, then resolve overlaps with a pool-adjacent-violators style pass that keeps the row's weighted mean.
    const order = [...row].sort((a, b) => (want.get(a) - want.get(b)) || (byId.get(a).i - byId.get(b).i));
    const pos = order.map((id) => want.get(id));
    const w = order.map((id) => byId.get(id).w);
    // minimum centre distance between neighbours
    const d = order.slice(1).map((id, k) => (w[k] + w[k + 1]) / 2 + gapX);
    // convert to "offset" coordinates so the separation constraint becomes monotonic, then isotonic regression
    const off = [0];
    d.forEach((dk, k) => off.push(off[k] + dk));
    const y = pos.map((p, k) => p - off[k]);
    const blocks = [];
    y.forEach((v) => {
      blocks.push({ sum: v, n: 1 });
      while (blocks.length > 1 && blocks.at(-2).sum / blocks.at(-2).n > blocks.at(-1).sum / blocks.at(-1).n) {
        const b = blocks.pop();
        blocks.at(-1).sum += b.sum;
        blocks.at(-1).n += b.n;
      }
    });
    let k = 0;
    blocks.forEach((b) => { const v = b.sum / b.n; for (let j = 0; j < b.n; j++, k++) x.set(order[k], v + off[k]); });
    return order;
  };

  for (let s = 0; s < sweeps; s++) {
    for (let r = 1; r < R; r++) {
      const want = new Map(rows[r].map((id) => [id, parents.get(id).length ? mean(parents.get(id)) : x.get(id)]));
      rows[r] = relax(rows[r], want);
    }
    for (let r = R - 2; r >= 0; r--) {
      const want = new Map(rows[r].map((id) => [id, kids.get(id).length ? mean(kids.get(id)) : x.get(id)]));
      rows[r] = relax(rows[r], want);
    }
  }
  // final top-down pass so parents never end up off their (single) children
  for (let r = 1; r < R; r++) {
    const want = new Map(rows[r].map((id) => [id, parents.get(id).length ? mean(parents.get(id)) : x.get(id)]));
    rows[r] = relax(rows[r], want);
  }

  const out = {};
  let y = y0;
  rows.forEach((row, r) => {
    const hmax = Math.max(...row.map((id) => byId.get(id).h));
    row.forEach((id) => { out[id] = { x: x.get(id), y: y + hmax / 2, rank: r }; });
    y += hmax + gapY;
  });
  return out;
}

/** Bounding box of positioned nodes ({id: {x,y}} + sizes by id). */
export function bounds(pos, size) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const [id, p] of Object.entries(pos)) {
    const s = size[id];
    x0 = Math.min(x0, p.x - s.w / 2); x1 = Math.max(x1, p.x + s.w / 2);
    y0 = Math.min(y0, p.y - s.h / 2); y1 = Math.max(y1, p.y + s.h / 2);
  }
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
}
