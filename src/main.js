import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
import {canOccupy,constrainPosition,terrainHeight} from './movement.js';
import './style.css';

const $=s=>document.querySelector(s), canvas=$('#world');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.75)); renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.AgXToneMapping;renderer.toneMappingExposure=1.0;
renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const scene=new THREE.Scene();scene.background=new THREE.Color('#aebfc2');scene.fog=new THREE.FogExp2('#aebfc2',.0019);
const camera=new THREE.PerspectiveCamera(48,1,.1,650);camera.position.set(26,98,103);
const orbit=new OrbitControls(camera,canvas);orbit.target.set(-20,11,-16);orbit.enableDamping=true;orbit.minDistance=5;orbit.maxDistance=240;orbit.maxPolarAngle=Math.PI*.49;
const hemi=new THREE.HemisphereLight('#d8e5ec','#45543b',1.65);scene.add(hemi);
const sun=new THREE.DirectionalLight('#e3e9d8',2.3);sun.position.set(-70,100,60);sun.castShadow=true;
sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-95,right:95,top:95,bottom:-95,near:1,far:280});sun.shadow.bias=-.0003;sun.shadow.normalBias=.035;scene.add(sun);
for(const [x,y,z] of [[-20,17,-17],[-38,11,-18],[-2,11,-18],[-2,17.4,-18],[-82,11,-28]]){const light=new THREE.PointLight('#cee4bd',85,20,2);light.position.set(x,y,z);scene.add(light);}
let world,chapters,worldGroup,originalGroup=new THREE.Group(),sourceMode=false,mode='overview',episode=0,ready=false;
let yaw=0,pitch=0,uiHidden=false,lastPointer=null,transition=null;
const keys=new Set(),clock=new THREE.Clock(),up=new THREE.Vector3(0,1,0),pointer=new THREE.Vector2();
const textureLoader=new THREE.TextureLoader(),textureCache=new Map();
scene.add(originalGroup);originalGroup.visible=false;
function resize(){renderer.setSize(innerWidth,innerHeight);camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();}
addEventListener('resize',resize);resize();
function toast(message){$('#toast').textContent=message;$('#toast').hidden=false;setTimeout(()=>$('#toast').hidden=true,3500);}
async function json(path){const r=await fetch(path);if(!r.ok)throw Error(`无法读取 ${path} (${r.status})`);return r.json();}
function batchTrees(root){
  const batches=new Map();const remove=[];root.updateMatrixWorld(true);const inverse=new THREE.Matrix4().copy(root.matrixWorld).invert();
  root.traverse(o=>{if(o.isMesh && /^Fir[ _]/.test(o.parent?.name||'')){const k=o.geometry.uuid+'|'+o.material.uuid;if(!batches.has(k))batches.set(k,[]);batches.get(k).push(o);remove.push(o);}});
  for(const objects of batches.values()){const first=objects[0],mesh=new THREE.InstancedMesh(first.geometry,first.material,objects.length);objects.forEach((o,i)=>mesh.setMatrixAt(i,new THREE.Matrix4().multiplyMatrices(inverse,o.matrixWorld)));mesh.instanceMatrix.needsUpdate=true;mesh.name='Instanced fir forest';root.add(mesh);}
  remove.forEach(o=>o.removeFromParent());
  const staticBatches=new Map();root.updateMatrixWorld(true);
  root.traverse(o=>{if(!o.isMesh||o.isInstancedMesh||o.isSkinnedMesh||Array.isArray(o.material)||o.material.transparent)return;
    const key=o.material.uuid+'|'+Object.keys(o.geometry.attributes).sort().join(',');
    if(!staticBatches.has(key))staticBatches.set(key,[]);staticBatches.get(key).push(o);
  });
  for(const objects of staticBatches.values()){
    if(objects.length<2)continue;
    const parts=objects.map(o=>{const g=o.geometry.index?o.geometry.toNonIndexed():o.geometry.clone();g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(inverse,o.matrixWorld));return g;});
    const geometry=mergeGeometries(parts,false);parts.forEach(g=>g.dispose());if(!geometry)continue;
    const mesh=new THREE.Mesh(geometry,objects[0].material);mesh.name='Batched reference architecture';root.add(mesh);objects.forEach(o=>o.removeFromParent());
  }
}
async function start(){
  [world,chapters]=await Promise.all([json('data/world.json'),json('data/chapter-104.json')]);
  const gltf=await new GLTFLoader().loadAsync(world.model,e=>{if(e.total)$('#load-status').textContent=`正在展开林地… ${Math.round(e.loaded/e.total*100)}%`;});
  worldGroup=gltf.scene;batchTrees(worldGroup);worldGroup.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;if(o.material.map)o.material.map.anisotropy=Math.min(renderer.capabilities.getMaxAnisotropy(),8);}});scene.add(worldGroup);
  chapters.forEach((s,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${String(s.number).padStart(2,'0')} · ${s.title}`;$('#episodes').append(o);});
  await changeEpisode(0);ready=true;$('#loading').hidden=true;document.body.classList.add('ready');
}
async function getTexture(path){if(!textureCache.has(path))textureCache.set(path,textureLoader.loadAsync(path).then(t=>{t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=Math.min(renderer.capabilities.getMaxAnisotropy(),8);return t;}));return textureCache.get(path);}
let episodeToken=0;
async function changeEpisode(index){
  episode=(index+chapters.length)%chapters.length;const s=chapters[episode],token=++episodeToken;
  $('#episode-number').textContent=`04 / ${String(s.number).padStart(2,'0')} · ${s.date}`;
  $('#episode-title').textContent=s.title;$('#episode-description').textContent=s.description;$('#episodes').value=episode;
  if(!sourceMode){return;}
  const textures=await Promise.all([...new Set(s.draws.map(d=>d.texture))].map(async p=>[p,await getTexture(p)]));
  if(token!==episodeToken)return;const map=new Map(textures);
  for(const o of [...originalGroup.children]){o.geometry.dispose();o.material.dispose();originalGroup.remove(o);}
  s.draws.forEach((draw,index)=>{
    const positions=[],uv=[];
    for(const face of draw.faces)for(let k=1;k<face.length-1;k++)for(const c of [face[0],face[k],face[k+1]]){
      const v=draw.vertices[c[0]],t=draw.uv[c[1]];positions.push(v[0]-52,v[1]+17,(4.1-v[2])*.01);uv.push(t[0],t[1]);
    }
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.computeVertexNormals();
    const m=new THREE.MeshBasicMaterial({map:map.get(draw.texture),transparent:true,side:THREE.DoubleSide,depthTest:false,depthWrite:false,toneMapped:false});
    const mesh=new THREE.Mesh(g,m);mesh.renderOrder=index;originalGroup.add(mesh);
  });
  camera.position.set(s.center[0]-52,s.center[1]+17,23);orbit.target.set(s.center[0]-52,s.center[1]+17,0);orbit.update();
}
function directionFromCamera(){const e=new THREE.Euler().setFromQuaternion(camera.quaternion,'YXZ');yaw=e.y;pitch=e.x;}
function setMode(next,lock=false){
  if(sourceMode && next!=='overview'){toggleSource(false);}
  mode=next;transition=null;keys.clear();orbit.enabled=mode==='overview';
  if(mode!=='overview'){
    if(camera.position.y>35 || camera.position.length()>220)camera.position.set(0,mode==='walk'?2:20,35);
    if(mode==='walk')camera.position.y=constrainPosition(camera.position,world,true).y;
    camera.lookAt(-20,mode==='walk'?3:15,-10);directionFromCamera();
    if(lock && matchMedia('(pointer:fine)').matches)canvas.requestPointerLock?.()?.catch(()=>{});
  }else{document.exitPointerLock?.();orbit.target.set(-20,4,-10);}
  updateUi();
}
function updateUi(){
  document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
  $('#mode-label').textContent=sourceMode?'原版沙盘':({overview:'总览',walk:'步行',fly:'飞行'})[mode];
  $('#source-mode').textContent=sourceMode?'返回大世界':'原版沙盘';
  $('#reticle').hidden=mode==='overview';$('#capture').hidden=mode==='overview'||document.pointerLockElement===canvas||matchMedia('(pointer:coarse)').matches;
  $('#touch-pad').hidden=mode==='overview'||!matchMedia('(pointer:coarse)').matches;$('#touch-height').hidden=mode!=='fly'||!matchMedia('(pointer:coarse)').matches;
}
async function toggleSource(value=!sourceMode){
  sourceMode=value;setMode('overview');worldGroup.visible=!value;originalGroup.visible=value;
  scene.background.set(value?'#1c292b':'#aebfc2');scene.fog=value?null:new THREE.FogExp2('#aebfc2',.0019);
  if(value){orbit.maxPolarAngle=Math.PI;await changeEpisode(episode);}else{orbit.maxPolarAngle=Math.PI*.49;resetView();}
  updateUi();
}
function resetView(){
  transition=null;if(sourceMode){changeEpisode(episode);return;}
  if(mode==='overview'){camera.position.set(26,98,103);orbit.target.set(-20,11,-16);orbit.update();}
  else{camera.position.set(0,mode==='walk'?2:20,35);camera.lookAt(-20,3,-10);directionFromCamera();}
}
function jump(place){
  if(sourceMode){toast('返回大世界后可进入地点');return;}
  const p=world.destinations[place];
  const end=new THREE.Vector3(p[0],mode==='overview'?32:mode==='walk'?terrainHeight(p[0],p[2])+1.8:16,p[2]+(mode==='overview'?35:0));
  transition={from:camera.position.clone(),end,start:performance.now(),target:new THREE.Vector3(p[0],3,p[2]-14)};
}
function hideUi(value=!uiHidden){uiHidden=value;document.body.classList.toggle('clean-view',value);$('#restore-ui').hidden=!value;}
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.mode,true));
document.querySelectorAll('[data-place]').forEach(b=>b.onclick=()=>jump(b.dataset.place));
$('#source-mode').onclick=()=>toggleSource().catch(e=>toast(e.message));$('#reset').onclick=resetView;
$('#episodes').onchange=e=>changeEpisode(Number(e.target.value));$('#next').onclick=()=>changeEpisode(episode+1);$('#prev').onclick=()=>changeEpisode(episode-1);
$('#help-toggle').onclick=()=>$('#help').hidden=!$('#help').hidden;$('#help-close').onclick=()=>$('#help').hidden=true;
$('#fullscreen').onclick=()=>document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen().catch(()=>toast('当前浏览器不支持全屏'));
$('#restore-ui').onclick=()=>hideUi(false);$('#capture').onclick=()=>canvas.requestPointerLock?.()?.catch(()=>toast('可按住场景拖动环视'));
document.addEventListener('pointerlockchange',updateUi);
addEventListener('keydown',e=>{if(e.target.matches('select,input,textarea'))return;if(['KeyW','KeyA','KeyS','KeyD','KeyQ','KeyE','ShiftLeft','ShiftRight'].includes(e.code)){keys.add(e.code);e.preventDefault();}if(e.code==='KeyR')resetView();if(e.code==='KeyH')hideUi();});
addEventListener('keyup',e=>keys.delete(e.code));addEventListener('blur',()=>keys.clear());document.addEventListener('visibilitychange',()=>keys.clear());
canvas.addEventListener('pointerdown',e=>{if(mode!=='overview'){lastPointer={id:e.pointerId,x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);}});
canvas.addEventListener('pointerup',()=>lastPointer=null);canvas.addEventListener('pointercancel',()=>lastPointer=null);
canvas.addEventListener('pointermove',e=>{
  if(mode==='overview')return;
  let dx=0,dy=0;if(document.pointerLockElement===canvas){dx=e.movementX;dy=e.movementY;}else if(lastPointer?.id===e.pointerId){dx=e.clientX-lastPointer.x;dy=e.clientY-lastPointer.y;lastPointer.x=e.clientX;lastPointer.y=e.clientY;}else return;
  yaw-=dx*.0026;pitch=THREE.MathUtils.clamp(pitch-dy*.0026,-1.35,1.35);
});
document.querySelectorAll('[data-key]').forEach(b=>{b.onpointerdown=e=>{e.preventDefault();keys.add(b.dataset.key);b.setPointerCapture(e.pointerId);};b.onpointerup=b.onpointercancel=()=>keys.delete(b.dataset.key);});
function move(dt){
  if(mode==='overview'||!ready||transition)return;
  camera.quaternion.setFromEuler(new THREE.Euler(pitch,yaw,0,'YXZ'));
  const speed=(keys.has('ShiftLeft')||keys.has('ShiftRight')?22:mode==='fly'?14:6)*dt;
  const forward=new THREE.Vector3(-Math.sin(yaw),0,-Math.cos(yaw));const right=new THREE.Vector3(Math.cos(yaw),0,-Math.sin(yaw));
  const delta=new THREE.Vector3();delta.addScaledVector(forward,Number(keys.has('KeyW'))-Number(keys.has('KeyS')));delta.addScaledVector(right,Number(keys.has('KeyD'))-Number(keys.has('KeyA')));if(delta.lengthSq()>1)delta.normalize();delta.multiplyScalar(speed);
  if(mode==='fly')delta.y=(Number(keys.has('KeyE'))-Number(keys.has('KeyQ')))*speed;
  let next=camera.position.clone().add(delta);
  if(mode==='walk'){
    if(!canOccupy(next.x,camera.position.z,world.colliders,.65,camera.position.y-1.8))next.x=camera.position.x;
    if(!canOccupy(next.x,next.z,world.colliders,.65,camera.position.y-1.8))next.z=camera.position.z;
  }
  const p=constrainPosition(next,world,mode==='walk');camera.position.set(p.x,p.y,p.z);
}
const map=$('#minimap'),mc=map.getContext('2d');let mapTick=0;
function drawMap(){
  mc.clearRect(0,0,300,150);mc.fillStyle='#233b34';mc.fillRect(0,0,300,150);mc.fillStyle='#b6c5c3';mc.fillRect(0,0,300,31);mc.strokeStyle='#a6aa80';
  for(const road of world.roads){mc.lineWidth=road.width/320*300;mc.beginPath();road.points.forEach(([x,z],i)=>mc[i?'lineTo':'moveTo']((x+160)/320*300,(z+80)/160*150));mc.stroke();}
  for(const {x,z,w,d} of world.landmarks){mc.fillStyle='#d8d4bb';mc.fillRect((x+160)/320*300-w/320*150,(z+80)/160*150-d/160*75,w/320*300,d/160*150);}
  const x=(camera.position.x+160)/320*300,z=(camera.position.z+80)/160*150;mc.fillStyle='#f3d9a1';mc.beginPath();mc.arc(x,z,3.5,0,Math.PI*2);mc.fill();mc.strokeStyle='#f3d9a1';mc.beginPath();mc.moveTo(x,z);mc.lineTo(x-Math.sin(yaw)*10,z-Math.cos(yaw)*10);mc.stroke();
  $('#coordinates').textContent=`X ${camera.position.x.toFixed(0)} · Z ${camera.position.z.toFixed(0)}`;
}
function animate(){
  requestAnimationFrame(animate);const dt=Math.min(clock.getDelta(),.05);
  if(transition){const t=Math.min((performance.now()-transition.start)/900,1),a=1-(1-t)**3;camera.position.lerpVectors(transition.from,transition.end,a);if(mode==='overview')orbit.target.lerp(transition.target,.12);else{camera.lookAt(transition.target);directionFromCamera();}if(t===1)transition=null;}
  move(dt);if(orbit.enabled)orbit.update();if(++mapTick%8===0&&!sourceMode)drawMap();renderer.render(scene,camera);
}
animate();start().catch(e=>{$('#load-status').textContent=e.message;$('#loading').classList.add('failed');console.error(e);});
