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
test('rebuilt castle exports auditorium, stepped towers, furniture and adapted back passages',async()=>{
  const b=await readFile('public/models/tigers-world.glb');const j=JSON.parse(b.toString('utf8',20,20+b.readUInt32LE(12)));const names=j.nodes.map(n=>n.name||'').join('\n');
  for(const feature of ['Auditorium','Stepped tower','Rear passage','Stair flight','Room bed','Facade course'])assert.ok(names.includes(feature),`Missing ${feature}`);
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
