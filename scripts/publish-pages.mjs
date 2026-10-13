import {execFileSync} from 'node:child_process';
import {cp,mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const git=(args,cwd=process.cwd())=>execFileSync('git',args,{cwd,encoding:'utf8'}).trim();
const remote=git(['remote','get-url','origin']);
execFileSync(process.platform==='win32'?'npm.cmd':'npm',['run','build'],{stdio:'inherit',shell:process.platform==='win32'});
const dir=await mkdtemp(join(tmpdir(),'tigers-pages-'));
try {
  await cp('dist',dir,{recursive:true});
  git(['init','-b','gh-pages'],dir);
  git(['config','user.name',git(['config','user.name'])],dir);
  git(['config','user.email',git(['config','user.email'])],dir);
  git(['add','.'],dir);git(['commit','-m','Publish static world'],dir);
  git(['remote','add','origin',remote],dir);
  // A new orphan snapshot contains generated artifacts only; force applies solely to gh-pages.
  git(['push','--force','origin','HEAD:gh-pages'],dir);
  console.log('Published generated static site to gh-pages.');
} finally {await rm(dir,{recursive:true,force:true});}
