import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {canOccupy,constrainPosition,terrainHeight} from '../src/movement.js';
import * as THREE from 'three';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
test('walking cannot cross solid castle walls',()=>{const c=[{x:0,z:0,w:10,d:2}];assert.equal(canOccupy(0,.5,c),false);assert.equal(canOccupy(0,4,c),true);});
test('walking and flying remain in world bounds and above terrain',()=>{const w={bounds:{minX:-155,maxX:155,minZ:-75,maxZ:75}};let p=constrainPosition({x:900,z:-900,y:-10},w,true);assert.equal(p.x,155);assert.equal(p.z,-75);assert.equal(p.y,terrainHeight(155,-75)+1.8);p=constrainPosition({x:0,z:0,y:1000},w);assert.equal(p.y,90);});
test('all original textures match pinned upstream source hashes',async()=>{const m=JSON.parse(await readFile('public/data/sources.json'));assert.equal(m.files.length,11);for(const f of m.files){const b=await readFile('public/'+f.path);assert.equal(createHash('sha256').update(b).digest('hex'),f.sha256);}});
test('Blender GLB is valid and contains genuine geometry',async()=>{const b=await readFile('public/models/tigers-world.glb');assert.equal(b.toString('ascii',0,4),'glTF');assert.equal(b.readUInt32LE(4),2);assert.equal(b.readUInt32LE(8),b.length);const j=JSON.parse(b.toString('utf8',20,20+b.readUInt32LE(12)));assert.ok(j.meshes.length>20);assert.ok(j.nodes.length>500);});
test('chapter contains all 23 original scenes and valid UV faces',async()=>{const s=JSON.parse(await readFile('public/data/chapter-104.json'));assert.equal(s.length,23);for(const scene of s)for(const d of scene.draws)for(const face of d.faces)for(const [v,u] of face){assert.ok(d.vertices[v]);assert.ok(d.uv[u]);}});
test('walking follows accessible room floors without jumping to upstairs floors',()=>{
  const w={bounds:{minX:-155,maxX:155,minZ:-75,maxZ:75},walkSurfaces:[{x:0,z:0,w:8,d:8,y:.25},{x:0,z:0,w:8,d:8,y:9}]};
  const p=constrainPosition({x:0,z:0,y:2},w,true);assert.equal(p.y,2.05);
});
test('walking follows the adapted staircase ramp',()=>{
  const w={bounds:{minX:-155,maxX:155,minZ:-75,maxZ:75},walkSurfaces:[{x:0,z:0,w:4,d:8,y:1,slopeZ:.5}]};
  const p=constrainPosition({x:0,z:1,y:3.2},w,true);assert.equal(p.y,3.3);
});

test('walking follows the textured northern massif instead of sinking beneath it',()=>{
  assert.ok(Math.abs(terrainHeight(0,-80)-29.555555555555557)<1e-9);
  assert.equal(terrainHeight(0,-48),1.6666666666666665);
});
test('rebuilt castle exports auditorium, stepped towers, furniture and adapted back passages',async()=>{
  const b=await readFile('public/models/tigers-world.glb');const j=JSON.parse(b.toString('utf8',20,20+b.readUInt32LE(12)));const names=j.nodes.map(n=>n.name||'').join('\n');
  for(const feature of ['Auditorium','Stepped tower','Rear passage','Stair flight','Facade course'])assert.ok(names.includes(feature),`Missing ${feature}`);
});

test('central cutaway rooms preserve the distinct source fixtures instead of duplicated beds',async()=>{
  const b=await readFile('public/models/tigers-world.glb');const j=JSON.parse(b.toString('utf8',20,20+b.readUInt32LE(12)));
  const items=j.nodes.filter(n=>n.extras?.referenceFixture);
  assert.equal(items.length,4,'Source shows one west opening and three east openings');
  assert.deepEqual(items.map(n=>n.extras.referenceFixture).sort(),['east-lower-seat','east-middle-desk','east-upper-long-fixture','west-seat']);
  assert.ok(items.every(n=>n.extras.sourceTexture==='assets/all/m_s08_hddtc_background_a03_manual__48c359e04b.webp'&&n.extras.sourcePixels?.length===4));
  assert.equal(j.nodes.filter(n=>/Central .* room floor$/.test(n.name||'')).length,4);
  const east=items.filter(n=>n.extras.referenceFixture.startsWith('east'));
  assert.equal(new Set(east.map(n=>n.extras.shape)).size,3,'Distinct rooms must not reuse the same furniture shape');
});

test('central hall preserves the visible lower window band, split roof and tower channels',async()=>{
  const b=await readFile('public/models/tigers-world.glb');const j=JSON.parse(b.toString('utf8',20,20+b.readUInt32LE(12)));const names=j.nodes.map(n=>n.name||'');
  assert.equal(names.filter(n=>/^Auditorium lower window \d+$/.test(n)).length,7);
  assert.ok(names.some(n=>n.includes('Auditorium reference roof silhouette')));
  assert.equal(names.filter(n=>/^Central .* vertical recessed channel$/.test(n)).length,2);
});

test('auditorium uses the source hanging circular emblem instead of an invented crescent',async()=>{
  const b=await readFile('public/models/tigers-world.glb');const j=JSON.parse(b.toString('utf8',20,20+b.readUInt32LE(12)));
  const rings=j.nodes.filter(n=>n.extras?.sourceFeature==='auditorium-ring');
  assert.equal(rings.length,2);
  for(const n of rings){const p=j.meshes[n.mesh].primitives[0];assert.ok(j.accessors[p.attributes.POSITION].count>=90);}
  assert.ok(j.nodes.some(n=>n.extras?.sourceFeature==='auditorium-pendant'));
});

test('northern mountains reuse the original cliff atlas on continuous geometry, not generic boulders',async()=>{
  const b=await readFile('public/models/tigers-world.glb');const j=JSON.parse(b.toString('utf8',20,20+b.readUInt32LE(12)));
  const n=j.nodes.find(n=>n.extras?.sourceFeature==='northern-massif');assert.ok(n);
  const p=j.meshes[n.mesh].primitives[0];assert.ok(j.accessors[p.attributes.POSITION].count>400);assert.ok(p.attributes.TEXCOORD_0!==undefined);
  const mat=j.materials[p.material],t=j.textures[mat.pbrMetallicRoughness.baseColorTexture.index];
  const i=j.images[t.extensions?.EXT_texture_webp?.source??t.source];assert.ok(i.name.includes('background_a01'));
  assert.equal(j.nodes.filter(n=>/Snow granite ridge/.test(n.name||'')).length,0);
});
test('collision ignores walls above the walking floor but keeps same-level walls solid',()=>{
  const upper=[{x:0,z:0,w:4,d:1,yMin:6,height:5}];
  assert.equal(canOccupy(0,0,upper,.65,0),true);
  assert.equal(canOccupy(0,0,upper,.65,7),false);
});
test('the actual rear staircase has an unobstructed doorway into the gallery',async()=>{
  const w=JSON.parse(await readFile('public/data/world.json'));
  assert.equal(canOccupy(-38,-24,w.colliders,.65,6.85),true);
});
test('the exterior rear stair is walkable without passing through bedroom ceilings',async()=>{
  const w=JSON.parse(await readFile('public/data/world.json'));
  assert.equal(constrainPosition({x:-13,z:-37,y:5.45},w,true).y,5.45);
  assert.equal(canOccupy(-13,-37,w.colliders,.65,3.65),true);
});
test('runtime batching reduces architectural draws without losing their world positions',async()=>{
  const text=await readFile('src/main.js','utf8');
  const code=text.slice(text.indexOf('function batchTrees('),text.indexOf('async function start('));
  const batch=new Function('THREE','mergeGeometries',code+'; return batchTrees;')(THREE,mergeGeometries);
  const root=new THREE.Group();root.position.x=10;
  const material=new THREE.MeshStandardMaterial();
  for(let i=0;i<12;i++){const wall=new THREE.Mesh(new THREE.BoxGeometry(),material);wall.position.set(i,0,0);root.add(wall);}
  batch(root);const meshes=[];root.traverse(o=>{if(o.isMesh)meshes.push(o);});assert.equal(meshes.length,1);
  meshes[0].geometry.computeBoundingBox();assert.equal(meshes[0].geometry.boundingBox.min.x,-.5);assert.equal(meshes[0].geometry.boundingBox.max.x,11.5);
});
test('fir instancing accepts the sanitized names emitted by GLTFLoader',async()=>{
  const text=await readFile('src/main.js','utf8');const code=text.slice(text.indexOf('function batchTrees('),text.indexOf('async function start('));
  const batch=new Function('THREE','mergeGeometries',code+'; return batchTrees;')(THREE,mergeGeometries);
  const root=new THREE.Group(),geometry=new THREE.BoxGeometry(),material=new THREE.MeshStandardMaterial();
  for(let i=0;i<4;i++){const group=new THREE.Group();group.name='Fir_'+i;group.position.x=i;group.add(new THREE.Mesh(geometry,material));root.add(group);}
  batch(root);const instances=[];root.traverse(o=>{if(o.isInstancedMesh)instances.push(o);});assert.equal(instances.length,1);assert.equal(instances[0].count,4);
});

test('peripheral buildings have individually traced silhouettes rather than repeated bedroom templates',async()=>{
  const b=await readFile('public/models/tigers-world.glb');const j=JSON.parse(b.toString('utf8',20,20+b.readUInt32LE(12)));
  const features=new Map(j.nodes.filter(n=>n.extras?.referenceBuilding).map(n=>[n.extras.referenceBuilding,n]));
  for(const id of ['western-institution','roof-bedroom-annex','sports-terrace','rotunda','front-gatehouse','library-cutaway','curved-dormitory','orbital-platform']){
    assert.ok(features.has(id),`Missing reference building ${id}`);
    assert.equal(features.get(id).extras.sourcePixels.length,4);
    assert.ok(features.get(id).extras.sourceTexture.startsWith('assets/all/'));
  }
  const names=j.nodes.map(n=>n.name||'');
  for(const part of ['Table tennis net','Rotunda central drum','Library bookcase','Gatehouse purple car','Annex blue orb','Curved dorm scalloped rim','Orbital silver globe'])assert.ok(names.some(n=>n.includes(part)),`Missing ${part}`);
  assert.ok(!names.some(n=>/Eastern residence|North lookout|Western greenhouse/.test(n)));
});

test('navigation and reference landmarks share the actual exported building locations',async()=>{
  const w=JSON.parse(await readFile('public/data/world.json'));
  assert.equal(w.revision,4);assert.ok(w.landmarks.length>=7);
  assert.equal(w.landmarks.find(l=>l.id==='sports-terrace').x,88);
  assert.equal(w.landmarks.find(l=>l.id==='roof-bedroom-annex').x,34);
  assert.ok(w.landmarks.every(l=>l.w>0&&l.d>0));
  assert.ok(w.destinations.east&&w.destinations.castle&&w.destinations.forest);
});

async function exportedScene(){const b=await readFile('public/models/tigers-world.glb');return JSON.parse(b.toString('utf8',20,20+b.readUInt32LE(12)));}
function descendants(j,root){const result=[];for(const i of root.children||[]){const n=j.nodes[i];result.push(n,...descendants(j,n));}return result;}

test('the middle opening has one observed rear backrest, not two guessed chairs or invented desktop objects',async()=>{
  const j=await exportedScene(),root=j.nodes.find(n=>n.extras?.referenceFixture==='east-middle-desk');
  const parts=descendants(j,root);
  assert.equal(parts.filter(n=>n.name?.includes('rear back')).length,1);
  assert.equal(parts.filter(n=>/pale small object|green small object/.test(n.name||'')).length,0);
  assert.ok(parts.some(n=>n.extras?.observedPart==='raised-inset-panel'));
});

test('library display preserves three open pink frame shapes instead of a flower cluster',async()=>{
  const j=await exportedScene(),root=j.nodes.find(n=>n.extras?.referenceBuilding==='library-cutaway'),parts=descendants(j,root);
  assert.equal(parts.filter(n=>/flower cluster/.test(n.name||'')).length,0);
  assert.equal(parts.filter(n=>n.extras?.observedPart==='pink-open-frame').length,3);
  for(const n of parts.filter(n=>n.extras?.observedPart==='pink-open-frame')){
    const primitive=j.meshes[n.mesh].primitives[0],positions=j.accessors[primitive.attributes.POSITION];
    assert.ok(positions.count>=16,'Open frames need an inner boundary, not a solid cuboid');
  }
});

test('only clearly observed bedrooms contain beds, each with the source two-pillow arrangement',async()=>{
  const j=await exportedScene(),beds=j.nodes.filter(n=>n.extras?.confirmedSourceBed);
  assert.equal(beds.length,4);for(const b of beds){
    const parts=descendants(j,b);assert.equal(parts.filter(n=>n.extras?.observedPart==='pillow').length,2);
    assert.ok(b.extras.sourcePixels?.length===4&&b.extras.sourceTexture);
  }
  for(const fixture of j.nodes.filter(n=>n.extras?.referenceFixture))assert.equal(descendants(j,fixture).filter(n=>n.extras?.confirmedSourceBed).length,0);
});

test('dorm preserves the visible translucent central sheet rather than leaving the roof empty',async()=>{
  const j=await exportedScene(),root=j.nodes.find(n=>n.extras?.referenceBuilding==='curved-dormitory');
  const part=descendants(j,root).find(n=>n.extras?.observedPart==='translucent-central-contour');assert.ok(part);
  const material=j.materials[j.meshes[part.mesh].primitives[0].material];assert.equal(material.alphaMode,'BLEND');
});

test('masonry uses the inspected grey wall region rather than the warm roof patch',async()=>{
  const b=await readFile('public/models/tigers-world.glb'),j=await exportedScene(),mi=j.materials.findIndex(m=>m.name?.startsWith('Foundation limestone')),m=j.materials[mi];
  assert.deepEqual(m.extras?.sourcePixels,[900,1215,943,1290]);
  assert.ok(m.pbrMetallicRoughness.baseColorTexture);
  let points=0;const binStart=28+b.readUInt32LE(12);
  for(const mesh of j.meshes)for(const p of mesh.primitives)if(p.material===mi){
    const a=j.accessors[p.attributes.TEXCOORD_0];assert.ok(a,'Masonry must have actual source UVs');
    const v=j.bufferViews[a.bufferView],offset=binStart+(v.byteOffset||0)+(a.byteOffset||0);
    for(let i=0;i<a.count;i++){
      const at=offset+i*(v.byteStride||8),u=b.readFloatLE(at),t=b.readFloatLE(at+4);
      // glTF texture v runs downward; only the inspected source patch is allowed.
      assert.ok(u>=900/2048-.0001&&u<=943/2048+.0001&&t>=1215/2048-.0001&&t<=1290/2048+.0001,`Unexpected masonry UV ${u},${t}`);points++;
    }
  }
  assert.ok(points>1000,'Inspect the exported geometry, not just metadata');
});

test('bed linen does not intersect its mattress and create invented white holes',async()=>{
  const b=await readFile('public/models/tigers-world.glb'),j=await exportedScene(),binStart=28+b.readUInt32LE(12);
  const covers=j.nodes.filter(n=>n.name?.startsWith('Observed creased bed linen'));assert.equal(covers.length,4);
  for(const n of covers){
    const a=j.accessors[j.meshes[n.mesh].primitives[0].attributes.POSITION],v=j.bufferViews[a.bufferView],offset=binStart+(v.byteOffset||0)+(a.byteOffset||0);
    for(let i=0;i<a.count;i++){
      const at=offset+i*(v.byteStride||12),y=b.readFloatLE(at+4),z=b.readFloatLE(at+8);
      if(z<=2.115)assert.ok(y>.8351,`${n.name} intersects mattress at ${y},${z}`);
    }
  }
});
