import test from 'node:test';
import assert from 'node:assert/strict';
import {pack, load, blocks} from './pack.mjs';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

test('fences and tables remain atomic', () => {
  const input='```rust\nstruct A {\n\n x: u8\n}\n```\n\n| a | b |\n| - | - |\n| 1 | 2 |\n';
  const result=blocks(input);
  assert.equal(result.length,2); assert.match(result[0],/x: u8/); assert.match(result[1],/1 \| 2/);
});
test('all cards retain full direct contracts and target, bounded segments lose no text', () => {
  const cards=load();
  for(const [id,card] of cards) {
    const result=pack(id);
    assert.ok(result.text.includes(card.body.trim()),id+' target');
    for(const dep of card.deps) assert.ok(result.text.includes(cards.get(dep).contract.trim()),id+' -> '+dep);
    for(const segment of result.chunks) assert.ok([...segment].length<=80000,id+' segment');
    assert.equal(result.chunks.join('').replace(/\s/g,''),result.text.replace(/\s/g,''),id+' lossless');
  }
});
test('unknown cards and paths outside workspace are rejected', () => {
  assert.throws(()=>pack('CORE-999'),/Unknown card/);
  assert.throws(()=>pack('CORE-01',{extra:['../outside.txt']}),/outside workspace/);
});

test('platform locks, dependency contracts and uncollected local definitions are reported', () => {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'sadd-pack-'));
  const sadd=path.join(root,'SADD'); fs.mkdirSync(sadd);
  try {
    const card=(id,deps,contract)=>`### ${id} fixture\n\n**依赖**：${deps}\n\n**接口契约**\n\n${contract}\n\n**实现约束**\n\nfixture\n`;
    fs.writeFileSync(path.join(sadd,'01-公共核心-v5.md'),
      card('CORE-01','','struct RootFixture {}')+card('CORE-02','','`contracts/errors/registry.yaml`')+
      card('CORE-54','','class SelectionController {}')+card('CORE-57','CORE-01、CORE-02','SelectionController onlyUsed;'));
    for(const f of ['02-Android端-v5.md','03-Windows端-v5.md','README.md','附录A-架构决策与评审记录.md'])fs.writeFileSync(path.join(sadd,f),'');
    fs.mkdirSync(path.join(root,'app/android'),{recursive:true});
    fs.writeFileSync(path.join(root,'app/android/toolchain.versions'),'ndk=fixture-lock');
    fs.mkdirSync(path.join(root,'contracts/errors'),{recursive:true});
    fs.writeFileSync(path.join(root,'contracts/errors/registry.yaml'),'fixture_dependency_contract: true');
    const result=pack('CORE-57',{sadd});
    assert.ok(result.text.includes('ndk=fixture-lock'));
    assert.ok(result.text.includes('fixture_dependency_contract: true'));
    assert.ok(result.report.missing.includes('app/windows/toolchain.versions'));
    assert.ok(result.report.missingFromMaterials.some(x=>x.symbol==='SelectionController' && x.sources.some(s=>s.card==='CORE-54')));
    assert.ok(!result.text.includes('class SelectionController {}'));
  } finally {
    assert.equal(path.dirname(path.resolve(root)), path.resolve(os.tmpdir()));
    assert.ok(path.basename(root).startsWith('sadd-pack-'));
    fs.rmSync(root,{recursive:true,force:true});
  }
});
