import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {load,ROOT} from './pack.mjs';

const kinds=new Set(['error','file','route','installer','shortcut','startup','firstFrame','settings']);
export function validateReservations(value,cards) {
  const errors=[]; const seen=new Set();
  if(!value || value.version!==1 || !Array.isArray(value.entries) ||
    Object.keys(value).some(k=>!['version','entries'].includes(k))) return ['EXT-1: invalid root/version'];
  for(const [i,row] of value.entries.entries()) {
    if(!row || typeof row!=='object' || Array.isArray(row) ||
      Object.keys(row).sort().join(',')!=='key,kind,owner,point' ||
      !['kind','key','owner','point'].every(k=>typeof row[k]==='string' && row[k].trim())) {
      errors.push(`EXT-1: invalid entry ${i}`); continue;
    }
    const key=`${row.kind}:${row.key}`;
    if(!kinds.has(row.kind))errors.push(`EXT-1: unknown kind ${key}`);
    if(seen.has(key))errors.push(`EXT-2: duplicate ${key}`);
    seen.add(key);
    if(!cards.has(row.owner))errors.push(`EXT-3: unknown owner ${row.owner}`);
    if(row.kind==='route' && !/^\/(?:[a-z][a-z0-9_-]*)(?:\/[a-z][a-z0-9_-]*)*$/.test(row.key))errors.push(`EXT-1: invalid route ${key}`);
    if(row.kind==='error' && !/^[A-Z]+(?:_[A-Z0-9]+)+$/.test(row.key))errors.push(`EXT-1: invalid code ${key}`);
    if(['startup','firstFrame','settings'].includes(row.kind) && !/^(?:0|[1-9][0-9]{0,2})$/.test(row.key))errors.push(`EXT-1: invalid order ${key}`);
  }
  return errors;
}
export function compareActual(policy,actual,cards) {
  const errors=validateReservations(actual,cards);
  const allowed=new Map(policy.entries.map(x=>[`${x.kind}:${x.key}`,x]));
  if(errors.length)return errors;
  for(const row of actual.entries) {
    const key=`${row.kind}:${row.key}`, expected=allowed.get(key);
    if(!expected || expected.owner!==row.owner || expected.point!==row.point) errors.push(`EXT-4: unallocated or changed ${key}`);
  }
  return errors;
}
if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try {
    const opt=name=>{const i=process.argv.indexOf(name);if(i<0)return undefined;if(!process.argv[i+1] || process.argv[i+1].startsWith('--'))throw Error(`Missing ${name}`);return process.argv[i+1];};
    const policy=JSON.parse(fs.readFileSync(opt('--policy')??path.join(ROOT,'contracts/policies/shared-writes.json'),'utf8'));
    const cards=load();const errors=validateReservations(policy,cards);
    const actualFile=opt('--actual');
    if(actualFile && !errors.length)errors.push(...compareActual(policy,JSON.parse(fs.readFileSync(actualFile,'utf8')),cards));
    console.log(JSON.stringify({mode:actualFile?'implementation':'design',entries:policy.entries?.length,errors}));
    process.exitCode=errors.length?1:0;
  } catch(error) {console.error(`EXT-INPUT: ${error.message}`);process.exitCode=2;}
}
