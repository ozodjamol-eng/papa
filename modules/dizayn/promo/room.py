"""Пустая квартира-«коробка» для промо OZOD JAMOL Дизайн: бетон, окно со светом.
Рендер 9:16 + JSON с экранными координатами точек чертежа (для моушн-слоя)."""
import bpy, math, sys, json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else "/tmp/room"
RX, RY = (int(args[1]), int(args[2])) if len(args) > 2 else (540, 960)
SAMPLES = int(args[3]) if len(args) > 3 else 16
W, L, H = 3.6, 4.4, 2.75

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def concrete(name, base, scale, bump=0.25, rough=0.85):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = N["Principled BSDF"]; b.inputs["Roughness"].default_value = rough
    tc = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 12; nz.inputs["Roughness"].default_value = 0.6
    nz2 = N.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = scale * 0.08; nz2.inputs["Detail"].default_value = 3
    Lk.new(tc.outputs["Object"], nz.inputs["Vector"]); Lk.new(tc.outputs["Object"], nz2.inputs["Vector"])
    mix = N.new("ShaderNodeMix"); mix.data_type = "FLOAT"; mix.inputs[0].default_value = 0.45
    Lk.new(nz.outputs["Fac"], mix.inputs[2]); Lk.new(nz2.outputs["Fac"], mix.inputs[3])
    cr = N.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[0].color = (base[0]*0.62, base[1]*0.62, base[2]*0.61, 1)
    cr.color_ramp.elements[1].position = 0.68; cr.color_ramp.elements[1].color = (*base, 1)
    Lk.new(mix.outputs[0], cr.inputs["Fac"]); Lk.new(cr.outputs["Color"], b.inputs["Base Color"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = 0.01
    Lk.new(nz.outputs["Fac"], bp.inputs["Height"]); Lk.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def flat(name, col, rough=0.5, emit=None, strength=0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    return m

def box(x0, y0, z0, x1, y1, z1, m, name="b"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0+x1)/2, (y0+y1)/2, (z0+z1)/2))
    o = bpy.context.object; o.name = name; o.scale = (x1-x0, y1-y0, z1-z0)
    bpy.ops.object.transform_apply(scale=True); o.data.materials.append(m); return o

WALL = concrete("wall", (0.58, 0.56, 0.53), 4.0, 0.6)
FLOOR = concrete("floor", (0.40, 0.39, 0.37), 2.5, 0.3, 0.55)
CEIL = concrete("ceil", (0.66, 0.65, 0.63), 7.0, 0.15)
SKY = flat("sky", (1, 1, 1), emit=(0.85, 0.92, 1.0), strength=6)
T = 0.2
box(-T, -T, -0.1, W+T, L+T, 0, FLOOR, "floor")
box(-T, -T, H, W+T, L+T, H+0.15, CEIL, "ceil")
box(-T, -T, 0, 0, L+T, H, WALL, "wall_w")
box(W, -T, 0, W+T, L+T, H, WALL, "wall_e")
box(0, -T, 0, W, 0, H, WALL, "wall_s")
# северная стена с окном 1.4 × 1.5 (x 1.1–2.5, z 0.85–2.35)
wx0, wx1, wz0, wz1 = 1.1, 2.5, 0.85, 2.35
box(0, L, 0, wx0, L+T, H, WALL, "wn_a"); box(wx1, L, 0, W, L+T, H, WALL, "wn_b")
box(wx0, L, 0, wx1, L+T, wz0, WALL, "wn_c"); box(wx0, L, wz1, wx1, L+T, H, WALL, "wn_d")

PVC = flat("pvc", (0.92, 0.92, 0.90), 0.35)
for x in (wx0, (wx0+wx1)/2 - 0.03, wx1 - 0.06):
    box(x, L + 0.06, wz0, x + 0.06, L + 0.12, wz1, PVC)
box(wx0, L + 0.06, wz0, wx1, L + 0.12, wz0 + 0.06, PVC); box(wx0, L + 0.06, wz1 - 0.06, wx1, L + 0.12, wz1, PVC)
box(wx0 - 0.05, L - 0.08, wz0 - 0.03, wx1 + 0.05, L + 0.06, wz0, flat("sill", (0.55, 0.54, 0.52), 0.8))
RAD = flat("rad", (0.88, 0.88, 0.86), 0.4)
for i in range(10):
    box(1.25 + i * 0.11, L - 0.12, 0.18, 1.25 + i * 0.11 + 0.08, L - 0.03, 0.72, RAD)
BOXM = flat("rough", (0.75, 0.38, 0.12), 0.6)
def rbox(x, y, z, wall):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.012, location=(x, y, z),
        rotation=((0, math.pi/2, 0) if wall in "we" else (math.pi/2, 0, 0)))
    bpy.context.object.data.materials.append(BOXM)
rbox(0.006, 2.2, 0.3, "w"); rbox(0.006, 3.3, 1.1, "w"); rbox(W - 0.006, 2.1, 1.1, "e"); rbox(W - 0.006, 0.9, 0.9, "e")

# небо за окном
bpy.ops.mesh.primitive_plane_add(size=1, location=((wx0+wx1)/2, L+1.2, 1.6), rotation=(math.pi/2, 0, 0))
p = bpy.context.object; p.scale = (6, 4, 1); p.data.materials.append(SKY); p.visible_shadow = False
# проём двери на восточной стене (y 0.4–1.3) — тёмный коридор
bpy.ops.object.select_all(action="DESELECT")
# солнце через окно
bpy.ops.object.light_add(type="SUN", location=(0, 0, 0))
bpy.context.object.rotation_euler = Vector((-0.35, -0.75, -0.55)).to_track_quat("-Z", "Y").to_euler()
s = bpy.context.object.data; s.energy = 5.5; s.angle = math.radians(2.5); s.color = (1.0, 0.93, 0.82)
bpy.ops.object.light_add(type="AREA", location=((wx0+wx1)/2, L-0.05, 1.6), rotation=(math.radians(90), 0, 0))
a = bpy.context.object.data; a.size = 1.4; a.size_y = 1.5; a.shape = "RECTANGLE"; a.energy = 70; a.color = (0.9, 0.95, 1.0)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.75, 0.82, 0.95, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35

# камера: из ближнего угла на окно и левую стену
bpy.ops.object.camera_add(location=(W - 0.35, 0.35, 1.5))
cam = bpy.context.object
tgt = Vector((1.25, L, 1.05))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 15
sc.camera = cam
sc.render.engine = "CYCLES"; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = RX, RY
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
sc.view_settings.exposure = -0.35
sc.render.filepath = OUT + ".png"

# точки чертежа (мировые координаты) → экран
def scr(x, y, z):
    v = world_to_camera_view(sc, cam, Vector((x, y, z)))
    return [round(v.x, 5), round(1 - v.y, 5), round(v.z, 3)]
pts = {}
inset = 0.0
pts["floor"] = [scr(0, 0, 0), scr(W, 0, 0), scr(W, L, 0), scr(0, L, 0)]
pts["ceil"] = [scr(0, 0, H), scr(W, 0, H), scr(W, L, H), scr(0, L, H)]
pts["corners"] = [[scr(x, y, 0), scr(x, y, H)] for x, y in ((0, L), (W, L), (0, 0))]
pts["window"] = [scr(wx0, L, wz0), scr(wx1, L, wz0), scr(wx1, L, wz1), scr(wx0, L, wz1)]
# мебель на плане (следы на полу): угловой диван у западной стены, ковёр, тумба ТВ у восточной
def rectp(x0, y0, x1, y1, z=0.0): return [scr(x0, y0, z), scr(x1, y0, z), scr(x1, y1, z), scr(x0, y1, z)]
pts["sofa"] = [rectp(0.05, 1.0, 0.95, 3.9), rectp(0.95, 3.0, 2.0, 3.9)]
pts["table"] = rectp(1.35, 1.7, 1.95, 2.8)
pts["tv"] = rectp(W - 0.42, 1.2, W - 0.02, 3.0)
# размерные линии на полу (вдоль западной и северной стен, с отступом)
pts["dim_w"] = [scr(0.25, 0.3, 0.005), scr(0.25, L - 0.15, 0.005)]
pts["dim_n"] = [scr(0.15, L - 0.25, 0.005), scr(W - 0.15, L - 0.25, 0.005)]
pts["dim_w_mid"] = scr(0.25, L / 2, 0.005); pts["dim_n_mid"] = scr(W / 2, L - 0.25, 0.005)
# розетки и высоты
pts["sock"] = [{"p": scr(0, 2.2, 0.3), "t": "H=30"}, {"p": scr(0, 3.3, 1.1), "t": "H=110"},
               {"p": scr(W, 2.1, 1.1), "t": "H=110"}, {"p": scr(W, 0.9, 0.9), "t": "H=90"}]
pts["hdim"] = [scr(0.0, 4.25, 0.0), scr(0.0, 4.25, H)]
json.dump({"W": W, "L": L, "H": H, "pts": pts}, open(OUT + ".json", "w"))
bpy.ops.render.render(write_still=True)
print("DONE", OUT)
