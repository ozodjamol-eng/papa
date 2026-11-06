"""Безликий «манекен художника» в позе, рендер линиями (Freestyle) — как эскиз тушью.
python3 mannequin.py -- <pose> <out.png>"""
import bpy, math, sys
from mathutils import Vector
a = sys.argv[sys.argv.index('--')+1:]; pose, out = a[0], a[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
white = bpy.data.materials.new('w'); white.use_nodes = True
nt = white.node_tree; [nt.nodes.remove(n) for n in list(nt.nodes)]
e = nt.nodes.new('ShaderNodeEmission'); e.inputs[0].default_value = (1, 1, 1, 1); e.inputs[1].default_value = 1
o = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(e.outputs[0], o.inputs[0])

def V(*p): return Vector(p)
def limb(p, q, r1, r2=None):
    r2 = r2 or r1; d = q-p; L = d.length
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=r1, radius2=r2, depth=L, location=(p+q)/2)
    ob = bpy.context.object; ob.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    ob.data.materials.append(white)
    for c, r in ((p, r1), (q, r2)):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=r, location=c); bpy.context.object.data.materials.append(white)
    bpy.ops.object.shade_smooth()
def blob(c, sx, sy, sz, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1, location=c)
    ob = bpy.context.object; ob.scale = (sx, sy, sz); ob.rotation_euler = rot; ob.data.materials.append(white)
    bpy.ops.object.shade_smooth()

if pose == 'sit':   # сидит на земле, обхватил колени, голова опущена
    hip = V(0, 0, .14); ch = V(.13, 0, .62)
    blob((hip+ch)/2, .145, .14, .28, (0, math.radians(22), 0))          # торс
    blob(V(.36, 0, .60), .105, .095, .125, (0, math.radians(55), 0))    # голова на коленях
    limb(V(.24, 0, .64), V(.33, 0, .62), .05)                           # шея
    for s in (-1, 1):
        y = .1*s
        limb(V(.02, y, .14), V(.40, y*.9, .46), .085, .07)               # бедро
        limb(V(.40, y*.9, .46), V(.50, y*.9, .06), .065, .045)           # голень
        limb(V(.50, y*.9, .05), V(.64, y*.9, .03), .04, .03)             # стопа
        limb(V(.15, .16*s, .58), V(.30, .2*s, .36), .045, .04)           # плечо
        limb(V(.30, .2*s, .36), V(.52, .02*s, .36), .04, .032)           # предплечье обнимает голени
elif pose == 'stand':  # стоит, руки в карманах, голова чуть опущена
    blob(V(0, 0, 1.25), .17, .12, .30)
    blob(V(.03, 0, 1.68), .1, .095, .125, (0, math.radians(12), 0))
    limb(V(0, 0, 1.48), V(.02, 0, 1.58), .05)
    for s in (-1, 1):
        y = .09*s
        limb(V(0, y, .95), V(0, y, .5), .08, .06); limb(V(0, y, .5), V(.01, y, .06), .06, .045); limb(V(.0, y, .04), V(.14, y, .02), .04, .03)
        limb(V(0, .2*s, 1.48), V(-.02, .22*s, 1.18), .045, .04); limb(V(-.02, .22*s, 1.18), V(.06, .15*s, .98), .04, .032)
cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'
co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
if pose == 'sit': co.location = (.32, -6, .36); cam.ortho_scale = 1.15
else: co.location = (.03, -6, .95); cam.ortho_scale = 2.1
co.rotation_euler = (math.radians(90), 0, 0)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (1, 1, 1, 1)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 4; sc.cycles.device = 'CPU'
sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'; sc.render.line_thickness = 3.4
fs = sc.view_layers[0].freestyle_settings
ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new('ink')
if ls.linestyle is None: ls.linestyle = bpy.data.linestyles.new('ink')
ls.select_by_visibility = True; ls.select_silhouette = True; ls.select_border = True; ls.select_crease = False
ls.linestyle.color = (0.05, 0.05, 0.05)
ls.linestyle.chaining = 'PLAIN'
th = ls.linestyle.thickness_modifiers.new('n', 'NOISE'); th.amplitude = 1.1; th.period = 140
tp = ls.linestyle.thickness_modifiers.new('t', 'ALONG_STROKE'); tp.blend = 'MULTIPLY'; tp.mapping = 'CURVE'
ls.linestyle.use_length_min = True; ls.linestyle.length_min = 25.0
ls.linestyle.caps = 'ROUND'
sc.render.resolution_x = 1000; sc.render.resolution_y = 1000 if pose == 'sit' else 1600
sc.view_settings.view_transform = 'Standard'
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
