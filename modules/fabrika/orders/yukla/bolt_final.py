import bpy, math, sys
from mathutils import Vector
a=sys.argv[sys.argv.index('--')+1:]
ang=float(a[0]); samples=int(a[1]); res=int(a[2]); out=a[3]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
pts=[(0.15,1.0),(-0.55,-0.1),(-0.05,-0.1),(-0.25,-1.0),(0.55,0.15),(0.05,0.15),(0.35,1.0)]
cu=bpy.data.curves.new('bolt','CURVE');cu.dimensions='2D';cu.fill_mode='BOTH'
sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
for p,(x,y) in zip(sp.points,pts): p.co=(x-0.0,y,0,1)
sp.use_cyclic_u=True
cu.extrude=0.18;cu.bevel_depth=0.075;cu.bevel_resolution=10
ob=bpy.data.objects.new('bolt',cu);sc.collection.objects.link(ob)
ob.rotation_euler=(math.radians(78),math.radians(8),math.radians(ang))
m=bpy.data.materials.new('candy');m.use_nodes=True
b=m.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value=(1.0,0.42,0.0,1);b.inputs['Roughness'].default_value=0.18
b.inputs['Coat Weight'].default_value=1.0;b.inputs['Coat Roughness'].default_value=0.02
b.inputs['Subsurface Weight'].default_value=0.15;b.inputs['Subsurface Radius'].default_value=(1.0,0.4,0.1)
ob.data.materials.append(m)
# world: deep blue, low
w=bpy.data.worlds.new('w');sc.world=w;w.use_nodes=True
bg=w.node_tree.nodes['Background'];bg.inputs[0].default_value=(0.02,0.05,0.14,1);bg.inputs[1].default_value=1.0
# softbox strips (seen in reflections, hidden from camera)
def strip(loc,rot,sx,sy,stren):
    bpy.ops.mesh.primitive_plane_add(size=1,location=loc,rotation=rot);p=bpy.context.object
    p.scale=(sx,sy,1)
    em=bpy.data.materials.new('em');em.use_nodes=True;nt=em.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    e=nt.nodes.new('ShaderNodeEmission');e.inputs[1].default_value=stren
    o=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(e.outputs[0],o.inputs[0])
    p.data.materials.append(em);p.visible_camera=False
strip((-2.2,-1.6,1.2),(math.radians(90),0,math.radians(-50)),0.5,3.5,14)
strip((2.4,-1.2,0.6),(math.radians(90),0,math.radians(55)),0.35,3.0,9)
strip((0,-1.5,3.2),(math.radians(20),0,0),3.0,0.6,6)
strip((-1.6,-5.0,1.6),(math.radians(75),0,math.radians(-15)),0.9,4.0,10)
strip((1.8,-5.2,-0.4),(math.radians(95),0,math.radians(20)),0.25,3.5,7)
l=bpy.data.lights.new('key','AREA');l.size=3;l.energy=260
lo=bpy.data.objects.new('key',l);lo.location=(-2.5,-3,3);sc.collection.objects.link(lo)
lo.rotation_euler=(Vector((0,0,0))-lo.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.cameras.new('c');cam.lens=85
co=bpy.data.objects.new('c',cam);sc.collection.objects.link(co);sc.camera=co
co.location=(0,-7.5,0.6)
co.rotation_euler=(Vector((0,0,0))-co.location).to_track_quat('-Z','Y').to_euler()
sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=samples;sc.cycles.use_denoising=True
sc.render.film_transparent=True
sc.render.resolution_x=res;sc.render.resolution_y=res
sc.render.image_settings.color_mode='RGBA'
sc.view_settings.view_transform='Standard';sc.view_settings.exposure=-0.9
sc.render.filepath=out;bpy.ops.render.render(write_still=True)
