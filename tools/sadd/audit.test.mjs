import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {APPENDIX, sandbox} from './fixtures/core76/harness.mjs';

const KINDS = new Set(['outside-closure', 'missing-local-definition', 'sdk-unknown', 'q-drift']);
// 历史快照只读：reports/ 下每个文件分别取哈希（Test:16）。
const hashTree = dir => Object.fromEntries(fs.readdirSync(dir).sort().map(name =>
  [name, crypto.createHash('sha256').update(fs.readFileSync(path.join(dir, name))).digest('hex')]));
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));

test('--sadd and --out report every required field with one material row per card', () => {
  const s = sandbox();
  try {
    const hashes = hashTree(path.join(s.sadd, 'reports'));
    const out = path.join(s.root, 'build/report.json');
    const r = s.run('audit.mjs', '--sadd', s.sadd, '--out', out);
    assert.equal(r.status, 0, r.stderr);
    const data = read(out);
    assert.deepEqual(Object.keys(data), ['version', 'toolchain', 'stats', 'errors', 'warnings', 'materials']);
    assert.equal(data.version, 1);
    assert.equal(data.toolchain.node, process.version);
    assert.equal(data.toolchain.sadd, path.resolve(s.sadd));
    assert.deepEqual(data.stats, {cards: 3, CORE: 2, AND: 1, WIN: 0, currentRows: 3, ready: 1,
      grades: {A: 1, B: 1, '—': 1}});
    assert.deepEqual(data.errors, []);
    assert.deepEqual(data.materials.map(m => m.id).sort(), ['AND-01', 'CORE-01', 'CORE-02']);
    for (const m of data.materials) {
      assert.ok(Number.isSafeInteger(m.chars) && m.chars > 0, JSON.stringify(m));
      assert.ok(Number.isSafeInteger(m.segments) && m.segments >= 1, JSON.stringify(m));
      assert.equal(typeof m.overLimit, 'boolean');
      assert.equal(m.overLimit, m.chars > 80000);
    }
    const chars = data.materials.map(m => m.chars);
    assert.deepEqual(chars, [...chars].sort((a, b) => b - a));
    for (const w of data.warnings) {
      assert.ok(KINDS.has(w.kind), w.kind);
      assert.deepEqual(Object.keys(w), ['id', 'kind', 'evidence']);
      assert.equal(typeof w.id, 'string');
      assert.equal(typeof w.evidence, 'object');
    }
    // 夹具 §6 故意留了一行受 AND-01 影响但正文未提及的 Q，必须报 q-drift 而不是静默。
    assert.ok(data.warnings.some(w => w.kind === 'q-drift'), JSON.stringify(data.warnings));
    assert.deepEqual(hashTree(path.join(s.sadd, 'reports')), hashes);
  } finally {
    s.clean();
  }
});

test('without --out the report lands in build/sadd/audit.json under the root', () => {
  const s = sandbox();
  try {
    fs.writeFileSync(path.join(s.sadd, 'reports', 'v9.0.0-reviews.json'), '{"version":1,"entries":[]}\n');
    const hashes = hashTree(path.join(s.sadd, 'reports'));
    const r = s.run('audit.mjs');
    assert.equal(r.status, 0, r.stderr);
    const data = read(path.join(s.root, 'build', 'sadd', 'audit.json'));
    assert.equal(data.stats.cards, 3);
    assert.deepEqual(hashTree(path.join(s.sadd, 'reports')), hashes);
  } finally {
    s.clean();
  }
});

test('writing into SADD/reports is refused with exit 2', () => {
  const s = sandbox();
  try {
    const r = s.run('audit.mjs', '--sadd', s.sadd, '--out', path.join(s.sadd, 'reports', 'audit.json'));
    assert.equal(r.status, 2, r.stderr);
    assert.ok(r.stderr.includes('refusing to write'), r.stderr);
    assert.ok(!fs.existsSync(path.join(s.sadd, 'reports', 'audit.json')));
  } finally {
    s.clean();
  }
});

test('a card over 80000 characters only shows up as overLimit', () => {
  const s = sandbox();
  try {
    // 拆成多个可分段的小块：单块超 80000 会被 pack 判为不可分并报错（CORE-57）。
    const body = Array.from({length: 30}, (_, i) => '要点' + i + '：' + '夹具填充说明文字。'.repeat(400)).join('\n\n');
    fs.appendFileSync(path.join(s.sadd, '02-Android端-v5.md'),
      '\n### AND-02 假大材料卡\n\n**依赖**：无。\n\n**实现说明**\n\n' + body + '\n');
    s.edit(APPENDIX, '| AND-01 | S0 |', '| AND-02 | S0 | — | — | 未就绪（D.12 未评级） | 夹具大材料 |\n| AND-01 | S0 |');
    const stats = s.run('stats.mjs');
    assert.equal(stats.status, 0, stats.stderr);
    const out = path.join(s.root, 'build/big.json');
    const r = s.run('audit.mjs', '--sadd', s.sadd, '--out', out);
    assert.equal(r.status, 0, r.stderr);
    const data = read(out);
    const card = data.materials.find(m => m.id === 'AND-02');
    assert.ok(card.chars > 80000, JSON.stringify(card));
    assert.equal(card.overLimit, true);
    assert.deepEqual(data.materials.filter(m => m.overLimit).map(m => m.id), ['AND-02']);
    assert.deepEqual(data.errors, []);
    assert.deepEqual(data.stats.grades, {A: 1, B: 1, '—': 2});
    assert.equal(data.stats.ready, 1);
  } finally {
    s.clean();
  }
});

test('any validateCurrent error exits 1 and every error keeps the SADD-12 prefix', () => {
  const s = sandbox();
  try {
    // CORE-02 的最右复核列改成 A，但机器记录仍是 B：等级与记录不一致。
    s.edit(APPENDIX, '| CORE-02 | S0 | — | B |', '| CORE-02 | S0 | — | A |');
    const out = path.join(s.root, 'build/bad.json');
    const r = s.run('audit.mjs', '--sadd', s.sadd, '--out', out);
    assert.equal(r.status, 1, r.stderr);
    const data = read(out);
    assert.ok(data.errors.length >= 1);
    for (const error of data.errors) assert.ok(error.startsWith('SADD-12: '), error);
    assert.ok(data.errors.some(e => e.includes('CORE-02')), data.errors.join('; '));
  } finally {
    s.clean();
  }
});

test('a version mismatch between the column and the D.10 narrative only warns', () => {
  const s = sandbox();
  try {
    const before = s.text(APPENDIX);
    const hashes = hashTree(path.join(s.sadd, 'reports'));
    s.edit(APPENDIX, '## D.10 逐卡评审等级（v9.9.9 复核）', '## D.10 逐卡评审等级（v9.9.8 复核）');
    const out = path.join(s.root, 'build/version.json');
    const r = s.run('audit.mjs', '--sadd', s.sadd, '--out', out);
    assert.equal(r.status, 0, r.stderr);
    assert.ok(r.stderr.includes('不一致'), r.stderr);
    assert.ok(r.stderr.includes('v9.9.8'), r.stderr);
    assert.equal(s.text(APPENDIX), before.replace('（v9.9.9 复核）', '（v9.9.8 复核）'));
    assert.ok(s.text(APPENDIX).includes('| v9.9.9 复核 |'), 'column name must not be rewritten');
    assert.deepEqual(hashTree(path.join(s.sadd, 'reports')), hashes);
  } finally {
    s.clean();
  }
});

test('stats.ready only counts the exact ready string, even when the run fails', () => {
  const s = sandbox();
  try {
    // CORE-01 改成指向另一张卡的 D.12 记录：就绪既不计入也必须报错。
    s.edit(APPENDIX, '就绪（D.12 P2-CORE-01）', '就绪（D.12 P2-CORE-02）');
    const out = path.join(s.root, 'build/ready.json');
    const r = s.run('audit.mjs', '--sadd', s.sadd, '--out', out);
    assert.equal(r.status, 1, r.stderr);
    const data = read(out);
    assert.equal(data.stats.ready, 0);
    assert.ok(data.errors.some(e => e.includes('ready without complete independent evidence CORE-01')), data.errors.join('; '));
  } finally {
    s.clean();
  }
});
