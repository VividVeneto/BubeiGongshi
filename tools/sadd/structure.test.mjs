// CORE-70 自测：SADD 结构、追踪、错误表、Q 影响列、证据适配、验收容器与发布门禁（node --test）。
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {run, render, main} from './structure.mjs';
import {load} from './pack.mjs';
import {reviewColumn, validateCurrent} from './current.mjs';

const BT = String.fromCharCode(96);
const CARD_REL = 'SADD/S0/S0_CORE-01_基座.md';
const README_REL = 'SADD/README.md';
const TEST_REL = 'SADD/Test/S0/S0_CORE-01_TEST.md';
const APPENDIX_REL = 'SADD/附录D-编码就绪检查记录.md';
const REVIEWS_REL = 'SADD/reports/v5.3.3-reviews.json';
const JOBS_REL = 'tools/ci/acceptance_jobs.json';
const CI_REL = '.github/workflows/ci.yml';

const tmpRoot = () => fs.mkdtempSync(path.join(os.tmpdir(), 'check-sadd-'));
const file = (root, rel) => path.join(root, rel);
const write = (root, rel, text) => {
  const target = file(root, rel);
  fs.mkdirSync(path.dirname(target), {recursive: true});
  fs.writeFileSync(target, text);
};
const readText = (root, rel) => fs.readFileSync(file(root, rel), 'utf8');
const mutate = (root, rel, from, to) => {
  const text = readText(root, rel);
  if (!text.includes(from)) throw new Error('夹具中找不到要替换的文本（' + rel + '）：' + from);
  write(root, rel, text.replace(from, to));
};
const rows = (...list) => list.join('\n') + '\n';

const cardText = () => rows(
  '### CORE-01 骨架',
  '',
  '**目标**：测试卡；Q1。',
  '',
  '**范围**',
  '- 包含：演示',
  '- 不包含：别的',
  '',
  '**依赖**：—',
  '',
  '**接口契约**',
  '见 [README](../README.md)。',
  '',
  '| 错误码 | 级别 | 可重试 | 触发条件 |',
  '| --- | --- | --- | --- |',
  '| ' + BT + 'DEMO_FAIL' + BT + ' | error | 否 | 测试 |',
  '',
  '**实现约束**',
  '- 无',
  '',
  '**验收标准**：测试方案全文见 [Test/S0/S0_CORE-01_TEST.md](../Test/S0/S0_CORE-01_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。',
  '',
  '**规模**：约 100 行；仓库根。',
);

const readmeText = () => rows(
  '# SADD：测试 v5.3.3',
  '',
  '> 版本：v5.3.3 修订日期：2026-10-20',
  '',
  '## 4. 版本说明',
  '',
  '| 版本 | 日期 | 说明 |',
  '| --- | --- | --- |',
  '| **v5.3.3** | **2026-10-20** | **现行本地基线** |',
  '',
  '## 5. 需求基线',
  '',
  '| 编号 | 需求 | 卡 |',
  '| --- | --- | --- |',
  '| R01 | 需求一 | CORE-01 |',
  '',
  '## 6. 已确认与待确认事项',
  '',
  '| 编号 | 问题 | 影响模块 |',
  '| --- | --- | --- |',
  '| Q1 | 问题一 | CORE-01 |',
);

const overviewCore = () => rows(
  '# 01 公共核心 v5.3.3',
  '',
  '## 2. 建议实施顺序',
  '',
  '| 阶段 | 模块 | 出口 |',
  '| --- | --- | --- |',
  '| S0 骨架 | CORE-01 | x |',
  '',
  '## 3. 模块索引',
  '',
  '| 编号 | 名称 | 代码位置 | 直接依赖 | 预估规模 |',
  '| --- | --- | --- | --- | --- |',
  '| CORE-01 | 骨架 | 仓库根 | — | 100 |',
  '',
  '## 4. 模块卡',
  '',
  '<!-- sadd:card CORE-01 -->',
);

const overviewOther = (title) => rows(
  '# ' + title + ' v5.3.3',
  '',
  '## 2. 建议实施顺序',
  '',
  '| 阶段 | 模块 | 出口 |',
  '| --- | --- | --- |',
);

const testPlanText = () => rows(
  '# CORE-01 测试方案',
  '',
  '> 来源卡：测试夹具。',
  '',
  '**验收标准**',
  '- [R01] 第一条验收',
  '- [R01] 第二条验收',
);

const reviewEntry = (over = {}) => ({
  record: 'P2-CORE-01', card: 'CORE-01', grade: 'B', reviewer: 'r1', date: '2026-10-22',
  materialChars: 10, segments: 1,
  checks: Object.fromEntries(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6'].map(k => [k, 'pass'])),
  blockers: [], conclusion: 'pass', consumerConfirmation: null, history: [],
  ...over,
});

const appendixText = () => rows(
  '# 附录D',
  '',
  '## D.10 现行卡表',
  '',
  '| 编号 | 阶段 | v5.3.3 复核 | 当前状态 |',
  '| --- | --- | --- | --- |',
  '| CORE-01 | S0 | B | 就绪（D.12 P2-CORE-01） |',
  '',
  '## D.12 复核记录',
  '',
  '| 记录 | 卡 | 复核人 / 日期 | 复核输入字符 / 段 | a～g | S1～S6 | 发现、处理及调用方确认 | conclusion |',
  '| --- | --- | --- | --- | --- | --- | --- | --- |',
  '| P2-CORE-01 | CORE-01 | r1 / 2026-10-22 | 10 / 1 | PPPPPPP | PPPPPP | 无 | pass |',
  '',
  '## D.13 其他',
  '',
  '无。',
);

/** 合法的最小夹具：1 张卡、1 条需求、1 条 Q、1 条错误表行、D.10/D.12 自洽。 */
function makeSadd(root) {
  write(root, CARD_REL, cardText());
  write(root, README_REL, readmeText());
  write(root, 'SADD/core/00-总览.md', overviewCore());
  write(root, 'SADD/and/00-总览.md', overviewOther('02 Android 端'));
  write(root, 'SADD/win/00-总览.md', overviewOther('03 Windows 端'));
  write(root, TEST_REL, testPlanText());
  write(root, APPENDIX_REL, appendixText());
  write(root, REVIEWS_REL, JSON.stringify({version: 1, entries: [reviewEntry()]}, null, 2));
  write(root, 'contracts/errors/registry.yaml', rows(
    'registry_version: 1',
    'entries:',
    '  - code: DEMO_FAIL',
    '    severity: error',
    '    surface: client',
    '  - code: DEMO_SERVER',
    '    severity: info',
    '    surface: server',
  ));
  write(root, 'contracts/dto/manifest.json', JSON.stringify({version: 1, ops: [
    {op: 'demo.open', owner: 'CORE-01', mode: 'call'},
    {op: 'demo.later', owner: 'CORE-02', mode: 'sync'},
  ]}, null, 2));
  write(root, 'contracts/policies/shared-writes.json', JSON.stringify({version: 1, entries: [
    {kind: 'file', key: 'tools/ci/x.py', owner: 'CORE-41', point: 'ci'},
    {kind: 'dir', key: 'app/lib/ui/', owner: 'CORE-30', point: 'ui'},
  ]}, null, 2));
  write(root, CI_REL, rows(
    'name: ci',
    'on: [push]',
    'jobs:',
    '  build:',
    '    runs-on: windows-latest',
    '    steps:',
    '      - run: echo ok',
    '  test:',
    '    runs-on: windows-latest',
  ));
  return root;
}

const fresh = () => makeSadd(tmpRoot());
const runOn = (root, opts = {}) => run({root, ...opts});
const rules = (result) => [...new Set(result.findings.map((f) => f.rule))].sort();
const byRule = (result, rule) => result.findings.filter((f) => f.rule === rule);
const messages = (result, rule) => byRule(result, rule).map((f) => f.message);

const materialDir = (report) => {
  const dir = tmpRoot();
  write(dir, 'report.json', typeof report === 'string' ? report : JSON.stringify(report, null, 2));
  return dir;
};
const materialReport = (over = {}) => ({
  version: 1, id: 'CORE-01',
  manifest: [{card: 'CORE-01', mode: 'target', retained: ['### CORE-01']}],
  filteredFiles: [], missingFromMaterials: [], closure: [],
  ...over,
});

const jobsDoc = (extra = []) => JSON.stringify({version: 1, rows: [
  {card: 'CORE-01', requirement: '[R01]', criterion: '1', stage: 'S0', environment: 'host-rust', target: 'path:SADD/README.md', status: 'active'},
  ...extra,
]}, null, 2);

test('合法夹具：0 违例、退出 0，终端给出计数行', () => {
  const result = runOn(fresh());
  assert.deepEqual(result.findings, []);
  assert.equal(result.code, 0);
  assert.match(render(result), /共 0 项违例，\d+ 项 warning，\d+ 项 SKIP\n$/);
});

test('SADD-1 缺字段：finding 指向卡片文件，退出 1', () => {
  const root = fresh();
  mutate(root, CARD_REL, '**实现约束**\n- 无\n\n', '');
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-1').includes('missing field 实现约束'));
  assert.equal(byRule(result, 'SADD-1')[0].file, CARD_REL);
});

test('SADD-1 重复字段', () => {
  const root = fresh();
  mutate(root, CARD_REL, '**依赖**：—', '**依赖**：—\n\n**依赖**：—');
  const result = runOn(root);
  assert.ok(messages(result, 'SADD-1').includes('duplicate field 依赖'));
});

test('SADD-1 章节顺序颠倒', () => {
  const root = fresh();
  mutate(root, CARD_REL,
    '**目标**：测试卡；Q1。\n\n**范围**\n- 包含：演示\n- 不包含：别的',
    '**范围**\n- 包含：演示\n- 不包含：别的\n\n**目标**：测试卡；Q1。');
  const result = runOn(root);
  assert.ok(messages(result, 'SADD-1').includes('field order 目标 after 范围'));
});

test('SADD-1 范围缺“不包含”子项', () => {
  const root = fresh();
  mutate(root, CARD_REL, '- 不包含：别的', '- 其他：别的');
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-1').includes('missing 范围 item 不包含'));
});

test('SADD-1 代码围栏内的字段字样不算字段', () => {
  const root = fresh();
  const fence = BT + BT + BT;
  mutate(root, CARD_REL, '**实现约束**',
    fence + 'text\n**目标**：围栏内\n**依赖**：—\n' + fence + '\n\n**实现约束**');
  const result = runOn(root);
  assert.deepEqual(result.findings, []);
});

test('SADD-1 HTML 注释内的字段字样不算字段', () => {
  const root = fresh();
  mutate(root, CARD_REL, '**实现约束**', '<!-- **目标**：注释内 **规模**：约 1 行 -->\n\n**实现约束**');
  const result = runOn(root);
  assert.deepEqual(result.findings, []);
});

test('SADD-7 卡内断链：finding 指向断链所在行', () => {
  const root = fresh();
  mutate(root, CARD_REL, '见 [README](../README.md)。', '见 [README](../MISSING.md)。');
  const result = runOn(root);
  const finding = byRule(result, 'SADD-7')[0];
  assert.ok(finding);
  assert.equal(finding.file, CARD_REL);
  assert.match(finding.message, /broken link \.\.\/MISSING\.md/);
  assert.equal(finding.line, readText(root, CARD_REL).split('\n').findIndex((l) => l.includes('MISSING.md')) + 1);
});

test('SADD-6 测试方案引用未知需求', () => {
  const root = fresh();
  write(root, TEST_REL, testPlanText() + '- [R99] 未登记的验收\n');
  const result = runOn(root);
  assert.equal(result.code, 1);
  const finding = byRule(result, 'SADD-6')[0];
  assert.equal(finding.file, TEST_REL);
  assert.match(finding.message, /unknown requirement R99/);
});

test('SADD-6 §5 存在未被引用的需求', () => {
  const root = fresh();
  mutate(root, README_REL, '| R01 | 需求一 | CORE-01 |', '| R01 | 需求一 | CORE-01 |\n| R02 | 需求二 | CORE-01 |');
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-6').some((m) => m.includes('R02') && m.includes('not referenced')));
});

test('SADD-6 替换为未知卡 ID 而保持行数不变仍失败', () => {
  const root = fresh();
  mutate(root, README_REL, '| R01 | 需求一 | CORE-01 |', '| R01 | 需求一 | CORE-99 |');
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-6').some((m) => m.includes('unknown card CORE-99')));
});

test('SADD-8 首三列顺序错误', () => {
  const root = fresh();
  mutate(root, CARD_REL, '| 错误码 | 级别 | 可重试 | 触发条件 |', '| 错误码 | 可重试 | 级别 | 触发条件 |');
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-8').some((m) => m.includes('错误码/级别/可重试')));
});

test('SADD-8 尾列不以“触发条件”开头', () => {
  const root = fresh();
  mutate(root, CARD_REL, '| 错误码 | 级别 | 可重试 | 触发条件 |', '| 错误码 | 级别 | 可重试 | 说明 |');
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-8').some((m) => m.includes('触发条件')));
});

test('SADD-8 级别取值非法', () => {
  const root = fresh();
  mutate(root, CARD_REL, '| error | 否 | 测试 |', '| fatal | 否 | 测试 |');
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-8').some((m) => m.includes('invalid 级别')));
});

test('SADD-8 可重试取值非法', () => {
  const root = fresh();
  mutate(root, CARD_REL, '| error | 否 | 测试 |', '| error | 也许 | 测试 |');
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-8').some((m) => m.includes('invalid 可重试')));
});

test('SADD-8 服务端 op 卡的错误表缺 HTTP 列', () => {
  const root = fresh();
  mutate(root, CARD_REL, BT + 'DEMO_FAIL' + BT + ' | error | 否 | 测试 |', BT + 'DEMO_SERVER' + BT + ' | info | 否 | 测试 |');
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-8').some((m) => m.includes('lacks HTTP column')));
});

test('SADD-11 代码围栏内的 Q 字样仍算正文提及（不因围栏误报）', () => {
  const root = fresh();
  const fence = BT + BT + BT;
  mutate(root, CARD_REL, '**目标**：测试卡；Q1。', '**目标**：测试卡。\n\n' + fence + 'text\n说明见 Q1\n' + fence + '\n');
  assert.deepEqual(runOn(root).findings, []);
});

test('SADD-11 Q 影响列与卡正文不符', () => {
  const root = fresh();
  mutate(root, CARD_REL, '**目标**：测试卡；Q1。', '**目标**：测试卡。');
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-11').some((m) => m.includes('Q1') && m.includes('CORE-01')));
});

test('SADD-9 未给 --material：打印 SKIP pending SADD-9 且不判通过', () => {
  const result = runOn(fresh());
  assert.ok(result.skips.includes('SKIP pending SADD-9'));
  assert.match(render(result), /SKIP pending SADD-9/);
  assert.equal(result.code, 0);
});

test('SADD-9 --material 缺 report.json 退出 2', () => {
  assert.throws(() => runOn(fresh(), {material: tmpRoot()}), /report\.json/);
});

test('SADD-9 --material 报告损坏退出 2', () => {
  assert.throws(() => runOn(fresh(), {material: materialDir('{not json')}), /不是有效 JSON/);
});

test('SADD-9 材料清单引用未知卡退出 1', () => {
  const root = fresh();
  const material = materialDir(materialReport({manifest: [{card: 'CORE-99', mode: 'target', retained: []}]}));
  const result = runOn(root, {material});
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-9').some((m) => m.includes('unknown card CORE-99')));
});

test('SADD-9 省略符号无来源退出 1，有来源只记 SADD-10 warning', () => {
  let result = runOn(fresh(), {material: materialDir(materialReport({
    missingFromMaterials: [{symbol: 'Foo', sources: []}],
  }))});
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-9').some((m) => m.includes('Foo')));
  result = runOn(fresh(), {material: materialDir(materialReport({
    missingFromMaterials: [{symbol: 'Foo', sources: [{card: 'CORE-01', file: CARD_REL, line: 3}]}],
  }))});
  assert.equal(result.code, 0);
  assert.ok(result.warnings.some((w) => w.rule === 'SADD-10' && w.message.includes('Foo')));
});

test('SADD-10 未知符号只记 warning 不算违例', () => {
  const result = runOn(fresh(), {material: materialDir(materialReport({undefinedIdentifiers: ['Bar']}))});
  assert.equal(result.code, 0);
  assert.ok(result.warnings.some((w) => w.rule === 'SADD-10' && w.message.includes('Bar')));
});

test('被“范围”列为复用的规则本卡不输出 finding', () => {
  const root = fresh();
  // 未知依赖卡（依赖方向/无环归 CORE-57 与文档工具项）、§2 阶段表与卡片文件阶段不一致（STAGE 归卡片工具）。
  mutate(root, CARD_REL, '**依赖**：—', '**依赖**：CORE-99');
  mutate(root, 'SADD/core/00-总览.md', '| S0 骨架 | CORE-01 | x |', '| S2 引擎 | CORE-01 | x |');
  const result = runOn(root);
  assert.deepEqual(result.findings, []);
});

// —— A2：acceptance_jobs.json 容器与 --release 发布门禁（卡 :17、:19）。
const jobRow = (over = {}) => ({
  card: 'CORE-01', requirement: '[R01]', criterion: '1', stage: 'S0',
  environment: 'host-rust', target: 'path:SADD/README.md', status: 'active',
  ...over,
});
const writeJobs = (root, list) => write(root, JOBS_REL, JSON.stringify({version: 1, rows: list}, null, 2));

test('acceptance_jobs.json 合法容器：0 违例', () => {
  const root = fresh();
  writeJobs(root, [jobRow(), jobRow({criterion: '2', environment: 'windows-host', target: 'job:build'})]);
  const result = runOn(root);
  assert.deepEqual(result.findings, []);
  assert.equal(result.code, 0);
});

test('acceptance_jobs.json 顶层多余键', () => {
  const root = fresh();
  write(root, JOBS_REL, JSON.stringify({version: 1, rows: [jobRow()], note: 'x'}, null, 2));
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('unexpected top-level key note')));
});

test('acceptance_jobs.json version 非 1 或缺少 rows：读写错误（CLI 退出 2）', () => {
  let root = fresh();
  write(root, JOBS_REL, JSON.stringify({version: 2, rows: []}));
  assert.throws(() => runOn(root), /version/);
  root = fresh();
  write(root, JOBS_REL, JSON.stringify({version: 1}));
  assert.throws(() => runOn(root), /rows/);
  root = fresh();
  write(root, JOBS_REL, '{oops');
  assert.throws(() => runOn(root), /JSON/);
});

test('acceptance 行缺字段、含未知字段', () => {
  const root = fresh();
  const row = jobRow();
  delete row.status;
  writeJobs(root, [{...row, extra: 1}]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('row lacks field status')));
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('row has unexpected field extra')));
});

test('acceptance 行引用未知卡、缺 [Rxx] 方括号与未登记需求', () => {
  const root = fresh();
  writeJobs(root, [
    jobRow({card: 'CORE-99'}),
    jobRow({card: 'CORE-01', requirement: 'R01', environment: 'manual'}),
    jobRow({card: 'CORE-01', requirement: '[R77]', criterion: '2', environment: 'windows-host'}),
  ]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('row names unknown card CORE-99')));
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('requirement must be [Rxx]: R01')));
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('[R77] is not in README §5')));
});

test('验收条目 [Rxx] 不是 §5 需求', () => {
  const root = fresh();
  writeJobs(root, [jobRow({requirement: '[R77]'})]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('is not in README §5')));
});

test('criterion 超出测试方案条目数', () => {
  const root = fresh();
  writeJobs(root, [jobRow({criterion: '3'})]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('exceeds the test plan criteria (2)')));
});

test('criterion 不是从 1 起的序号字符串', () => {
  const root = fresh();
  writeJobs(root, [
    jobRow({criterion: '0'}),
    jobRow({criterion: 'one', environment: 'manual'}),
  ]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  const text = messages(result, 'SADD-13').join('\n');
  assert.match(text, /criterion must be a 1-based index string: 0/);
  assert.match(text, /criterion must be a 1-based index string: one/);
});

test('environment / status / stage 越界', () => {
  const root = fresh();
  writeJobs(root, [jobRow({environment: 'linux-host'}), jobRow({criterion: '2', status: 'done'}), jobRow({criterion: '2', environment: 'manual', stage: 'S9'})]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  const text = messages(result, 'SADD-13').join('\n');
  assert.match(text, /environment out of range: linux-host/);
  assert.match(text, /status out of range: done/);
  assert.match(text, /stage out of range: S9/);
});

test('stage 与 §2 阶段表不一致', () => {
  const root = fresh();
  writeJobs(root, [jobRow({stage: 'S3'})]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('differs from the §2 stage table')));
});

test('同一卡同一验收条目同一环境重复登记', () => {
  const root = fresh();
  writeJobs(root, [jobRow(), jobRow({target: 'job:test'})]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('duplicate acceptance key')));
});

test('target 缺少 path:/job: 前缀', () => {
  const root = fresh();
  writeJobs(root, [jobRow({target: 'SADD/README.md'})]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('target must start with path: or job:')));
});

test('path: 目标是目录时视为不存在，active 行退出 1', () => {
  const root = fresh();
  writeJobs(root, [jobRow({target: 'path:SADD/S0'})]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('active target does not exist: path:SADD/S0')));
});

test('path: 目标越出仓库（含 ..）视为不存在', () => {
  const root = fresh();
  writeJobs(root, [jobRow({target: 'path:../outside.md'})]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('active target does not exist')));
});

test('path: 断链符号链接视为不存在', (t) => {
  const root = fresh();
  const link = path.join(root, 'SADD/linked.md');
  try {
    fs.symlinkSync(path.join(root, 'SADD/NOWHERE.md'), link);
  } catch {
    t.skip('当前环境不允许创建符号链接');
    return;
  }
  writeJobs(root, [jobRow({target: 'path:SADD/linked.md'})]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('active target does not exist: path:SADD/linked.md')));
});

test('job: 目标在 ci.yml 有 jobs 键时按作业名判定', () => {
  const root = fresh();
  writeJobs(root, [jobRow({target: 'job:build'})]);
  assert.deepEqual(runOn(root).findings, []);
  writeJobs(root, [jobRow({target: 'job:deploy'})]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('job:deploy')));
});

test('ci.yml 缺 jobs 键：警告并视 job: 目标为不存在', () => {
  const root = fresh();
  mutate(root, CI_REL, 'jobs:\n', 'on-hold:\n');
  writeJobs(root, [jobRow({target: 'job:build'})]);
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(result.warnings.some((w) => w.rule === 'SADD-13' && w.message.includes('没有顶层 jobs 键')));
});

test('非 active 行目标不存在时只记 SKIP，不判通过', () => {
  const root = fresh();
  writeJobs(root, [jobRow({target: 'job:deploy', status: 'pending-target'})]);
  const result = runOn(root);
  assert.equal(result.code, 0);
  assert.ok(result.skips.some((s) => s.includes('SKIP pending CORE-01: job:deploy')));
});

test('--release 缺 acceptance_jobs.json 退出 2', () => {
  const root = fresh();
  assert.throws(() => runOn(root, {release: true}), /acceptance_jobs\.json/);
  assert.equal(main(['--root', root, '--release', '--out', path.join(root, 'build/out')]), 2);
});

test('--release 拒绝 pending-target 行', () => {
  const root = fresh();
  mutate(root, 'SADD/core/00-总览.md', '| S0 骨架 | CORE-01 | x |', '| S7 发布 | CORE-01 | x |');
  writeJobs(root, [jobRow({stage: 'S7', target: 'job:deploy', status: 'pending-target'})]);
  const result = runOn(root, {release: true});
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('pending-target')));
});

test('--release 拒绝 active 但目标不存在的 S7 行', () => {
  const root = fresh();
  mutate(root, 'SADD/core/00-总览.md', '| S0 骨架 | CORE-01 | x |', '| S7 发布 | CORE-01 | x |');
  writeJobs(root, [jobRow({stage: 'S7', target: 'job:deploy'})]);
  const result = runOn(root, {release: true});
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('release gate: active target does not exist')));
});

test('--release 拒绝没有 S7 发布验收行的容器', () => {
  const root = fresh();
  writeJobs(root, [jobRow()]);
  const result = runOn(root, {release: true});
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-13').some((m) => m.includes('没有 stage=S7')));
});

test('--release 通过：S7 行 active 且目标存在', () => {
  const root = fresh();
  mutate(root, 'SADD/core/00-总览.md', '| S0 骨架 | CORE-01 | x |', '| S7 发布 | CORE-01 | x |');
  writeJobs(root, [jobRow({stage: 'S7', target: 'job:build'})]);
  const result = runOn(root, {release: true});
  assert.deepEqual(result.findings, []);
  assert.equal(result.code, 0);
});

test('--material 与 --release 同时生效', () => {
  const root = fresh();
  mutate(root, 'SADD/core/00-总览.md', '| S0 骨架 | CORE-01 | x |', '| S7 发布 | CORE-01 | x |');
  writeJobs(root, [jobRow({stage: 'S7', target: 'job:build'})]);
  const material = materialDir(materialReport());
  const result = runOn(root, {material, release: true});
  assert.equal(result.code, 0);
  assert.ok(!result.skips.includes('SKIP pending SADD-9'));
  assert.ok(!result.skips.some((s) => s.includes('acceptance_jobs.json')));
});

// —— A3：D.10/D.12 就绪证据（复用 CORE-76 的 validateCurrent）。
const appendixInputs = (root) => {
  const text = readText(root, APPENDIX_REL);
  const block = text.split('## D.10 ')[1].split('### D.10.1')[0];
  const blockLines = block.split('\n');
  const rows = blockLines.filter((l) => /^\| (?:CORE|AND|WIN)-\d+ \|/.test(l));
  const header = blockLines.find((l) => l.startsWith('| 编号 |'));
  const columns = header.split('|').map((c) => c.trim());
  const version = columns[reviewColumn(columns)].split(' ')[0];
  const reviews = JSON.parse(readText(root, 'SADD/reports/' + version + '-reviews.json'));
  return {rows, columns, reviews, text};
};

test('SADD-12 缺完整复核记录：退出 1', () => {
  const root = fresh();
  mutate(root, APPENDIX_REL, '| P2-CORE-01 | CORE-01 | r1 / 2026-10-22 | 10 / 1 | PPPPPPP | PPPPPP | 无 | pass |\n', '');
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(byRule(result, 'SADD-12').length > 0);
  assert.equal(byRule(result, 'SADD-12')[0].file, APPENDIX_REL);
});

test('SADD-12 reviewer 为空：退出 1', () => {
  const root = fresh();
  const reviews = JSON.parse(readText(root, REVIEWS_REL));
  reviews.entries[0].reviewer = '';
  write(root, REVIEWS_REL, JSON.stringify(reviews, null, 2));
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(byRule(result, 'SADD-12').length > 0);
});

test('SADD-12 reviewer 与同卡上一条有效记录相同：退出 1', () => {
  const root = fresh();
  const reviews = JSON.parse(readText(root, REVIEWS_REL));
  reviews.entries[0].history = [reviewEntry({record: 'P2-CORE-01-1', reviewer: 'r1'})];
  write(root, REVIEWS_REL, JSON.stringify(reviews, null, 2));
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-12').some((m) => m.includes('repeats the preceding record')));
});

test('SADD-12 上一条记录的 reviewer 不同则通过', () => {
  const root = fresh();
  const reviews = JSON.parse(readText(root, REVIEWS_REL));
  reviews.entries[0].history = [reviewEntry({record: 'P2-CORE-01-1', reviewer: 'r0'})];
  write(root, REVIEWS_REL, JSON.stringify(reviews, null, 2));
  assert.deepEqual(runOn(root).findings, []);
});

test('SADD-12 日期早于当前版本日期：退出 1', () => {
  const root = fresh();
  mutate(root, APPENDIX_REL, '| r1 / 2026-10-22 |', '| r1 / 2026-10-19 |');
  mutate(root, REVIEWS_REL, '"date": "2026-10-22"', '"date": "2026-10-19"');
  const result = runOn(root);
  assert.equal(result.code, 1);
  assert.ok(messages(result, 'SADD-12').some((m) => m.includes('earlier than the current version date 2026-10-20')));
});

test('SADD-12 取不到 README 现行版本日期：报“未校验”而不静默跳过', () => {
  const root = fresh();
  mutate(root, README_REL, '**现行本地基线**', '**本地基线**');
  mutate(root, APPENDIX_REL, '| r1 / 2026-10-22 |', '| r1 / 2026-10-19 |');
  mutate(root, REVIEWS_REL, '"date": "2026-10-22"', '"date": "2026-10-19"');
  const result = runOn(root);
  assert.equal(result.code, 0);
  assert.deepEqual(result.findings, []);
  const warning = result.warnings.find((w) => w.rule === 'SADD-12');
  assert.ok(warning, '缺基准时必须提示日期先后校验未执行');
  assert.equal(warning.file, README_REL);
  assert.match(warning.message, /not checked/);
  assert.match(render(result), /SADD-12 review date ordering is not checked/);
});

test('SADD-12 有现行版本日期时不提示未校验', () => {
  assert.ok(!runOn(fresh()).warnings.some((w) => w.rule === 'SADD-12'));
});

test('SADD-12 无复核日期可比时不提示未校验', () => {
  const root = fresh();
  mutate(root, README_REL, '**现行本地基线**', '**本地基线**');
  write(root, REVIEWS_REL, JSON.stringify({version: 1, entries: []}, null, 2));
  mutate(root, APPENDIX_REL, '| CORE-01 | S0 | B | 就绪（D.12 P2-CORE-01） |', '| CORE-01 | S0 | — | 未就绪 |');
  const result = runOn(root);
  assert.ok(!result.warnings.some((w) => w.rule === 'SADD-12'));
});

test('SADD-12 现行行内取不到日期：同样报未校验', () => {
  const root = fresh();
  mutate(root, README_REL, '| **2026-10-20** | **现行本地基线** |', '| **待定** | **现行本地基线** |');
  const result = runOn(root);
  assert.equal(result.code, 0);
  assert.deepEqual(result.findings, []);
  assert.ok(result.warnings.some((w) => w.rule === 'SADD-12' && /not checked/.test(w.message)));
});

test('SADD-12 findings 与 validateCurrent 同源', () => {
  const root = fresh();
  mutate(root, APPENDIX_REL, '| PPPPPPP | PPPPPP |', '| PPPFFPP | PPPPPP |');
  const result = runOn(root);
  const {rows: tableRows, columns, reviews, text} = appendixInputs(root);
  const cards = load(path.join(root, 'SADD'), {tests: true});
  const direct = validateCurrent(tableRows, columns, cards, reviews, text).map((m) => m.replace(/^SADD-12: /, ''));
  assert.ok(direct.length > 0);
  const produced = messages(result, 'SADD-12');
  for (const message of direct) assert.ok(produced.includes(message), '缺少 validateCurrent 的消息：' + message);
});

test('D.1 字段外的问题不影响就绪证据：D.9 意见覆盖不实现', () => {
  const root = fresh();
  mutate(root, APPENDIX_REL, '## D.12 复核记录', '## D.9 意见覆盖\n\n| CORE-01 | 意见一 | 未覆盖 |\n\n## D.12 复核记录');
  assert.deepEqual(runOn(root).findings, []);
});

// —— A4：structure.json 契约与确定性（卡 :13）。
const outDir = () => tmpRoot();
const outText = (dir) => fs.ReadIfExistsIgnoringCase ?? null;

test('--out 写 structure.json，键集符合契约', () => {
  const root = fresh();
  const dir = outDir();
  const result = runOn(root, {out: dir});
  assert.equal(result.code, 0);
  const doc = JSON.parse(fs.readFileSync(path.join(dir, 'structure.json'), 'utf8'));
  assert.deepEqual(Object.keys(doc).sort(), ['cards', 'findings', 'generatedAt', 'ops', 'owners', 'version'].sort());
  assert.equal(doc.version, 1);
  assert.deepEqual(doc.cards, [{id: 'CORE-01', stage: 'S0', file: CARD_REL}]);
  assert.deepEqual(doc.findings, []);
  assert.deepEqual(doc.ops, [
    {op: 'demo.later', owner: 'CORE-02', mode: 'sync'},
    {op: 'demo.open', owner: 'CORE-01', mode: 'call'},
  ]);
  assert.deepEqual(doc.owners.map((o) => o.key), ['app/lib/ui/', 'tools/ci/x.py']);
});

test('structure.json 两次运行忽略时间字段后字节相同，且不含绝对路径', () => {
  const root = fresh();
  const first = outDir();
  const second = outDir();
  runOn(root, {out: first});
  runOn(root, {out: second});
  const strip = (dir) => fs.readFileSync(path.join(dir, 'structure.json'), 'utf8')
    .replace(/"generatedAt": "[^"]*",\n/, '');
  const a = strip(first);
  const b = strip(second);
  assert.equal(a, b);
  assert.ok(!a.includes(root));
  assert.ok(!/[A-Za-z]:[\\/]/.test(a));
});

test('清单为空时 ops/owners 输出空数组', () => {
  const root = fresh();
  write(root, 'contracts/dto/manifest.json', JSON.stringify({version: 1, ops: []}, null, 2));
  write(root, 'contracts/policies/shared-writes.json', JSON.stringify({version: 1, entries: []}, null, 2));
  const dir = outDir();
  const result = runOn(root, {out: dir});
  assert.equal(result.code, 0);
  const doc = JSON.parse(fs.readFileSync(path.join(dir, 'structure.json'), 'utf8'));
  assert.deepEqual(doc.ops, []);
  assert.deepEqual(doc.owners, []);
});

test('清单缺失或损坏退出 2', () => {
  let root = fresh();
  fs.rmSync(path.join(root, 'contracts/dto/manifest.json'));
  assert.throws(() => runOn(root), /manifest\.json/);
  root = fresh();
  write(root, 'contracts/policies/shared-writes.json', '{oops');
  assert.throws(() => runOn(root), /shared-writes\.json/);
});

test('CLI：未知参数、缺取值、SADD 目录不可读均退出 2', () => {
  const root = fresh();
  assert.equal(main(['--root', root, '--unknown']), 2);
  assert.equal(main(['--root', root, '--out']), 2);
  assert.equal(main(['--root', path.join(root, 'NOWHERE')]), 2);
});

test('CLI：正常路径写出 structure.json 并返回 0', () => {
  const root = fresh();
  const dir = outDir();
  assert.equal(main(['--root', root, '--out', dir]), 0);
  assert.ok(fs.existsSync(path.join(dir, 'structure.json')));
});

test('CLI：有违例时返回 1', () => {
  const root = fresh();
  mutate(root, CARD_REL, '- 不包含：别的', '- 其他：别的');
  assert.equal(main(['--root', root, '--out', outDir()]), 1);
});
