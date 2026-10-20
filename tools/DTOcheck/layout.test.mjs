import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {tmpRoot, makeSadd, write} from './fixture.mjs';
import {checkCards} from './cards.mjs';
import {load} from '../sadd/pack.mjs';
import {readDocs, FILES} from '../sadd/layout.mjs';
import {splitTexts} from '../sadd/split.mjs';
import {extractTests} from '../sadd/split-tests.mjs';
import {testRelOf} from '../sadd/layout.mjs';

const ids = r => r.errors.map(e => e.id);
const groupOf = new Map([['CORE-01', '基座'], ['CORE-02', '基座'], ['CORE-05', '引擎'], ['AND-01', '平台'], ['WIN-01', '基座']]);

/** 生成合法夹具并转为拆分布局；返回 {root, sadd, original}。 */
function splitFixture() {
  const root = tmpRoot(); const sadd = makeSadd(root);
  const original = readDocs(sadd).texts;
  const {files, errors} = splitTexts(original, {groupOf});
  assert.deepEqual(errors, []);
  for (const f of FILES) fs.rmSync(path.join(sadd, f));
  for (const [f, t] of files) write(path.join(sadd, f), t);
  return {root, sadd, original};
}

test('拆分布局：文件名、文件夹与拼回结果', () => {
  const {sadd, original} = splitFixture();
  assert.deepEqual(fs.readdirSync(path.join(sadd, 'S0')).sort(), ['S0_CORE-01_基座.md', 'S0_CORE-02_基座.md', 'S0_WIN-01_基座.md']);
  assert.deepEqual(fs.readdirSync(path.join(sadd, 'core')).sort(), ['00-总览.md', 'S1_CORE-05_引擎.md']);
  assert.deepEqual(fs.readdirSync(path.join(sadd, 'and')).sort(), ['00-总览.md', 'S2_AND-01_平台.md']);
  const back = readDocs(sadd);
  assert.equal(back.layout, 'split');
  for (const f of FILES) assert.equal(back.texts[f], original[f]);
  assert.deepEqual(back.issues, []);
  assert.deepEqual(checkCards({sadd}).errors, []);
  const c = load(sadd).get('CORE-05');
  assert.equal(c.file, 'core/S1_CORE-05_引擎.md'); assert.equal(c.line, 1); assert.equal(c.doc, '01-公共核心-v5.md');
});

test('拆分布局：阶段、文件夹、分组、命名不符都报错', () => {
  const mv = (sadd, a, b) => fs.renameSync(path.join(sadd, a), path.join(sadd, b));
  let {sadd} = splitFixture(); mv(sadd, 'core/S1_CORE-05_引擎.md', 'core/S2_CORE-05_引擎.md');
  assert.ok(ids(checkCards({sadd})).includes('LAYOUT-02'));
  ({sadd} = splitFixture()); mv(sadd, 'S0/S0_WIN-01_基座.md', 'win/S0_WIN-01_基座.md');
  assert.ok(ids(checkCards({sadd})).includes('LAYOUT-03'));
  ({sadd} = splitFixture()); mv(sadd, 'core/S1_CORE-05_引擎.md', 'core/S1_CORE-05_杂项.md');
  assert.ok(ids(checkCards({sadd})).includes('LAYOUT-01'));
  ({sadd} = splitFixture()); write(path.join(sadd, 'core', 'CORE-05.md'), 'x');
  assert.ok(ids(checkCards({sadd})).includes('LAYOUT-01'));
});

test('拆分布局：卡片文件内容与总览标记必须对应', () => {
  let {sadd} = splitFixture();
  const f = path.join(sadd, 'core', 'S1_CORE-05_引擎.md');
  fs.writeFileSync(f, fs.readFileSync(f, 'utf8').replace('### CORE-05', '### CORE-06'));
  assert.ok(ids(checkCards({sadd})).includes('LAYOUT-04'));
  ({sadd} = splitFixture());
  const o = path.join(sadd, 'core', '00-总览.md');
  fs.writeFileSync(o, fs.readFileSync(o, 'utf8').replace('<!-- sadd:card CORE-05 -->\n', ''));
  assert.ok(ids(checkCards({sadd})).includes('LAYOUT-05'));
  ({sadd} = splitFixture());
  const o2 = path.join(sadd, 'core', '00-总览.md');
  fs.writeFileSync(o2, fs.readFileSync(o2, 'utf8') + '<!-- sadd:card CORE-09 -->\n');
  assert.ok(ids(checkCards({sadd})).includes('CARD-00'));
});

test('旧文档与拆分文件夹并存时拒绝读取', () => {
  const {sadd} = splitFixture();
  write(path.join(sadd, FILES[0]), '# x\n');
  assert.throws(() => readDocs(sadd), /同时存在/);
});

// ---- 测试方案剥离到 SADD/Test/ ----

/** 拆分夹具 + 给 CORE-05、WIN-01 补“验收标准”，返回剥离前的文档文本。 */
function testFixture() {
  const fx = splitFixture();
  const add = (rel, text) => { const f = path.join(fx.sadd, rel); fs.writeFileSync(f, fs.readFileSync(f, 'utf8').replace('**规模**', text + '**规模**')); };
  add('core/S1_CORE-05_引擎.md', '**验收标准**\n- [R01] 第一条\n\n- [R02] 第二条，含 ```rust\nlet x = 1;\n```\n\n');
  add('S0/S0_WIN-01_基座.md', '**验收标准**\n- [R03] 只有一条\n\n');
  const before = readDocs(fx.sadd).texts;
  const {files, errors} = extractTests(fx.sadd);
  assert.deepEqual(errors, []);
  for (const [f, t] of files) write(path.join(fx.sadd, f), t);
  return {...fx, before};
}

test('测试方案剥离：文件位置、引用行与逐字节拼回', () => {
  const {sadd, before} = testFixture();
  assert.deepEqual(fs.readdirSync(path.join(sadd, 'Test')).sort(), ['S0', 'core']);
  assert.deepEqual(fs.readdirSync(path.join(sadd, 'Test/core')), ['S1_CORE-05_TEST.md']);
  assert.deepEqual(fs.readdirSync(path.join(sadd, 'Test/S0')), ['S0_WIN-01_TEST.md']);
  const card = fs.readFileSync(path.join(sadd, 'core/S1_CORE-05_引擎.md'), 'utf8');
  assert.ok(card.includes('**验收标准**：测试方案全文见 [Test/core/S1_CORE-05_TEST.md](../Test/core/S1_CORE-05_TEST.md)'));
  assert.ok(!card.includes('第一条'));
  const test = fs.readFileSync(path.join(sadd, 'Test/core/S1_CORE-05_TEST.md'), 'utf8');
  assert.ok(test.startsWith('# CORE-05 测试方案\n')); assert.ok(test.includes('](../../core/S1_CORE-05_引擎.md)'));
  const back = readDocs(sadd);
  for (const f of FILES) assert.equal(back.texts[f], before[f]);
  assert.deepEqual(back.issues, []);
  assert.deepEqual(checkCards({sadd}).errors, []);
  const c = load(sadd).get('CORE-05');
  assert.equal(c.testFile, 'Test/core/S1_CORE-05_TEST.md'); assert.ok(c.body.includes('第二条'));
  assert.equal(extractTests(sadd).files.size, 0);   // 已剥离的卡不再处理
});

test('测试方案剥离：缺失、孤立、命名不符、内联残留都报错', () => {
  let {sadd} = testFixture();
  fs.rmSync(path.join(sadd, 'Test/core/S1_CORE-05_TEST.md'));
  assert.ok(ids(checkCards({sadd})).includes('LAYOUT-06'));
  ({sadd} = testFixture());
  write(path.join(sadd, 'Test/core/S1_CORE-09_TEST.md'), '# CORE-09 测试方案\n\n**验收标准**\n- x\n');
  assert.ok(ids(checkCards({sadd})).includes('LAYOUT-06'));
  ({sadd} = testFixture());
  write(path.join(sadd, 'Test/core/CORE-05-test.md'), 'x');
  assert.ok(ids(checkCards({sadd})).includes('LAYOUT-06'));
  ({sadd} = testFixture());
  // 阶段改名：卡片改名而测试文件未改名
  fs.renameSync(path.join(sadd, 'core/S1_CORE-05_引擎.md'), path.join(sadd, 'core/S2_CORE-05_引擎.md'));
  const r = checkCards({sadd}); assert.ok(ids(r).includes('LAYOUT-06'));
  assert.equal(testRelOf('core', 'S2', 'CORE-05'), 'Test/core/S2_CORE-05_TEST.md');
  ({sadd} = testFixture());
  const f = path.join(sadd, 'Test/core/S1_CORE-05_TEST.md');
  fs.writeFileSync(f, fs.readFileSync(f, 'utf8').replace('# CORE-05 测试方案', '# CORE-06 测试方案'));
  assert.ok(ids(checkCards({sadd})).includes('LAYOUT-06'));
  ({sadd} = testFixture());
  const w = path.join(sadd, 'S0/S0_WIN-01_基座.md');
  fs.writeFileSync(w, fs.readFileSync(w, 'utf8').replace(/^\*\*验收标准\*\*：[^\n]*\n/m, '**验收标准**\n- 内联残留\n'));
  assert.ok(ids(checkCards({sadd})).includes('LAYOUT-07'));
});
