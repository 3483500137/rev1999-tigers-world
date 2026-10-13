import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
const run=promisify(execFile);
const base='https://3483500137.github.io/rev1999-tigers-world/';
const checkId=Date.now().toString();
async function get(path){try{const url=new URL(path,base);url.searchParams.set('verify',checkId);const {stdout}=await run('curl',['--fail','--silent','--show-error','--location','--retry','1','--connect-timeout','10','--max-time','55',url.href],{encoding:'buffer',maxBuffer:10e6});console.log(`Checked ${path||'homepage'}`);return stdout;}catch(e){throw Error(String(e.stderr||e.message));}}
const html=(await get('')).toString();if(!html.includes('老虎的金黄'))throw Error('Unexpected homepage');
const assets=[...html.matchAll(/(?:src|href)="(\.\/assets\/[^" ]+)"/g)].map(m=>m[1]);
await Promise.all(assets.map(get));
const world=JSON.parse((await get('data/world.json')).toString());
const model=await get(world.model),localModel=await readFile('public/'+world.model);
if(!model.equals(localModel))throw Error('Published model mismatch');
const chapter=JSON.parse((await get('data/chapter-104.json')).toString());if(chapter.length!==23)throw Error('Missing chapter scenes');
const sources=JSON.parse((await get('data/sources.json')).toString());
let index=0;await Promise.all(Array.from({length:3},async()=>{while(index<sources.files.length){const f=sources.files[index++],b=await get(f.path);if(createHash('sha256').update(b).digest('hex')!==f.sha256)throw Error('Asset mismatch: '+f.path);}}));
console.log(JSON.stringify({url:base,homepage:true,bundles:assets.length,modelBytes:model.length,scenes:chapter.length,originalTextures:sources.files.length,browserInteraction:'NOT VERIFIED'},null,2));
