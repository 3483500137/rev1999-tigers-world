import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
let text;
try { text = await readFile('reference/chapter-104.js', 'utf8'); }
catch {
  const r=await fetch('https://raw.githubusercontent.com/VioletWilde/1999-demo/1d83ddc454c9c7c193e4c458412db42bfc5d8031/data/chapter-104.js');
  if(!r.ok)throw Error(`Source download failed: ${r.status}`);
  text=await r.text();
}
const scenes = JSON.parse(text.slice(text.indexOf('=') + 1).trim().replace(/;$/, ''));
await mkdir('public/data', { recursive: true });
await writeFile('public/data/chapter-104.json', JSON.stringify(scenes));
const paths = [...new Set(scenes.flatMap(s => s.draws.map(m => m.texture)))];
const files = await Promise.all(paths.map(async path => {
  const b = await readFile(`public/${path}`);
  return { path, bytes: b.length, sha256: createHash('sha256').update(b).digest('hex') };
}));
await writeFile('public/data/sources.json', JSON.stringify({ repository: 'https://github.com/VioletWilde/1999-demo', commit: '1d83ddc454c9c7c193e4c458412db42bfc5d8031', chapter: 104, title: '老虎的金黄', scenes: scenes.length, files }, null, 2));
console.log(`${scenes.length} scenes, ${files.length} original textures, ${files.reduce((s,f)=>s+f.bytes,0)} bytes`);
