import bpy, math, sys
from mathutils import Vector
color=tuple(float(x) for x in sys.argv[sys.argv.index('--')+1].split(','))
out=sys.argv[sys.argv.index('--')+2]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
# bolt outline
pts=[(0.15,1.0),(-0.55,-0.1),(-0.05,-0.1),(-0.25,-1.0),(0.55,0.15),(0.05,0.15),(0.35,1.0)]
cu=bpy.data.curves.new('bolt','CURVE');cu.dimensions='2D';cu.fill_mode='BOTH'
sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
for p,(x,y) in zip(sp.points,pts): p.co=(x,y,0,1)
sp.use_cyclic_u=True
cu.extrude=0.16;cu.bevel_depth=0.09;cu.bevel_resolution=8
ob=bpy.data.objects.new('bolt',cu);sc.collection.objects.link(ob)
ob.rotation_euler=(math.radians(78),math.radians(-18),math.radians(22));ob.location=(0,0,1.25)
m=bpy.data.materials.new('lacquer');m.use_nodes=True
b=m.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=0.12
b.inputs['Coat Weight'].default_value=1.0;b.inputs['Coat Roughness'].default_value=0.03
ob.data.materials.append(m)
# floor + backdrop (cream)
bpy.ops.mesh.primitive_plane_add(size=40);fl=bpy.context.object
fm=bpy.data.materials.new('cream');fm.use_nodes=True
fb=fm.node_tree.nodes['Principled BSDF'];fb.inputs['Base Color'].default_value=(0.93,0.90,0.85,1);fb.inputs['Roughness'].default_value=0.6
fl.data.materials.append(fm)
w=bpy.data.worlds.new('w');sc.world=w;w.use_nodes=True
w.node_tree.nodes['Background'].inputs[0].default_value=(0.93,0.90,0.85,1);w.node_tree.nodes['Background'].inputs[1].default_value=0.25
def area(loc,size,en,rot):
    l=bpy.data.lights.new('a','AREA');l.size=size;l.energy=en
    o=bpy.data.objects.new('a',l);o.location=loc;o.rotation_euler=rot;sc.collection.objects.link(o)
area((-3,-2,5),3,380,(math.radians(35),0,math.radians(-55)))   # key
area((3.5,-1,2.5),1.2,260,(math.radians(70),0,math.radians(60)))   # rim
area((0,3,4),3,120,(math.radians(-40),0,0))                    # back
cam=bpy.data.cameras.new('c');cam.lens=70
co=bpy.data.objects.new('c',cam);sc.collection.objects.link(co);sc.camera=co
co.location=(0,-6.2,4.6)
d=Vector((0,0,1.0))-co.location;co.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=96;sc.cycles.use_denoising=True
sc.render.resolution_x=1080;sc.render.resolution_y=1080
sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Punchy';sc.view_settings.exposure=-0.3
sc.render.filepath=out;bpy.ops.render.render(write_still=True)
