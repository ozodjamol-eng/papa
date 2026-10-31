"""Офис OZOD JAMOL — 3D по замерам владельца (31.10.2026).
Оси: x — короткие стены (0 = западная, стена дивана; 3.45 = восточная, кресло),
     y — длинные стены (0 = южная, дверь во 2-ю комнату; 3.90 = северная, вход с улицы), z — высота.
Потолок 2.10. Стиль: минимализм + тёмная стена с рейками и подсветкой за диваном."""
import bpy, math, sys
from mathutils import Vector

W, L, H = 3.45, 3.90, 2.10
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/ofis"
SAMPLES = int(sys.argv[sys.argv.index("--") + 2]) if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 2 else 96

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def mat(name, color, rough=0.6, metal=0.0, emit=None, strength=0.0, transm=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if transm:
        b.inputs["Transmission Weight"].default_value = transm
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m

def box(name, x0, y0, z0, x1, y1, z1, m, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.object; o.name = name
    o.scale = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(m)
    if bevel:
        mod = o.modifiers.new("bev", "BEVEL"); mod.width = bevel; mod.segments = 3; mod.limit_method = "ANGLE"; mod.harden_normals = False
        for poly in o.data.polygons: poly.use_smooth = False
    return o

# --- материалы
WALL = mat("wall", (0.86, 0.84, 0.80), 0.85)
CEIL = mat("ceil", (0.92, 0.92, 0.91), 0.9)
OAK = mat("oak", (0.50, 0.33, 0.18), 0.45)
DARKBACK = mat("darkback", (0.015, 0.015, 0.015), 0.9)
SLAT = mat("slat", (0.022, 0.02, 0.018), 0.5)
LED = mat("led", (1, 0.75, 0.45), 0.5, emit=(1, 0.66, 0.36), strength=18)
SPOT = mat("spot", (1, 1, 1), 0.3, emit=(1, 0.85, 0.7), strength=30)
FABRIC = mat("fabric", (0.42, 0.42, 0.41), 0.95)
CUSH = mat("cush", (0.14, 0.14, 0.15), 0.95)
BROWN = mat("brownpvc", (0.18, 0.09, 0.05), 0.5)
WHITEPVC = mat("whitepvc", (0.9, 0.9, 0.88), 0.35)
FROST = mat("frost", (0.95, 0.93, 0.85), 0.3, emit=(1, 0.95, 0.85), strength=2.2)
DARKGLASS = mat("darkglass", (0.03, 0.03, 0.035), 0.08)
TVSCR = mat("tv", (0.01, 0.01, 0.012), 0.12)
ACW = mat("ac", (0.93, 0.93, 0.93), 0.4)
RUG = mat("rug", (0.78, 0.75, 0.70), 1.0)
LINEN = mat("linen", (0.82, 0.78, 0.70), 0.9)
GREEN = mat("leaf", (0.12, 0.30, 0.10), 0.7)
POT = mat("pot", (0.75, 0.72, 0.66), 0.8)

T = 0.1  # толщина стен (снаружи комнаты)
# пол, потолок
box("floor", 0, 0, -0.05, W, L, 0, OAK)
box("ceiling", 0, 0, H, W, L, H + 0.05, CEIL)
# стены: западная, восточная, южная (с проёмом двери 2.40–3.34), северная (проём 1.55–2.78)
box("wall_w", -T, -T, 0, 0, L + T, H, WALL)
box("wall_e", W, -T, 0, W + T, L + T, H, WALL)
box("wall_s_a", 0, -T, 0, 2.40, 0, H, WALL)
box("wall_s_b", 3.34, -T, 0, W, 0, H, WALL)
box("wall_s_top", 2.40, -T, 2.00, 3.34, 0, H, WALL)
box("wall_n_a", 0, L, 0, 1.55, L + T, H, WALL)
box("wall_n_b", 2.78, L, 0, W, L + T, H, WALL)
box("wall_n_top", 1.55, L, 2.02, 2.78, L + T, H, WALL)

# --- вход с улицы: коричневый блок (узкое окно слева + дверь), стекло матовое со светом улицы
y0, y1 = L + 0.02, L + 0.08
box("ent_frame", 1.55, y1, 0, 2.78, y1 + 0.02, 2.02, BROWN)
box("ent_side_glass", 1.62, y0, 0.95, 1.92, y1, 1.85, FROST)
box("ent_door_glass", 2.05, y0, 0.95, 2.70, y1, 1.85, FROST)
box("ent_transom", 1.62, y0, 1.90, 2.70, y1, 1.98, FROST)
box("ent_door_low", 2.05, y0 - 0.01, 0.05, 2.70, y1, 0.90, BROWN)
box("ent_side_low", 1.62, y0 - 0.01, 0.05, 1.92, y1, 0.90, BROWN)
for (a, b) in ((1.55, 1.62), (1.92, 2.05), (2.70, 2.78)):
    box("ent_mull", a, y0 - 0.02, 0, b, y1, 2.02, BROWN)
box("ent_rail", 1.55, y0 - 0.02, 1.85, 2.78, y1, 1.95, BROWN)
# рулонная штора (лён) — свёрнута вверху
bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=1.25, location=(2.165, L - 0.06, 1.99), rotation=(0, math.pi / 2, 0))
bpy.context.object.data.materials.append(LINEN)

# --- кондиционер справа от входа
box("ac", 2.86, L - 0.21, 1.74, 3.40, L, 2.03, ACW, bevel=0.02)
box("ac_slot", 2.90, L - 0.215, 1.76, 3.36, L - 0.20, 1.79, mat("acslot", (0.6, 0.6, 0.6), 0.5))

# --- вытяжка на северной стене, слева над ТВ
box("fan", 0.55, L - 0.03, 1.62, 0.77, L, 1.84, ACW)

# --- дверь во 2-ю комнату (белая ПВХ, два тёмных стекла)
box("in_frame_l", 2.40, -0.04, 0, 2.46, 0.02, 2.00, WHITEPVC)
box("in_frame_r", 3.28, -0.04, 0, 3.34, 0.02, 2.00, WHITEPVC)
box("in_frame_t", 2.40, -0.04, 1.94, 3.34, 0.02, 2.00, WHITEPVC)
box("in_leaf", 2.46, -0.03, 0, 3.28, 0.0, 1.94, WHITEPVC)
box("in_glass_a", 2.52, 0.0, 0.92, 2.85, 0.005, 1.88, DARKGLASS)
box("in_glass_b", 2.90, 0.0, 0.92, 3.22, 0.005, 1.88, DARKGLASS)
box("in_handle", 2.50, 0.005, 1.00, 2.53, 0.05, 1.03, mat("chrome", (0.8, 0.8, 0.8), 0.2, 1.0))

# --- тёмная стена с рейками за диваном (западная), LED сверху и снизу
box("slat_back", 0, 0, 0, 0.012, L, H, DARKBACK)
x = 0.012
yy = 0.02
while yy < L - 0.04:
    box("slat", x, yy, 0.06, x + 0.022, yy + 0.04, H - 0.06, SLAT)
    yy += 0.065
box("led_top", 0.04, 0.02, H - 0.035, 0.05, L - 0.02, H - 0.025, LED)
box("led_bot", 0.04, 0.02, 0.03, 0.05, L - 0.02, 0.04, LED)
# скрытая подсветка по периметру потолка (остальные стены)
for (n, a) in (("cove_e", (W - 0.05, 0.02, H - 0.03, W - 0.04, L - 0.02, H - 0.02)),
               ("cove_s", (0.06, 0.04, H - 0.03, W - 0.06, 0.05, H - 0.02)),
               ("cove_n", (0.06, L - 0.05, H - 0.03, W - 0.06, L - 0.04, H - 0.02))):
    box(n, *a, LED)
# точечные светильники
for (sx, sy) in ((0.9, 1.0), (0.9, 2.9), (2.5, 1.0), (2.5, 2.9), (1.7, 1.95)):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.01, location=(sx, sy, H - 0.004))
    bpy.context.object.data.materials.append(SPOT)

# --- угловой диван (Г): вдоль западной стены + вдоль южной
def sofa_run(n, x0, y0, x1, y1, back_side):
    box(n + "_base", x0, y0, 0.06, x1, y1, 0.30, FABRIC, bevel=0.02)
    box(n + "_seat", x0, y0, 0.30, x1, y1, 0.44, FABRIC, bevel=0.04)
    if back_side == "w":
        box(n + "_back", x0, y0, 0.30, x0 + 0.22, y1, 0.82, FABRIC, bevel=0.05)
    else:
        box(n + "_back", x0, y0, 0.30, x1, y0 + 0.22, 0.82, FABRIC, bevel=0.05)
sofa_run("sofa_w", 0.06, 0.06, 0.96, 3.05, "w")
sofa_run("sofa_s", 0.96, 0.06, 2.20, 0.96, "s")
box("sofa_arm_n", 0.055, 2.85, 0.06, 0.965, 3.055, 0.62, FABRIC, bevel=0.04)
box("sofa_arm_e", 2.00, 0.055, 0.06, 2.205, 0.965, 0.62, FABRIC, bevel=0.04)
for cy in (0.6, 1.4, 2.2):
    box("cush", 0.30, cy, 0.44, 0.44, cy + 0.42, 0.84, CUSH, bevel=0.06)
for cx in (1.1, 1.65):
    box("cush", cx, 0.30, 0.44, cx + 0.42, 0.44, 0.84, CUSH, bevel=0.06)

# --- ТВ + парящая тумба (северная стена, слева от входа)
box("console", 0.25, L - 0.40, 0.28, 1.45, L, 0.55, OAK, bevel=0.01)
box("tv", 0.30, L - 0.06, 0.95, 1.42, L - 0.02, 1.58, TVSCR, bevel=0.005)

# --- журнальный стол, ковёр, кресло, растение
box("rug", 1.05, 1.05, 0, 2.35, 2.95, 0.012, RUG)
box("table_top", 1.25, 1.35, 0.36, 1.85, 2.55, 0.42, OAK, bevel=0.01)
box("table_base", 1.32, 1.42, 0.05, 1.78, 2.48, 0.36, OAK)
box("arm_seat", 2.62, 1.55, 0.10, 3.40, 2.35, 0.44, FABRIC, bevel=0.04)
box("arm_back", 3.18, 1.55, 0.10, 3.40, 2.35, 0.82, FABRIC, bevel=0.05)
box("arm_l", 2.615, 1.545, 0.10, 3.40, 1.70, 0.62, FABRIC, bevel=0.04)
box("arm_r", 2.615, 2.20, 0.10, 3.405, 2.355, 0.62, FABRIC, bevel=0.04)
bpy.ops.mesh.primitive_cylinder_add(radius=0.16, depth=0.36, location=(3.18, 3.55, 0.18))
bpy.context.object.data.materials.append(POT)
for i, (dx, dy, dz, r) in enumerate(((0, 0, 0.75, 0.28), (0.08, -0.05, 1.05, 0.22), (-0.06, 0.04, 1.28, 0.16))):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(3.18 + dx, 3.55 + dy, dz))
    bpy.context.object.data.materials.append(GREEN)

# --- свет: тёплый общий + мягкий заполняющий
bpy.ops.object.light_add(type="AREA", location=(W / 2, L / 2, H - 0.02))
lt = bpy.context.object.data; lt.size = 2.0; lt.energy = 30; lt.color = (1, 0.9, 0.8)
world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.05

# --- рендер
sc.render.engine = "CYCLES"
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1280, 960
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
sc.view_settings.exposure = -0.6

CAMS = {
    "1_vhod": ((2.45, 0.35, 1.30), (1.75, 3.90, 1.05)),
    "2_divan": ((3.30, 1.20, 1.25), (0.0, 2.10, 0.85)),
    "3_dlinny": ((1.95, 3.70, 1.35), (1.55, 0.0, 0.85)),
    "4_kreslo": ((0.95, 2.70, 1.25), (3.45, 1.10, 0.95)),
}
for name, (pos, tgt) in CAMS.items():
    bpy.ops.object.camera_add(location=pos)
    cam = bpy.context.object
    cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 15
    cam.data.clip_start = 0.05
    sc.camera = cam
    sc.render.filepath = f"{OUT}/{name}.png"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name, flush=True)
