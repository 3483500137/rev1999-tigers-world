"""Build the Chapter 4 reference map and its explorable 3D reconstruction.
Run inside Blender: exec(compile(open(path, encoding='utf-8').read(), path, 'exec'))
"""
import bpy, bmesh, math, random, json, os
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
seatframe=mat('Reference ochre seat frame',(.36,.26,.095),.72)
seatpad=mat('Reference olive ivory seat inset',(.52,.56,.35),.9)
darktop=mat('Reference dark long fixture',(.055,.065,.052),.7)
wood=mat('Wood',(0.20,0.14,0.085))
trunk=mat('Fir bark',(0.14,0.16,0.12))
greens=[mat('Fir canopy '+str(i),c) for i,c in enumerate([(.18,.22,.10),(.22,.25,.12),(.12,.19,.11),(.27,.24,.13)])]
earth=mat('Forest floor',(0.12,0.19,0.11))
snow=mat('Snow ridge',(0.69,0.77,0.79))
rock=mat('Slate',(0.14,0.19,0.21))
black=mat('Checkered floor black',(0.024,0.033,0.025))
ivory=mat('Checkered floor ivory',(0.76,0.79,0.70))
grass=mat('Lawn',(0.30,0.37,0.23))
water=mat('Water',(0.12,0.24,0.23),0.25)
glass=mat('Window green',(0.12,0.23,0.19),0.35)
lightmat=mat('Foundation interior light',(0.68,0.82,0.61))
p=next(n for n in lightmat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
p.inputs['Emission Color'].default_value=(0.67,0.79,0.52,1);p.inputs['Emission Strength'].default_value=1.4

# Original atlas patch applied to reconstructed limestone walls, without recolouring.
atlas=bpy.data.images.load(os.path.join(ROOT,'public/assets/all/m_s08_hddtc_background_a03_manual__48c359e04b.webp'))
texture=stone.node_tree.nodes.new('ShaderNodeTexImage');texture.image=atlas
stone.node_tree.links.new(texture.outputs['Color'],next(n for n in stone.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'])
STONE_PIXELS=[900,1215,943,1290]
STONE_UV=[(900/2048,1-1290/2048),(943/2048,1-1290/2048),(943/2048,1-1215/2048),(900/2048,1-1215/2048)]
stone['sourcePixels']=STONE_PIXELS;stone['sourceTexture']='assets/all/m_s08_hddtc_background_a03_manual__48c359e04b.webp'
# Foliage palette sampled at known pixels of the unchanged source atlas.
pixels=atlas.pixels[:]
for m,(px,py) in zip(greens,[(731,962),(630,701),(660,575),(1280,981)]):
    i=((2047-py)*2048+px)*4
    colors=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in pixels[i:i+3]]
    next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(*colors,1)
    m['sourcePixel']=[px,py]

colliders=[]
walk_surfaces=[]
landmarks=[{'id':'central-auditorium','x':-20,'z':-16,'w':50,'d':33}]

def tiled_stone(o,size):
    """Repeat the unchanged atlas patch per physical panel, not once per tower.

    Explicit tessellation keeps identical UVs in Blender and exported glTF;
    glTF cannot export arbitrary Blender shader-node coordinate arithmetic.
    """
    vs=[];fs=[];uvs=[]
    for normal in range(3):
        a=(normal+1)%3;b=(normal+2)%3
        na=max(1,math.ceil(size[a]/2.8));nb=max(1,math.ceil(size[b]/3.6))
        for sign in (-1,1):
            for j in range(nb):
                for i in range(na):
                    pts=[]
                    for aa,bb in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]:
                        p=[0,0,0];p[normal]=sign*size[normal]/2
                        p[a]=-size[a]/2+aa*size[a]/na;p[b]=-size[b]/2+bb*size[b]/nb;pts.append(p)
                    if sign<0:pts.reverse()
                    start=len(vs);vs.extend(pts);fs.append(tuple(range(start,start+4)))
                    uvs.append(STONE_UV)
    o.data.clear_geometry();o.data.from_pydata(vs,[],fs);o.data.update()
    uv=o.data.uv_layers.active or o.data.uv_layers.new()
    for face,coords in zip(o.data.polygons,uvs):
        for li,t in zip(face.loop_indices,coords):uv.data[li].uv=t
    o['stonePanelSize']=[2.8,3.6]
def cube(name,loc,size,material,solid=False):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material)
    if material==stone:tiled_stone(o,size)
    if solid:colliders.append({'x':loc[0],'z':-loc[1],'w':size[0],'d':size[1],'height':size[2],'yMin':loc[2]-size[2]/2})
    return o

def height(x,y):
    ridge=max(0,(y-42)/36)
    t=max(0,min(1,(y-48)/32))
    crest=19+15*math.sin(x*.039)**2+6*math.sin(x*.12)**2
    return ridge*(10+7*math.sin(x*.035)**2)+0.45*math.sin(x*.025)*math.cos(y*.06)+math.sin(t*math.pi/2)*crest

# Continuous terrain, not disconnected flat cards.
verts=[];faces=[];nx=128;ny=64
for j in range(ny+1):
    y=-80+j*160/ny
    for i in range(nx+1):
        x=-160+i*320/nx;verts.append((x,y,height(x,y)))
for j in range(ny):
    for i in range(nx):
        if -80+(j+.5)*160/ny>49:continue
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
road_routes=[('Main forest avenue',[(-143,-48),(-87,-34),(-20,-23),(44,-25),(101,-35),(148,-49)],4),
 ('Castle approach',[(-20,-72),(-20,-23),(-20,-10),(-20,3)],4.5),
 ('Campus perimeter',[(-51,-2),(-51,36),(-25,43),(22,44),(51,23),(50,-5),(20,-10),(-51,-2)],1.5),
 ('Library lane',[(19,-26),(28,-39),(60,-51),(113,-55)],1.8),
 ('West woodland trail',[(-128,-55),(-115,-20),(-102,2),(-98,31)],2)]
for name,coords,width in road_routes:path(name,coords,width)

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

def bed(x,y,z,source_pixels,angle=0,teal=False,source='m_s08_hddtc_background_a03_manual__48c359e04b.webp'):
    """Only the four source bedrooms with distinct pillows/linen use this.

    Central framed fixtures do not call this function. Geometry is built in
    local coordinates so opposite headboard directions are kept independent.
    """
    root=bpy.data.objects.new('Confirmed source bed',None);scene.collection.objects.link(root)
    root['confirmedSourceBed']=True;root['sourcePixels']=source_pixels;root['sourceTexture']='assets/all/'+source
    root['observedEvidence']='Two separate pillows, folded fabric, low timber frame and a single headboard'
    before=set(scene.objects)
    cube('Observed low timber bed frame',(0,0,.34),(3.45,4.45,.35),seatframe)
    cube('Observed bed mattress',(0,0,.67),(3.18,4.23,.33),ivory)
    for xx in (-.8,.8):
        ob=cube('Observed separate pillow',(xx,1.37,.96),(1.48,.92,.27),ivory);ob.rotation_euler.x=-.06;ob['observedPart']='pillow'
    cube('Observed single bed headboard',(0,2.16,.90),(3.48,.18,1.42),wood)
    linen=mat('Source teal cover',(.035,.18,.205)) if teal else ivory
    # Folded fabric has shallow creases and an irregular hanging foot edge.
    vs=[];fs=[];cols=12;rows=12
    for j in range(rows+1):
        yy=-2.20 if j==0 else -2.06+j*3.0/rows
        for i in range(cols+1):
            xx=-1.58+i*3.16/cols;zz=.99+.065*math.sin(i*2.1+j*.45)
            if j==0:zz-=.18+.10*math.sin(i*1.8)
            vs.append((xx,yy,zz))
    for j in range(rows):
        for i in range(cols):
            a=j*(cols+1)+i;fs.append((a,a+1,a+cols+2,a+cols+1))
    me=bpy.data.meshes.new('Observed creased bed linen');me.from_pydata(vs,[],fs);me.materials.append(linen)
    ob=bpy.data.objects.new('Observed creased bed linen',me);scene.collection.objects.link(ob)
    for child in set(scene.objects)-before:child.parent=root
    root.location=(x,y,z);root.rotation_euler.z=angle
    return root

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

def reference_fixture(kind,x,y,z):
    """Trace each central opening independently; do not substitute generic beds.

    Pixel bounds are in the unchanged 2048px a03 atlas, top-left origin.
    The source names no furniture: keep descriptive shape IDs, not lore claims.
    """
    source_pixels={'west-seat':[850,1695,950,1830],
                   'east-lower-seat':[1585,1790,1715,1935],
                   'east-middle-desk':[1570,1530,1740,1645],
                   'east-upper-long-fixture':[1570,1300,1715,1455]}
    root=bpy.data.objects.new('Reference fixture '+kind,None);scene.collection.objects.link(root)
    root['referenceFixture']=kind;root['sourceTexture']='assets/all/m_s08_hddtc_background_a03_manual__48c359e04b.webp'
    root['sourcePixels']=source_pixels[kind]
    root['shape']='rigid-double-ended-inset' if kind.endswith('seat') else ('crosswise-raised-panel' if kind.endswith('desk') else 'long-dark-fixture')
    root['identificationScope']='Visible shape only; unknown purpose is not inferred from resemblance'
    before=set(scene.objects)
    if kind.endswith('seat'):
        # The visible object has rigid raised sides/back and an olive seat,
        # rather than a white mattress, pillow or blanket.
        ob=cube(kind+' rigid central inset',(x,y,z+.83),(2.8,3.7,.23),seatpad);ob.rotation_euler.x=.10;ob['observedPart']='rigid-inset-not-mattress'
        cube(kind+' front ochre end',(x,y-2,z+.85),(3.4,.35,1.1),seatframe)
        cube(kind+' front dark end inset',(x,y-1.78,z+1.06),(2.65,.08,.36),wood)
        cube(kind+' raised rear end',(x,y+1.9,z+1.36),(3.4,.35,1.75),seatframe)
        cube(kind+' dark rear end inset',(x,y+1.7,z+1.40),(2.65,.04,.95),wood)
        for side in (-1,1):
            cube(kind+' narrow rigid side',(x+side*1.48,y,z+.95),(.18,3.7,.24),seatframe)
            for yy in (-1.65,1.65):cube(kind+' square support',(x+side*1.4,y+yy,z+.4),(.28,.28,.8),wood)
    elif kind.endswith('desk'):
        cube(kind+' crosswise surrounding frame',(x,y,z+1.30),(6,2.4,.18),seatframe)
        ob=cube(kind+' raised ochre inset panel',(x,y,z+1.48),(4.3,1.5,.20),seatpad);ob['observedPart']='raised-inset-panel'
        for yy in (-1.16,1.16):cube(kind+' narrow surrounding rim',(x,y+yy,z+1.45),(6,.12,.26),seatframe)
        for side in (-1,1):
            cube(kind+' pale front rectangular support',(x+side*2,y-.80,z+.88),(.48,.38,.87),trim)
        cube(kind+' rear seat',(x,y+1.75,z+.62),(1.12,.95,.18),wood)
        cube(kind+' rear back',(x,y+2.12,z+1.18),(1.12,.14,1.15),wood)
    else:
        cube(kind+' long dark top',(x,y,z+1.1),(3.5,7.8,.22),darktop)
        cube(kind+' narrow timber inset',(x,y,z+1.23),(1.2,7.6,.03),wood)
        for side in (-1,1):
            cube(kind+' slim edge',(x+side*1.65,y,z+1.25),(.11,7.8,.08),trim)
            for yy in (-3.1,3.1):cube(kind+' slim support',(x+side*1.4,y+yy,z+.52),(.14,.14,1.04),darktop)
    for ob in set(scene.objects)-before:ob.parent=root

def room(name,x,y,z,w=11,d=10,h=5,fixture='west-seat'):
    floor(name+' floor',x,y,z,w,d)
    if fixture.endswith('seat'):checker(name+' checker tiles',x,y,z+.015,w-.8,d-.8)
    else:checker(name+' narrow checker runner',x,y,z+.015,3.6,d-.8)
    facade(name+' rear',x,y+d/2,z,w,h,door=3.8)
    cube(name+' side',(x+w/2,y,z+h/2),(.5,d,h),stone,True)
    cube(name+' cutaway edge',(x-w/2,y,z+.35),(.5,d,.7),stone)
    reference_fixture(fixture,x,y+.45,z)
    if fixture=='east-lower-seat':
        for dx in (-.85,.85):cube(name+' source vertical window',(x+dx,y+d/2-.34,z+3.4),(.65,.03,2.2),lightmat)
    elif fixture=='east-middle-desk':
        cube(name+' source vertical light',(x-3.7,y+d/2-.34,z+3),(.7,.03,3.3),lightmat)
    cube(name+' ceiling lip',(x,y+d/2-.5,z+h),(w,1,.2),trim)

def auditorium(x,y,z):
    floor('Auditorium stone floor',x,y,z,17,18)
    facade('Auditorium back',x,y+9,z,17,13)
    for side in (-1,1):
        cube('Auditorium tall flank',(x+side*8.6,y+2,z+6.5),(.75,14,13),stone,True)
        for k in range(3):cube('Auditorium vertical light',(x+side*8.17,y+1+k*3,z+7),(.035,.3,5),lightmat)
    for row in range(3):
        radius=3.7+row*1.05;vs=[];fs=[];n=24
        for i in range(n+1):
            a=math.radians(200+i*140/n)
            for r in (radius,radius+.65):vs.append((x+math.cos(a)*r,y+3+math.sin(a)*r,z+.18+row*.22))
        # The original has a central aisle, not uninterrupted concentric rings.
        for i in range(n):
            if abs((i+.5)/n-.5)>.085:fs.append((i*2,i*2+1,i*2+3,i*2+2))
        me=bpy.data.meshes.new('Auditorium semicircular seating');me.from_pydata(vs,[],fs);me.materials.append(seatpad)
        ob=bpy.data.objects.new('Auditorium semicircular seating',me);scene.collection.objects.link(ob)
        sol=ob.modifiers.new('Seating volume','SOLIDIFY');sol.thickness=.22;bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=sol.name)
    cube('Auditorium dais',(x,y+4,z+.16),(5.3,3.8,.32),trim)
    cube('Auditorium reference front table',(x,y+4,z+.76),(4.4,1,.42),trim)
    for i in range(3):
        cube('Auditorium rear chair back',(x+(i-1)*1.25,y+4.8,z+1.4),(.7,.18,.8),wood)
        cube('Auditorium front table support',(x+(i-1)*1.25,y+4,z+.4),(.35,.6,.8),stone)
    for ring in range(2):
        vs=[];fs=[];radius=1.2-ring*.37
        for i in range(48):
            a=i*math.tau/48
            for r in (radius,radius+.055):vs.append((x+math.cos(a)*r,y+1,z+8.3+math.sin(a)*r))
        for i in range(48):fs.append((i*2,i*2+1,((i+1)%48)*2+1,((i+1)%48)*2))
        me=bpy.data.meshes.new('Reference auditorium hanging ring');me.from_pydata(vs,[],fs);me.materials.append(brass)
        ob=bpy.data.objects.new('Reference auditorium hanging ring '+str(ring),me);scene.collection.objects.link(ob);ob['sourceFeature']='auditorium-ring'
    ob=cube('Reference auditorium pendant',(x,y+1,z+8.5),(.065,.065,3.7),brass);ob['sourceFeature']='auditorium-pendant'
    cube('Auditorium weathered roof terrace',(x,y+1,z+13.3),(18,16,.4),roof)
    # Broad roof head and two projecting prongs visible in the a03 atlas.
    silhouette=[(-5.8,-9),(-5.8,-3.5),(-7,-3.5),(-7,2.5),(-5.4,4.3),(5.4,4.3),(7,2.5),(7,-3.5),(5.8,-3.5),(5.8,-9),(1.1,-9),(1.1,-3.5),(-1.1,-3.5),(-1.1,-9)]
    n=len(silhouette);vs=[(x+xx,y+yy,z+zz) for zz in (13.4,14.3) for xx,yy in silhouette]
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    me=bpy.data.meshes.new('Auditorium reference roof silhouette');me.from_pydata(vs,[],fs);me.materials.append(stone)
    uv=me.uv_layers.new()
    for face in me.polygons:
        for li in face.loop_indices:
            v=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=(STONE_UV[0][0]+(v.x-x+7)/14*(43/2048),STONE_UV[0][1]+(v.y-y+9)/14*(75/2048))
    ob=bpy.data.objects.new('Auditorium reference roof silhouette',me);scene.collection.objects.link(ob)
    for side in (-1,1):
        cube('Auditorium rear roof block',(x+side*3.5,y+7,z+14.6),(5.5,2.7,1.1),stone)
        for yy in (-7,5):cube('Auditorium brass roof pin',(x+side*8,y+yy,z+14),(.12,.12,1.3),brass)
    rail('Auditorium front rail',x,y-8.5,z,16)

def reference_building(id,texture,pixels,x,y,w,d):
    root=bpy.data.objects.new('Source building '+id,None);scene.collection.objects.link(root)
    root['referenceBuilding']=id;root['sourceTexture']='assets/all/'+texture;root['sourcePixels']=pixels
    root['placementScope']='Estimated depth and ground position from the isometric front; not original 3D coordinates'
    landmarks.append({'id':id,'x':x,'z':-y,'w':w,'d':d})
    return root

def finish_building(root,before):
    for ob in set(scene.objects)-before:
        if ob!=root and ob.parent is None:ob.parent=root

def cylinder(name,x,y,z,radius,depth,material,vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=(x,y,z))
    ob=bpy.context.object;ob.name=name;ob.data.materials.append(material)
    if material==stone:
        vs=[];fs=[];rows=max(1,math.ceil(depth/3.6))
        for j in range(rows+1):
            for i in range(vertices):
                angle=i*math.tau/vertices;vs.append((radius*math.cos(angle),radius*math.sin(angle),-depth/2+j*depth/rows))
        for j in range(rows):
            for i in range(vertices):fs.append((j*vertices+i,j*vertices+(i+1)%vertices,(j+1)*vertices+(i+1)%vertices,(j+1)*vertices+i))
        fs.extend([tuple(range(vertices-1,-1,-1)),tuple(range(rows*vertices,(rows+1)*vertices))])
        ob.data.clear_geometry();ob.data.from_pydata(vs,[],fs);ob.data.update();uv=ob.data.uv_layers.active or ob.data.uv_layers.new()
        for face in ob.data.polygons:
            for k,li in enumerate(face.loop_indices):
                if len(face.loop_indices)==4:uv.data[li].uv=STONE_UV[k]
                else:
                    v=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=((900+943)/4096+v.x/radius*43/4096,1-(1215+1290)/4096+v.y/radius*75/4096)
    return ob

def inset_window_band(name,x,y,z,w,rows,columns):
    for row in range(rows):
        for column in range(columns):
            cube(name,(x-w/2+(column+.5)*w/columns,y,z+row*1.15),(w/columns*.68,.06,.36),glass)

def western_institution(x,y):
    before=set(scene.objects);root=reference_building('western-institution','m_s08_hddtc_background_a02_manual__e4f2121375.webp',[1280,540,2048,1330],x,y,38,29);z=height(x,y)+.4
    floor('Institution foundation',x,y,z,40,31)
    floor('Institution luminous main hall',x,y-3,z+1,25,15)
    checker('Institution central checker aisle',x,y-3,z+1.02,2.6,14)
    facade('Institution tall hall back',x,y+4.5,z+1,25,13)
    for side in (-1,1):
        cube('Institution vertical window pair',(x+side*5,y+4.13,z+6),(.6,.04,4.4),lightmat)
        cube('Institution second vertical window',(x+side*6.4,y+4.13,z+6),(.5,.04,4.4),lightmat)
    cube('Institution main roof',(x-4,y+7,z+14),(22,13,.8),stone)
    # Actual two bedroom openings appear only in this side wing in a02/a03.
    for level in (1,7):
        floor('Institution side bedroom',x+15,y-2,z+level,9,10,True)
        facade('Institution bedroom back',x+15,y+3,z+level,9,5.5)
        cube('Institution bedroom right wall',(x+19.5,y-2,z+level+2.7),(.7,10,5.4),stone,True)
        bed(x+15,y-1,z+level+.02,[270,level==1 and 985 or 730,414,level==1 and 1080 or 850],angle=-math.pi/2)
    for xx in (-2,2):
        for zz in range(5):cube('Institution archive shelf',(x+xx,y+2,z+1.5+zz*.45),(2.6,.7,.15),darktop)
    cube('Institution small purple bench',(x+1,y-1,z+1.45),(2.6,1,.5),brass)
    floor('Institution roof walkway',x+15,y-2,z+13.1,10,12)
    for xx in (-4.7,4.7):rail('Institution roof runway',x+15+xx,y-2,z+13.1,12,'y')
    stepped_tower('Institution front pier',x-17,y-6,z,9,10,22)
    floor('Institution front pier rooftop',x-17,y-6,z+22.5,9,10)
    for xx in (-4,4):rail('Institution pier roof rail',x-17+xx,y-6,z+22.5,10,'y')
    stepped_tower('Institution rear split pier',x-13,y+11,z,8,9,33)
    stepped_tower('Institution taller rear pier',x-4,y+13,z,7,8,37)
    stair('Institution front approach',x,y-13,z,7,5,1)
    finish_building(root,before)

def roof_annex(x,y):
    before=set(scene.objects);root=reference_building('roof-bedroom-annex','m_s08_hddtc_background_a03_manual__48c359e04b.webp',[1240,0,1790,805],x,y,25,19);z=height(x,y)+.4
    cube('Annex closed lower block',(x,y,z+7),(25,19,14),stone,True)
    inset_window_band('Annex narrow inset window',x,y-9.54,z+1.5,23,9,8)
    floor('Annex single cutaway roof bedroom',x+4,y-4,z+14.15,13,9,True)
    facade('Annex bedroom back',x+4,y+.5,z+14.15,13,4.3)
    cube('Annex bedroom right wall',(x+10.5,y-4,z+16.3),(.7,9,4.3),stone)
    bed(x+.7,y-3,z+14.17,[1490,430,1650,530],angle=math.pi/2)
    cube('Annex square orb table',(x+7,y-3.4,z+15.1),(2.2,2.2,.35),wood)
    for dx in (-.8,.8):
        for dy in (-.8,.8):cube('Annex orb table leg',(x+7+dx,y-3.4+dy,z+14.57),(.15,.15,.8),wood)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.4,location=(x+7,y-3.4,z+15.7))
    ob=bpy.context.object;ob.name='Annex blue orb';ob.data.materials.append(mat('Reference blue globe',(.07,.24,.32),.23))
    cube('Annex closed rear roof',(x-3,y+3.5,z+14.3),(19,10,.6),stone)
    cube('Annex tall back split tower',(x+3,y+7,z+26),(10,8,24),stone,True)
    for side in (-1,1):cube('Annex split crown',(x+3+side*2.6,y+7,z+38.4),(4.6,8,.8),stone)
    cube('Annex dark tower notch',(x+3,y+2.95,z+29),(3.8,.06,1.2),darktop)
    finish_building(root,before)

def sports_terrace(x,y):
    before=set(scene.objects);root=reference_building('sports-terrace','m_s08_hddtc_background_a04_manual__416aec4db2.webp',[220,235,1030,1280],x,y,24,24);z=height(x,y)+.5
    # Chamfered plinth and recessed blue ping-pong niche, not a bedroom.
    bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=14,depth=8,location=(x,y,z+4),rotation=(0,0,math.pi/8))
    ob=bpy.context.object;ob.name='Sports chamfered octagonal plinth';ob.data.materials.append(stone)
    uv=ob.data.uv_layers.active or ob.data.uv_layers.new()
    for face in ob.data.polygons:
        for k,li in enumerate(face.loop_indices):
            if len(face.loop_indices)==4:uv.data[li].uv=STONE_UV[k]
            else:
                a=k*math.tau/len(face.loop_indices);uv.data[li].uv=((900+943)/4096+math.cos(a)*43/4096,1-(1215+1290)/4096+math.sin(a)*75/4096)
    floor('Sports rooftop court',x,y,z+9,22,20)
    for xx in (-11,11):cube('Sports side parapet',(x+xx,y,z+10.5),(.7,20,3),stone)
    cube('Sports rear parapet',(x,y+10,z+10.5),(22,.7,3),stone)
    for yy in (-4,1,6):cube('Sports three side cap blocks',(x+10.5,y+yy,z+12.16),(1.5,1,.26),trim)
    for xx in (-7,0,7):cube('Sports white court line',(x+xx,y+2,z+9.02),(.10,15,.02),ivory)
    for yy in (-5,9):cube('Sports white boundary',(x,y+yy,z+9.02),(15,.1,.02),ivory)
    for xx in (-1.1,1.1):cube('Sports paired rooftop dash',(x+xx,y+1,z+9.03),(1.7,.22,.025),ivory)
    blue=mat('Source table tennis blue border',(.055,.07,.18))
    cube('Sports blue recessed apron',(x,y-7,z+9.04),(11,6,.08),blue)
    floor('Sports ivory table niche',x,y-7,z+9.10,10,5)
    cube('Sports source pale niche floor',(x,y-7,z+9.115),(10,5,.025),trim)
    for side in (-1,1):
        cube('Table tennis table half',(x+side*1.16,y-7,z+10.1),(2.24,2.6,.14),glass)
        cube('Table tennis edge line',(x+side*2.24,y-7,z+10.18),(.04,2.6,.015),ivory)
        for yy in (-1.27,1.27):cube('Table tennis white perimeter',(x+side*1.16,y-7+yy,z+10.18),(2.24,.04,.015),ivory)
        cube('Table tennis central length line',(x+side*1.16,y-7,z+10.18),(2.24,.035,.015),ivory)
        for yy in (-1,1):cube('Table tennis leg',(x+side*1.8,y-7+yy,z+9.58),(.09,.09,.96),darktop)
    cube('Table tennis net',(x,y-7,z+10.4),(.04,2.75,.5),darktop)
    for xx,col in [(-1.8,(.45,.07,.04)),(1.8,(.5,.24,.055))]:
        m=mat('Source table paddle '+str(xx),col);cylinder('Table tennis paddle',x+xx,y-7.4,z+10.21,.16,.035,m,16)
        cube('Table tennis paddle short handle',(x+xx+.19,y-7.4,z+10.21),(.22,.06,.035),wood)
    stepped_tower('Sports tall rear block',x-5,y+15,z,9,10,34)
    stepped_tower('Sports shorter rear block',x+5,y+14,z,7,8,29)
    cube('Sports isolated stone block',(x+14,y+12,z+5),(4,4,10),stone)
    finish_building(root,before)

def rotunda(x,y):
    before=set(scene.objects);root=reference_building('rotunda','m_s08_hddtc_background_a04_manual__416aec4db2.webp',[305,1260,1100,2048],x,y,27,26);z=height(x,y)+.4
    cylinder('Rotunda lower cylinder',x,y,z+5,11.5,10,stone)
    for h in (1.3,6.8):cylinder('Rotunda dark continuous window belt',x,y,z+h,11.56,.75,glass)
    cylinder('Rotunda broad flat roof',x,y,z+10.3,12.2,.6,stone)
    cylinder('Rotunda central drum',x,y,z+12.3,3.8,3.6,stone)
    cylinder('Rotunda central drum cap',x,y,z+14.15,4,.15,trim)
    cube('Rotunda projecting roof landing',(x,y-9,z+10.3),(6,14,.6),stone)
    for xx in (-3,3):cube('Rotunda projecting landing lip',(x+xx,y-9,z+10.8),(.22,14,.8),trim)
    cube('Rotunda projecting front volume',(x,y-13,z+5),(6,3,10),stone,True)
    stepped_tower('Rotunda tall rear block',x+7,y+10,z,7,8,31)
    stepped_tower('Rotunda stepped rear block',x+14,y+10,z,5,6,22)
    floor('Rotunda adjacent green terrace',x-17,y,z+1,10,19)
    for xx in (-21,-13):cube('Rotunda adjacent line',(x+xx,y,z+1.02),(.09,17,.015),ivory)
    finish_building(root,before)

def gatehouse(x,y):
    before=set(scene.objects);root=reference_building('front-gatehouse','m_s08_hddtc_background_a02b_manual__ca83fee478.webp',[915,0,1500,300],x,y,19,12);z=.45
    floor('Gatehouse entry floor',x,y,z,19,12)
    for side in (-1,1):
        cube('Gatehouse notched front pier',(x+side*6.5,y-4,z+4.5),(6,3,9),stone,True)
        cube('Gatehouse projecting vertical blade',(x+side*3.9,y-5.7,z+3.3),(1,1,6.6),stone)
        cube('Gatehouse side wall',(x+side*9,y+1,z+3),(.6,12,6),stone,True)
    cube('Gatehouse door lintel',(x,y-4,z+7.8),(7,3,2.4),stone,True)
    checker('Gatehouse short checker aisle',x,y+2,z+.02,2,8)
    for side in (-1,1):cube('Gatehouse inner vertical light',(x+side*4,y+4,z+4.6),(.5,.1,3),lightmat)
    cube('Gatehouse rear lintel',(x,y+5,z+7.5),(16,.7,1.4),stone)
    purple=mat('Source purple car paint',(.17,.10,.25),.36)
    cube('Gatehouse purple car body',(x,y-15,z+.65),(1.9,3.9,.9),purple,True)
    cube('Gatehouse purple car cabin',(x,y-14.85,z+1.35),(1.65,1.9,.65),purple)
    for yy in (-15.84,-13.86):cube('Gatehouse purple car windshield',(x,yy,z+1.4),(1.5,.055,.42),glass)
    for xx in (-1.0,1.0):
        for yy in (-16.1,-13.85):
            ob=cylinder('Gatehouse purple car wheel',x+xx,yy,z+.45,.38,.20,darktop,16);ob.rotation_euler.y=math.pi/2
    finish_building(root,before)

def library(x,y):
    before=set(scene.objects);root=reference_building('library-cutaway','m_s08_hddtc_background_a02b_manual__ca83fee478.webp',[1110,1250,1600,1610],x,y,19,12);z=height(x,y)+.4
    floor('Library open wooden floor',x,y,z,19,12)
    paving=[mat('Source library paving '+str(i),c) for i,c in enumerate([(.36,.33,.25),(.40,.37,.29),(.32,.31,.25)])]
    for row in range(8):
        for column in range(10):
            cube('Library rectangular paving tile',(x-8.55+column*1.9,y-5.25+row*1.5,z+.02),(1.87,1.47,.04),paving[(column+row*2)%3])
    cube('Library ochre back wall',(x,y+5.8,z+3.5),(19,.7,7),seatpad,True)
    for xx in (-9,-3,3,9):
        cube('Library pillar ochre square foot',(x+xx,y+5,z+.62),(1.3,1.5,1.24),seatframe)
        cylinder('Library pale round pillar',x+xx,y+5,z+4.1,.46,5.8,trim,32)
    cube('Library narrow roof canopy',(x,y+4,z+7.3),(20,5,.45),stone)
    for xx in (-6,0,6):
        cube('Library bookcase dark back',(x+xx,y+5.1,z+3),(4.3,.5,5.6),darktop)
        for dx in (-2.15,2.15):cube('Library bookcase side',(x+xx+dx,y+4.6,z+3),(.22,1.1,5.6),wood)
        for level in range(6):
            cube('Library bookcase shelf',(x+xx,y+4.6,z+.35+level*1.0),(4.4,1.1,.15),wood)
            if level<5:
                for b in range(13):
                    cube('Library visible book spine',(x+xx-1.85+b*.30,y+4.03,z+.73+level),(.18,.16,.55+(b%3)*.08),[wood,brass,glass,seatframe][b%4])
    cube('Library central black table',(x,y-1.8,z+1.4),(7,2.4,.3),darktop)
    for dx in (-2.6,2.6):cube('Library central table leg',(x+dx,y-1.8,z+.6),(.22,1.8,1.2),wood)
    for i in range(16):cube('Library table checker edge',(x-3.5+(i+.5)*7/16,y-3.03,z+1.35),(7/16,.035,.16),ivory if i%2 else black)
    pink=mat('Source pink rectangular frame',(.49,.17,.26))
    for i in range(3):
        ob=open_rectangular_frame('Library pink slanted open frame',x+(i-1)*.6,y-1.8,z+2.2,.5,1.9,.085,pink)
        ob.rotation_euler.x=math.radians(55);ob['observedPart']='pink-open-frame'
        for yy in (-.95,.95):
            cap=cube('Library frame pale rectangular end',(x+(i-1)*.6,y-1.8+yy*math.cos(math.radians(55)),z+2.2+yy*math.sin(math.radians(55))),(.54,.17,.12),ivory);cap.rotation_euler.x=math.radians(55)
    for dx,dy,w,d,h in [(4,12,9,8,13),(14,14,6,6,9),(20,3,7,7,10)]:
        cube('Library neighborhood plain block',(x+dx,y+dy,z+h/2),(w,d,h),stone,True)
        cube('Library neighborhood brown roof',(x+dx,y+dy,z+h+.08),(w,d,.18),wood)
    finish_building(root,before)

def open_rectangular_frame(name,x,y,z,w,d,thickness,material):
    outline=[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]
    inner=[(-w/2+.075,-d/2+.075),(w/2-.075,-d/2+.075),(w/2-.075,d/2-.075),(-w/2+.075,d/2-.075)]
    vs=[(xx,yy,zz) for zz in (-thickness/2,thickness/2) for contour in (outline,inner) for xx,yy in contour];fs=[]
    for i in range(4):
        j=(i+1)%4;fs.extend([(i,j,j+4,i+4),(i+8,i+12,j+12,j+8),(i,i+8,j+8,j),(i+4,j+4,j+12,i+12)])
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(material)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);ob.location=(x,y,z);return ob

def rounded_profile(name,x,y,z,w,d,thickness,material,rim=False,open_front=False):
    """Scalloped rounded silhouette visible in the source dormitory strip."""
    vs=[];fs=[];n=64
    for h in (0,thickness):
        for inset in ((0,.6) if rim else (0,)):
            for i in range(n):
                a=i*math.tau/n;c=math.cos(a);s=math.sin(a)
                xx=math.copysign(abs(c)**.5,c)*(w/2-inset);yy=math.copysign(abs(s)**.5,s)*(d/2-inset)
                if s>.15:yy+=.45*math.cos(a*8)
                vs.append((x+xx,y+yy,z+h))
    if rim:
        for i in range(n):
            if open_front and math.sin((i+.5)*math.tau/n)<-.25:continue
            j=(i+1)%n
            fs.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    else:
        fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(material)
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);return ob

def curved_dorm(x,y):
    before=set(scene.objects);root=reference_building('curved-dormitory','m_s08_hddtc_background_a04b_manual__21a953f5d2.webp',[1040,0,1830,615],x,y,34,24);z=height(x,y)+.4
    gold=mat('Source dorm ochre paving',(.40,.32,.15));cream=mat('Source dorm pale curved band',(.57,.57,.43));blue=mat('Source dorm teal blanket',(.065,.25,.27))
    rounded_profile('Curved dorm ochre paving island',x+3,y-2,z,39,32,.4,gold)
    rounded_profile('Curved dorm continuous dark windows',x,y,z+.5,25,20,12.5,darktop)
    for level in range(5):
        rounded_profile('Curved dorm scalloped horizontal floor',x,y,z+.8+level*2.7,25.7,20.7,.9,cream)
    rounded_profile('Curved dorm open rooftop floor',x,y,z+14.5,25.5,20.5,.4,gold)
    walk_surfaces.append({'x':x,'z':-y,'w':22,'d':17,'y':z+14.9})
    for level in range(4):rounded_profile('Curved dorm scalloped rim',x,y,z+15+level*2.05,26,21,.75,cream,True,True)
    bed(x-6,y+1,z+14.92,[1280,120,1365,225],teal=True,source='m_s08_hddtc_background_a04b_manual__21a953f5d2.webp')
    cylinder('Curved dorm standing lamp base',x-9,y-1,z+15.05,.4,.25,darktop,24)
    cylinder('Curved dorm standing lamp stem',x-9,y-1,z+16.4,.08,2.6,brass,16)
    ob=cylinder('Curved dorm standing lamp disc',x-9,y-1,z+17.7,.45,.16,cream,24);ob.rotation_euler.y=math.pi/2
    cube('Curved dorm low black rooftop object',(x-1,y-4,z+15.4),(1.5,.6,1),darktop)
    cube('Curved dorm small bedside hollow block',(x-9,y+3,z+15.6),(1.3,1.3,1.1),seatframe)
    cube('Curved dorm small bedside inset',(x-9,y+2.32,z+15.65),(.94,.02,.55),darktop)
    # The pale central contour is visible, but its in-game purpose is unknown.
    translucent=mat('Source pale translucent central contour',(.30,.49,.43),.35)
    shader=next(n for n in translucent.node_tree.nodes if n.type=='BSDF_PRINCIPLED');shader.inputs['Alpha'].default_value=.23
    translucent.surface_render_method='BLENDED';translucent.use_backface_culling=False
    vs=[];fs=[];segments=18
    for i in range(segments+1):
        t=i/segments;yy=y-8+t*16;xx=x-1.4+.95*math.sin(t*math.pi);top=z+15.1+3.8+3.0*t
        vs.extend([(xx,yy,z+15.1),(xx,yy,top)])
    for i in range(segments):fs.append((i*2,i*2+1,i*2+3,i*2+2))
    me=bpy.data.meshes.new('Observed dorm translucent central contour');me.from_pydata(vs,[],fs);me.materials.append(translucent)
    ob=bpy.data.objects.new('Observed dorm translucent central contour',me);scene.collection.objects.link(ob);ob['observedPart']='translucent-central-contour';ob['identificationScope']='Visible translucent contour, purpose unknown'
    # A dark curved enclosure with wooden steps is visible at the roof right.
    vs=[];fs=[]
    for h in (0,3.4):
        for r in (3.2,3.4):
            for i in range(25):
                a=-math.pi/2+i*math.pi/24;vs.append((x+8+r*math.cos(a),y-2+r*math.sin(a),z+15+h))
    for i in range(24):fs.extend([(i,i+1,i+51,i+50),(i+25,i+75,i+76,i+26),(i+50,i+51,i+76,i+75)])
    me=bpy.data.meshes.new('Source dorm dark curved enclosure');me.from_pydata(vs,[],fs);me.materials.append(darktop)
    ob=bpy.data.objects.new('Source dorm dark curved enclosure',me);scene.collection.objects.link(ob)
    for i in range(4):cube('Source dorm short timber step',(x+7.9,y-3.2+i*.75,z+15.12+i*.19),(2.1,.73,.24+i*.38),wood)
    for level in range(6):
        rounded_profile('Curved dorm narrow auxiliary tower',x+19,y+2,z+.7+level*2.7,7.5,10,.9,cream,True)
        for dx,dy in [(-3,0),(3,0),(0,-4.2),(0,4.2)]:cube('Curved dorm auxiliary thin vertical strut',(x+19+dx,y+2+dy,z+1.65+level*2.7),(.15,.15,2.3),brass)
    for i in range(20):
        a=i*math.tau/20;cylinder('Curved dorm top dark perforation',x+19+3.25*math.cos(a),y+2+4.6*math.sin(a),z+.7+5*2.7+.91,.10,.03,darktop,8)
    rounded_profile('Curved dorm small front court',x-13,y-15,z+.4,8,7,1.2,cream,True)
    for dx,dy,w,d in [(15,-12,6,3),(9,-16,3,2),(18,-16,6,5),(-7,-14,9,2)]:cube('Curved dorm dark paving inset',(x+dx,y+dy,z+.46),(w,d,.12),glass)
    # Bounding volumes describe opaque lower facade, not the open rooftop.
    colliders.append({'x':x,'z':-y,'w':23,'d':18,'height':14.4,'yMin':z})
    finish_building(root,before)

def orbital_platform(x,y):
    before=set(scene.objects);root=reference_building('orbital-platform','m_s08_hddtc_background_a02_manual__e4f2121375.webp',[0,1630,470,2048],x,y,26,26);z=height(x,y)+.4
    silver=mat('Source orbital silver',(.62,.68,.69),.24)
    next(n for n in silver.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Metallic'].default_value=.78
    cylinder('Orbital silver circular foundation',x,y,z+.6,12,.7,silver)
    cylinder('Orbital ochre stage',x,y,z+1.02,10.8,.15,seatpad)
    rounded_profile('Orbital silver enclosing rim',x,y,z+1.08,23,23,.35,silver,True)
    for dx,dy in [(-5,-4),(5,-4),(0,5)]:
        cube('Orbital globe stone plinth',(x+dx,y+dy,z+1.55),(1.8,1.8,1),trim)
        cylinder('Orbital globe short support',x+dx,y+dy,z+2.5,.23,1,silver,16)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=1.35,location=(x+dx,y+dy,z+3.8));ob=bpy.context.object;ob.name='Orbital silver globe';ob.data.materials.append(silver)
        for a in (0,math.pi*.7,math.pi*1.4):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=4,radius=.19,location=(x+dx+1.25*math.cos(a),y+dy+1.25*math.sin(a),z+3.8));bpy.context.object.name='Orbital dark globe aperture';bpy.context.object.data.materials.append(darktop)
    for dx in (-9,9):
        vs=[];fs=[]
        for i in range(49):
            a=i*math.pi/48
            for t in (-.35,.35):vs.append((x+dx+t,y+11*math.cos(a),z+1+9*math.sin(a)))
        for i in range(48):fs.append((i*2,i*2+1,i*2+3,i*2+2))
        me=bpy.data.meshes.new('Orbital curved silver arch');me.from_pydata(vs,[],fs);me.materials.append(silver)
        ob=bpy.data.objects.new('Orbital curved silver arch',me);scene.collection.objects.link(ob)
    cylinder('Orbital central silver pole',x,y,z+8,.16,14,silver,16)
    finish_building(root,before)

# Rebuild the visible central compound, including its distinctive auditorium.
x=-20;y=16;z=.45
floor('Central foundation plinth',x,y,z,50,33)
stair('Central entrance',x,-3,0,12,7,.45)
auditorium(x,y-3,z+6.4)
cube('Auditorium wallwash',(x,y+5.65,z+12.4),(13,.02,9),lightmat)
# The hall sits above a visible strip of narrow windows, not at ground level.
cube('Auditorium lower rear volume',(x,y+3,z+3.2),(17,10,6.4),stone,True)
cube('Auditorium lower facade sill',(x,y-8.7,z+.75),(17,.7,1.5),stone)
cube('Auditorium lower facade lintel',(x,y-8.7,z+5.5),(17,.7,1.8),stone)
for i in range(7):
    wx=x-7.2+i*2.4
    cube('Auditorium lower window '+str(i),(wx,y-8.67,z+3.25),(.85,.08,2.9),darktop)
    cube('Auditorium lower window pier',(wx+1.2,y-8.7,z+3.25),(1.4,.75,3.5),stone,True)
    cube('Auditorium lower window sill',(wx,y-9.1,z+2.1),(.85,.2,.15),trim)
for side in (-1,1):
    sx=x+side*18
    wing='Central '+('west' if side<0 else 'east')
    levels=[(6.4,'west-seat')] if side<0 else [(6.4,'east-lower-seat'),(12.8,'east-middle-desk'),(19.2,'east-upper-long-fixture')]
    for level,kind in levels:room(wing+' '+kind+' room',sx,y+2,z+level,11,12,5.7,kind)
    # A single tall, vertically channelled tower encloses each cutaway wing.
    # Hidden-side adaptation: retain a real gallery door through the thick
    # tower core at the first accessible room level.
    cube(wing+' Stepped tower rear lower',(sx,y+11,z+3.2),(12,5,6.4),stone,True)
    cube(wing+' Stepped tower rear upper',(sx,y+11,z+21.3),(12,5,23.8),stone,True)
    for dx in (-1,1):cube(wing+' rear door jamb',(sx+dx*3.95,y+11,z+7.9),(4.1,5,3),stone,True)
    cube(wing+' Stepped tower lower closed facade',(sx,y-4.1,z+3.1),(11,.75,6.2),stone,True)
    cap=12.8 if side<0 else 25.6
    cube(wing+' Stepped tower closed upper',(sx,y+2,z+(cap+33.2)/2),(11,12,33.2-cap),stone,True)
    cube(wing+' vertical recessed channel',(sx,y-4.08,z+(cap+33.2)/2),(1.05,.05,33.2-cap),joint)
    for xx in (-1,1):cube(wing+' vertical projecting blade',(sx+xx*2.6,y-4.6,z+(cap+33.2)/2),(3.9,1.6,33.2-cap),stone)
    cube(wing+' notched roof west',(sx-3.1,y+2,z+33.35),(4.8,12,.3),stone)
    cube(wing+' notched roof east',(sx+3.1,y+2,z+33.35),(4.8,12,.3),stone)
    for level in range(1,28):
        if level*1.2<6.4 or level*1.2>cap:cube(wing+' Facade course',(sx,y-4.94,z+level*1.2),(11,.025,.025),joint)
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
western_institution(-82,28)
roof_annex(34,38)
sports_terrace(88,37)
rotunda(96,-2)
gatehouse(-20,-12)
library(28,-44)
curved_dorm(-105,-35)
orbital_platform(-137,4)
# Open central lawn, monuments and castle staircase.
cube('Castle front lawn',(-20,-5,.15),(34,12,.1),grass)
for x,y in [(-55,30),(17,17),(111,24)]:cube('Reference stone monolith',(x,y,height(x,y)+5),(6,7,10),stone,True)

# Fir prototype matches the faceted foliage and taper in the official sandtable.
parts=[]
bpy.ops.mesh.primitive_cylinder_add(vertices=7,radius=.18,depth=2.8,location=(0,0,1.4));parts.append(bpy.context.object);parts[-1].data.materials.append(trunk)
for level in range(12):
    radius=2.1*(1-level/12.8)**.85*(.95+.07*math.sin(level*1.7))
    bpy.ops.mesh.primitive_cone_add(vertices=28,radius1=radius,radius2=radius*.17,depth=1.1,location=(0,0,1.1+level*.50))
    for v in bpy.context.object.data.vertices:
        a=math.atan2(v.co.y,v.co.x);factor=1+.13*math.sin(a*7+level*.8)+.055*math.cos(a*11+level)
        v.co.x*=factor;v.co.y*=factor
        if v.co.z<0:v.co.z+=.17*math.cos(a*7+level*.8)
    parts.append(bpy.context.object);parts[-1].data.materials.append(greens[0])
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();prototype=bpy.context.object;prototype.name='Fir prototype'
bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
canopies=[]
for color in greens:
    data=prototype.data.copy();data.materials[1]=color;canopies.append(data)
def near_road(x,y):
    for _,coords,width in road_routes:
        for (ax,ay),(bx,by) in zip(coords,coords[1:]):
            dx=bx-ax;dy=by-ay;t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
            if math.hypot(x-ax-t*dx,y-ay-t*dy)<width/2+1.3:return True
    return False

for i in range(1450):
    x=random.uniform(-153,153);y=random.uniform(-72,72)
    if any(abs(x-l['x'])<l['w']/2+3 and abs(y+l['z'])<l['d']/2+3 for l in landmarks):continue
    if (7<x<57 and -65<y<-26) or (-106<x<-60 and 29<y<47) or (70<x<111 and 33<y<56):continue
    if -24<x<-9 and 30<y<46:continue
    if near_road(x,y):continue
    ob=bpy.data.objects.new('Fir %04d'%i,random.choices(canopies,weights=[.62,.24,.11,.03])[0]);scene.collection.objects.link(ob)
    ob.location=(x,y,height(x,y));sc=random.uniform(.60,1.18);ob.scale=(sc,sc,sc*random.uniform(.95,1.25));ob.rotation_euler.z=random.random()*math.tau
bpy.data.objects.remove(prototype,do_unlink=True)
# Continuous mountain front: official cliff/snow texture, no generic spheres.
mountain=mat('Original a01 cliff and snow',(1,1,1))
tex=mountain.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(os.path.join(ROOT,'public/assets/all/m_s08_hddtc_background_a01_manual__0e4ca30c84.webp'),check_existing=True)
mountain.node_tree.links.new(tex.outputs['Color'],next(n for n in mountain.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'])
vs=[];fs=[];cols=128;rows=12
for j in range(rows+1):
    t=j/rows;yy=50+30*t
    for i in range(cols+1):
        xx=-160+320*i/cols
        vs.append((xx,yy,height(xx,yy)))
for j in range(rows):
    for i in range(cols):
        a=j*(cols+1)+i;fs.extend([(a,a+1,a+cols+2),(a,a+cols+2,a+cols+1)])
me=bpy.data.meshes.new('Reference continuous northern massif');me.from_pydata(vs,[],fs);me.materials.append(mountain);uv=me.uv_layers.new()
for p in me.polygons:
    for li in p.loop_indices:
        v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=((v.x+160)/320,.72+(v.y-50)/30*.28)
ob=bpy.data.objects.new('Reference continuous northern massif',me);scene.collection.objects.link(ob);ob['sourceFeature']='northern-massif'

bpy.ops.object.camera_add(location=(26,-103,109));camera=bpy.context.object;camera.name='World overview'
camera.rotation_euler=(Vector((-20,16,13))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=124;scene.camera=camera
bpy.ops.object.light_add(type='SUN',location=(0,-30,80));sun=bpy.context.object;sun.name='Overcast winter sun';sun.data.energy=1.8;sun.data.angle=math.radians(16);sun.rotation_euler=(.4,-.5,-.3)
for lx,ly,lz in [(-20,17,17),(-38,18,11),(-2,18,11),(-82,28,11)]:
    bpy.ops.object.light_add(type='AREA',location=(lx,ly,lz));light=bpy.context.object;light.name='Interior indirect light';light.data.energy=400;light.data.color=(.83,.97,.83);light.data.shape='DISK';light.data.size=7
scene.world=bpy.data.worlds.new('Winter sky');scene.world.use_nodes=True
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Color'].default_value=(.49,.59,.63,1)
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Strength'].default_value=.65
scene.render.engine='BLENDER_EEVEE';scene.view_settings.view_transform='AgX'
scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'

os.makedirs(os.path.join(ROOT,'public/models'),exist_ok=True)
with open(os.path.join(ROOT,'public/data/world.json'),'w',encoding='utf-8') as f:
    json.dump({'bounds':{'minX':-155,'maxX':155,'minZ':-75,'maxZ':75},'colliders':colliders,'walkSurfaces':walk_surfaces,'landmarks':landmarks,'roads':[{'points':[[px,-py] for px,py in coords],'width':width} for _,coords,width in road_routes],'destinations':{'castle':[-20,4,32],'east':[34,4,-23],'forest':[-70,4,23]},'spawn':[0,2,35], 'model':'models/tigers-world.glb','revision':4,'sourceScope':'Central openings and eight peripheral silhouettes traced from original atlases; depth, ground positions, vegetation, mountain geometry and hidden faces remain estimated'},f,ensure_ascii=False)
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT,'public/models/tigers-world.glb'),export_format='GLB',use_active_scene=True,export_cameras=False,export_lights=False,export_extras=True)

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
inspection=bpy.data.images.get('Reference inspection')
if inspection:bpy.data.images.remove(inspection)
bpy.ops.file.pack_all()
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
        area.spaces.active.shading.type='MATERIAL'
previous_versions=bpy.context.preferences.filepaths.save_version;bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'blender/tigers-world.blend'))
finally:bpy.context.preferences.filepaths.save_version=previous_versions
print('Created world:',len(scene.objects),'objects; GLB and editable .blend saved')
