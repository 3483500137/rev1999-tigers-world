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
seatframe=mat('Reference ochre seat frame',(.36,.26,.095),.72)
seatpad=mat('Reference olive ivory seat inset',(.52,.56,.35),.9)
darktop=mat('Reference dark long fixture',(.055,.065,.052),.7)
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
p.inputs['Emission Color'].default_value=(0.67,0.79,0.52,1);p.inputs['Emission Strength'].default_value=1.4

# Original atlas patch applied to reconstructed limestone walls, without recolouring.
atlas=bpy.data.images.load(os.path.join(ROOT,'public/assets/all/m_s08_hddtc_background_a03_manual__48c359e04b.webp'))
texture=stone.node_tree.nodes.new('ShaderNodeTexImage');texture.image=atlas
stone.node_tree.links.new(texture.outputs['Color'],next(n for n in stone.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'])
# Foliage palette sampled at known pixels of the unchanged source atlas.
pixels=atlas.pixels[:]
for m,(px,py) in zip(greens,[(731,962),(630,701),(660,575),(1280,981)]):
    i=((2047-py)*2048+px)*4
    colors=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in pixels[i:i+3]]
    next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(*colors,1)
    m['sourcePixel']=[px,py]

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
    root['shape']='high-backed-seat' if kind.endswith('seat') else ('crosswise-desk' if kind.endswith('desk') else 'long-dark-fixture')
    before=set(scene.objects)
    if kind.endswith('seat'):
        # The visible object has rigid raised sides/back and an olive seat,
        # rather than a white mattress, pillow or blanket.
        cube(kind+' rigid seat',(x,y,z+.85),(2.8,3.7,.4),seatpad)
        cube(kind+' front ochre rail',(x,y-1.9,z+.85),(3.2,.28,.75),seatframe)
        cube(kind+' tall back',(x,y+1.75,z+1.85),(3.2,.35,2.55),seatframe)
        cube(kind+' dark back inset',(x,y+1.55,z+1.92),(2.65,.04,1.5),wood)
        for side in (-1,1):
            cube(kind+' raised side',(x+side*1.48,y,z+1.22),(.25,3.7,.55),seatframe)
            for yy in (-1.65,1.65):cube(kind+' square support',(x+side*1.4,y+yy,z+.4),(.28,.28,.8),wood)
    elif kind.endswith('desk'):
        cube(kind+' crosswise top',(x,y,z+1.42),(6,2.4,.25),seatframe)
        cube(kind+' dark inset',(x,y,z+1.56),(4.3,1.35,.035),wood)
        for side in (-1,1):
            cube(kind+' panel support',(x+side*2.4,y,z+.66),(.3,1.9,1.3),wood)
            cube(kind+' rear seat',(x+side*1.1,y+1.65,z+.55),(.9,.9,.18),wood)
            cube(kind+' rear back',(x+side*1.1,y+2.02,z+1.13),(.9,.12,1.3),wood)
        cube(kind+' pale small object',(x-.7,y+.15,z+1.63),(.75,.5,.12),ivory)
        cube(kind+' green small object',(x+.3,y+.2,z+1.69),(.45,.38,.25),glass)
    else:
        cube(kind+' long dark top',(x,y,z+1.1),(3.5,7.8,.22),darktop)
        cube(kind+' narrow timber inset',(x,y,z+1.23),(1.2,7.6,.03),wood)
        for side in (-1,1):
            cube(kind+' slim edge',(x+side*1.65,y,z+1.25),(.11,7.8,.08),brass)
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
        me=bpy.data.meshes.new('Auditorium semicircular seating');me.from_pydata(vs,[],fs);me.materials.append(roof)
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
            uv.data[li].uv=(.700+(v.x-x+7)/14*.027,.870+(v.y-y+9)/14*.04)
    ob=bpy.data.objects.new('Auditorium reference roof silhouette',me);scene.collection.objects.link(ob)
    for side in (-1,1):
        cube('Auditorium rear roof block',(x+side*3.5,y+7,z+14.6),(5.5,2.7,1.1),stone)
        for yy in (-7,5):cube('Auditorium brass roof pin',(x+side*8,y+yy,z+14),(.12,.12,1.3),brass)
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
auditorium(x,y-3,z+6.4)
cube('Auditorium wallwash',(x,y+5.65,z+12.4),(5.8,.02,7),lightmat)
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
for level in range(7):
    radius=2.1*(1-level/7.6)**.85
    bpy.ops.mesh.primitive_cone_add(vertices=21,radius1=radius,radius2=radius*.10,depth=1.45,location=(0,0,1.25+level*.82))
    for v in bpy.context.object.data.vertices:
        a=math.atan2(v.co.y,v.co.x);factor=1+.18*math.sin(a*7+level*.8)
        v.co.x*=factor;v.co.y*=factor
        if v.co.z<0:v.co.z+=.24*math.cos(a*7+level*.8)
    parts.append(bpy.context.object);parts[-1].data.materials.append(greens[0])
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();prototype=bpy.context.object;prototype.name='Fir prototype'
bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
canopies=[]
for color in greens:
    data=prototype.data.copy();data.materials[1]=color;canopies.append(data)
for i in range(1050):
    x=random.uniform(-153,153);y=random.uniform(-72,72)
    if any(abs(x-bx)<bw and abs(y-by)<bd for bx,by,bw,bd in [(-20,16,30,23),(66,17,18,18),(109,42,14,13),(-105,2,18,16),(40,-40,19,15)]):continue
    if -24<x<-9 and 30<y<46:continue
    if abs(y-(-19-.09*x))<4 or (abs(x+20)<5 and -15<y<45):continue
    ob=bpy.data.objects.new('Fir %04d'%i,random.choices(canopies,weights=[.62,.24,.11,.03])[0]);scene.collection.objects.link(ob)
    ob.location=(x,y,height(x,y));sc=random.uniform(.95,1.7);ob.scale=(sc,sc,sc*random.uniform(.95,1.25));ob.rotation_euler.z=random.random()*math.tau
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

bpy.ops.object.camera_add(location=(2,-105,72));camera=bpy.context.object;camera.name='World overview'
camera.rotation_euler=(Vector((-20,16,13))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=112;scene.camera=camera
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
    json.dump({'bounds':{'minX':-155,'maxX':155,'minZ':-75,'maxZ':75},'colliders':colliders,'walkSurfaces':walk_surfaces,'spawn':[0,2,35], 'model':'models/tigers-world.glb','revision':3,'sourceScope':'Central fixtures and visible openings traced from a03; remaining world still reference-guided adaptation'},f,ensure_ascii=False)
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
