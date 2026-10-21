import test from 'node:test';
import assert from 'node:assert/strict';
import {pack, load, blocks, segment, writeOutput, filterJsonArray, filterJsonObject, jsonItems, schemaRefs, definedSymbols} from './pack.mjs';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

test('fences and tables remain atomic', () => {
  const input='```rust\nstruct A {\n\n x: u8\n}\n```\n\n| a | b |\n| - | - |\n| 1 | 2 |\n';
  const result=blocks(input);
  assert.equal(result.length,2); assert.match(result[0],/x: u8/); assert.match(result[1],/1 \| 2/);
});
test('all cards retain full direct contracts and target, bounded segments lose no text', () => {
  const cards=load(undefined,{tests:false});
  const contractFiles=[];
  const walk=d=>{for(const n of fs.readdirSync(d)){const p=d+'/'+n; if(fs.statSync(p).isDirectory())walk(p); else contractFiles.push(p);}};
  walk('contracts');
  for(const [id,card] of cards) {
    const result=pack(id);
    assert.ok(result.text.includes(card.body.trim()),id+' target');
    for(const dep of card.deps) assert.ok(result.text.includes(cards.get(dep).contract.trim()),id+' -> '+dep);
    for(const segment of result.chunks) assert.ok([...segment].length<=80000,id+' segment');
    assert.equal(result.chunks.join(''),result.text,id+' lossless');
    const accounted=new Set([...result.report.files,...result.report.filteredFiles.map(f=>f.path)]);
    for(const f of contractFiles) assert.ok(accounted.has(f),id+' accounts for '+f);
  }
});
test('test plans are excluded by default and included only with withTests', () => {
  const withTests=load(); const plain=load(undefined,{tests:false});
  const id=[...withTests.keys()].find(k=>withTests.get(k).testFile);
  assert.ok(id,'some card references a test plan');
  const plan=fs.readFileSync(path.join('SADD',withTests.get(id).testFile),'utf8');
  assert.equal(plain.get(id).testFile,withTests.get(id).testFile);
  assert.ok(!plain.get(id).body.includes(plan.split('\n').slice(2).join('\n').trim().slice(0,200)),'plain body keeps only the reference line');
  const def=pack(id); const full=pack(id,{withTests:true});
  assert.equal(def.report.tests,'excluded'); assert.equal(full.report.tests,'included');
  assert.ok(def.text.includes(plain.get(id).body.trim()));
  assert.ok(full.text.includes(withTests.get(id).body.trim()));
  assert.ok(def.text.includes('测试方案默认不收录'));
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

test('downstream classification requires every occurrence and ADR selection preserves evidence', () => {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'sadd-pack-'));
  const sadd=path.join(root,'SADD'); fs.mkdirSync(sadd);
  try {
    const card=(id,text)=>`### ${id} fixture\n\n**依赖**：\n\n**接口契约**\n\n${text}\n\n**实现约束**\nfixture\n`;
    const file=path.join(sadd,'01-公共核心-v5.md');
    const source=card('CORE-01','root')+card('CORE-02','errors')+card('CORE-50','class DownstreamOnly {}');
    fs.writeFileSync(file,source+card('CORE-57','CORE-50（下游说明，非契约）；ADR-V5-39'));
    for(const f of ['02-Android端-v5.md','03-Windows端-v5.md','README.md'])fs.writeFileSync(path.join(sadd,f),'');
    fs.writeFileSync(path.join(sadd,'附录A-架构决策与评审记录.md'),
      '### A.4.10 ADR-V5-39\n\nrelevant-source-evidence\n\n### A.4.11 unrelated\n\nunrelated-source-evidence\n');
    const result=pack('CORE-57',{sadd});
    assert.equal(result.report.classifiedReferences.length,1);
    assert.ok(!result.text.includes('class DownstreamOnly {}'));
    assert.ok(result.text.includes('relevant-source-evidence'));
    assert.ok(!result.text.includes('unrelated-source-evidence'));
    assert.deepEqual(result.report.excludedSupplements,['### A.4.11 unrelated']);
    fs.writeFileSync(file,source+card('CORE-57','CORE-50（下游说明，非契约）\n\nCORE-50 required without classification'));
    assert.ok(pack('CORE-57',{sadd}).text.includes('class DownstreamOnly {}'));
  } finally {
    assert.equal(path.dirname(path.resolve(root)),path.resolve(os.tmpdir()));
    assert.ok(path.basename(root).startsWith('sadd-pack-'));
    fs.rmSync(root,{recursive:true,force:true});
  }
});

test('real contract inventory accounts for the policy and every ready schema; --file restores full text',()=>{
 const manifest=JSON.parse(fs.readFileSync('contracts/dto/manifest.json','utf8'));
 const dto=pack('CORE-67');
 const accounted=new Set([...dto.report.files,...dto.report.filteredFiles.map(f=>f.path)]);
 for(const op of manifest.ops.filter(x=>x.status==='ready')) assert.ok(accounted.has('contracts/dto/'+op.schema),op.op);
 assert.ok(accounted.has('contracts/dto/types.schema.json'));
 assert.equal(pack('CORE-75').report.filteredFiles.find(f=>f.path==='contracts/policies/shared-writes.json').mode,'filtered');
 const forced=pack('CORE-75',{extra:['contracts/policies/shared-writes.json']});
 assert.ok(forced.report.files.includes('contracts/policies/shared-writes.json'));
 assert.ok(forced.text.includes(fs.readFileSync('contracts/policies/shared-writes.json','utf8')));
});

// ---- 去噪（contracts 与附录 A 只收录相关内容） ----
const MAN = 'contracts/dto/manifest.json', SW = 'contracts/policies/shared-writes.json', TYPES = 'contracts/dto/types.schema.json';
const read = f => fs.readFileSync(f, 'utf8');
const sha = text => crypto.createHash('sha256').update(text).digest('hex');
/** 取材料中某个“已有文件”小节的围栏正文。 */
const fenced = (text, title) => {
  const at = text.indexOf('## 已有文件 ' + title); assert.ok(at >= 0, title);
  const start = text.indexOf('```text\n', at) + '```text\n'.length; const end = text.indexOf('\n```', start);
  return text.slice(start, end);
};

test('unrelated schemas are only listed with size and SHA-256; related schemas are complete', () => {
  const unrelated = 'contracts/dto/account.close_profile.schema.json';   // owner CORE-23
  const r78 = pack('CORE-78');
  const entry = r78.report.filteredFiles.find(f => f.path === unrelated);
  assert.equal(entry.mode, 'listed'); assert.equal(entry.includedBytes, 0);
  assert.equal(entry.sha256, sha(read(unrelated))); assert.equal(entry.originalBytes, Buffer.byteLength(read(unrelated)));
  assert.ok(r78.text.includes(`| ${unrelated} | ${entry.originalBytes} | ${entry.sha256} |`));
  assert.ok(!r78.text.includes(read(unrelated)));
  assert.ok(!r78.report.files.includes(unrelated));
  // CORE-13（CORE-78 的直接依赖）拥有的 store.* schema 完整收录。
  for (const f of ['contracts/dto/store.open.schema.json', 'contracts/dto/store.close.schema.json']) {
    assert.ok(r78.report.files.includes(f)); assert.ok(r78.text.includes(read(f)));
  }
  const r23 = pack('CORE-23');
  assert.ok(r23.report.files.includes(unrelated)); assert.ok(r23.text.includes(read(unrelated)));
  // 被收录 schema 经 $ref 引用的 types 条目进入切片。
  const slice = JSON.parse(fenced(r23.text, TYPES + '（切片）'));
  assert.ok(slice.$defs.AccountState && slice.$defs.Profile);
});

test('manifest and shared-writes are filtered by owner as valid JSON with byte-identical entries', () => {
  for (const id of ['CORE-78', 'CORE-26', 'CORE-77']) {
    const result = pack(id); const related = new Set(result.report.related);
    for (const [file, key] of [[MAN, 'ops'], [SW, 'entries']]) {
      const original = read(file); const filtered = fenced(result.text, file + '（已按 owner 过滤）');
      const doc = JSON.parse(filtered); const all = JSON.parse(original)[key];
      assert.deepEqual(doc[key], all.filter(x => related.has(x.owner)), id + ' ' + file);
      const originalItems = new Set(jsonItems(original, key).map(x => x.text));
      for (const item of jsonItems(filtered, key)) assert.ok(originalItems.has(item.text), id + ' bytes ' + file);
      const entry = result.report.filteredFiles.find(f => f.path === file);
      assert.equal(entry.mode, 'filtered'); assert.equal(entry.kept, doc[key].length); assert.equal(entry.total, all.length);
      assert.equal(entry.sha256, sha(original));
      assert.ok(result.text.includes(`原文件 SHA-256=${entry.sha256}，条目数 ${entry.kept}/${entry.total}`));
    }
  }
});

test('types.schema.json slices keep whole $defs entries and their internal references', () => {
  const result = pack('CORE-77');
  const original = read(TYPES); const sliced = fenced(result.text, TYPES + '（切片）');
  const doc = JSON.parse(sliced); const full = JSON.parse(original);
  assert.equal(doc.$schema, full.$schema); assert.equal(doc.title, full.title);
  for (const name of ['DimExpr', 'TypeExpr', 'DimensionFull', 'MathKind', 'Rational']) assert.ok(doc.$defs[name], name);
  const originalItems = new Map(jsonItems(original, '$defs').map(x => [x.key, x.text]));
  for (const item of jsonItems(sliced, '$defs')) assert.equal(item.text, originalItems.get(item.key));
  for (const def of Object.values(doc.$defs)) for (const ref of schemaRefs(def)) {
    const name = ref.match(/#\/\$defs\/(.+)$/)?.[1]; if (name) assert.ok(doc.$defs[name], 'closure ' + name);
  }
  const entry = result.report.filteredFiles.find(f => f.path === TYPES);
  assert.equal(entry.mode, 'sliced'); assert.ok(result.text.includes('（切片）'));
});

test('JSON filters keep original bytes for pretty and minified input and allow empty results', () => {
  const pretty = '{\n  "v": 1,\n  "ops": [\n    {"owner": "A", "x": "]}\\"," },\n    {\n      "owner": "B"\n    }\n  ],\n  "tail": true\n}\n';
  const a = filterJsonArray(pretty, 'ops', x => x.owner === 'B');
  assert.deepEqual(JSON.parse(a.text), {v: 1, ops: [{owner: 'B'}], tail: true}); assert.ok(a.text.includes('{\n      "owner": "B"\n    }'));
  const none = filterJsonArray(pretty, 'ops', () => false);
  assert.deepEqual(JSON.parse(none.text).ops, []); assert.equal(none.kept, 0); assert.equal(none.total, 2);
  const mini = '{"$defs":{"A":{"$ref":"#/$defs/B"},"B":{"type":"string"},"C":{}}}';
  const o = filterJsonObject(mini, '$defs', k => k !== 'C');
  assert.equal(o.text, '{"$defs":{"A":{"$ref":"#/$defs/B"},"B":{"type":"string"}}}');
});

test('fixture: owned schemas, $ref slices, vectors cited by acceptance and ADR rows are selected; the rest is listed', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sadd-pack-'));
  const sadd = path.join(root, 'SADD'); fs.mkdirSync(sadd);
  try {
    const card = (id, deps, contract, acceptance = 'fixture') => `### ${id} fixture\n\n**依赖**：${deps}\n\n**接口契约**\n\n${contract}\n\n**实现约束**\n\nfixture\n\n**验收标准**\n\n${acceptance}\n`;
    fs.writeFileSync(path.join(sadd, '01-公共核心-v5.md'), card('CORE-01', '', 'root') + card('CORE-02', '', 'errors') +
      card('CORE-10', 'CORE-01', 'owner of a.op', '- [R01] 向量 cited-v1 全部通过') + card('CORE-20', '', 'unrelated owner') +
      card('CORE-57', 'CORE-01、CORE-02、CORE-10', 'uses a.op；见 ADR-V5-07'));
    for (const f of ['02-Android端-v5.md', '03-Windows端-v5.md', 'README.md']) fs.writeFileSync(path.join(sadd, f), '');
    fs.writeFileSync(path.join(sadd, '附录A-架构决策与评审记录.md'), '## A.4 ADR\n\n### A.4.1 表\n\n| 编号 | 决策 | 结论 | 被否方案的代价 | 重新评估条件 | 状态 | 模块卡 |\n| --- | --- | --- | --- | --- | --- | --- |\n' +
      '| ADR-V5-07 | 相关 | x | x | x | 已采纳 | CORE-10 |\n| ADR-V5-08 | 本卡 | x | x | x | 已采纳 | CORE-57 |\n| ADR-V5-09 | 无关 | x | x | x | 已采纳 | CORE-20 |\n\n### A.4.2 补充 ADR-V5-07\n\nsupplement-evidence\n\n### A.4.3 无关\n\nunrelated-supplement\n');
    const dto = path.join(root, 'contracts/dto'); fs.mkdirSync(dto, {recursive: true});
    fs.mkdirSync(path.join(root, 'contracts/vectors'));
    fs.writeFileSync(path.join(dto, 'manifest.json'), JSON.stringify({version: 1, ops: [
      {op: 'a.op', owner: 'CORE-10', status: 'ready', schema: 'a.op.schema.json'},
      {op: 'b.op', owner: 'CORE-20', status: 'ready', schema: 'b.op.schema.json'}]}, null, 2));
    fs.writeFileSync(path.join(dto, 'a.op.schema.json'), '{"title":"a-op-body","$ref":"types.schema.json#/$defs/Alpha"}');
    fs.writeFileSync(path.join(dto, 'b.op.schema.json'), '{"title":"b-op-body"}');
    fs.writeFileSync(path.join(dto, 'types.schema.json'), '{"$defs":{"Alpha":{"$ref":"#/$defs/Beta"},"Beta":{"title":"beta-def"},"Gamma":{"title":"gamma-def"}}}');
    fs.writeFileSync(path.join(root, 'contracts/vectors/cited-v1.json'), '{"vector":"cited-body"}');
    fs.writeFileSync(path.join(root, 'contracts/vectors/other-v1.json'), '{"vector":"other-body"}');
    const result = pack('CORE-57', {sadd});
    const by = p => result.report.filteredFiles.find(f => f.path === p);
    assert.ok(result.text.includes('a-op-body') && !result.text.includes('b-op-body'));
    assert.equal(by('contracts/dto/b.op.schema.json').mode, 'listed');
    assert.ok(result.text.includes('beta-def') && !result.text.includes('gamma-def'));
    assert.deepEqual(by('contracts/dto/types.schema.json').entries, ['Alpha', 'Beta']);
    assert.ok(result.text.includes('cited-body') && !result.text.includes('other-body'));
    assert.equal(by('contracts/vectors/other-v1.json').mode, 'listed');
    assert.equal(by('contracts/dto/manifest.json').kept, 1);
    assert.ok(result.text.includes('| ADR-V5-07 |') && result.text.includes('| ADR-V5-08 |') && !result.text.includes('| ADR-V5-09 |'));
    assert.ok(result.text.includes('supplement-evidence') && !result.text.includes('unrelated-supplement'));
    assert.equal(by('SADD/附录A-架构决策与评审记录.md').mode, 'filtered');
    // --file 指定时收录全文。
    const forced = pack('CORE-57', {sadd, extra: ['contracts/dto/b.op.schema.json', 'contracts/dto/types.schema.json']});
    assert.ok(forced.text.includes('b-op-body') && forced.text.includes('gamma-def'));
  } finally {
    assert.equal(path.dirname(path.resolve(root)), path.resolve(os.tmpdir()));
    assert.ok(path.basename(root).startsWith('sadd-pack-'));
    fs.rmSync(root, {recursive: true, force: true});
  }
});

test('writeOutput removes stale part files and records how material.md relates to the parts', () => {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'sadd-pack-out-'));
  try {
    for (let i = 1; i <= 9; i++) fs.writeFileSync(path.join(out, `part-${i}.md`), 'stale');
    fs.writeFileSync(path.join(out, 'notes.txt'), 'keep');
    const result = pack('CORE-78');
    const {parts, removedStaleParts} = writeOutput(out, result);
    const names = fs.readdirSync(out).filter(n => /^part-\d+\.md$/.test(n)).sort();
    assert.deepEqual(names, parts.slice().sort()); assert.equal(parts.length, result.chunks.length);
    assert.equal(removedStaleParts.length, 9 - parts.length);
    assert.ok(fs.existsSync(path.join(out, 'notes.txt')));
    assert.equal(parts.map(p => read(path.join(out, p))).join(''), read(path.join(out, 'material.md')));
    const report = JSON.parse(read(path.join(out, 'report.json')));
    assert.equal(report.reading.material, 'material.md'); assert.deepEqual(report.reading.parts, parts);
    assert.match(report.reading.relation, /择一阅读/);
    assert.ok(Array.isArray(report.filteredFiles) && report.filteredFiles.length > 0);
    for (const f of report.filteredFiles) for (const k of ['path', 'originalBytes', 'includedBytes', 'reason', 'sha256', 'mode']) assert.ok(k in f, k);
  } finally {
    assert.ok(path.basename(out).startsWith('sadd-pack-out-'));
    fs.rmSync(out, {recursive: true, force: true});
  }
});

test('segmentation is exact: parts concatenate to the material byte for byte', () => {
  const text = 'a\n\n\n' + '```text\nx\n\ny\n```\n\n' + 'z\n'.repeat(5);
  const chunks = segment(text, 25);
  assert.equal(chunks.join(''), text);
  assert.ok(chunks.some(c => c.includes('```text\nx\n\ny\n```')));
  assert.throws(() => segment('x'.repeat(20), 10), /indivisible/);
});

test('denoising cuts material size markedly', () => {
  for (const id of ['CORE-77', 'CORE-78']) assert.ok(pack(id).report.chars < 100000, id);
  const r = pack('CORE-26');
  const saved = r.report.filteredFiles.reduce((s, f) => s + f.originalBytes - f.includedBytes, 0);
  assert.ok(saved > 150000, String(saved));
});


test('indirect dependencies contribute only blocks that define a needed symbol; mention-only blocks are counted', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sadd-pack-'));
  const sadd = path.join(root, 'SADD'); fs.mkdirSync(sadd);
  try {
    const card = (id, deps, contract) => `### ${id} fixture\n\n**依赖**：${deps}\n\n**接口契约**\n\n${contract}\n\n**实现约束**\n\nfixture\n\n`;
    const indirect = [
      '```rust\npub struct FooType { pub bar: BarType }\n```',
      '```rust\nimpl FooType {\n    pub fn helper(&self) -> u8;\n}\n```',
      '说明：FooType 只在 mention-only-prose 中被提到。',
      '```rust\npub struct BarType {}\n```',
      '```rust\npub struct UnrelatedType {}\n```',
      '| 码 | 级别 |\n| --- | --- |\n| `FOO_FAILED` | error |',
      '- `foo.do_thing` body={} ok={}',
      '```rust\npub const MAX_FOO: usize = 3;\n```',
    ].join('\n\n');
    fs.writeFileSync(path.join(sadd, '01-公共核心-v5.md'), card('CORE-01', '', 'root') + card('CORE-02', '', 'errors') +
      card('CORE-20', 'CORE-01', indirect) + card('CORE-10', 'CORE-20', 'direct uses FooType, FOO_FAILED, foo.do_thing and MAX_FOO') +
      card('CORE-57', 'CORE-01、CORE-02、CORE-10', 'target'));
    for (const f of ['02-Android端-v5.md', '03-Windows端-v5.md', 'README.md', '附录A-架构决策与评审记录.md']) fs.writeFileSync(path.join(sadd, f), '');
    const result = pack('CORE-57', {sadd});
    for (const s of ['pub struct FooType', 'impl FooType', 'pub struct BarType', '`FOO_FAILED` | error', '`foo.do_thing` body', 'MAX_FOO: usize']) assert.ok(result.text.includes(s), s);
    assert.ok(!result.text.includes('mention-only-prose')); assert.ok(!result.text.includes('UnrelatedType'));
    const entry = result.report.manifest.find(m => m.card === 'CORE-20');
    assert.equal(entry.mode, 'symbols'); assert.equal(entry.mentionOnly, 1);
    assert.deepEqual([...definedSymbols('impl<T> Display for FooType {}')], ['FooType']);
  } finally {
    assert.equal(path.dirname(path.resolve(root)), path.resolve(os.tmpdir()));
    assert.ok(path.basename(root).startsWith('sadd-pack-'));
    fs.rmSync(root, {recursive: true, force: true});
  }
});
