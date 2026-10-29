import test from 'node:test';
import assert from 'node:assert/strict';
import { layered } from '../engine/layout.js';

const n = (id, w = 200, h = 80, extra = {}) => ({ id, w, h, ...extra });

test('layered: chain gets increasing ranks and one shared x', () => {
  const p = layered([n('a'), n('b'), n('c')], [['a', 'b'], ['b', 'c']], { x0: 500, gapY: 100 });
  assert.deepEqual(['a', 'b', 'c'].map((k) => p[k].rank), [0, 1, 2]);
  assert.ok(['a', 'b', 'c'].every((k) => Math.abs(p[k].x - 500) < 1e-6));
  assert.ok(p.b.y - p.a.y === 180 && p.c.y - p.b.y === 180);
});

test('layered: siblings are centred under their parent and never overlap', () => {
  const nodes = [n('r', 300), n('x', 260), n('y', 260), n('z', 260)];
  const p = layered(nodes, [['r', 'x'], ['r', 'y'], ['r', 'z']], { x0: 540, gapX: 30 });
  assert.ok(Math.abs(p.y.x - p.r.x) < 1e-6);
  const xs = ['x', 'y', 'z'].map((k) => p[k].x);
  assert.ok(xs[1] - xs[0] >= 260 + 30 - 1e-6 && xs[2] - xs[1] >= 260 + 30 - 1e-6);
});

test('layered: a node with two parents sits between them; explicit rank wins', () => {
  const nodes = [n('a'), n('b'), n('m'), n('late', 200, 80, { rank: 4 })];
  const p = layered(nodes, [['a', 'm'], ['b', 'm'], ['m', 'late']], { x0: 0, gapX: 40 });
  assert.ok(Math.abs(p.m.x - (p.a.x + p.b.x) / 2) < 1e-6);
  assert.equal(p.late.rank, 4);
});

test('layered: rows with different heights stack without overlap', () => {
  const p = layered([n('a', 200, 60), n('b', 200, 160), n('c', 200, 60)], [['a', 'c'], ['b', 'c']], { gapY: 50, y0: 10 });
  assert.equal(p.a.y, 10 + 80);            // tallest in rank 0 is b (160)
  assert.equal(p.c.y, 10 + 160 + 50 + 30);
});

test('layered: cycles and unknown ids are rejected', () => {
  assert.throws(() => layered([n('a'), n('b')], [['a', 'b'], ['b', 'a']]), /cycle/);
  assert.throws(() => layered([n('a')], [['a', 'zz']]), /unknown/);
});

test('layered: wide uneven trees keep every row free of overlaps', () => {
  const nodes = [n('r', 300), n('l', 300), n('q', 300), ...Array.from({ length: 5 }, (_, i) => n(`k${i}`, 220 + 20 * i))];
  const edges = [['r', 'l'], ['r', 'q'], ['l', 'k0'], ['l', 'k1'], ['l', 'k2'], ['q', 'k3'], ['q', 'k4']];
  const p = layered(nodes, edges, { gapX: 24 });
  const row = nodes.filter((k) => p[k.id].rank === 2).sort((a, b) => p[a.id].x - p[b.id].x);
  for (let i = 1; i < row.length; i++) assert.ok(p[row[i].id].x - p[row[i - 1].id].x >= (row[i].w + row[i - 1].w) / 2 + 24 - 1e-6);
});
