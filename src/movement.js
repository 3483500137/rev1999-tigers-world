export function terrainHeight(x,z) {
  const y=-z, ridge=Math.max(0,(y-42)/36);
  const t=Math.max(0,Math.min(1,(y-48)/32));
  const crest=19+15*Math.sin(x*.039)**2+6*Math.sin(x*.12)**2;
  return ridge*(10+7*Math.sin(x*.035)**2)+.45*Math.sin(x*.025)*Math.cos(y*.06)+Math.sin(t*Math.PI/2)*crest;
}
export function canOccupy(x,z,colliders,radius=.65,feetY=null) {
  return !colliders.some(b => {
    if(feetY!==null && Number.isFinite(b.yMin) && (b.yMin>=feetY+1.65 || b.yMin+b.height<=feetY+.12))return false;
    return Math.abs(x-b.x)<b.w/2+radius && Math.abs(z-b.z)<b.d/2+radius;
  });
}
export function constrainPosition(position,world,walk=false) {
  const b=world.bounds;
  const x=Math.max(b.minX,Math.min(b.maxX,position.x));
  const z=Math.max(b.minZ,Math.min(b.maxZ,position.z));
  let ground=terrainHeight(x,z);
  if(walk)for(const s of world.walkSurfaces||[]){
    if(Math.abs(x-s.x)>s.w/2||Math.abs(z-s.z)>s.d/2)continue;
    const y=s.y+(s.slopeZ||0)*(z-s.z);
    if(y<=position.y-1.8+.45)ground=Math.max(ground,y);
  }
  return {x,z,y:walk ? ground+1.8 : Math.max(terrainHeight(x,z)+1.8,Math.min(90,position.y))};
}

export function initialView(world,mode='overview') {
  if(mode==='overview')return {
    position:[...(world.overview?.position||[26,98,103])],
    target:[...(world.overview?.target||[-20,11,-16])],
    zoom:1,
  };
  const [x,y,z]=world.spawn||[-20,2,35];
  const p=constrainPosition({x,y:mode==='fly'?Math.max(20,y):y,z},world,mode==='walk');
  const hall=world.landmarks?.find(l=>l.id==='central-auditorium');
  return {position:[p.x,p.y,p.z],target:[hall?.x??x,mode==='walk'?p.y+1:15,hall?.z??-16],zoom:1};
}
