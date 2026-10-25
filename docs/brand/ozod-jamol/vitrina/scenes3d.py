import bpy,bmesh,math,sys
from mathutils import Vector
A=dict(a.split('=') for a in sys.argv[sys.argv.index('--')+1:])
S=A['s'];RW,RH=map(int,A.get('res','540x960').split('x'));SPP=int(A.get('spp','16'));OUT=A['out']
f0,f1=map(int,A.get('frames','0-149').split('-'));STEP=int(A.get('step','1'))
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;sc.render.fps=30
def mat(name,base,metal,rough,coat=0,emit=None,es=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value=(*base,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;p.inputs['Coat Weight'].default_value=coat
    if emit: p.inputs['Emission Color'].default_value=(*emit,1);p.inputs['Emission Strength'].default_value=es
    return m
def emat(name,col,st):
    m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();e=nt.nodes.new('ShaderNodeEmission');e.inputs[0].default_value=(*col,1);e.inputs[1].default_value=st
    o=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(e.outputs[0],o.inputs[0]);return m
def light(name,loc,rot,size,energy,col=(1,1,1),shape='RECTANGLE',sx=None):
    l=bpy.data.lights.new(name,'AREA');l.energy=energy;l.color=col;l.shape=shape;l.size=size;l.size_y=sx or size
    o=bpy.data.objects.new(name,l);sc.collection.objects.link(o);o.location=loc;o.rotation_euler=rot;return o
def card(name,loc,rot,sx,sy,col,st):
    bpy.ops.mesh.primitive_plane_add(size=1,location=loc,rotation=rot);p=bpy.context.active_object;p.scale=(sx,sy,1);p.data.materials.append(emat(name,col,st));p.visible_camera=False
    if name.startswith('back'): p.visible_glossy=False
    return p
def key(o,f,**kw):
    for k,v in kw.items(): setattr(o,k,v);o.keyframe_insert(k,frame=f)
def ease(o,e='EASE_IN_OUT'):
    for fc in o.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation='BEZIER';kp.easing=e
w=bpy.data.worlds.new('w');sc.world=w;w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(0.001,0.001,0.0012,1)
# glossy black floor
fm=mat('floor',(0.004,0.004,0.005),0.0,0.18,coat=1.0)
bpy.ops.mesh.primitive_plane_add(size=80,location=(0,0,0));fl=bpy.context.active_object;fl.data.materials.append(fm)
cam=bpy.data.cameras.new('c');cam.lens=70;cam.sensor_fit='VERTICAL';cam.sensor_height=36;co=bpy.data.objects.new('cam',cam);sc.collection.objects.link(co);sc.camera=co
tgt=bpy.data.objects.new('t',None);sc.collection.objects.link(tgt);c=co.constraints.new('DAMPED_TRACK');c.target=tgt;c.track_axis='TRACK_NEGATIVE_Z'
if S=='3':
    def glass(name,col,rough=0.0):
        m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*col,1)
        p.inputs['Transmission Weight'].default_value=1.0;p.inputs['Roughness'].default_value=rough;p.inputs['IOR'].default_value=1.5;return m
    def rbox(loc,size,bev,segs,m):
        bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.active_object;o.scale=size;bpy.ops.object.transform_apply(scale=True)
        b=o.modifiers.new('b','BEVEL');b.width=bev;b.segments=segs;o.data.materials.append(m);bpy.ops.object.shade_smooth();return o
    b=rbox((0,0,1.6),(3.0,1.5,3.2),0.35,10,glass('glass',(0.97,0.97,0.98)))
    lq=rbox((0,0,1.45),(2.45,0.98,2.55),0.22,8,glass('liquid',(0.95,0.02,0.04)))
    pl=rbox((0,-0.77,1.5),(1.7,0.04,0.5),0.02,3,mat('chrome',(0.95,0.95,0.95),1.0,0.05))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.3,depth=0.3,location=(0,0,3.35),vertices=64);nk=bpy.context.active_object;nk.data.materials.append(mat('chrome2',(0.95,0.95,0.95),1.0,0.06));bpy.ops.object.shade_smooth()
    cp=rbox((0,0,3.95),(1.1,1.1,0.9),0.14,8,mat('blackchrome',(0.04,0.04,0.045),1.0,0.15))
    root=bpy.data.objects.new('root',None);sc.collection.objects.link(root)
    for o in (b,lq,pl,nk,cp): o.parent=root
    key(root,0,rotation_euler=(0,0,math.radians(-70)));key(root,149,rotation_euler=(0,0,math.radians(50)));
    for fc in root.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation='LINEAR'
    key(root,0,location=(0,0,7));key(root,14,location=(0,0,0));
    for fc in root.animation_data.action.fcurves:
        if fc.data_path=='location':
            for kp in fc.keyframe_points: kp.interpolation='BOUNCE';kp.easing='EASE_OUT'
    key(co,0,location=(0,-17,4.2));key(co,149,location=(0,-14.5,3.4));ease(co,'EASE_OUT')
    key(tgt,0,location=(0,0,2.3));key(tgt,149,location=(0,0,2.2))
    light('key',(-4,-4,6),(math.radians(50),0,math.radians(-40)),3,900,sx=8)
    light('rimR',(5,2,3),(0,math.radians(75),0),0.4,1100,(1,0.15,0.15),sx=8)
    light('rimL',(-5,2,3),(0,math.radians(-75),0),0.4,800,(1,1,1),sx=8)
    light('top',(0,0,9),(0,0,0),4,600)
    card('strip',(2.5,-8,3),(math.radians(90),0,0),0.6,8,(1,1,1),6)
    card('strip2',(-3,-8,3),(math.radians(90),0,0),0.3,8,(1,1,1),4)
    card('back',(0,7,2.2),(math.radians(90),0,0),5,6,(1,0.85,0.85),2.2)
    card('backR',(0,6,1.2),(math.radians(90),0,0),2.2,1.2,(1,0.05,0.08),6)
elif S=='6':
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,0));ph=bpy.context.active_object;ph.scale=(1.9,0.22,4.0);bpy.ops.object.transform_apply(scale=True)
    m=ph.modifiers.new('b','BEVEL');m.width=0.32;m.segments=14;ph.data.materials.append(mat('ti',(0.08,0.08,0.09),1.0,0.22));bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_plane_add(size=1,location=(0,-0.115,0),rotation=(math.radians(90),0,0));scr=bpy.context.active_object;scr.scale=(1.78,3.88,1)
    sm=bpy.data.materials.new('scr');sm.use_nodes=True;nt=sm.node_tree;nt.nodes.clear();tx=nt.nodes.new('ShaderNodeTexImage')
    img=bpy.data.images.load('/home/claude/reel/scr2/s0001.jpg');img.source='SEQUENCE';tx.image=img;tx.image_user.frame_duration=130;tx.image_user.frame_start=0;tx.image_user.use_auto_refresh=True
    em=nt.nodes.new('ShaderNodeEmission');em.inputs[1].default_value=1.0;gl=nt.nodes.new('ShaderNodeBsdfGlossy');gl.inputs['Roughness'].default_value=0.02
    mx=nt.nodes.new('ShaderNodeMixShader');mx.inputs[0].default_value=0.08;out=nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(tx.outputs[0],em.inputs[0]);nt.links.new(em.outputs[0],mx.inputs[1]);nt.links.new(gl.outputs[0],mx.inputs[2]);nt.links.new(mx.outputs[0],out.inputs[0]);scr.data.materials.append(sm)
    # rounded screen mask via uv bevel is skipped; bezel covers corners
    root=bpy.data.objects.new('root',None);sc.collection.objects.link(root);ph.parent=root;scr.parent=root;root.location=(0,0,4.6)
    key(root,0,rotation_euler=(math.radians(25),math.radians(-30),math.radians(55)),location=Vector((3,6,9)));key(root,40,rotation_euler=(math.radians(4),math.radians(-4),math.radians(-8)),location=Vector((0,0,4.6)));key(root,119,rotation_euler=(0,0,math.radians(6)),location=Vector((0,0,4.6)))
    ease(root,'EASE_OUT')
    key(co,0,location=(0,-12,4.9));key(co,119,location=(0,-10.5,4.7));ease(co,'EASE_OUT');key(tgt,0,location=(0,0,4.6))
    light('key',(-5,-6,8),(math.radians(50),0,math.radians(-40)),3,700,sx=8)
    light('rimR',(6,3,5),(0,math.radians(75),0),0.4,1400,(1,0.1,0.12),sx=10)
    light('rimL',(-6,3,5),(0,math.radians(-75),0),0.4,900,(1,1,1),sx=10)
    card('strip',(3,-10,6),(math.radians(90),0,math.radians(15)),0.5,12,(1,1,1),5)
sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=SPP;sc.cycles.use_denoising=True;sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=0.04;sc.cycles.max_bounces=8;sc.cycles.transmission_bounces=6;sc.cycles.caustics_reflective=False;sc.cycles.caustics_refractive=False
sc.render.resolution_x=RW;sc.render.resolution_y=RH;sc.view_settings.view_transform='Standard';sc.view_settings.exposure=-0.4
sc.render.image_settings.file_format='PNG'
for f in range(f0,f1+1,STEP):
    sc.frame_set(f);sc.render.filepath=f'{OUT}/f{f:03d}.png';bpy.ops.render.render(write_still=True)
