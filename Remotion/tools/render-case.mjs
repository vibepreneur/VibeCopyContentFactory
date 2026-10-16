import {spawnSync} from 'node:child_process';
import {existsSync, mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import {parseArgs} from 'node:util';
import {createTimeline} from '../src/timeline.mjs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

// v6 export hotfix: run Node executables directly without cmd.exe/shell.
// On Windows, shell:true would split `C:\\Program Files\\...` at the space.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const {values, positionals} = parseArgs({allowPositionals:true, options:{
  native:{type:'boolean'},verbose:{type:'boolean'},output:{type:'string'},
  metadata:{type:'string'},'restore-config':{type:'boolean'},
}});
const native = values.native;
const casePath = positionals[0] || 'cases/CASE_001.json';
const verbose = values.verbose;
const shared = path.join(root,'src','case.generated.mjs');
const previous = readFileSync(shared);
let generated;

function runNode(file, params) {
  const result = spawnSync(process.execPath, [file, ...params], {
    cwd: root,
    stdio: 'inherit',
    shell: false,
    windowsHide: true,
  });
  if (result.error) {
    console.error('Unable to start process:', result.error.message);
    throw result.error;
  }
  if (result.signal) {
    console.error('Process exited with signal:', result.signal);
  }
  if (result.status !== 0) throw Error(`Child exited ${result.status || result.signal}`);
}

try {
runNode(path.join(root, 'tools', 'prepare-case.mjs'), [casePath]);
generated = readFileSync(shared);

const composition = native ? 'VibeCopyNative' : 'VibeCopySocialFill';
const id = path.basename(casePath, '.json').replace(/[^a-zA-Z0-9_-]/g, '_');
const destination = path.resolve(root, values.output || path.join('out', `${id}-${native ? 'native' : 'social-fill-1080x1920'}.mp4`));
const project = path.dirname(root);
for(const candidate of [destination,...(values.metadata?[path.resolve(root,values.metadata)]:[])]) {
  if(!candidate.startsWith(project+path.sep)) throw Error('Output must be inside Factory project');
}
mkdirSync(path.dirname(destination), {recursive: true});
if(values.metadata) {
  const cfg=JSON.parse(readFileSync(path.resolve(root,casePath),'utf8'));
  const timeline=createTimeline(cfg);
  const meta=path.resolve(root,values.metadata);
  mkdirSync(path.dirname(meta),{recursive:true});
  writeFileSync(meta,JSON.stringify({fps:timeline.fps,frames:timeline.end,stages:timeline.stages,photos:cfg.photos},null,2));
}

// The CLI package officially declares `remotion-cli.js` as its executable.
const cli = path.join(root, 'node_modules', '@remotion', 'cli', 'remotion-cli.js');
if (!existsSync(cli)) {
  console.error(`Remotion CLI not installed: ${cli}`);
  console.error('Run: npm install');
  throw Error('Remotion CLI missing');
}

console.log(`Rendering ${composition} -> ${destination}`);
console.log('Stability settings: concurrency=1, parallel encoding disabled.');
runNode(cli, [
  'render',
  'src/index.ts',
  composition,
  destination,
  '--codec=h264',
  '--concurrency=1',
  '--disallow-parallel-encoding',
  ...(verbose ? ['--log=verbose'] : []),
]);
console.log('Video saved:', destination);
} finally {
  if(values['restore-config'] && generated) {
    if(readFileSync(shared).equals(generated)) writeFileSync(shared,previous);
    else throw Error('Shared config changed externally; refusing to overwrite');
  }
}
