"""Build the Chapter 4 reference map and its explorable 3D reconstruction.
Run inside Blender: exec(compile(open(path, encoding='utf-8').read(), path, 'exec'))
"""
import bpy, math, random, json, os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
random.seed(104)
scene = bpy.data.scenes.new('El oro de los tigres - 3D World')
bpy.context.window.scene = scene

def mat(name, color, roughness=0.85):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=roughness
    return m

stone=mat('Foundation limestone / reference sampled palette',(0.51,0.55,0.51))
roof=mat('Weathered terrace',(0.38,0.43,0.38))
wood=mat('Wood',(0.20,0.14,0.085))
trunk=mat('Fir bark',(0.14,0.16,0.12))
greens=[mat('Fir canopy '+str(i),c) for i,c in enumerate([(0.19,0.23,0.13),(0.23,0.27,0.15),(0.15,0.20,0.14),(0.25,0.27,0.16)])]
earth=mat('Forest floor',(0.23,0.28,0.19))
snow=mat('Snow ridge',(0.79,0.84,0.85))
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
def cube(name,loc,size,material,solid=False):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material)
    if material==stone:
        uv=o.data.uv_layers.active
        if uv:
            for face in o.data.polygons:
                coords=[(0.71,0.84),(0.74,0.84),(0.74,0.91),(0.71,0.91)]
                for k,li in enumerate(face.loop_indices):uv.data[li].uv=coords[k%4]
    if solid:colliders.append({'x':loc[0],'z':-loc[1],'w':size[0],'d':size[1],'height':size[2]})
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
    vs=[];fs=[];idx=[];tile=1.1
    for j in range(int(d/tile)):
        for i in range(int(w/tile)):
            xx=x-w/2+i*tile;yy=y-d/2+j*tile;a=len(vs)
            vs.extend([(xx,yy,z),(xx+tile,yy,z),(xx+tile,yy+tile,z),(xx,yy+tile,z)])
            fs.append((a,a+1,a+2,a+3));idx.append((i+j)%2)
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(black);me.materials.append(ivory)
    for p,index in zip(me.polygons,idx):p.material_index=index
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob)

def bed(x,y,z):
    cube('Reference room bed',(x,y,z+0.4),(2.4,3.7,0.7),wood)
    cube('Ivory bed linen',(x,y,z+0.87),(2.2,3.45,0.25),ivory)
    cube('Pillow',(x,y+1.15,z+1.06),(1.7,0.7,0.2),ivory)
    cube('Headboard',(x,y+1.85,z+0.95),(2.5,0.2,1.5),wood)

def building(name,x,y,w,d,h,towers=True):
    z=height(x,y)+0.1
    cube(name+' base',(x,y,z+0.4),(w+2,d+2,0.8),roof)
    # Cutaway front retains the original miniature map's visible interior rooms.
    cube(name+' back',(x,y+d/2,z+h/2),(w,1.2,h),stone,True)
    cube(name+' west',(x-w/2,y,z+h/2),(1.2,d,h),stone,True)
    cube(name+' east',(x+w/2,y,z+h/2),(1.2,d,h),stone,True)
    for floor in (0, h*.46):
        cube(name+' floor',(x,y,z+floor+0.6),(w,d,0.35),roof)
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
            cube(name+' twin tower',(tx,ty,z+(h+10)/2),(5.5,7,h+10),stone,True)
            cube(name+' tower cap',(tx,ty,z+h+10.15),(5.9,7.4,.3),roof)
            for wx in (-1,1):cube(name+' tower slit',(tx+wx*1.3,ty-3.52,z+h+4),(.45,.08,3),glass)

building('Central foundation castle',-20,16,32,23,16)
building('Eastern residence',66,17,22,18,14)
building('North lookout',109,42,15,12,13)
building('Western greenhouse',-105,2,21,17,9)
# Open central lawn, monuments and castle staircase.
cube('Castle front lawn',(-20,-5,.15),(34,12,.1),grass)
for step in range(6):cube('Castle stair',(-20,1-step*.65,.15+(6-step)*.12),(9,.68,(6-step)*.24),stone)
cube('Water basin',(40,-40,.13),(27,19,.12),water)
for x,y in [(-55,30),(20,34),(91,-22)]:cube('Reference stone monolith',(x,y,height(x,y)+5),(6,7,10),stone,True)

# Fir prototype matches the faceted foliage and taper in the official sandtable.
parts=[]
bpy.ops.mesh.primitive_cylinder_add(vertices=7,radius=.18,depth=2.8,location=(0,0,1.4));parts.append(bpy.context.object);parts[-1].data.materials.append(trunk)
for level in range(4):
    bpy.ops.mesh.primitive_cone_add(vertices=9,radius1=1.45-level*.27,radius2=.05,depth=2.2,location=(0,0,2+level*.87))
    parts.append(bpy.context.object);parts[-1].data.materials.append(greens[0])
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();prototype=bpy.context.object;prototype.name='Fir prototype'
bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
for i in range(640):
    x=random.uniform(-153,153);y=random.uniform(-72,72)
    if any(abs(x-bx)<bw and abs(y-by)<bd for bx,by,bw,bd in [(-20,16,24,23),(66,17,18,18),(109,42,14,13),(-105,2,18,16),(40,-40,19,15)]):continue
    if abs(y-(-19-.09*x))<4 or (abs(x+20)<5 and -15<y<45):continue
    ob=bpy.data.objects.new('Fir %04d'%i,prototype.data);scene.collection.objects.link(ob)
    ob.location=(x,y,height(x,y));sc=random.uniform(.65,1.65);ob.scale=(sc,sc,sc);ob.rotation_euler.z=random.random()*math.tau
bpy.data.objects.remove(prototype,do_unlink=True)
for i in range(34):
    x=random.uniform(-155,155);y=random.uniform(51,76)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=(x,y,height(x,y)+2))
    ob=bpy.context.object;ob.name='Snowy rock';ob.scale=(random.uniform(3,8),random.uniform(3,7),random.uniform(3,9));ob.data.materials.append(snow if i%3 else rock)

bpy.ops.object.camera_add(location=(85,-110,85));camera=bpy.context.object;camera.name='World overview'
camera.rotation_euler=(Vector((0,8,0))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=32;scene.camera=camera
bpy.ops.object.light_add(type='SUN',location=(0,-30,80));sun=bpy.context.object;sun.name='Overcast winter sun';sun.data.energy=2;sun.rotation_euler=(.4,-.5,-.3)
scene.world=bpy.data.worlds.new('Winter sky');scene.world.use_nodes=True
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Color'].default_value=(.38,.48,.53,1)
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Strength'].default_value=.7
scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'

os.makedirs(os.path.join(ROOT,'public/models'),exist_ok=True)
with open(os.path.join(ROOT,'public/data/world.json'),'w',encoding='utf-8') as f:
    json.dump({'bounds':{'minX':-155,'maxX':155,'minZ':-75,'maxZ':75},'colliders':colliders,'spawn':[0,2,35], 'model':'models/tigers-world.glb'},f,ensure_ascii=False)
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT,'public/models/tigers-world.glb'),export_format='GLB',use_active_scene=True,export_cameras=False,export_lights=False)

# A second Blender scene preserves all original draw meshes and their UVs.
original=bpy.data.scenes.new('Original chapter 104 sandtable');bpy.context.window.scene=original
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
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'blender/tigers-world.blend'))
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_location=(0,0,0);area.spaces.active.region_3d.view_distance=180
print('Created world:',len(scene.objects),'objects; GLB and editable .blend saved')
