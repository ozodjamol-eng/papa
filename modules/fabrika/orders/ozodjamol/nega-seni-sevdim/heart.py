"""Глянцевое 3D-сердце (стиль «плоский мир + глянцевый герой», как молния Yukla).
python3 heart.py -- <ang> <gap> <samples> <res> <out.png>   gap=0 — целое, >0 — трещина (половинки расходятся)"""
import bpy, math, sys
from mathutils import Vector
a = sys.argv[sys.argv.index('--')+1:]
ang, gap, samples, res, out = float(a[0]), float(a[1]), int(a[2]), int(a[3]), a[4]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def hp(t):
    x = 16*math.sin(t)**3
    y = 13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t)
    return (x/17.0, (y+6)/17.0)

N = 90
right = [hp(math.pi*i/N) for i in range(1, N)]          # от выемки к острию, x>0
left = [hp(math.pi+math.pi*i/N) for i in range(1, N)]   # от острия к выемке, x<0
top, tip = hp(0), hp(math.pi)
top = (0.0, top[1]-0.05); tip = (0.0, tip[1]+0.06)
right = [p for p in right if p[1] > tip[1]+0.02 or abs(p[0]) > 0.04]
left = [p for p in left if p[1] > tip[1]+0.02 or abs(p[0]) > 0.04]
zz = []                                                  # трещина-зигзаг от выемки к острию
K = 9
for i in range(K+1):
    f = i/K
    y = top[1]+(tip[1]-top[1])*f
    x = 0 if i in (0, K) else (0.07 if i % 2 else -0.07)
    zz.append((x, y))

mat = bpy.data.materials.new('candy'); mat.use_nodes = True
b = mat.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value = (0.78, 0.004, 0.025, 1); b.inputs['Roughness'].default_value = 0.16
b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.02
b.inputs['Subsurface Weight'].default_value = 0.2; b.inputs['Subsurface Radius'].default_value = (1.0, 0.15, 0.1)

def solid(pts, name, dx=0.0, rz=0.0):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '2D'; cu.fill_mode = 'BOTH'
    sp = cu.splines.new('POLY'); sp.points.add(len(pts)-1)
    for p, (x, y) in zip(sp.points, pts): p.co = (x, y, 0, 1)
    sp.use_cyclic_u = True
    cu.extrude = 0.24; cu.bevel_depth = 0.0
    ob = bpy.data.objects.new(name, cu); sc.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.convert(target='MESH'); ob = bpy.context.view_layer.objects.active
    rm = ob.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.012
    sm = ob.modifiers.new('sm', 'SMOOTH'); sm.factor = 1.0; sm.iterations = 45
    bpy.ops.object.shade_smooth()
    ob.select_set(False)
    ob.data.materials.append(mat)
    par = bpy.data.objects.new(name+'_p', None); sc.collection.objects.link(par)
    ob.parent = par; ob.location = (dx, 0, 0); ob.rotation_euler = (0, 0, math.radians(rz))
    return par

root = bpy.data.objects.new('root', None); sc.collection.objects.link(root)
if gap <= 0:
    whole = [top]+right+[tip]+left
    solid(whole, 'heart').parent = root
else:
    R = [top]+right+[tip]+list(reversed(zz[1:-1]))
    L = [tip]+left+[top]+zz[1:-1]
    solid(R, 'hr', gap*0.5, -gap*18).parent = root
    solid(L, 'hl', -gap*0.5, gap*18).parent = root
root.rotation_euler = (math.radians(90), 0, math.radians(ang))

w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.03, 0.03, 0.035, 1); bg.inputs[1].default_value = 1.0
def strip(loc, rot, sx, sy, stren):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot); p = bpy.context.object
    p.scale = (sx, sy, 1)
    em = bpy.data.materials.new('em'); em.use_nodes = True; nt = em.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs[1].default_value = stren
    o = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(e.outputs[0], o.inputs[0])
    p.data.materials.append(em); p.visible_camera = False
strip((-2.2, -1.6, 1.2), (math.radians(90), 0, math.radians(-50)), 0.5, 3.5, 14)
strip((2.4, -1.2, 0.6), (math.radians(90), 0, math.radians(55)), 0.35, 3.0, 9)
strip((0, -1.5, 3.2), (math.radians(20), 0, 0), 3.0, 0.6, 6)
strip((-1.6, -5.0, 1.6), (math.radians(75), 0, math.radians(-15)), 0.9, 4.0, 10)
strip((1.8, -5.2, -0.4), (math.radians(95), 0, math.radians(20)), 0.25, 3.5, 7)
l = bpy.data.lights.new('key', 'AREA'); l.size = 3; l.energy = 240
lo = bpy.data.objects.new('key', l); lo.location = (-2.5, -3, 3); sc.collection.objects.link(lo)
lo.rotation_euler = (Vector((0, 0, 0))-lo.location).to_track_quat('-Z', 'Y').to_euler()
cam = bpy.data.cameras.new('c'); cam.lens = 85
co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
co.location = (0, -7.5, 0.4)
co.rotation_euler = (Vector((0, 0, 0))-co.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
sc.render.film_transparent = True
sc.render.resolution_x = res; sc.render.resolution_y = res
sc.render.image_settings.color_mode = 'RGBA'
sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -1.0
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
