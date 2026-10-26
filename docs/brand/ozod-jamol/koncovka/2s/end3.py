import bpy, bmesh, math, sys, json, re, random
from mathutils import Vector, Euler
A=dict(a.split('=') for a in sys.argv[sys.argv.index('--')+1:])
V='e';COL=A.get('col','white');RW,RH=map(int,A.get('res','720x1280').split('x'));SPP=int(A.get('spp','16'));OUT=A['out'];FR=A.get('frames','0-101')
f0,f1=map(int,FR.split('-'))
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene
sc.render.fps=30;sc.frame_start=0;sc.frame_end=59
from shapely.geometry import Polygon, Point, MultiPoint
from shapely.ops import triangulate
E=json.load(open('/home/claude/build/emblem.json'))
S=10/968.0;CX=(57+1025)/2;CY=(24+718)/2
def polys(d):
    return [Polygon([tuple(map(float,p.split(','))) for p in re.findall(r'[-\d.]+,[-\d.]+',sub)]) for sub in re.findall(r'M([^Z]+)Z',d)]
def lin(c): return tuple((x/255)**2.2 for x in c)
def mat(name,base,metal,rough,coat=0,emit=None,es=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value=(*base,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;p.inputs['Coat Weight'].default_value=coat
    if emit: p.inputs['Emission Color'].default_value=(*emit,1);p.inputs['Emission Strength'].default_value=es
    return m
WHITE=mat('white',(0.012,0.012,0.014),0.0,0.18,coat=1.0) if COL=='white' else mat('white',(0.85,0.86,0.86),0.35,0.22,coat=0.6)
WHITE_R=mat('whiteR',(0.08,0.08,0.09),1,0.12) if COL=='white' else mat('whiteR',(0.95,0.95,0.95),1,0.07)
RED=mat('red',(0.9,0.004,0.016),0.6,0.26,coat=0.25)
RED_R=mat('redR',(0.9,0.05,0.06),0.7,0.12)
if COL=='red':
    RED=mat('blk',(0.012,0.012,0.014),0.0,0.15,coat=1.0);RED_R=mat('blkR',(0.08,0.08,0.09),1,0.1)
def emitmat(name,col,st):
    m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();e=nt.nodes.new('ShaderNodeEmission');e.inputs[0].default_value=(*col,1);e.inputs[1].default_value=st
    o=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(e.outputs[0],o.inputs[0]);return m
def extrude_poly(name,pg,ext,bev,fm,rm,center=None):
    coords=list(pg.exterior.coords)[:-1]
    if center is None: center=(0,0)
    bm=bmesh.new();vs=[bm.verts.new(((x-CX)*S-center[0],-(y-CY)*S-center[1],0)) for x,y in coords]
    f=bm.faces.new(vs);bmesh.ops.recalc_face_normals(bm,faces=[f])
    if f.normal.z<0: f.normal_flip()
    r=bmesh.ops.extrude_face_region(bm,geom=[f]);nv=[e for e in r['geom'] if isinstance(e,bmesh.types.BMVert)]
    bmesh.ops.translate(bm,verts=nv,vec=(0,0,ext));bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);sc.collection.objects.link(o)
    if bev>0:
        b=o.modifiers.new('bev','BEVEL');b.width=bev;b.segments=4;b.limit_method='ANGLE';b.angle_limit=math.radians(35);b.harden_normals=True
    o.data.materials.append(fm);o.data.materials.append(rm)
    return o
def assign_rim(o):
    bpy.context.view_layer.objects.active=o
    for m in list(o.modifiers): 
        o.select_set(True);bpy.ops.object.modifier_apply(modifier=m.name)
    for p in o.data.polygons: p.material_index=0 if p.normal.z>0.985 else 1;p.use_smooth=True
    o.modifiers.new('wn','WEIGHTED_NORMAL')
EXT=0.55
parts={}
for name in ('O','band','J'):
    pg=polys(E[name])[0].simplify(0.6)
    green=name!='O'
    o=extrude_poly(name,pg,EXT,0.09,RED if green else WHITE,RED_R if green else WHITE_R)
    assign_rim(o);parts[name]=o
# centre each part origin on its own centroid so rotations look natural
for o in parts.values():
    bpy.context.view_layer.objects.active=o;bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY',center='BOUNDS')
FINAL={k:(o.location.copy(),Euler((0,0,0))) for k,o in parts.items()}

w=bpy.data.worlds.new('w');sc.world=w;w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1);w.node_tree.nodes['Background'].inputs[1].default_value=0.6 if COL=='white' else 0.25
# белая стена за логотипом
wm=mat('wall',(0.92,0.915,0.905),0.0,0.6)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-2.2));wall=bpy.context.active_object;wall.data.materials.append(wm);wall.is_shadow_catcher=True
root=bpy.data.objects.new('root',None);sc.collection.objects.link(root)
cen=sum((o.location for o in parts.values()),Vector())/3;cen.z=EXT/2;root.location=cen
for o in parts.values():
    L=o.location.copy();o.parent=root;o.location=L-cen
def key(o,f,**kw):
    for k,v in kw.items(): setattr(o,k,v);o.keyframe_insert(k,frame=f)
def ease(o,e):
    for fc in o.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation='BEZIER';kp.easing=e
O,B,J=parts['O'],parts['band'],parts['J']
for o,dx in ((O,-9),(J,9),(B,9)):
    L=o.location.copy();key(o,0,location=L+Vector((dx,0,0)),rotation_euler=(0,math.radians(-80 if dx<0 else 80),0));key(o,12,location=L,rotation_euler=(0,0,0));ease(o,'EASE_OUT')
key(root,0,scale=(0.75,0.75,0.75),rotation_euler=(0,0,0));key(root,12,scale=(1,1,1),rotation_euler=(0,0,0))
key(root,14,rotation_euler=(0,0,0));key(root,40,rotation_euler=(0,math.radians(360),0))
key(root,40,scale=(1,1,1));key(root,49,scale=(0.0,0.0,0.0))
for fc in root.animation_data.action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation='BEZIER';kp.easing='EASE_IN_OUT'
# красная точка
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5,location=cen,segments=48,ring_count=24);dot=bpy.context.active_object;bpy.ops.object.shade_smooth();dot.data.materials.append(RED)
key(dot,0,scale=(0,0,0));key(dot,42,scale=(0,0,0));key(dot,48,scale=(0.9,0.9,0.9));key(dot,53,scale=(0.9,0.9,0.9));key(dot,58,scale=(0,0,0));ease(dot,'EASE_IN_OUT')
cam=bpy.data.cameras.new('c');cam.lens=50;cam.sensor_fit='VERTICAL' if RH>RW else 'HORIZONTAL';cam.sensor_height=36;cam.sensor_width=36
co=bpy.data.objects.new('cam',cam);sc.collection.objects.link(co);sc.camera=co;co.location=(cen.x,cen.y,(31 if RH>RW else 26));co.rotation_euler=(0,0,0)
def light(name,loc,rot,size,energy,col=(1,1,1),sy=None):
    l=bpy.data.lights.new(name,'AREA');l.energy=energy;l.color=col;l.shape='RECTANGLE';l.size=size;l.size_y=sy or size
    o=bpy.data.objects.new(name,l);sc.collection.objects.link(o);o.location=loc;o.rotation_euler=rot;return o
light('key',(cen.x-8,cen.y+10,14),(math.radians(-35),math.radians(-25),0),6,2500)
light('fill',(cen.x+10,cen.y-4,10),(math.radians(15),math.radians(40),0),8,800)
def card(name,loc,sx,sy,st,rz=0):
    bpy.ops.mesh.primitive_plane_add(size=1,location=loc,rotation=(math.radians(180),0,rz));p=bpy.context.active_object;p.scale=(sx,sy,1);p.data.materials.append(emitmat(name,(1,1,1),st));p.visible_camera=False;return p
card('c1',(cen.x,cen.y+6,22),40,5,3);card('c2',(cen.x+5,cen.y,21),2,60,6,math.radians(45));card('c3',(cen.x-7,cen.y-6,20),30,3,2)
sc.render.engine='CYCLES';sc.cycles.samples=SPP;sc.cycles.use_denoising=True;sc.cycles.device='CPU';sc.cycles.max_bounces=6
sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=0.03
sc.render.resolution_x=RW;sc.render.resolution_y=RH;sc.view_settings.view_transform='Standard';sc.view_settings.exposure=0.0
sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.render.film_transparent=True
for f in range(f0,f1+1,int(A.get('step','1'))):
    sc.frame_set(f);sc.render.filepath=f'{OUT}/f{f:03d}.png';bpy.ops.render.render(write_still=True)
