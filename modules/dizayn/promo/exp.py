"""Экспорт линий чертежа в экранные координаты той же камеры (без рендера)."""
import bpy, json, sys
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
OUT = sys.argv[sys.argv.index("--") + 1]
W, L, H = 3.6, 4.4, 2.75
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
bpy.ops.object.camera_add(location=(W - 0.35, 0.35, 1.5))
cam = bpy.context.object
cam.rotation_euler = (Vector((1.25, L, 1.05)) - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 15
sc.camera = cam
bpy.context.view_layer.update()

def P(x, y, z):
    v = world_to_camera_view(sc, cam, Vector((x, y, z)))
    return (round(v.x, 5), round(1 - v.y, 5), v.z)

def poly(pts3, n=60):
    """ломаная по 3D-точкам, сэмплирование, обрезка того, что за камерой"""
    out = []
    for a, b in zip(pts3, pts3[1:]):
        for i in range(n + 1):
            t = i / n
            q = [a[k] + (b[k] - a[k]) * t for k in range(3)]
            x, y, z = P(*q)
            if z > 0.15 and -0.6 < x < 1.6 and -0.6 < y < 1.6:
                out.append([x, y])
            elif out and out[-1] is not None:
                out.append(None)
    # разрезаем на сегменты
    segs, cur = [], []
    for p in out:
        if p is None:
            if len(cur) > 1: segs.append(cur)
            cur = []
        else:
            cur.append(p)
    if len(cur) > 1: segs.append(cur)
    return segs

D = {}
D["floor"] = poly([(0, 0, 0), (0, L, 0), (W, L, 0), (W, 0, 0)])
D["ceil"] = poly([(0, 0, H), (0, L, H), (W, L, H), (W, 0, H)])
D["vert"] = poly([(0, L, 0), (0, L, H)]) + poly([(W, L, 0), (W, L, H)])
wx0, wx1, wz0, wz1 = 1.1, 2.5, 0.85, 2.35
D["window"] = poly([(wx0, L, wz0), (wx1, L, wz0), (wx1, L, wz1), (wx0, L, wz1), (wx0, L, wz0)], 20)
grid = []
for i in range(1, 9):
    y = i * 0.5
    if y < L: grid += poly([(0, y, 0.002), (W, y, 0.002)], 30)
for i in range(1, 8):
    x = i * 0.5
    if x < W: grid += poly([(x, 0, 0.002), (x, L, 0.002)], 30)
D["grid"] = grid
def rect(x0, y0, x1, y1): return poly([(x0, y0, .004), (x1, y0, .004), (x1, y1, .004), (x0, y1, .004), (x0, y0, .004)], 25)
D["furn"] = rect(0.08, 1.0, 0.95, 3.95) + rect(0.95, 3.05, 2.05, 3.95) + rect(1.4, 1.75, 1.95, 2.75) + rect(W - 0.42, 1.25, W - 0.04, 3.0)
# размеры: вдоль западной стены (440) и северной (360), с засечками
dims = []
def dim(a, b, tick, label):
    seg = poly([a, b], 40)
    ta = poly([(a[0] - tick[0], a[1] - tick[1], a[2]), (a[0] + tick[0], a[1] + tick[1], a[2])], 4)
    tb = poly([(b[0] - tick[0], b[1] - tick[1], b[2]), (b[0] + tick[0], b[1] + tick[1], b[2])], 4)
    m = P(*[a[k] + (b[k] - a[k]) * (0.66 if label == "440" else 0.5) for k in range(3)])
    dims.append({"seg": seg, "ticks": ta + tb, "label": label, "m": [m[0], m[1]]})
dim((0.3, 0.6, .005), (0.3, L - 0.05, .005), (0.08, 0, 0), "440")
dim((0.05, L - 0.3, .005), (W - 0.05, L - 0.3, .005), (0, 0.08, 0), "360")
dim((0.02, L - 0.12, 0.0), (0.02, L - 0.12, H), (0, 0.08, 0), "275")
dims[-1]["m"] = list(P(0.02, L - 0.12, H * 0.78)[:2])
D["dims"] = dims
cand = [(0, 3.3, 1.1, "H=110"), (0, 2.2, 0.3, "H=30"), (0.55, L, 0.3, "H=30"), (3.05, L, 1.1, "H=110")]
D["sock"] = [{"p": P(x, y, z)[:2], "t": t} for x, y, z, t in cand if 0.04 < P(x, y, z)[0] < 0.96]
json.dump(D, open(OUT, "w"))
print("EXPORTED", {k: len(v) for k, v in D.items()})
