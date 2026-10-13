export function terrainHeight(x,z) {
  const y=-z, ridge=Math.max(0,(y-42)/36);
  return ridge*(10+7*Math.sin(x*.035)**2)+.45*Math.sin(x*.025)*Math.cos(y*.06);
}
export function canOccupy(x,z,colliders,radius=.65) {
  return !colliders.some(b => Math.abs(x-b.x)<b.w/2+radius && Math.abs(z-b.z)<b.d/2+radius);
}
export function constrainPosition(position,world,walk=false) {
  const b=world.bounds;
  const x=Math.max(b.minX,Math.min(b.maxX,position.x));
  const z=Math.max(b.minZ,Math.min(b.maxZ,position.z));
  return {x,z,y:walk ? terrainHeight(x,z)+1.8 : Math.max(terrainHeight(x,z)+1.8,Math.min(90,position.y))};
}
