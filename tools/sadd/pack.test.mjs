import test from 'node:test';
import assert from 'node:assert/strict';
import {pack, load, blocks, segment, writeOutput, filterJsonArray, filterJsonObject, jsonItems, schemaRefs, definedSymbols} from './pack.mjs';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import * as packModule from './pack.mjs';

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
  // 完整收录 ffi 2.2.0 / ffigen 23.0.0 锁文件后，主线单变量锁替换实测 CORE-77/78 为 131843/143402 字符；
  // 锁文件增加 5672 字符，filteredFiles/manifest 不变。固定上限 140000/150000 留约 6%/5% 余量，超出仍须先排查去噪回归，不能裁剪锁或契约。
  for (const [id, max] of [['CORE-77', 140000], ['CORE-78', 150000]]) assert.ok(pack(id).report.chars < max, id);
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


// ---- 退出码分类、超量报警、公开面与 CO-60-1（卡 :16/:19，测试方案 L7/L10/L12/L14） ----
const run = args => spawnSync(process.execPath, [path.resolve('tools/sadd/pack.mjs'), ...args], {cwd: process.cwd(), encoding: 'utf8'});
const outDir = () => fs.mkdtempSync(path.join(os.tmpdir(), 'sadd-pack-run-'));
const partNames = dir => { if (!fs.existsSync(dir)) return []; return fs.readdirSync(dir).filter(n => n.startsWith('part-') && n.endsWith('.md')).sort((a, b) => parseInt(a.slice(5), 10) - parseInt(b.slice(5), 10)); };

test('CLI exits 2 for usage and contract errors and writes no material', () => {
  const none = run([]);
  assert.equal(none.status, 2); assert.match(none.stderr, /Usage/);
  const dir = outDir();
  try {
    const unknown = run(['CORE-999', '--out', dir]);
    assert.equal(unknown.status, 2); assert.match(unknown.stderr, /Unknown card/);
    assert.ok(!fs.existsSync(path.join(dir, 'material.md')));
    const outside = run(['CORE-01', '--out', dir, '--file', '../outside.txt']);
    assert.equal(outside.status, 2); assert.match(outside.stderr, /outside workspace/);
    assert.deepEqual(partNames(dir), []);
    assert.ok(!fs.existsSync(path.join(dir, 'material.md')));
  } finally { fs.rmSync(dir, {recursive: true, force: true}); }
});

// 卡 :19：取值缺失或紧接另一选项属于用法错误（2），不得落成 TypeError（3）或静默回退默认值（C57-N1）。
test('CLI treats missing option values as usage errors and writes no material', () => {
  const cwd = fs.mkdtempSync(path.join(os.tmpdir(), 'sadd-pack-run-'));
  const inCwd = args => spawnSync(process.execPath, [path.resolve('tools/sadd/pack.mjs'), ...args], {cwd, encoding: 'utf8'});
  try {
    const cases = [
      [['CORE-57', '--file'], /Missing value for --file/],
      [['CORE-57', '--file', '--with-tests'], /Missing value for --file/],
      [['CORE-57', '--out'], /Missing value for --out/],
      [['CORE-57', '--sadd'], /Missing value for --sadd/],
      [['CORE-57', '--sadd', '--out', path.join(cwd, 'packed')], /Missing value for --sadd/],
    ];
    for (const [args, message] of cases) {
      const result = inCwd(args);
      assert.equal(result.status, 2, args.join(' ') + ' -> ' + result.stderr);
      assert.match(result.stderr, message);
    }
    // 默认输出目录也不得被静默写出：--out 缺值不得回退 build/sadd/<卡号>。
    assert.ok(!fs.existsSync(path.join(cwd, 'build')));
  } finally { fs.rmSync(cwd, {recursive: true, force: true}); }
});

test('CLI exits 2 for an indivisible block above 80000 and 3 for unexpected internal failures', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sadd-pack-'));
  const sadd = path.join(root, 'SADD'); fs.mkdirSync(sadd);
  const out = path.join(root, 'out');
  try {
    const card = (id, deps, contract) => '### ' + id + ' fixture\n\n**依赖**：' + deps + '\n\n**接口契约**\n\n' + contract + '\n\n**实现约束**\nfixture\n';
    const write = text => fs.writeFileSync(path.join(sadd, '01-公共核心-v5.md'),
      card('CORE-01', '', 'root') + card('CORE-02', '', 'errors') + card('CORE-57', 'CORE-01、CORE-02', text));
    for (const f of ['02-Android端-v5.md', '03-Windows端-v5.md', 'README.md', '附录A-架构决策与评审记录.md']) fs.writeFileSync(path.join(sadd, f), '');
    write('y'.repeat(80001));
    const big = run(['CORE-57', '--sadd', sadd, '--out', out]);
    assert.equal(big.status, 2); assert.match(big.stderr, /Single indivisible block/);
    assert.ok(!fs.existsSync(path.join(out, 'material.md')));
    // 未预期内部异常（contracts JSON 损坏）必须落到 3，不得落到 1。
    fs.mkdirSync(path.join(root, 'contracts/dto'), {recursive: true});
    write('fixture contract');
    fs.writeFileSync(path.join(root, 'contracts/dto/manifest.json'), '{not json');
    const broken = run(['CORE-57', '--sadd', sadd, '--out', out]);
    assert.equal(broken.status, 3); assert.match(broken.stderr, /^pack: /);
    assert.ok(!fs.existsSync(path.join(out, 'material.md')));
    assert.deepEqual(partNames(out), []);
  } finally {
    assert.ok(path.basename(root).startsWith('sadd-pack-'));
    fs.rmSync(root, {recursive: true, force: true});
  }
});

test('--check-budget exits 1 on an over-limit card with complete material and 0 without the flag', () => {
  const dir = outDir();
  try {
    const on = run(['WIN-13', '--out', dir, '--check-budget']);
    assert.equal(on.status, 1);
    const report = JSON.parse(read(path.join(dir, 'report.json')));
    const material = read(path.join(dir, 'material.md'));
    assert.equal(report.overLimit, true); assert.ok(report.chars > 80000);
    assert.equal(report.chars, [...material].length);
    const parts = partNames(dir);
    assert.deepEqual(parts, report.reading.parts);
    assert.equal(parts.length, report.segments);
    assert.equal(parts.map(p => read(path.join(dir, p))).join(''), material);
    const off = run(['WIN-13', '--out', dir]);
    assert.equal(off.status, 0);
    const again = JSON.parse(read(path.join(dir, 'report.json')));
    assert.equal(again.overLimit, true); assert.equal(again.chars, report.chars);
  } finally { fs.rmSync(dir, {recursive: true, force: true}); }
});

test('oversized read-only fixture cards report chars, segments, overLimit, manifest and missing locks', () => {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'sadd-pack-big-'));
  try {
    for (const id of ['WIN-13', 'AND-12', 'WIN-14', 'WIN-08', 'CORE-50']) {
      const dir = path.join(base, id); const result = pack(id);
      const {parts, removedStaleParts} = writeOutput(dir, result);
      assert.deepEqual(removedStaleParts, []);
      const material = read(path.join(dir, 'material.md'));
      assert.equal(result.report.chars, [...material].length, id + ' chars');
      assert.equal(result.report.segments, parts.length, id + ' segments');
      assert.deepEqual(partNames(dir), parts.map((_, i) => 'part-' + (i + 1) + '.md'), id + ' part numbering');
      assert.ok(result.report.chars > 80000, id + ' over limit');
      assert.equal(result.report.overLimit, true);
      assert.ok(result.report.warnings.some(w => /超过 80000/.test(w)), id + ' over-limit warning');
      assert.ok(result.report.manifest.length > 0, id + ' manifest');
      for (const entry of result.report.manifest) for (const k of ['card', 'before', 'after', 'retained']) assert.ok(k in entry, id + ' ' + k);
      assert.ok(result.report.missing.some(f => /toolchain\.versions$/.test(f)), id + ' missing locks');
      assert.equal(parts.map(p => read(path.join(dir, p))).join(''), material, id + ' lossless parts');
    }
  } finally {
    assert.ok(path.basename(base).startsWith('sadd-pack-big-'));
    fs.rmSync(base, {recursive: true, force: true});
  }
});

test('public surface stays fixed and report.json keeps the card field order', () => {
  for (const name of ['ROOT', 'FILES', 'load', 'pack', 'segment', 'blocks', 'definedSymbols', 'schemaRefs', 'jsonItems', 'filterJsonArray', 'filterJsonObject', 'writeOutput']) assert.ok(name in packModule, name + ' exported');
  for (const name of ['listContracts', 'skipString', 'skipValue', 'members', 'rebuild', 'selectAdr']) assert.ok(!(name in packModule), name + ' stays internal');
  assert.equal(typeof packModule.ROOT, 'string');
  const deps = load().get('CORE-78').deps;
  const result = pack('CORE-78');
  assert.deepEqual(Object.keys(result).sort(), ['chunks', 'report', 'text']);
  assert.equal(result.chunks.join(''), result.text);
  assert.deepEqual(result.report.closure, deps);
  assert.deepEqual([...result.report.related].sort(), [...new Set(['CORE-78', ...deps, 'CORE-01', 'CORE-02'])].sort());
  const dir = outDir();
  try {
    const {parts, removedStaleParts} = writeOutput(dir, result, {node: 'v-fixture'});
    const report = JSON.parse(read(path.join(dir, 'report.json')));
    assert.deepEqual(Object.keys(report), ['id', 'chars', 'overLimit', 'segments', 'tests', 'closure', 'related', 'manifest', 'files', 'filteredFiles', 'adr', 'missing', 'warnings', 'missingFromMaterials', 'undefinedIdentifiers', 'classifiedReferences', 'excludedSupplements', 'reading', 'removedStaleParts', 'node']);
    assert.equal(report.node, 'v-fixture');
    assert.deepEqual(removedStaleParts, []);
    assert.equal(parts.length, result.chunks.length);
  } finally { fs.rmSync(dir, {recursive: true, force: true}); }
});

test('the policy maintainer in the closure gets the whole file; zero-hit filtering warns (CO-60-1)', () => {
  const sw = read(SW); const entries = JSON.parse(sw).entries;
  const maintainer = entries.find(e => e.kind === 'file' && e.key === SW).owner;
  assert.equal(maintainer, 'CORE-75');
  const r75 = pack('CORE-75');
  assert.ok(r75.report.files.includes(SW), 'maintainer file is collected whole');
  assert.equal(fenced(r75.text, SW + '（整文件收录）'), sw);
  assert.ok(r75.report.warnings.some(w => w.includes(SW) && w.includes(maintainer) && /整文件收录/.test(w)), 'explicit warning');
  const entry = r75.report.filteredFiles.find(f => f.path === SW);
  assert.equal(entry.kept, entries.length); assert.equal(entry.total, entries.length);
  assert.equal(entry.sha256, sha(sw)); assert.equal(entry.includedBytes, Buffer.byteLength(sw));
  // 维护者不在相关卡内时仍按 owner 过滤；命中 0 条不得静默。
  const r67 = pack('CORE-67');
  for (const file of [SW, MAN]) {
    const hit = r67.report.filteredFiles.find(f => f.path === file);
    assert.equal(hit.mode, 'filtered'); assert.equal(hit.kept, 0); assert.ok(hit.total > 0, file + ' total');
    assert.ok(r67.report.warnings.some(w => w.includes(file) && /0\//.test(w)), file + ' zero-hit warning');
  }
});

// ---- 错误码 contracts（CORE-02 阶段1）按相关性收录 ----
const ERR_REGISTRY = 'contracts/errors/registry.yaml', ERR_OWNERSHIP = 'contracts/errors/ownership.yaml';
const ERR_README = 'contracts/errors/README.md', ERR_VECTOR = 'contracts/vectors/errors-v1.json';

test('errors contracts are complete for the card that owns them (CORE-02)', () => {
  // 失败情形：registry 或任一生成镜像/错误向量被改成按相关卡过滤或只列名时，report.files 不再含该路径、
  // material 里没有该文件全文，或出现切片/过滤标题——任一断言即失败；放宽成“只要提到就整收”的反向改动
  // 会被 CORE-77/CORE-78 的上限用例抓住。
  const result = pack('CORE-02');
  for (const file of [ERR_REGISTRY, ERR_OWNERSHIP, ERR_README, ERR_VECTOR]) {
    assert.ok(result.report.files.includes(file), file + ' file-list');
    assert.equal(result.report.filteredFiles.find(f => f.path === file), undefined, file + ' not filtered');
    assert.ok(result.text.includes(read(file)), file + ' full text');
  }
  assert.ok(!result.text.includes(ERR_REGISTRY + '（按 owner/引用过滤）'), 'owner card has no slice');
  assert.ok(!result.report.warnings.some(w => w.includes(ERR_REGISTRY)), 'no slice warning');
});

test('errors contracts are sliced or listed by relevance for a card that does not own them (CORE-77)', () => {
  // 失败情形（逐条对应断言）：registry 退回整收 → 不再有 filteredFiles 切片条目、report.files 含该路径、
  // 材料里没有“按 owner/引用过滤”小节；切片丢掉 entries: 以上头部 → 头部断言失败；切片漏收相关 owner 或
  // 正文引用的 code → 逐条 owner/正文断言与 kept/entries 断言失败；切片把不相关条目带进来 → 同上逐条断言失败；
  // 生成镜像或错误向量改回整收 → 只列名断言与“正文不含其内容”断言失败；--file 不再恢复全文 → 末尾断言失败。
  const id = 'CORE-77';
  const result = pack(id);
  const target = load(undefined, {tests: false}).get(id);
  const original = read(ERR_REGISTRY);
  assert.ok(!result.report.files.includes(ERR_REGISTRY), 'registry not whole');
  assert.ok(!result.text.includes(original), 'no full registry text');
  const entry = result.report.filteredFiles.find(f => f.path === ERR_REGISTRY);
  assert.equal(entry.mode, 'sliced');
  assert.equal(entry.sha256, sha(original));
  assert.equal(entry.originalBytes, Buffer.byteLength(original));
  assert.ok(entry.includedBytes > 0 && entry.includedBytes < entry.originalBytes, String(entry.includedBytes));
  assert.ok(entry.kept > 0 && entry.kept < entry.total, entry.kept + '/' + entry.total);
  const slice = fenced(result.text, ERR_REGISTRY + '（按 owner/引用过滤）');
  const head = original.slice(0, original.indexOf('entries:\n') + 'entries:\n'.length);
  assert.ok(slice.startsWith(head), 'header kept');
  assert.ok(slice.includes('registry_version: 1'), 'registry_version kept');
  assert.ok(result.text.includes('原文件 SHA-256=' + entry.sha256), 'note carries original sha');
  const blocks = slice.slice(head.length).split(/^(?=  - code: )/m).filter(block => block.trim());
  assert.equal(blocks.length, entry.kept, 'block count');
  const related = new Set(result.report.related);
  const codes = [];
  for (const block of blocks) {
    const code = block.match(/^  - code: (\S+)/)[1];
    const owner = block.match(/^ {4}owner: (\S+)$/m)[1];
    codes.push(code);
    assert.ok(related.has(owner) || new RegExp('(?<![A-Za-z0-9_])' + code + '(?![A-Za-z0-9_])').test(target.body), code + '/' + owner);
    assert.ok(block.includes('namespace: ') || block.includes('severity: '), code + ' entry body kept');
  }
  assert.deepEqual(codes, entry.entries);
  const omitted = original.split(/^(?=  - code: )/m).slice(1).map(b => b.match(/^  - code: (\S+)/)[1]).find(c => !codes.includes(c));
  assert.ok(omitted, 'some entry omitted');
  assert.ok(!slice.includes('  - code: ' + omitted), 'omitted entry absent');
  for (const file of [ERR_OWNERSHIP, ERR_README, ERR_VECTOR]) {
    const listed = result.report.filteredFiles.find(f => f.path === file);
    assert.equal(listed.mode, 'listed', file);
    assert.equal(listed.includedBytes, 0, file);
    assert.equal(listed.sha256, sha(read(file)), file);
    assert.equal(listed.originalBytes, Buffer.byteLength(read(file)), file);
    assert.ok(!result.report.files.includes(file), file + ' not whole');
    assert.ok(result.text.includes('| ' + file + ' | ' + listed.originalBytes + ' | ' + listed.sha256 + ' |'), file + ' listed row');
    assert.ok(!result.text.includes(read(file)), file + ' no body');
  }
  const forced = pack(id, {extra: [ERR_REGISTRY]});
  assert.ok(forced.report.files.includes(ERR_REGISTRY), '--file restores registry');
  assert.ok(forced.text.includes(original), '--file restores full text');
});
