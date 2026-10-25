import bpy, bmesh, math, sys, json, re, random
from mathutils import Vector, Euler
A=dict(a.split('=') for a in sys.argv[sys.argv.index('--')+1:])
V=A['v'];RW,RH=map(int,A.get('res','720x1280').split('x'));SPP=int(A.get('spp','16'));OUT=A['out'];FR=A.get('frames','0-101')
f0,f1=map(int,FR.split('-'))
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene
sc.render.fps=30;sc.frame_start=0;sc.frame_end=101
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
WHITE=mat('white',(0.85,0.86,0.86),0.35,0.22,coat=0.6)
WHITE_R=mat('whiteR',(0.95,0.95,0.95),1,0.07)
RED=mat('red',(0.9,0.004,0.016),0.6,0.26,coat=0.25)
RED_R=mat('redR',(1.0,0.25,0.25),0.5,0.1,emit=(1.0,0.05,0.06),es=0.35)
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
# world
w=bpy.data.worlds.new('w');sc.world=w;w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(0.002,0.002,0.0025,1)
def plane(name,loc,rot,size,col,st,parent=None,cam_vis=False):
    bpy.ops.mesh.primitive_plane_add(size=1,location=loc,rotation=rot);p=bpy.context.active_object;p.name=name;p.scale=(size[0],size[1],1)
    p.data.materials.append(emitmat(name+'m',col,st));p.visible_camera=cam_vis
    if parent: p.parent=parent
    return p
cam=bpy.data.cameras.new('c');cam.lens=50;cam.sensor_fit='VERTICAL';cam.sensor_height=36
co=bpy.data.objects.new('cam',cam);sc.collection.objects.link(co);sc.camera=co
tgt=bpy.data.objects.new('tgt',None);sc.collection.objects.link(tgt)
tc=co.constraints.new('DAMPED_TRACK');tc.target=tgt;tc.track_axis='TRACK_NEGATIVE_Z'
# reflection cards parented to camera (always behind camera)
plane('cardBase',(0,0,40),(0,0,0),(90,70),(1,1,1),0.15,parent=co)
plane('cardTop',(0,8,38),(0,0,0),(90,10),(1,1,1),2.4,parent=co)
plane('cardDiag',(4,2,37),(0,0,math.radians(45)),(5,120),(1,1,1),5,parent=co)
for p in [o for o in sc.objects if o.name.startswith('card')]:
    p.rotation_euler=(math.radians(180),0,0)
plane('key',(-7,9,8),(math.radians(-50),math.radians(-30),0),(12,6),(1,1,1),5)
plane('strip',(9,1,6),(0,math.radians(55),0),(1.2,16),(1,1,1),9)
plane('fillL',(-10,-3,4),(0,math.radians(-60),0),(1.0,14),(1,0.12,0.12),4)
FINALCAM=Vector((0,-2.4,36));FINALTGT=Vector((0,-2.4,0))
def key(o,f,loc=None,rot=None,scale=None):
    if loc is not None: o.location=loc;o.keyframe_insert('location',frame=f)
    if rot is not None: o.rotation_euler=rot;o.keyframe_insert('rotation_euler',frame=f)
    if scale is not None: o.scale=scale;o.keyframe_insert('scale',frame=f)
def ease_all(ob,interp='BEZIER',easing='EASE_OUT'):
    if ob.animation_data and ob.animation_data.action:
        for fc in ob.animation_data.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation=interp;kp.easing=easing
flash=bpy.data.lights.new('flash','POINT');flash.color=(1,0.3,0.3);fo=bpy.data.objects.new('flash',flash);sc.collection.objects.link(fo);fo.location=(0,0,4)
def flash_at(f,peak=20000):
    flash.energy=0;flash.keyframe_insert('energy',frame=f-1);flash.energy=peak;flash.keyframe_insert('energy',frame=f);flash.energy=0;flash.keyframe_insert('energy',frame=f+8)
def rim_pulse(f):
    n=RED_R.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
    n.default_value=0.35;n.keyframe_insert('default_value',frame=f-1);n.default_value=6;n.keyframe_insert('default_value',frame=f);n.default_value=0.35;n.keyframe_insert('default_value',frame=f+12)
if V=='1':
    O,B,J=parts['O'],parts['band'],parts['J']
    key(O,0,loc=FINAL['O'][0]+Vector((-8,6,-70)),rot=(0,math.radians(200),math.radians(20)));key(O,40,loc=FINAL['O'][0],rot=(0,0,0))
    key(J,6,loc=FINAL['J'][0]+Vector((14,-4,-40)),rot=(0,math.radians(-110),0));key(J,46,loc=FINAL['J'][0],rot=(0,0,0))
    key(J,0,loc=FINAL['J'][0]+Vector((14,-4,-40)),rot=(0,math.radians(-110),0))
    key(B,0,loc=FINAL['band'][0]+Vector((-30,-30,10)),rot=(0,0,0));key(B,30,loc=FINAL['band'][0]+Vector((-30,-30,10)));key(B,50,loc=FINAL['band'][0])
    key(co,0,loc=Vector((10,-8,24)));key(co,62,loc=FINALCAM);key(co,101,loc=FINALCAM+Vector((0,0,-2.0)))
    key(tgt,0,loc=Vector((0,-1,0)));key(tgt,62,loc=FINALTGT);key(tgt,101,loc=FINALTGT)
    for ob in (O,J,B,co,tgt): ease_all(ob)
    flash_at(50);rim_pulse(50)
elif V=='2':
    # wall
    wm=mat('wall',(0.006,0.006,0.007),0.0,0.85);nt=wm.node_tree;p=nt.nodes['Principled BSDF'];n=nt.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=6;n.inputs['Detail'].default_value=12
    bp=nt.nodes.new('ShaderNodeBump');bp.inputs['Strength'].default_value=0.4;nt.links.new(n.outputs['Fac'],bp.inputs['Height']);nt.links.new(bp.outputs['Normal'],p.inputs['Normal'])
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0));wall=bpy.context.active_object;wall.data.materials.append(wm)
    for o in parts.values():
        L=o.location.copy();key(o,0,loc=Vector((L.x,L.y,-0.01)),scale=(1,1,0.02));key(o,22,loc=Vector((L.x,L.y,-0.01)),scale=(1,1,0.02));key(o,52,loc=L,scale=(1,1,1));ease_all(o)
    # laser seam: thin emissive bar along band diagonal growing
    las=emitmat('laser',(1,0.05,0.06),30)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,0.02));lz=bpy.context.active_object;lz.data.materials.append(las);lz.rotation_euler=(0,0,math.radians(45))
    key(lz,0,scale=(0.01,0.06,0.02));key(lz,12,scale=(26,0.06,0.02));key(lz,24,scale=(26,0.02,0.02));key(lz,34,scale=(0.01,0.0,0.0))
    lz.location=(parts['band'].location.x,parts['band'].location.y,0.02)
    rake=bpy.data.lights.new('rake','AREA');rake.energy=2500;rake.size=6;rake.color=(1,0.9,0.9);ro=bpy.data.objects.new('rake',rake);sc.collection.objects.link(ro)
    ro.location=(-16,4,3);ro.rotation_euler=(0,math.radians(-80),0);ro.visible_camera=False
    redk=bpy.data.lights.new('redk','AREA');redk.energy=1500;redk.size=8;redk.color=(1,0.1,0.1);rk=bpy.data.objects.new('redk',redk);sc.collection.objects.link(rk);rk.location=(16,-4,3);rk.rotation_euler=(0,math.radians(80),0)
    key(co,0,loc=Vector((16,-10,20)));key(co,30,loc=Vector((12,-8,26)));key(co,70,loc=FINALCAM);key(co,101,loc=FINALCAM+Vector((0,0,-1.5)))
    key(tgt,0,loc=FINALTGT);key(tgt,101,loc=FINALTGT)
    for ob in (co,): ease_all(ob,easing='EASE_IN_OUT')
    flash_at(52,12000);rim_pulse(52)
elif V=='3':
    random.seed(5)
    shards=[]
    for name in ('O','band','J'):
        pg=polys(E[name])[0].simplify(1.0)
        minx,miny,maxx,maxy=pg.bounds;pts=list(pg.exterior.coords)[::3]
        for i in range(int(pg.area/1500)):
            p=Point(random.uniform(minx,maxx),random.uniform(miny,maxy))
            if pg.contains(p): pts.append((p.x,p.y))
        for tri in triangulate(MultiPoint(pts)):
            if not pg.contains(tri.centroid): continue
            t=tri.intersection(pg)
            if t.is_empty or t.geom_type!='Polygon' or t.area<20: continue
            c=t.centroid;cc=((c.x-CX)*S,-(c.y-CY)*S)
            green=name!='O'
            o=extrude_poly(f's_{name}',t,EXT,0,RED if green else WHITE,RED_R if green else WHITE_R,center=cc)
            for pp in o.data.polygons: pp.material_index=0 if pp.normal.z>0.985 else 1
            o.location=(cc[0],cc[1],0);shards.append(o)
    for o in parts.values():
        o.hide_render=True;o.keyframe_insert('hide_render',frame=0);o.keyframe_insert('hide_render',frame=55);o.hide_render=False;o.keyframe_insert('hide_render',frame=56)
    for o in shards:
        L=o.location.copy();d=Vector((random.uniform(-1,1),random.uniform(-1,1),random.uniform(-0.2,1))).normalized()*random.uniform(25,60)
        st=random.randint(0,18);en=st+random.randint(26,36);en=min(en,54)
        key(o,0,loc=L+d,rot=(random.uniform(-6,6),random.uniform(-6,6),random.uniform(-6,6)));key(o,st,loc=L+d,rot=o.rotation_euler.copy());key(o,en,loc=L,rot=(0,0,0))
        ease_all(o)
        o.hide_render=False;o.keyframe_insert('hide_render',frame=55);o.hide_render=True;o.keyframe_insert('hide_render',frame=56)
    key(co,0,loc=Vector((-6,-10,30)));key(co,60,loc=FINALCAM);key(co,101,loc=FINALCAM+Vector((0,0,-2)))
    key(tgt,0,loc=FINALTGT);key(tgt,101,loc=FINALTGT);ease_all(co)
    flash_at(56,22000);rim_pulse(56)
for ob in sc.objects:
    if ob.animation_data and ob.animation_data.action:
        for fc in ob.animation_data.action.fcurves:
            if fc.data_path=='hide_render':
                for kp in fc.keyframe_points: kp.interpolation='CONSTANT'
sc.render.engine='CYCLES';sc.cycles.samples=SPP;sc.cycles.use_denoising=True;sc.cycles.device='CPU';sc.cycles.max_bounces=4
sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=0.05
sc.render.resolution_x=RW;sc.render.resolution_y=RH;sc.render.film_transparent=(V!='2')
sc.view_settings.view_transform='Standard';sc.view_settings.exposure=-0.65
sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA'
for f in range(f0,f1+1,int(A.get('step','1'))):
    sc.frame_set(f);sc.render.filepath=f'{OUT}/f{f:03d}.png';bpy.ops.render.render(write_still=True)
print('DONE')
