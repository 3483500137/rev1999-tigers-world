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
