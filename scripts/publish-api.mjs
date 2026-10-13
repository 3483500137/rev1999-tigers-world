// Alternative transport when github.com Git connections are unavailable.
// Authentication stays inside the already authenticated GitHub CLI.
import {execFileSync,execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {readFile,readdir} from 'node:fs/promises';
import {resolve,relative,join} from 'node:path';
import {createHash} from 'node:crypto';
const run=promisify(execFile),root=resolve(process.argv[2]||'dist'),branch=process.argv[3]||'gh-pages';
if(!['main','gh-pages'].includes(branch))throw Error('Only main or gh-pages may be published.');
const repo='3483500137/rev1999-tigers-world',base=`repos/${repo}`;
async function api(path,body){
  if(body===undefined){const {stdout}=await run('gh',['api',`${base}/${path}`],{maxBuffer:20e6});return JSON.parse(stdout);}
  return new Promise((yes,no)=>{const child=execFile('gh',['api','--method','POST',`${base}/${path}`,'--input','-'],{maxBuffer:20e6},(err,out)=>err?no(err):yes(JSON.parse(out)));child.stdin.end(JSON.stringify(body));});
}
async function list(dir){const files=[];for(const e of await readdir(dir,{withFileTypes:true})){const p=join(dir,e.name);if(e.isDirectory())files.push(...await list(p));else if(e.isFile())files.push(relative(root,p).replaceAll('\\','/'));}return files;}
// A main snapshot preserves the remote parent but may have a different commit SHA
// than local Git history. Only tracked source files are included, never .git/secrets.
const paths=branch==='main'?execFileSync('git',['ls-files','-z'],{cwd:root}).toString().split('\0').filter(Boolean):await list(root);
let parent=null,old=new Map();
try{const ref=await api(`git/ref/heads/${branch}`);parent=ref.object.sha;const tree=await api(`git/trees/${parent}?recursive=1`);old=new Map(tree.tree.map(e=>[e.path,e.sha]));}
catch(e){if(!String(e.stderr||e.message).includes('404'))throw e;}
const entries=[];let cursor=0;
await Promise.all(Array.from({length:3},async()=>{while(cursor<paths.length){const path=paths[cursor++],data=branch==='main'?execFileSync('git',['show',`:${path}`],{cwd:root,maxBuffer:20e6}):await readFile(join(root,path));const sha=createHash('sha1').update(`blob ${data.length}\0`).update(data).digest('hex');let blob=sha;if(old.get(path)!==sha){blob=(await api('git/blobs',{content:data.toString('base64'),encoding:'base64'})).sha;}entries.push({path,mode:'100644',type:'blob',sha:blob});console.log(`Prepared ${path}`);}}));
const tree=await api('git/trees',{tree:entries});
const commit=await api('git/commits',{message:branch==='main'?'Update scene source and API publishing tools':'Publish explorable world',tree:tree.sha,parents:parent?[parent]:[]});
if(parent){await new Promise((yes,no)=>{const child=execFile('gh',['api','--method','PATCH',`${base}/git/refs/heads/${branch}`,'--input','-'],(err)=>err?no(err):yes());child.stdin.end(JSON.stringify({sha:commit.sha,force:false}));});}
else await api('git/refs',{ref:`refs/heads/${branch}`,sha:commit.sha});
console.log(`Published ${branch}: ${commit.sha}`);
