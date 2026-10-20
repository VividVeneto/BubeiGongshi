import fs from 'node:fs';
import path from 'node:path';
import {load, pack, ROOT} from './pack.mjs';
const sadd=path.resolve(process.argv[2]??path.join(ROOT,'SADD'));
const cards=load(sadd);
const readme=fs.readFileSync(path.join(sadd,'README.md'),'utf8');
const appendix=fs.readFileSync(path.join(sadd,'附录D-编码就绪检查记录.md'),'utf8');
const current=appendix.split('## D.10 ')[1]?.split('## D.11 ')[0]??'';
const rows=current.split('\n').filter(l=>/^\| (?:CORE|AND|WIN)-\d+ \|/.test(l));
const columns=current.split('\n').find(l=>l.startsWith('| 编号 |'))?.split('|').map(x=>x.trim())??[];
const reviewColumn=columns.indexOf('v5.3.2 复核');
const stats={cards:cards.size,CORE:0,AND:0,WIN:0,currentRows:rows.length,ready:0,grades:{}};
for(const id of cards.keys()) stats[id.split('-')[0]]++;
for(const row of rows){
  const cells=row.split('|').map(x=>x.trim());
  const grade=reviewColumn<0?'未独立复核':cells[reviewColumn]; stats.grades[grade]=(stats.grades[grade]??0)+1;
  if(cells.some(c=>/^就绪（/.test(c)))stats.ready++;
}
const errors=[]; const warnings=[]; const materials=[];
const generated=appendix.match(/<!-- sadd-current-stats:start -->[\s\S]*?<!-- sadd-current-stats:end -->/)?.[0]??'';
if(!generated.includes(`总计${cards.size}卡；`) || !generated.includes(`就绪=${stats.ready}。`) || Object.entries(stats.grades).some(([k,v])=>!generated.includes(`${k}=${v}`))) errors.push('SADD-12: generated current statistics drift; run stats.mjs');
if(rows.length!==cards.size)errors.push(`SADD-12: current rows ${rows.length} != cards ${cards.size}`);
for(const [id,card] of cards){
  const result=pack(id,{sadd});
  materials.push({id,chars:result.report.chars,segments:result.chunks.length});
  for(const warning of result.report.warnings) warnings.push({id,rule:'SADD-9/10',warning});
  for(const row of readme.split('\n')) {
    const q=row.match(/^\| (Q\d+) \|/); if(!q)continue;
    const affected=(row.split('|').at(-2)??'').match(/(?:CORE|AND|WIN)-\d+/g)??[];
    const mentioned=new RegExp(`\\b${q[1]}\\b`).test(card.body);
    if(affected.includes(id)!==mentioned)warnings.push({id,rule:'SADD-11',q:q[1],affected:affected.includes(id),mentioned});
  }
}
materials.sort((a,b)=>b.chars-a.chars);
const report={stats,errors,warnings,materials};
const out=path.join(ROOT,'temp/tools/out/p1-audit.json');
fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(report,null,2));
console.log(JSON.stringify({stats,errors:errors.length,warnings:warnings.length,overLimit:materials.filter(m=>m.chars>80000).length,max:materials[0]}));
process.exitCode=errors.length?1:0;
