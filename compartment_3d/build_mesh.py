"""Build the compressed lower-leg model used by compartment_3d.html.

Source: BodyParts3D (c) The Database Center for Life Science, CC BY-SA 2.1 JP.
https://dbarchive.biosciencedbc.jp/en/bodyparts3d/

Usage:
  python build_mesh.py <isa_BP3D_4.0_obj_99 dir> <out dir>
Needs: trimesh, numpy, fast-simplification, shapely, networkx.

Writes leg.bin: every part packed with a small custom codec (16-bit quantised,
delta + zigzag positions split into byte planes, high-water-mark indices as
varints) and zlib-compressed, so the browser can unpack it with the built-in
DecompressionStream and no decoder library. Also writes leg_meta.json: part
table, artery centre-lines and fascia outlines at the cut plane.
"""
import json
import os
import sys
import zlib

import fast_simplification
import numpy as np
import shapely
import trimesh
from shapely.geometry import MultiPolygon, Polygon

SRC, OUT = sys.argv[1], sys.argv[2]

# name in the model -> (BodyParts3D element file, compartment, triangle budget)
PARTS = {
    "tibia": ("FJ3387", "bone", 5000),
    "fibula": ("FJ3366", "bone", 2500),
    "tibialis_anterior": ("FJ1439", "anterior", 2500),
    "extensor_digitorum_longus": ("FJ1406", "anterior", 2000),
    "extensor_hallucis_longus": ("FJ1408", "anterior", 1500),
    "fibularis_tertius": ("FJ1411", "anterior", 800),
    "fibularis_longus": ("FJ1410", "lateral", 2000),
    "fibularis_brevis": ("FJ1409", "lateral", 1500),
    "gastrocnemius_medial": ("FJ1397", "superficial_posterior", 2500),
    "gastrocnemius_lateral": ("FJ1394", "superficial_posterior", 2500),
    "soleus": ("FJ1437", "superficial_posterior", 3000),
    "plantaris": ("FJ1429", "superficial_posterior", 600),
    "calcaneal_tendon": ("FJ1405", "superficial_posterior", 800),
    "tibialis_posterior": ("FJ1440", "deep_posterior", 2000),
    "flexor_digitorum_longus": ("FJ1414", "deep_posterior", 1500),
    "flexor_hallucis_longus": ("FJ1415", "deep_posterior", 1500),
    "popliteus": ("FJ1430", "deep_posterior", 800),
    "anterior_tibial_artery": ("FJ2130", "vessel", 1200),
    "posterior_tibial_artery": ("FJ2172", "vessel", 1200),
}
CUT_FRACTION = 0.40  # cut plane height: 40% of tibia length above the ankle


def load(fj):
    path = os.path.join(SRC, fj + ".obj")
    m = trimesh.load(path, force="mesh", process=True)
    return m


meshes = {k: load(v[0]) for k, v in PARTS.items()}

# BodyParts3D: millimetres, Z up, X = patient's left, Y = posterior.
tib = meshes["tibia"]
zmin, zmax = tib.bounds[0][2], tib.bounds[1][2]
cut_z = zmin + CUT_FRACTION * (zmax - zmin)
centre = tib.bounds.mean(axis=0)
origin = np.array([centre[0], centre[1], cut_z])


def to_three(p):
    """BP3D mm (x left, y posterior, z up) -> three.js metres (x right-of-viewer, y up, z anterior)."""
    p = (np.asarray(p) - origin) / 1000.0
    return np.stack([p[..., 0], p[..., 2], -p[..., 1]], axis=-1)


parts = {}
for name, m in meshes.items():
    budget = PARTS[name][2]
    v, f = m.vertices, m.faces
    if len(f) > budget:
        v, f = fast_simplification.simplify(v, f, target_reduction=1 - budget / len(f))
    t = trimesh.Trimesh(to_three(v), f, process=True)
    t.fix_normals()
    parts[name] = t
    print(f"{name:28s} {len(m.faces):6d} -> {len(t.faces):5d} tris")

lo = np.min([t.vertices.min(0) for t in parts.values()], axis=0)
hi = np.max([t.vertices.max(0) for t in parts.values()], axis=0)
Q = 65535.0


def varint(n, out):
    while n >= 0x80:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    out.append(n)


def encode(t):
    """Reorder vertices by first use, then pack indices and positions."""
    order, remap = [], {}
    for i in t.faces.ravel():
        if i not in remap:
            remap[i] = len(order)
            order.append(i)
    idx = np.array([remap[i] for i in t.faces.ravel()])
    q = np.round((t.vertices[order] - lo) / (hi - lo) * Q).astype(np.int64)
    d = np.diff(q, axis=0, prepend=np.zeros((1, 3), np.int64))
    d = (d + 32768) % 65536 - 32768  # wrap to int16; decoder adds mod 65536
    zz = ((d << 1) ^ (d >> 63)).astype(np.uint32)  # zigzag
    planes = bytes(np.concatenate([(zz.T & 0xFF).ravel(), (zz.T >> 8).ravel()]).astype(np.uint8))
    ib, hw = bytearray(), 0
    for i in idx:
        varint(hw - i, ib)  # 0 = next new vertex
        if i == hw:
            hw += 1
    return planes, bytes(ib), len(order), len(idx)


blob, table = bytearray(), []
for name, t in parts.items():
    planes, ib, nv, ni = encode(t)
    table.append({"name": name, "comp": PARTS[name][1], "nv": nv, "ni": ni, "ib": len(ib)})
    blob += planes + ib
packed = zlib.compress(bytes(blob), 9)
with open(os.path.join(OUT, "leg.bin"), "wb") as fh:
    fh.write(packed)
print(f"raw {len(blob)} B -> packed {len(packed)} B")


def centreline(m, step=6.0):
    """Mean of vertices in Z slabs, top to bottom (mm), returned in three.js metres."""
    z = m.vertices[:, 2]
    pts = []
    for z0 in np.arange(z.max(), z.min(), -step):
        sel = m.vertices[(z <= z0) & (z > z0 - step)]
        if len(sel):
            pts.append(sel.mean(axis=0))
    pts = np.array(pts)
    # light smoothing
    k = np.array([1, 2, 3, 2, 1], float)
    k /= k.sum()
    sm = np.stack([np.convolve(np.pad(pts[:, i], 2, mode="edge"), k, mode="valid") for i in range(3)], 1)
    return np.round(to_three(sm), 4).tolist()


def section_polys(m):
    s = m.section(plane_origin=[0, 0, cut_z], plane_normal=[0, 0, 1])
    if s is None:
        return []
    polys = []
    for ent in s.discrete:
        if len(ent) >= 4:
            p = Polygon(ent[:, :2])
            if p.is_valid and p.area > 1:
                polys.append(p)
            elif not p.is_valid:
                p = p.buffer(0)
                if p.area > 1:
                    polys.append(p)
    return polys


outlines = {}
groups = {}
for name, (_, comp, _) in PARTS.items():
    if comp in ("anterior", "lateral", "superficial_posterior", "deep_posterior", "bone"):
        groups.setdefault(comp, []).extend(section_polys(meshes[name]))

for comp, polys in groups.items():
    if not polys or comp == "bone":
        continue
    u = shapely.union_all([p.buffer(2.2) for p in polys]).buffer(-0.6)
    if isinstance(u, MultiPolygon):
        u = max(u.geoms, key=lambda g: g.area)
    ring = np.array(u.exterior.simplify(0.4).coords)
    pts3 = np.column_stack([ring, np.full(len(ring), cut_z)])
    c3 = np.array([[u.centroid.x, u.centroid.y, cut_z]])
    outlines[comp] = {
        "ring": np.round(to_three(pts3), 4).tolist(),
        "centroid": np.round(to_three(c3)[0], 4).tolist(),
    }
    print(comp, "outline", len(ring), "pts, area", round(u.area), "mm2")

meta = {
    "parts": table,
    "lo": np.round(lo, 6).tolist(),
    "hi": np.round(hi, 6).tolist(),
    "lateral_x": float(np.sign(parts["fibula"].vertices[:, 0].mean() - parts["tibia"].vertices[:, 0].mean())),
    "tibia_top": round((zmax - cut_z) / 1000, 4),
    "tibia_bottom": round((zmin - cut_z) / 1000, 4),
    "arteries": {
        "anterior_tibial": centreline(meshes["anterior_tibial_artery"]),
        "posterior_tibial": centreline(meshes["posterior_tibial_artery"]),
    },
    "outlines": outlines,
}
with open(os.path.join(OUT, "leg_meta.json"), "w") as fh:
    json.dump(meta, fh, separators=(",", ":"))
print("cut at", round(cut_z, 1), "mm; meta written")
