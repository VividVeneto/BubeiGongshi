import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync, spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {cardiffAll, cardiffOne, cutCards, diffLines, unified, formatAll, CardiffError} from './cardiff.mjs';
import {marker, testRef, testHeader, testRelOf} from './layout.mjs';

const CLI = path.join(path.dirname(fileURLToPath(import.meta.url)), 'cardiff.mjs');
const git = (dir, ...args) => execFileSync('git', ['-C', dir, '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', ...args], {encoding: 'utf8'});
const write = (dir, rel, text) => { fs.mkdirSync(path.dirname(path.join(dir, rel)), {recursive: true}); fs.writeFileSync(path.join(dir, rel), text); };
const tmp = () => fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'cardiff-'));
const rmAll = dir => fs.rmSync(dir, {recursive: true, force: true});

const ACCEPT = ['**验收标准**', '- [R01] 同键覆盖', '- [R01] 删除幂等', ''].join('\n');
/** 卡片全文：accept 为 null 时不含验收标准（拆分布局中由引用行代替）。 */
const cardText = (id, title, {body = '正文一行', scale = '**规模**：约 100 行', accept = ACCEPT} = {}) =>
  ['### ' + id + ' ' + title, '', '**目标**：' + title, '', '**接口契约**', body, '', '**实现约束**', '- 约束', '', accept, scale, '', ''].join('\n');
const legacyDoc = (title, intro, cards, tailText = '## 4. 附录\n\n附录内容\n') =>
  '# ' + title + '\n\n' + intro + '\n\n## 3. 模块索引\n\n索引表\n\n## 5. 模块卡\n\n' + cards.join('') + tailText;

/** 基线：旧三份文档（01 含 CORE-01、CORE-02；02/03 无卡）。 */
function baseRepo(dir, cards = [cardText('CORE-01', '骨架'), cardText('CORE-02', '错误码')]) {
  git(dir, 'init', '-q');
  write(dir, 'SADD/01-公共核心-v5.md', legacyDoc('公共核心', '旧引言', cards));
  write(dir, 'SADD/02-Android端-v5.md', '# Android\n\n无卡\n');
  write(dir, 'SADD/03-Windows端-v5.md', '# Windows\n\n无卡\n');
  git(dir, 'add', '-A'); git(dir, 'commit', '-qm', 'base');
  return git(dir, 'rev-parse', 'HEAD').trim();
}
/** 当前：拆分布局。cards: [{id, group, text, test?}]，test 为测试方案“验收标准”行起的全文。 */
function splitNow(dir, cards, {intro = '新引言（章节标题与引言改了）'} = {}) {
  for (const f of ['01-公共核心-v5.md', '02-Android端-v5.md', '03-Windows端-v5.md']) fs.rmSync(path.join(dir, 'SADD', f), {force: true});
  write(dir, 'SADD/core/00-总览.md', '# 公共核心\n\n' + intro + '\n\n## 3. 模块索引\n\n新索引表\n\n## 5. 模块卡\n\n' + cards.map(c => marker(c.id) + '\n').join('') + '\n## 4. 附录\n\n附录内容\n');
  write(dir, 'SADD/and/00-总览.md', '# Android\n');
  write(dir, 'SADD/win/00-总览.md', '# Windows\n');
  for (const c of cards) {
    const rel = testRelOf('core', 'S1', c.id);
    const raw = c.test == null ? c.text : c.text.replace(ACCEPT, testRef(rel) + '\n');
    write(dir, 'SADD/core/S1_' + c.id + '_' + (c.group ?? '引擎') + '.md', raw);
    if (c.test != null) write(dir, 'SADD/' + rel, testHeader(c.id, c.title ?? c.id, 'core', 'S1_' + c.id + '_引擎.md') + c.test);
  }
}
const withRepo = fn => { const dir = tmp(); try { return fn(dir, baseRepo(dir)); } finally { rmAll(dir); } };
const ids = list => list.map(x => x.id);

test('仅布局变化（拆分、章节标题、引言、卡片标记）不报', () => withRepo((dir, base) => {
  splitNow(dir, [{id: 'CORE-01', text: cardText('CORE-01', '骨架')}, {id: 'CORE-02', text: cardText('CORE-02', '错误码')}]);
  const r = cardiffAll({repo: dir, base});
  assert.deepEqual([ids(r.changed), ids(r.scaleOnly), ids(r.added), ids(r.removed)], [[], [], [], []]);
  assert.equal(r.unchanged.length, 2);
  assert.deepEqual(r.issues, []);
  assert.match(cardiffOne('CORE-01', {repo: dir, base}), /无内容变化/);
}));

test('验收标准搬到 Test/ 不报；引用的测试方案缺失时才会报', () => withRepo((dir, base) => {
  const body = ACCEPT;
  splitNow(dir, [{id: 'CORE-01', text: cardText('CORE-01', '骨架'), test: body}, {id: 'CORE-02', text: cardText('CORE-02', '错误码'), test: body}]);
  assert.ok(fs.existsSync(path.join(dir, 'SADD', testRelOf('core', 'S1', 'CORE-01'))));
  assert.ok(!fs.readFileSync(path.join(dir, 'SADD/core/S1_CORE-01_引擎.md'), 'utf8').includes('同键覆盖'), '卡片里已没有验收条目');
  const r = cardiffAll({repo: dir, base});
  assert.deepEqual([ids(r.changed), ids(r.scaleOnly), ids(r.added)], [[], [], []]);
  assert.deepEqual(r.issues, []);
  // 反例：测试方案文件被删，引用行取不回，必须暴露为差异和布局问题，而不是静默通过。
  fs.rmSync(path.join(dir, 'SADD', testRelOf('core', 'S1', 'CORE-01')));
  const bad = cardiffAll({repo: dir, base});
  assert.deepEqual(ids(bad.changed), ['CORE-01']);
  assert.ok(bad.issues.some(i => i.id === 'LAYOUT-06'));
}));

test('只改规模行：归入“仅规模口径”，不进内容变化', () => withRepo((dir, base) => {
  splitNow(dir, [
    {id: 'CORE-01', text: cardText('CORE-01', '骨架', {scale: '**规模**：约 80 行（不计测试代码）'}), test: ACCEPT},
    {id: 'CORE-02', text: cardText('CORE-02', '错误码'), test: ACCEPT}]);
  const r = cardiffAll({repo: dir, base});
  assert.deepEqual(ids(r.scaleOnly), ['CORE-01']);
  assert.deepEqual(ids(r.changed), []);
  assert.deepEqual(r.scaleOnly[0].scale, {old: ['**规模**：约 100 行'], new: ['**规模**：约 80 行（不计测试代码）']});
  const one = cardiffOne('CORE-01', {repo: dir, base});
  assert.match(one, /仅规模口径/);
  assert.match(one, /^-\*\*规模\*\*：约 100 行$/m);
  assert.match(one, /^\+\*\*规模\*\*：约 80 行/m);
  assert.equal(r.unchanged.length, 1);
}));

test('内容差异：报告增删字符，单卡输出 unified diff；规模行同时变化会标注', () => withRepo((dir, base) => {
  splitNow(dir, [
    {id: 'CORE-01', text: cardText('CORE-01', '骨架', {body: '新的正文一行加长', scale: '**规模**：约 90 行'}), test: ACCEPT},
    {id: 'CORE-02', text: cardText('CORE-02', '错误码'), test: ACCEPT}]);
  const r = cardiffAll({repo: dir, base});
  assert.deepEqual(ids(r.changed), ['CORE-01']);
  const c = r.changed[0];
  assert.deepEqual([c.addLines, c.delLines, c.addChars, c.delChars], [1, 1, '新的正文一行加长'.length, '正文一行'.length]);
  assert.deepEqual(ids(r.scaleOnly), []);
  const one = cardiffOne('CORE-01', {repo: dir, base});
  assert.match(one, /内容变化 \+8 \/ -4 字符/);
  assert.match(one, /^--- .*:CORE-01$/m);
  assert.match(one, /^@@ -\d+,\d+ \+\d+,\d+ @@$/m);
  assert.match(one, /^-正文一行$/m);
  assert.match(one, /^\+新的正文一行加长$/m);
  assert.match(one, /^-\*\*规模\*\*：约 100 行$/m, '单卡 diff 同时显示规模行');
  assert.match(formatAll(r), /规模行也有变化/);
}));

test('新增卡与删除卡', () => withRepo((dir, base) => {
  splitNow(dir, [
    {id: 'CORE-01', text: cardText('CORE-01', '骨架'), test: ACCEPT},
    {id: 'CORE-03', text: cardText('CORE-03', '新卡'), test: ACCEPT}]);
  const r = cardiffAll({repo: dir, base});
  assert.deepEqual(ids(r.added), ['CORE-03']);
  assert.deepEqual(ids(r.removed), ['CORE-02']);
  assert.match(cardiffOne('CORE-03', {repo: dir, base}), /新增卡/);
  assert.match(cardiffOne('CORE-02', {repo: dir, base}), /已没有这张卡/);
  assert.throws(() => cardiffOne('CORE-99', {repo: dir, base}), CardiffError);
}));

test('基线缺失：提交不存在、基线没有旧文档，都抛错且 CLI 退出码为 2', () => {
  const dir = tmp();
  try {
    const base = baseRepo(dir);
    splitNow(dir, [{id: 'CORE-01', text: cardText('CORE-01', '骨架'), test: ACCEPT}, {id: 'CORE-02', text: cardText('CORE-02', '错误码'), test: ACCEPT}]);
    git(dir, 'add', '-A'); git(dir, 'commit', '-qm', 'split');
    const head = git(dir, 'rev-parse', 'HEAD').trim();
    assert.throws(() => cardiffAll({repo: dir, base: 'deadbeef00000'}), /基线提交不存在/);
    assert.throws(() => cardiffAll({repo: dir, base: head}), /没有旧三份文档/);
    const run = (...args) => spawnSync(process.execPath, [CLI, ...args, '--repo', dir], {encoding: 'utf8'});
    assert.equal(run('--all', '--base', 'deadbeef00000').status, 2);
    assert.equal(run('CORE-01', '--base', head).status, 2);
    assert.equal(run('CORE-01', '--base', base).status, 0, '正常基线退出 0');
    assert.equal(run('CORE-1x', '--base', base).status, 2, '卡号格式错误');
    assert.equal(spawnSync(process.execPath, [CLI], {encoding: 'utf8'}).status, 2, '缺参数');
    const all = run('--all', '--base', base);
    assert.equal(all.status, 0, all.stderr);
    assert.match(all.stdout, /## 内容变化（0）/);
    assert.match(all.stdout, /## 仅规模口径（0）/);
    assert.match(all.stdout, /## 新增卡（0）/);
  } finally { rmAll(dir); }
});

test('切卡：围栏内的假标题不算卡，标题与列表之前的章节不并入上一张卡', () => {
  const text = '# T\n\n## 5\n\n### CORE-01 甲\n\n正文\n```\n### CORE-98 围栏内\n```\n\n## 6. 另一节\n\n不属于卡\n\n### CORE-02 乙\n\n乙文\n';
  const cards = cutCards(text);
  assert.deepEqual([...cards.keys()], ['CORE-01', 'CORE-02']);
  assert.ok(cards.get('CORE-01').text.includes('CORE-98 围栏内'));
  assert.ok(!cards.get('CORE-01').text.includes('不属于卡'));
});

test('行级 diff 与 unified 输出', () => {
  const ops = diffLines(['a', 'b', 'c', 'd'], ['a', 'x', 'c', 'd', 'e']);
  assert.deepEqual(ops.filter(o => o.t !== ' ').map(o => o.t + o.s), ['-b', '+x', '+e']);
  assert.equal(unified('a\nb', 'a\nb', 'o', 'n'), '');
  const u = unified('1\n2\n3\n4\n5\n6\n7\n8\n9\n10', '1\n2\n3\n4\n5\nsix\n7\n8\n9\n10', 'o', 'n', 2);
  assert.equal(u, ['--- o', '+++ n', '@@ -4,5 +4,5 @@', ' 4', ' 5', '-6', '+six', ' 7', ' 8'].join('\n'));
});
