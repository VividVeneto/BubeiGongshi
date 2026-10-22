import test from 'node:test';
import assert from 'node:assert/strict';
import {reviewColumn, validateCurrent} from './current.mjs';
import {load} from './pack.mjs';
import {FIXTURE, read, reviews} from './fixtures/core76/harness.mjs';

const cards = new Map([['CORE-01', {}], ['CORE-02', {}]]);
const columns = ['', '编号', 'v5.3.2 复核', '当前状态', ''];
const keys = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6'];
const D12_HEADER = '| 记录 | 卡 | 复核人 / 日期 | 复核输入字符 / 段 | a～g | S1～S6 | 发现、处理及调用方确认 | conclusion |';
const D12_SEP = '| --- | --- | --- | --- | --- | --- | --- | --- |';
// D.12 记录表：表头逐字、每条 P2-<卡号> 一行；区块止于 D.13。
const d12 = (...rows) => ['## D.12 整卡语义复核', '', D12_HEADER, D12_SEP, ...rows, '', '## D.13 后续', ''].join('\n');
const entry = (card, over = {}) => ({record: 'P2-' + card, card, grade: 'A', reviewer: '复核人甲', date: '2026-10-20',
  materialChars: 123, segments: 1, checks: Object.fromEntries(keys.map(k => [k, 'pass'])), conclusion: 'pass', blockers: [],
  consumerConfirmation: 'consumer', ...over});
const record = e => '| ' + [e.record, e.card, e.reviewer + ' / ' + e.date, e.materialChars + ' / ' + e.segments,
  'PPPPPPP', 'PPPPPP', 'fixture', 'pass'].join(' | ') + ' |';
const evidence = (...entries) => ({version: 1, entries});

test('reviewColumn takes the right-most vX.Y.Z review column and -1 when absent', () => {
  assert.equal(reviewColumn(['', '编号', 'v5.3.1 修订后（未独立复核）', 'v5.3.2 复核', '当前状态', 'v5.3.3 复核', '']), 5);
  assert.equal(reviewColumn(['', '编号', '当前状态', '']), -1);
  assert.equal(reviewColumn(['', '编号', 'v5.3.3 复核（待补）', 'v5.3.3 复核人', '']), -1);
  assert.equal(reviewColumn(undefined), -1);
});

test('same-sized unknown, duplicate and missing inventories fail', () => {
  const errors = validateCurrent(['| CORE-01 | A | 待复核 |', '| CORE-999 | B | 待复核 |'], columns, cards);
  assert.ok(errors.some(x => x.includes('unknown current card CORE-999')));
  assert.ok(errors.some(x => x.includes('missing current card CORE-02')));
  assert.ok(validateCurrent(['| CORE-01 | A | 待复核 |', '| CORE-01 | A | 待复核 |'], columns, cards)
    .some(x => x.includes('duplicate current card')));
});

test('only independent grades and the explicit unreviewed marker are valid', () => {
  assert.deepEqual(validateCurrent(['| CORE-01 | A | 待复核 |', '| CORE-02 | — | 待复核 |'], columns, cards), []);
  assert.ok(validateCurrent(['| CORE-01 | PASS | 待复核 |', '| CORE-02 | C | 待复核 |'], columns, cards)
    .some(x => x.includes('invalid independent grade')));
});

test('latest grade and exact D.12 record gate every ready spelling', () => {
  const columns = ['', '编号', 'v5.3.2 复核', 'v5.3.3 复核', '当前状态', ''];
  const rows = ['| CORE-01 | C | A | 就绪（D.12 P2-CORE-01） |', '| CORE-02 | C | B | 待复核 |'];
  const first = entry('CORE-01'), second = entry('CORE-02', {grade: 'B'});
  const appendix = d12(record(first), record(second));
  const graph = new Map([['CORE-01', {}], ['CORE-02', {deps: ['CORE-01']}]]);
  const both = evidence(first, second);
  assert.deepEqual(validateCurrent(rows, columns, graph, both, appendix), []);
  // 没有机器记录时“就绪”一律失败；附录为空也不得跳过记录核对。
  assert.ok(validateCurrent(rows, columns, graph).some(e => e.includes('ready without')));
  assert.ok(validateCurrent(rows, columns, graph, both, '').some(e => e.includes('D.12 record')));
  for (const mutation of [r => { r.checks.S2 = 'pending'; }, r => { r.conclusion = 'fail'; },
    r => { r.consumerConfirmation = null; }, r => { r.grade = 'C'; }, r => { r.record = 'nonexistent'; }]) {
    const changed = structuredClone(both);
    mutation(changed.entries[0]);
    assert.ok(validateCurrent(rows, columns, graph, changed, appendix).length);
  }
  assert.ok(validateCurrent(rows, columns, graph, {...both, version: 999}, appendix).some(e => e.includes('root/version')));
  assert.ok(validateCurrent(rows, columns, graph, both, appendix.replace('PPPPPPP', 'PFFFFFF')).some(e => e.includes('mismatched D.12')));
  for (const status of ['就绪', '就绪（D.12 nonexistent）', '就绪 - 检查通过']) {
    const drifted = [rows[0].replace('就绪（D.12 P2-CORE-01）', status), rows[1]];
    assert.ok(validateCurrent(drifted, columns, graph, both, appendix).some(e => e.includes('ready without')));
  }
  assert.ok(validateCurrent(rows, columns, graph, evidence(first), appendix).some(e => e.includes('grade lacks')));
});

test('status header drift or malformed rows cannot bypass ready evidence checks', () => {
  const ok = ['', '编号', 'v5.3.3 复核', '当前状态', ''];
  const rows = ['| CORE-01 | A | 就绪 |', '| CORE-02 | — | 待复核 |'];
  // 基准：裸“就绪”必须被拒。
  assert.ok(validateCurrent(rows, ok, cards).some(e => e.includes('ready without')));
  // 状态列改名、缺失、重复都失败，不能因缺列而跳过就绪检查。
  assert.ok(validateCurrent(rows, ['', '编号', 'v5.3.3 复核', '状态', ''], cards).some(e => e.includes('exactly one 当前状态')));
  assert.ok(validateCurrent(rows, ['', '编号', 'v5.3.3 复核', ''], cards).some(e => e.includes('exactly one 当前状态')));
  assert.ok(validateCurrent(rows, ['', '编号', 'v5.3.3 复核', '当前状态', '当前状态', ''], cards).some(e => e.includes('exactly one 当前状态')));
  // 编号列缺失或重复。
  assert.ok(validateCurrent(rows, ['', '卡号', 'v5.3.3 复核', '当前状态', ''], cards).some(e => e.includes('exactly one 编号')));
  // 行宽与表头不符是坏表，不能把状态整体串位。
  assert.ok(validateCurrent(['| CORE-01 | A |', '| CORE-02 | — | 待复核 |'], ok, cards).some(e => e.includes('row width')));
  assert.ok(validateCurrent(['| CORE-01 | A | 待复核 | x |', '| CORE-02 | — | 待复核 |'], ok, cards).some(e => e.includes('row width')));
});

test('D.12 field rename, missing header, cell pipes and duplicate records fail', () => {
  const columns = ['', '编号', 'v5.3.3 复核', '当前状态', ''];
  const rows = ['| CORE-01 | A | 待复核 |'];
  const graph = new Map([['CORE-01', {}]]);
  const only = entry('CORE-01');
  const data = evidence(only), line = record(only);
  assert.deepEqual(validateCurrent(rows, columns, graph, data, d12(line)), []);
  // 表头字段改名即失败，不能靠读位置悄悄改口径。
  const renamed = validateCurrent(rows, columns, graph, data, d12(line).replace('| 卡 |', '| 卡片 |'));
  assert.ok(renamed.some(e => e.includes('D.12 header fields changed')), renamed.join('; '));
  // 缺表头时数据行不得被当作已定义宽度解析。
  assert.ok(validateCurrent(rows, columns, graph, data, d12(line).replace(D12_HEADER + '\n', ''))
    .some(e => e.includes('D.12 header missing before P2-CORE-01')));
  // 单元格里多出的 | 使行宽与表头不符。
  assert.ok(validateCurrent(rows, columns, graph, data, d12(line.replace('fixture', 'fix|ture')))
    .some(e => e.includes('D.12 row width 9 differs from header width 8')));
  // 同一记录重复出现。
  assert.ok(validateCurrent(rows, columns, graph, data, d12(line, line)).some(e => e.includes('duplicate D.12 record')));
  // 早期序号表与非 P2 行整行忽略（卡 :20）。
  const early = d12(line).replace(D12_HEADER, '| 序号 | 卡 | 结论 |\n| --- | --- | --- |\n| 1 | CORE-01 | 早期格式 |\n' + D12_HEADER);
  assert.deepEqual(validateCurrent(rows, columns, graph, data, early), []);
  // 记录列不匹配 ^P2-(CORE|AND|WIN)-\d+$ 的行整行忽略（卡 :20）。
  const nearMiss = d12(line, '| P2-COREX-1 | CORE-01 | 复核人甲 / 2026-10-20 | 1 / 1 | PPPPPPP | PPPPPP | x | pass |',
    '| P2-CORE-1a | CORE-01 | 复核人甲 / 2026-10-20 | 1 / 1 | PPPPPPP | PPPPPP | x | pass |');
  assert.deepEqual(validateCurrent(rows, columns, graph, data, nearMiss), []);
  const decoy = d12(line) + line + '\n';
  assert.ok(!validateCurrent(rows, columns, graph, data, decoy).some(e => e.includes('duplicate')));
});

test('each machine-evidence mismatch is reported instead of throwing', () => {
  const columns = ['', '编号', 'v5.3.3 复核', '当前状态', ''];
  const rows = ['| CORE-01 | A | 待复核 |'];
  const graph = new Map([['CORE-01', {}]]);
  const only = entry('CORE-01'), base = evidence(only), appendix = d12(record(only));
  assert.deepEqual(validateCurrent(rows, columns, graph, base, appendix), []);
  const cases = [
    {name: 'negative materialChars', change: e => { e.materialChars = -1; }, expect: 'malformed review CORE-01'},
    {name: 'zero segments', change: e => { e.segments = 0; }, expect: 'malformed review CORE-01'},
    {name: 'unknown check flag', change: e => { e.checks.S3 = 'ok'; }, expect: 'malformed review CORE-01'},
    {name: 'record does not name its card', change: e => { e.record = 'P2-CORE-02'; }, expect: 'malformed review CORE-01'},
    {name: 'grade differs from D.10', change: e => { e.grade = 'B'; }, expect: 'grade lacks matching review CORE-01'},
    {name: 'check not pass in D.12', change: e => { e.checks.S5 = 'fail'; }, expect: 'mismatched D.12 record CORE-01'},
    {name: 'conclusion not pass in D.12', change: e => { e.conclusion = 'pending'; }, expect: 'mismatched D.12 record CORE-01'},
  ];
  for (const item of cases) {
    const changed = structuredClone(base);
    item.change(changed.entries[0]);
    const errors = validateCurrent(rows, columns, graph, changed, appendix);
    assert.ok(errors.some(e => e.includes(item.expect)), item.name + ': ' + errors.join('; '));
  }
  // 附录侧被改（字符数、复核人）同样失败。
  for (const [from, to] of [['123 / 1', '124 / 1'], ['复核人甲', '复核人乙']]) {
    assert.ok(validateCurrent(rows, columns, graph, base, appendix.replace(from, to)).some(e => e.includes('mismatched D.12')));
  }
  // 无法解析的输入只报错，不抛异常。
  for (const bad of [null, undefined, 42, 'x', []]) {
    assert.deepEqual(validateCurrent(rows, columns, bad, base, appendix), ['SADD-12: cards must be a Map of card ids']);
  }
  assert.ok(Array.isArray(validateCurrent(rows, columns, graph, base, ' 不是附录D')));
});

test('fixture SADD baseline passes with no errors', () => {
  const {rows, columns, appendix} = read();
  assert.deepEqual(validateCurrent(rows, columns, load(FIXTURE), reviews(), appendix), []);
});
