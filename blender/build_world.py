"""Build the Chapter 4 reference map and its explorable 3D reconstruction.
Run inside Blender: exec(compile(open(path, encoding='utf-8').read(), path, 'exec'))
"""
import bpy, math, random, json, os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
random.seed(104)
scene = bpy.data.scenes.get('El oro de los tigres - 3D World')
if scene is None: raise RuntimeError('Open the existing tigers-world.blend first')
bpy.context.window.scene = scene
for ob in list(scene.objects):
    if len(ob.users_scene)>1: scene.collection.objects.unlink(ob)
    else: bpy.data.objects.remove(ob,do_unlink=True)
scene['restoration_scope']='Reference-guided visible fronts; adapted hidden surfaces'

def mat(name, color, roughness=0.85):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=roughness
    return m

stone=mat('Foundation limestone / reference sampled palette',(0.58,0.63,0.57))
roof=mat('Weathered terrace',(0.28,0.34,0.27))
trim=mat('Pale masonry coping',(.63,.69,.61))
joint=mat('Recessed masonry joint',(.24,.31,.27))
brass=mat('Muted brass',(.39,.33,.17),.5)
wood=mat('Wood',(0.20,0.14,0.085))
trunk=mat('Fir bark',(0.14,0.16,0.12))
greens=[mat('Fir canopy '+str(i),c) for i,c in enumerate([(.18,.22,.10),(.22,.25,.12),(.12,.19,.11),(.27,.24,.13)])]
earth=mat('Forest floor',(0.12,0.19,0.11))
snow=mat('Snow ridge',(0.69,0.77,0.79))
rock=mat('Slate',(0.14,0.19,0.21))
black=mat('Checkered floor black',(0.13,0.17,0.18))
ivory=mat('Checkered floor ivory',(0.76,0.79,0.70))
grass=mat('Lawn',(0.30,0.37,0.23))
water=mat('Water',(0.12,0.24,0.23),0.25)
glass=mat('Window green',(0.12,0.23,0.19),0.35)
lightmat=mat('Foundation interior light',(0.68,0.82,0.61))
p=next(n for n in lightmat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
p.inputs['Emission Color'].default_value=(0.4,0.55,0.32,1);p.inputs['Emission Strength'].default_value=0.35

# Original atlas patch applied to reconstructed limestone walls, without recolouring.
atlas=bpy.data.images.load(os.path.join(ROOT,'public/assets/all/m_s08_hddtc_background_a03_manual__48c359e04b.webp'))
texture=stone.node_tree.nodes.new('ShaderNodeTexImage');texture.image=atlas
stone.node_tree.links.new(texture.outputs['Color'],next(n for n in stone.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'])

colliders=[]
walk_surfaces=[]
def cube(name,loc,size,material,solid=False):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material)
    if material==stone:
        uv=o.data.uv_layers.active
        if uv:
            for face in o.data.polygons:
                coords=[(.700,.870),(.727,.870),(.727,.910),(.700,.910)]
                for k,li in enumerate(face.loop_indices):uv.data[li].uv=coords[k%4]
    if solid:colliders.append({'x':loc[0],'z':-loc[1],'w':size[0],'d':size[1],'height':size[2],'yMin':loc[2]-size[2]/2})
    return o

def height(x,y):
    ridge=max(0,(y-42)/36)
    return ridge*(10+7*math.sin(x*.035)**2)+0.45*math.sin(x*.025)*math.cos(y*.06)

# Continuous terrain, not disconnected flat cards.
verts=[];faces=[];nx=128;ny=64
for j in range(ny+1):
    y=-80+j*160/ny
    for i in range(nx+1):
        x=-160+i*320/nx;verts.append((x,y,height(x,y)))
for j in range(ny):
    for i in range(nx):
        a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
mesh=bpy.data.meshes.new('Terrain mesh');mesh.from_pydata(verts,[],faces);mesh.materials.append(earth);mesh.materials.append(snow)
terrain=bpy.data.objects.new('Continuous 320m x 160m terrain',mesh);scene.collection.objects.link(terrain)
for poly in mesh.polygons:
    cy=sum(mesh.vertices[v].co.y for v in poly.vertices)/4
    if cy>39:poly.material_index=1
cube('World soil cut edge',(0,0,-2.2),(320,160,3.6),rock)

def path(name,coords,width=3):
    vs=[]
    for k,(x,y) in enumerate(coords):
        prev=coords[max(0,k-1)];nxt=coords[min(len(coords)-1,k+1)]
        angle=math.atan2(nxt[1]-prev[1],nxt[0]-prev[0])+math.pi/2
        for s in (-1,1):
            xx=x+s*width/2*math.cos(angle);yy=y+s*width/2*math.sin(angle)
            vs.append((xx,yy,height(xx,yy)+0.08))
    fs=[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(coords)-1)]
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(roof)
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob)
path('Main forest avenue',[(-140,-40),(-90,-28),(-55,-18),(-20,-12),(20,-16),(60,-20),(110,-37),(150,-48)],5)
path('Castle approach',[(-20,-12),(-20,3),(-20,16),(-20,40)],4)
path('Northern lane',[(20,-16),(34,10),(68,22),(106,43)],3)
path('West woodland trail',[(-90,-28),(-95,0),(-116,22),(-140,42)],3)

def checker(name,x,y,z,w,d):
    vs=[];fs=[];idx=[];tile=.65
    for j in range(int(d/tile)):
        for i in range(int(w/tile)):
            xx=x-w/2+i*tile;yy=y-d/2+j*tile;a=len(vs)
            vs.extend([(xx,yy,z),(xx+tile,yy,z),(xx+tile,yy+tile,z),(xx,yy+tile,z)])
            fs.append((a,a+1,a+2,a+3));idx.append((i+j)%2)
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(black);me.materials.append(ivory)
    for p,index in zip(me.polygons,idx):p.material_index=index
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob)

def bed(x,y,z):
    cube('Room bed frame',(x,y,z+0.4),(2.4,3.7,0.7),wood)
    cube('Ivory bed linen',(x,y,z+0.87),(2.2,3.45,0.25),ivory)
    cube('Pillow',(x,y+1.15,z+1.06),(1.7,0.7,0.2),ivory)
    cube('Headboard',(x,y+1.85,z+0.95),(2.5,0.2,1.5),wood)
    cube('Room bed folded blanket',(x,y-.55,z+1.015),(2.23,2.1,.07),ivory)
    for xx in (-.95,.95):
        for yy in (-1.45,1.45):cube('Room bed brass foot',(x+xx,y+yy,z+.18),(.12,.12,.36),brass)

def floor(name,x,y,z,w,d,tiles=False):
    cube(name,(x,y,z-.16),(w,d,.32),roof)
    walk_surfaces.append({'x':x,'z':-y,'w':w,'d':d,'y':z})
    if tiles:checker(name+' checker tiles',x,y,z+.015,w,d)

def rail(name,x,y,z,w,axis='x'):
    cube(name+' handrail',(x,y,z+1.02),(w,.10,.11) if axis=='x' else (.10,w,.11),trim)
    for i in range(int(w/1.4)+1):
        p=-w/2+i*w/max(1,int(w/1.4))
        cube(name+' post',(x+(p if axis=='x' else 0),y+(p if axis=='y' else 0),z+.52),(.10,.10,1.04),trim)

def stair(name,x,y,z,width,length,rise):
    count=max(4,math.ceil(rise/.18))
    for i in range(count):
        top=z+(i+1)*rise/count
        cube(name+' Stair flight',(x,y-length/2+(i+.5)*length/count,(z+top)/2),(width,length/count+.015,top-z),stone)
    walk_surfaces.append({'x':x,'z':-y,'w':width,'d':length,'y':z+rise/2,'slopeZ':-rise/length})
    for side in (-1,1):
        a=Vector((x+side*width/2,y-length/2,z+1));b=Vector((x+side*width/2,y+length/2,z+rise+1))
        ob=cube(name+' inclined rail',(a+b)/2,(.10,.10,(b-a).length),trim);ob.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()

def facade(name,x,y,z,w,h,door=0):
    if door:
        width=(w-door)/2
        for side in (-1,1):cube(name+' wall',(x+side*(door+width)/2,y,z+h/2),(width,.65,h),stone,True)
        cube(name+' door lintel',(x,y,z+(h+3)/2),(door,.65,h-3),stone,True)
    else:cube(name+' wall',(x,y,z+h/2),(w,.65,h),stone,True)
    for i in range(1,int(h/.9)):cube(name+' Facade course',(x,y-.34,z+i*.9),(w,.027,.035),joint)
    cube(name+' coping',(x,y,z+h+.07),(w+.16,.8,.14),trim)

def stepped_tower(name,x,y,z,w=7,d=8,h=31):
    cube(name+' Stepped tower lower',(x,y,z+h*.35),(w+1.5,d+1.4,h*.70),stone,True)
    cube(name+' Stepped tower upper',(x,y+.65,z+h*.80),(w,d,h*.40),stone,True)
    cube(name+' Stepped tower crown',(x,y+.65,z+h+.13),(w+.3,d+.3,.26),trim)
    cube(name+' recessed tower inset',(x+.7,y-.35,z+h+1.1),(w*.52,d*.45,2),stone)
    for level in range(1,int(h/1.2)):
        width=w+1.5 if level*1.2<h*.7 else w
        cube(name+' Facade course',(x,y-(d+1.4)/2-.015,z+level*1.2),(width,.025,.03),joint)
    for zz in (7,14,21):
        for xx in (-1.35,1.35):cube(name+' tower slit',(x+xx,y-(d+1.4)/2-.04,z+zz),(.32,.045,1.3),glass)

def room(name,x,y,z,w=11,d=10,h=5):
    floor(name+' floor',x,y,z,w,d,True)
    facade(name+' rear',x,y+d/2,z,w,h,door=3.8)
    cube(name+' side',(x+w/2,y,z+h/2),(.5,d,h),stone,True)
    cube(name+' cutaway edge',(x-w/2,y,z+.35),(.5,d,.7),stone)
    bed(x-2,y+1,z)
    cube(name+' writing desk',(x+2,y+1,z+1),(1.6,1,.15),wood)
    for xx in (-.65,.65):
        for yy in (-.35,.35):cube(name+' desk leg',(x+2+xx,y+1+yy,z+.46),(.09,.09,.92),wood)
    cube(name+' desk paper',(x+2,y+.94,z+1.09),(.45,.38,.02),ivory)
    cube(name+' chair seat',(x+2,y-.1,z+.48),(.72,.72,.12),wood)
    cube(name+' chair back',(x+2,y-.5,z+.88),(.72,.09,.74),wood)
    cube(name+' interior backlight',(x,y+d/2-.34,z+h*.65),(w*.65,.03,1.4),lightmat)
    cube(name+' ceiling lip',(x,y+d/2-.5,z+h),(w,1,.2),trim)

def auditorium(x,y,z):
    floor('Auditorium stone floor',x,y,z,17,18)
    facade('Auditorium back',x,y+9,z,17,13)
    for side in (-1,1):
        cube('Auditorium tall flank',(x+side*8.6,y+2,z+6.5),(.75,14,13),stone,True)
        for k in range(3):cube('Auditorium vertical light',(x+side*8.17,y+1+k*3,z+7),(.035,.3,5),lightmat)
    for row in range(4):
        radius=3.7+row*1.05;vs=[];fs=[];n=24
        for i in range(n+1):
            a=math.radians(200+i*140/n)
            for r in (radius,radius+.65):vs.append((x+math.cos(a)*r,y+3+math.sin(a)*r,z+.18+row*.22))
        for i in range(n):fs.append((i*2,i*2+1,i*2+3,i*2+2))
        me=bpy.data.meshes.new('Auditorium semicircular seating');me.from_pydata(vs,[],fs);me.materials.append(roof)
        ob=bpy.data.objects.new('Auditorium semicircular seating',me);scene.collection.objects.link(ob)
        sol=ob.modifiers.new('Seating volume','SOLIDIFY');sol.thickness=.22;bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=sol.name)
    cube('Auditorium dais',(x,y+4,z+.16),(5.3,3.8,.32),trim)
    cube('Auditorium lectern pedestal',(x,y+4,z+.77),(.55,.65,1.22),stone)
    cube('Auditorium lectern top',(x,y+4,z+1.41),(1.7,.9,.12),wood)
    vs=[];fs=[]
    for i in range(25):
        a=math.radians(30+i*12.5)
        for r in (1.1,1.18):vs.append((x+math.cos(a)*r,y+8.63,z+8+math.sin(a)*r))
    for i in range(24):fs.append((i*2,i*2+1,i*2+3,i*2+2))
    me=bpy.data.meshes.new('Auditorium crescent');me.from_pydata(vs,[],fs);me.materials.append(brass)
    ob=bpy.data.objects.new('Auditorium crescent emblem',me);scene.collection.objects.link(ob)
    cube('Auditorium lintel',(x,y-3,z+13),(18,3,.5),stone)
    cube('Auditorium roof terrace',(x,y+5.5,z+13.3),(18,7,.4),roof)
    rail('Auditorium front rail',x,y-8.5,z,16)

def building(name,x,y,w,d,h,towers=True):
    z=height(x,y)+0.1
    cube(name+' base',(x,y,z+0.4),(w+2,d+2,0.8),roof)
    # Cutaway front retains the original miniature map's visible interior rooms.
    cube(name+' back',(x,y+d/2,z+h/2),(w,1.2,h),stone,True)
    cube(name+' west',(x-w/2,y,z+h/2),(1.2,d,h),stone,True)
    cube(name+' east',(x+w/2,y,z+h/2),(1.2,d,h),stone,True)
    for floor in (0, h*.46):
        cube(name+' floor',(x,y,z+floor+0.6),(w,d,0.35),roof)
        walk_surfaces.append({'x':x,'z':-y,'w':w,'d':d,'y':z+floor+.8})
        checker(name+' interior floor',x,y,z+floor+0.8,w-2,d-2)
        bed(x-w*.28,y+d*.20,z+floor+.82)
        cube('Archive desk',(x+w*.26,y+d*.18,z+floor+1.5),(3,1.4,.24),wood)
        for xx in (-1,1):
            for yy in (-1,1):cube('Desk leg',(x+w*.26+xx*1.25,y+d*.18+yy*.5,z+floor+1.1),(.15,.15,.7),wood)
        cube(name+' division',(x,y+d*.1,z+floor+h*.2),(0.4,d*.8,h*.4),stone)
    cube(name+' side parapet',(x,y+d/2,z+h+.3),(w,.8,.7),stone)
    for i in range(1, int(w/3)):
        cube(name+' window',(x-w/2+i*3,y+d/2+.62,z+h*.6),(1.35,.08,2.3),glass)
    if towers:
        for xx in (-1,1):
            tx=x+xx*(w/2+1.8);ty=y+d/2
            stepped_tower(name,tx,ty,z,4.5,5.5,h+10)
            for wx in (-1,1):cube(name+' tower slit',(tx+wx*1.3,ty-3.52,z+h+4),(.45,.08,3),glass)

# Rebuild the visible central compound, including its distinctive auditorium.
x=-20;y=16;z=.45
floor('Central foundation plinth',x,y,z,50,33)
stair('Central entrance',x,-3,0,12,7,.45)
auditorium(x,y-3,z)
cube('Auditorium wallwash',(x,y+5.65,z+6),(5.8,.02,7),lightmat)
for side in (-1,1):
    sx=x+side*18
    for level in (0,6.4,12.8):room('Central '+('west' if side<0 else 'east')+' room',sx,y+2,z+level,12,12,5.7)
    stepped_tower('Central '+('west' if side<0 else 'east'),sx+side*4,y+19,z,7.5,9,33 if side<0 else 30)
    floor('Rear passage upper landing',sx,y+11,z+6.4,12,6)
    cube('Rear passage outer wall',(sx+side*6.3,y+6,z+3.2),(.45,20,6.4),stone,True)
    rail('Rear passage landing rail',sx,y+8.8,z+6.4,10)
floor('Rear passage connecting gallery',x,y+13,z+6.4,27,4)
rail('Rear passage gallery rail',x,y+11,z+6.4,23)
for sx in (x-10,x+10):cube('Central gallery column',(sx,y+13,z+3.2),(.8,.8,6.4),trim)
stair('Rear passage ascending',-13,37,z,3,11,6.4)
floor('Rear passage return bridge',-20,35.5,z+6.4,3,14)
floor('Rear passage stair head landing',-16.5,42.5,z+6.4,10,3)
rail('Rear passage return bridge guard',-21.5,35.5,z+6.4,14,'y')
rail('Rear passage return bridge guard',-18.5,35.5,z+6.4,11,'y')
building('Eastern residence',66,17,22,18,14)
building('North lookout',109,42,15,12,13)
building('Western greenhouse',-105,2,21,17,9)
# Open central lawn, monuments and castle staircase.
cube('Castle front lawn',(-20,-5,.15),(34,12,.1),grass)
cube('Water basin',(40,-40,.13),(27,19,.12),water)
for x,y in [(-55,30),(20,34),(91,-22)]:cube('Reference stone monolith',(x,y,height(x,y)+5),(6,7,10),stone,True)

# Fir prototype matches the faceted foliage and taper in the official sandtable.
parts=[]
bpy.ops.mesh.primitive_cylinder_add(vertices=7,radius=.18,depth=2.8,location=(0,0,1.4));parts.append(bpy.context.object);parts[-1].data.materials.append(trunk)
for level in range(11):
    radius=2.0*(1-level/12)**.85
    bpy.ops.mesh.primitive_cone_add(vertices=14,radius1=radius,radius2=radius*.12,depth=.9,location=(0,0,1.15+level*.53))
    for v in bpy.context.object.data.vertices:
        a=math.atan2(v.co.y,v.co.x);factor=1+.16*math.sin(a*5+level*.5)
        v.co.x*=factor;v.co.y*=factor
        if v.co.z<0:v.co.z+=.15*math.cos(a*7)
    parts.append(bpy.context.object);parts[-1].data.materials.append(greens[0])
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();prototype=bpy.context.object;prototype.name='Fir prototype'
bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
for i in range(1050):
    x=random.uniform(-153,153);y=random.uniform(-72,72)
    if any(abs(x-bx)<bw and abs(y-by)<bd for bx,by,bw,bd in [(-20,16,30,23),(66,17,18,18),(109,42,14,13),(-105,2,18,16),(40,-40,19,15)]):continue
    if -24<x<-9 and 30<y<46:continue
    if abs(y-(-19-.09*x))<4 or (abs(x+20)<5 and -15<y<45):continue
    ob=bpy.data.objects.new('Fir %04d'%i,prototype.data);scene.collection.objects.link(ob)
    ob.location=(x,y,height(x,y));sc=random.uniform(.72,1.35);ob.scale=(sc,sc,sc*random.uniform(.95,1.25));ob.rotation_euler.z=random.random()*math.tau
bpy.data.objects.remove(prototype,do_unlink=True)
for i in range(45):
    x=random.uniform(-155,155);y=random.uniform(51,76)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=(x,y,height(x,y)+1.2))
    ob=bpy.context.object;ob.name='Snow granite ridge';ob.scale=(random.uniform(4,10),random.uniform(3,8),random.uniform(3,10))
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);ob.data.materials.append(rock);ob.data.materials.append(snow)
    for p in ob.data.polygons:p.material_index=1 if p.normal.z>.25 else 0

bpy.ops.object.camera_add(location=(64,-102,79));camera=bpy.context.object;camera.name='World overview'
camera.rotation_euler=(Vector((-20,16,11))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=140;scene.camera=camera
bpy.ops.object.light_add(type='SUN',location=(0,-30,80));sun=bpy.context.object;sun.name='Overcast winter sun';sun.data.energy=1.8;sun.data.angle=math.radians(16);sun.rotation_euler=(.4,-.5,-.3)
for lx,ly,lz in [(-20,22,8),(-38,21,3.5),(-2,21,10)]:
    bpy.ops.object.light_add(type='AREA',location=(lx,ly,lz));light=bpy.context.object;light.name='Interior indirect light';light.data.energy=130;light.data.color=(.73,.90,.72);light.data.shape='DISK';light.data.size=7
scene.world=bpy.data.worlds.new('Winter sky');scene.world.use_nodes=True
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Color'].default_value=(.49,.59,.63,1)
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Strength'].default_value=.65
scene.render.engine='BLENDER_EEVEE';scene.view_settings.view_transform='AgX'
scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'

os.makedirs(os.path.join(ROOT,'public/models'),exist_ok=True)
with open(os.path.join(ROOT,'public/data/world.json'),'w',encoding='utf-8') as f:
    json.dump({'bounds':{'minX':-155,'maxX':155,'minZ':-75,'maxZ':75},'colliders':colliders,'walkSurfaces':walk_surfaces,'spawn':[0,2,35], 'model':'models/tigers-world.glb','revision':2,'sourceScope':'Reference-guided visible front; adapted hidden surfaces'},f,ensure_ascii=False)
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT,'public/models/tigers-world.glb'),export_format='GLB',use_active_scene=True,export_cameras=False,export_lights=False)

# A second Blender scene preserves all original draw meshes and their UVs.
original=bpy.data.scenes.get('Original chapter 104 sandtable') or bpy.data.scenes.new('Original chapter 104 sandtable');bpy.context.window.scene=original
for ob in list(original.objects):bpy.data.objects.remove(ob,do_unlink=True)
with open(os.path.join(ROOT,'public/data/chapter-104.json'),encoding='utf-8') as f:data=json.load(f)
materials={}
for draw in data[19]['draws']:
    key=draw['texture']
    if key not in materials:
        m=bpy.data.materials.new(os.path.basename(key));m.use_nodes=True;n=m.node_tree.nodes;n.clear()
        tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(os.path.join(ROOT,'public',key),check_existing=True)
        p=n.new('ShaderNodeBsdfPrincipled');p.inputs['Roughness'].default_value=1
        m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color']);m.node_tree.links.new(tex.outputs['Alpha'],p.inputs['Alpha'])
        out=n.new('ShaderNodeOutputMaterial');m.node_tree.links.new(p.outputs['BSDF'],out.inputs['Surface']);materials[key]=m
    vs=[(v[0]-52,v[1]+17,(4.1-v[2])*.08) for v in draw['vertices']]
    fs=[tuple(c[0] for c in face) for face in draw['faces']]
    me=bpy.data.meshes.new(draw['name']);me.from_pydata(vs,[],fs);me.materials.append(materials[key]);uv=me.uv_layers.new()
    for poly,face in zip(me.polygons,draw['faces']):
        for li,c in zip(poly.loop_indices,face):uv.data[li].uv=draw['uv'][c[1]]
    ob=bpy.data.objects.new(draw['name'],me);original.collection.objects.link(ob)
bpy.context.window.scene=scene
bpy.ops.file.pack_all()
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
        area.spaces.active.shading.type='MATERIAL'
previous_versions=bpy.context.preferences.filepaths.save_version;bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'blender/tigers-world.blend'))
finally:bpy.context.preferences.filepaths.save_version=previous_versions
print('Created world:',len(scene.objects),'objects; GLB and editable .blend saved')
