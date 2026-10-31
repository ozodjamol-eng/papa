"""Офис OZOD JAMOL — этапы «коробка → тёплый минимализм» для роликов (01.11.2026).
Геометрия — по замерам из ofis_ozod.py (3.45 × 3.90, потолок 2.10). Одна камера, кадр 9:16.
Запуск: python(bpy) ofis_etapy.py OUT SAMPLES RES_W STAGES
STAGES — через запятую: box, wrong, base, tv, sofa, full, night, ids"""
import bpy, math, sys, json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

OUT, SAMPLES, RW = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
STAGES = sys.argv[4].split(',')
W, L, H = 3.45, 3.90, 2.10
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def node_mat(name, color, rough=0.6, metal=0.0, emit=None, strength=0.0, noise=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    if noise:  # пятнистость штукатурки/бетона
        n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = noise[0]; n.inputs["Detail"].default_value = 8
        r = nt.nodes.new("ShaderNodeValToRGB"); r.color_ramp.elements[0].color = (*[c * noise[1] for c in color], 1)
        r.color_ramp.elements[1].color = (*[min(1, c * noise[2]) for c in color], 1)
        nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
        bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.15
        nt.links.new(n.outputs["Fac"], bm.inputs["Height"]); nt.links.new(bm.outputs["Normal"], b.inputs["Normal"])
    return m

def wood(name, color):  # дуб: полосы волокон
    m = node_mat(name, color, 0.42); nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    w = nt.nodes.new("ShaderNodeTexWave"); w.inputs["Scale"].default_value = 3.0; w.inputs["Distortion"].default_value = 6
    w.inputs["Detail"].default_value = 4
    r = nt.nodes.new("ShaderNodeValToRGB"); r.color_ramp.elements[0].color = (*[c * 0.78 for c in color], 1)
    r.color_ramp.elements[1].color = (*[min(1, c * 1.12) for c in color], 1)
    nt.links.new(w.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    return m

COL = {}
def col(name):
    if name not in COL:
        c = bpy.data.collections.new(name); sc.collection.children.link(c); COL[name] = c
    return COL[name]

def box(name, x0, y0, z0, x1, y1, z1, m, grp, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.object; o.name = name; o.scale = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    bpy.ops.object.transform_apply(scale=True); o.data.materials.append(m)
    if bevel:
        md = o.modifiers.new("bev", "BEVEL"); md.width = bevel; md.segments = 3; md.limit_method = "ANGLE"
    for c in o.users_collection: c.objects.unlink(o)
    col(grp).objects.link(o); return o

def put(o, grp):
    for c in o.users_collection: c.objects.unlink(o)
    col(grp).objects.link(o); return o

# --- материалы
PLASTER = node_mat("plaster", (0.55, 0.53, 0.50), 0.95, noise=(6, 0.82, 1.12))
CONCRETE = node_mat("concrete", (0.42, 0.41, 0.39), 0.9, noise=(9, 0.75, 1.18))
CEILRAW = node_mat("ceilraw", (0.62, 0.61, 0.59), 0.95, noise=(5, 0.85, 1.1))
WALLW = node_mat("wallwarm", (0.83, 0.79, 0.72), 0.85)
CEIL = node_mat("ceil", (0.93, 0.92, 0.90), 0.9)
LAM = wood("laminate", (0.62, 0.47, 0.32))
OAKL = wood("oaklight", (0.70, 0.54, 0.37))
DARKBACK = node_mat("darkback", (0.015, 0.015, 0.015), 0.9)
SLATD = node_mat("slatdark", (0.022, 0.02, 0.018), 0.5)
LED = node_mat("led", (1, 0.75, 0.45), 0.5, emit=(1, 0.66, 0.36), strength=22)
SPOT = node_mat("spot", (1, 1, 1), 0.3, emit=(1, 0.85, 0.7), strength=35)
SPOTOFF = node_mat("spotoff", (0.85, 0.85, 0.85), 0.3)
GREYF = node_mat("greyfabric", (0.62, 0.61, 0.59), 0.95)
CUSH = node_mat("cushion", (0.80, 0.77, 0.71), 0.95)
BROWN = node_mat("brownpvc", (0.18, 0.09, 0.05), 0.5)
WPVC = node_mat("whitepvc", (0.9, 0.9, 0.88), 0.35)
FROST = node_mat("frost", (0.95, 0.93, 0.85), 0.3, emit=(1, 0.95, 0.85), strength=2.4)
DGL = node_mat("darkglass", (0.03, 0.03, 0.035), 0.08)
TVS = node_mat("tv", (0.01, 0.01, 0.012), 0.12)
ACW = node_mat("ac", (0.93, 0.93, 0.93), 0.4)
RUG = node_mat("rug", (0.86, 0.83, 0.77), 1.0)
LINEN = node_mat("linen", (0.88, 0.84, 0.76), 0.9)
LINENB = node_mat("linenblind", (0.92, 0.88, 0.80), 0.9, emit=(1, 0.93, 0.82), strength=0.6)
GREEN = node_mat("leaf", (0.10, 0.27, 0.09), 0.7)
POT = node_mat("pot", (0.80, 0.77, 0.71), 0.8)
BULB = node_mat("bulb", (1, 1, 1), 0.2, emit=(1, 0.8, 0.55), strength=40)

T = 0.1
# --- коробка (сырая) и отделка — одинаковая геометрия, разные слои
def shell(grp, wm, fm, cm):
    box("floor", 0, 0, -0.05, W, L, 0, fm, grp); box("ceiling", 0, 0, H, W, L, H + 0.05, cm, grp)
    box("wall_w", -T, -T, 0, 0, L + T, H, wm, grp); box("wall_e", W, -T, 0, W + T, L + T, H, wm, grp)
    box("wall_s_a", 0, -T, 0, 2.40, 0, H, wm, grp); box("wall_s_b", 3.34, -T, 0, W, 0, H, wm, grp)
    box("wall_s_top", 2.40, -T, 2.00, 3.34, 0, H, wm, grp)
    box("wall_n_a", 0, L, 0, 1.55, L + T, H, wm, grp); box("wall_n_b", 2.78, L, 0, W, L + T, H, wm, grp)
    box("wall_n_top", 1.55, L, 2.02, 2.78, L + T, H, wm, grp)
shell("raw", PLASTER, CONCRETE, CEILRAW)
shell("fin", WALLW, LAM, CEIL)

# --- постоянное: вход с улицы, дверь во 2-ю комнату, кондиционер
y0, y1 = L + 0.02, L + 0.08
box("ent_frame", 1.55, y1, 0, 2.78, y1 + 0.02, 2.02, BROWN, "fix")
box("ent_side_glass", 1.62, y0, 0.95, 1.92, y1, 1.85, FROST, "fix")
box("ent_door_glass", 2.05, y0, 0.95, 2.70, y1, 1.85, FROST, "fix")
box("ent_transom", 1.62, y0, 1.90, 2.70, y1, 1.98, FROST, "fix")
box("ent_door_low", 2.05, y0 - 0.01, 0.05, 2.70, y1, 0.90, BROWN, "fix")
box("ent_side_low", 1.62, y0 - 0.01, 0.05, 1.92, y1, 0.90, BROWN, "fix")
for (a, b) in ((1.55, 1.62), (1.92, 2.05), (2.70, 2.78)):
    box("ent_mull", a, y0 - 0.02, 0, b, y1, 2.02, BROWN, "fix")
box("ent_rail", 1.55, y0 - 0.02, 1.85, 2.78, y1, 1.95, BROWN, "fix")
box("in_frame_l", 2.40, -0.04, 0, 2.46, 0.02, 2.00, WPVC, "fix"); box("in_frame_r", 3.28, -0.04, 0, 3.34, 0.02, 2.00, WPVC, "fix")
box("in_frame_t", 2.40, -0.04, 1.94, 3.34, 0.02, 2.00, WPVC, "fix"); box("in_leaf", 2.46, -0.03, 0, 3.28, 0.0, 1.94, WPVC, "fix")
box("in_glass_a", 2.52, 0.0, 0.92, 2.85, 0.005, 1.88, DGL, "fix"); box("in_glass_b", 2.90, 0.0, 0.92, 3.22, 0.005, 1.88, DGL, "fix")
box("ac", 2.86, L - 0.21, 1.74, 3.40, L, 2.03, ACW, "acg", bevel=0.02)

# --- голая лампочка в коробке
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(1.72, 1.95, H - 0.35)); put(bpy.context.object, "bulb").data.materials.append(BULB)
bpy.ops.mesh.primitive_cylinder_add(radius=0.004, depth=0.30, location=(1.72, 1.95, H - 0.15)); put(bpy.context.object, "bulb").data.materials.append(DGL)
bpy.ops.object.light_add(type="POINT", location=(1.72, 1.95, H - 0.36)); lb = put(bpy.context.object, "bulb")
lb.data.energy = 140; lb.data.color = (1, 0.78, 0.55); lb.data.shadow_soft_size = 0.05

# --- «так не надо»: тёмная стена с рейками (западная)
box("slat_back", 0, 0, 0, 0.012, L, H, DARKBACK, "wrong")
yy = 0.02
while yy < L - 0.04:
    box("slat", 0.012, yy, 0.06, 0.034, yy + 0.04, H - 0.06, SLATD, "wrong"); yy += 0.065

# --- ТВ-стена: рейки светлого дуба (северная, x 0.10–1.48), тумба, ТВ
yy = 0.10
while yy < 1.46:
    box("tvslat", yy, L - 0.035, 0.0, yy + 0.04, L, H, OAKL, "tv"); yy += 0.062
box("tvslat_back", 0.08, L - 0.01, 0, 1.50, L, H, node_mat("slatgap", (0.16, 0.11, 0.07), 0.8), "tv")
box("console", 0.25, L - 0.42, 0.28, 1.40, L - 0.035, 0.52, OAKL, "tv", bevel=0.01)
box("tv", 0.32, L - 0.08, 0.98, 1.34, L - 0.045, 1.56, TVS, "tv", bevel=0.005)

# --- мебель: светло-серый угловой диван, подушки, ковёр, стол
def sofa_run(n, x0, y0_, x1, y1_, side):
    box(n + "_base", x0, y0_, 0.06, x1, y1_, 0.30, GREYF, "sofa", bevel=0.02)
    box(n + "_seat", x0, y0_, 0.30, x1, y1_, 0.44, GREYF, "sofa", bevel=0.045)
    if side == "w": box(n + "_back", x0, y0_, 0.30, x0 + 0.22, y1_, 0.80, GREYF, "sofa", bevel=0.06)
    else: box(n + "_back", x0, y0_, 0.30, x1, y0_ + 0.22, 0.80, GREYF, "sofa", bevel=0.06)
sofa_run("sofa_w", 0.06, 0.06, 0.96, 3.05, "w"); sofa_run("sofa_s", 0.96, 0.06, 2.20, 0.96, "s")
box("arm_n", 0.055, 2.85, 0.06, 0.965, 3.055, 0.60, GREYF, "sofa", bevel=0.05)
box("arm_e", 2.00, 0.055, 0.06, 2.205, 0.965, 0.60, GREYF, "sofa", bevel=0.05)
for cy in (0.7, 1.5, 2.3): box("cush", 0.28, cy, 0.44, 0.42, cy + 0.42, 0.82, CUSH, "sofa", bevel=0.07)
box("rug", 1.05, 1.10, 0, 2.40, 3.00, 0.012, RUG, "sofa")
box("table_top", 1.28, 1.40, 0.36, 1.86, 2.55, 0.41, OAKL, "sofa", bevel=0.012)
box("table_base", 1.36, 1.48, 0.05, 1.78, 2.47, 0.36, OAKL, "sofa")

# --- финал: кресло, растение, льняная штора опущена
box("arm_seat", 2.62, 1.55, 0.10, 3.40, 2.35, 0.44, GREYF, "full", bevel=0.045)
box("arm_back", 3.18, 1.55, 0.10, 3.40, 2.35, 0.80, GREYF, "full", bevel=0.06)
box("arm_l", 2.615, 1.545, 0.10, 3.40, 1.70, 0.60, GREYF, "full", bevel=0.05)
box("arm_r", 2.615, 2.20, 0.10, 3.405, 2.355, 0.60, GREYF, "full", bevel=0.05)
bpy.ops.mesh.primitive_cylinder_add(radius=0.16, depth=0.36, location=(3.18, 3.40, 0.18)); put(bpy.context.object, "full").data.materials.append(POT)
for (dx, dy, dz, r) in ((0, 0, 0.72, 0.27), (0.07, -0.05, 1.0, 0.21), (-0.05, 0.04, 1.22, 0.15)):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=(3.18 + dx, 3.40 + dy, dz)); put(bpy.context.object, "full").data.materials.append(GREEN)
box("blind", 1.60, L - 0.07, 0.95, 2.74, L - 0.05, 1.98, LINENB, "full")

# --- свет: потолок с точками (выкл/вкл) и LED-контур
SPOTS = ((0.9, 1.0), (0.9, 2.9), (2.5, 1.0), (2.5, 2.9), (1.7, 1.95))
for (sx, sy) in SPOTS:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.01, location=(sx, sy, H - 0.004)); put(bpy.context.object, "spotsoff").data.materials.append(SPOTOFF)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.01, location=(sx, sy, H - 0.004)); put(bpy.context.object, "spotson").data.materials.append(SPOT)
    bpy.ops.object.light_add(type="SPOT", location=(sx, sy, H - 0.02)); s = put(bpy.context.object, "spotson")
    s.data.energy = 55; s.data.spot_size = math.radians(70); s.data.spot_blend = 0.6; s.data.color = (1, 0.82, 0.62); s.data.shadow_soft_size = 0.03
for a in ((0.06, 0.05, H - 0.03, 0.07, L - 0.05, H - 0.02), (W - 0.07, 0.05, H - 0.03, W - 0.06, L - 0.05, H - 0.02),
          (0.06, 0.05, H - 0.03, W - 0.06, 0.06, H - 0.02), (0.06, L - 0.06, H - 0.03, W - 0.06, L - 0.05, H - 0.02)):
    box("cove", *a, LED, "cove")
box("cove_drop", 0.0, 0.0, H - 0.07, W, 0.05, H - 0.06, CEIL, "cove")  # бортик ниши

# --- общий дневной/рабочий свет
bpy.ops.object.light_add(type="AREA", location=(W / 2, L / 2, H - 0.02)); amb = put(bpy.context.object, "amb")
amb.data.size = 2.4; amb.data.energy = 26; amb.data.color = (1, 0.93, 0.85)
bpy.ops.object.light_add(type="AREA", location=(2.16, L + 0.6, 1.4)); day = put(bpy.context.object, "day")
day.data.size = 1.3; day.data.energy = 90; day.data.color = (1, 0.97, 0.92); day.rotation_euler = (math.radians(90), 0, math.radians(180))
world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.04

# --- камера 9:16: из юго-восточного угла на ТВ-стену и диван
bpy.ops.object.camera_add(location=(2.88, 0.10, 1.40)); cam = bpy.context.object
cam.rotation_euler = (Vector((0.95, 3.90, 0.50)) - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 12; cam.data.sensor_fit = "HORIZONTAL"; cam.data.sensor_width = 24; cam.data.clip_start = 0.05
sc.camera = cam
sc.render.engine = "CYCLES"; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True; sc.cycles.device = "CPU"
sc.render.resolution_x = RW; sc.render.resolution_y = int(RW * 16 / 9); sc.render.resolution_percentage = 100
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
sc.render.image_settings.file_format = "PNG"

# экранные координаты точек света — для варианта «щелчок света»
pts = {}
for i, (sx, sy) in enumerate(SPOTS):
    v = world_to_camera_view(sc, cam, Vector((sx, sy, H - 0.01))); pts[f"spot{i}"] = (v.x, 1 - v.y)
for nm, p in (("tv", (0.85, L - 0.05, 1.27)), ("sofa", (0.5, 1.6, 0.55)), ("plant", (3.18, 3.40, 0.9)), ("arm", (3.0, 1.95, 0.5)), ("blind", (2.17, L - 0.06, 1.45))):
    v = world_to_camera_view(sc, cam, Vector(p)); pts[nm] = (v.x, 1 - v.y)
json.dump(pts, open(f"{OUT}/points.json", "w"))

SETS = {  # какие слои видны на каждом этапе + экспозиция
 "box":   (["raw", "fix", "acg", "bulb", "day"], 0.5),
 "wrong": (["raw", "fix", "acg", "bulb", "day", "wrong"], 0.5),
 "base":  (["fin", "fix", "acg", "spotsoff", "amb", "day", "cove"], -0.5),
 "tv":    (["fin", "fix", "acg", "spotsoff", "amb", "day", "cove", "tv"], -0.5),
 "sofa":  (["fin", "fix", "acg", "spotsoff", "amb", "day", "cove", "tv", "sofa"], -0.5),
 "full":  (["fin", "fix", "acg", "spotsoff", "amb", "day", "cove", "tv", "sofa", "full"], -0.5),
 "night": (["fin", "fix", "acg", "spotson", "cove", "tv", "sofa", "full", "coveon"], -0.9),
}
# слой «ids»: каждый предмет своим плоским цветом — из него рисуем линии чертежа
IDM = bpy.data.materials.new("ids"); IDM.use_nodes = True; nt = IDM.node_tree
for n in list(nt.nodes): nt.nodes.remove(n)
oi = nt.nodes.new("ShaderNodeObjectInfo"); hs = nt.nodes.new("ShaderNodeCombineColor"); em = nt.nodes.new("ShaderNodeEmission")
mo = nt.nodes.new("ShaderNodeOutputMaterial"); hs.mode = "HSV"; hs.inputs[1].default_value = 0.9; hs.inputs[2].default_value = 0.9
nt.links.new(oi.outputs["Random"], hs.inputs[0]); nt.links.new(hs.outputs[0], em.inputs["Color"]); nt.links.new(em.outputs[0], mo.inputs["Surface"])
SETS["ids"] = (SETS["night"][0], 0.0)
for st in STAGES:
    on, ex = SETS[st]
    if st == "ids":
        sc.view_layers[0].material_override = IDM; sc.cycles.samples = 1; sc.cycles.use_denoising = False
        sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
        for c in COL.values():
            for o in c.objects:
                if o.type == "LIGHT": o.hide_render = True
    for n, c in COL.items():
        c.hide_render = n not in on
    LED.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 22 if "coveon" in on else 0.0
    sc.view_settings.exposure = ex
    sc.render.filepath = f"{OUT}/{st}.png"; bpy.ops.render.render(write_still=True); print("RENDERED", st, flush=True)
