import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {tmpRoot, makeSadd, write} from './fixture.mjs';
import {checkCards} from './cards.mjs';
import {load} from '../sadd/pack.mjs';
import {readDocs, FILES} from '../sadd/layout.mjs';
import {splitTexts} from '../sadd/split.mjs';

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
