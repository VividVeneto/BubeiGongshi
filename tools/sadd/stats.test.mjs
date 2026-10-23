import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {APPENDIX, sandbox} from './fixtures/core76/harness.mjs';

const START = '<!-- sadd-current-stats:start -->';
const END = '<!-- sadd-current-stats:end -->';
// 历史快照只读：对 reports/ 下每个文件分别取哈希，运行前后必须一致（Test:16）。
const hashTree = dir => Object.fromEntries(fs.readdirSync(dir).sort().map(name =>
  [name, crypto.createHash('sha256').update(fs.readFileSync(path.join(dir, name))).digest('hex')]));
const summary = r => JSON.parse(r.stdout.trim().split('\n').at(-1));

// U76-N3：import 只装载模块，不得运行 CLI；对整棵沙箱目录逐文件取哈希比较写入。
const treeHash = (dir, base = dir, acc = {}) => {
  for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) treeHash(full, base, acc);
    else acc[path.relative(base, full)] = crypto.createHash('sha256').update(fs.readFileSync(full)).digest('hex');
  }
  return acc;
};
// 在子进程里用真实 import() 装载被复制的脚本；多给的参数只作 argv，不表示本次要跑 CLI。
const importOnly = (s, script, ...args) => spawnSync(process.execPath,
  ['--input-type=module', '-e', `await import(${JSON.stringify(pathToFileURL(path.join(s.root, 'tools', 'sadd', script)).href)})`,
    ...(args.length ? ['--', ...args] : [])],
  {cwd: s.root, encoding: 'utf8'});

test('baseline --check exits 0, reports the counts and leaves reports/ untouched', () => {
  const s = sandbox();
  try {
    const before = s.text(APPENDIX);
    fs.writeFileSync(path.join(s.sadd, 'reports', 'v9.0.0-reviews.json'), '{"version":1,"entries":[]}\n');
    const hashes = hashTree(path.join(s.sadd, 'reports'));
    const r = s.run('stats.mjs', '--check');
    assert.equal(r.status, 0, r.stderr);
    assert.deepEqual(summary(r), {cards: 3, grades: {A: 1, B: 1, '—': 1}, ready: 1});
    assert.ok(!r.stderr.includes('drift'), r.stderr);
    assert.equal(s.text(APPENDIX), before);
    assert.deepEqual(hashTree(path.join(s.sadd, 'reports')), hashes);
  } finally {
    s.clean();
  }
});

test('hand-edited numbers inside the block fail --check with drift and are not rewritten', () => {
  const s = sandbox();
  try {
    s.edit(APPENDIX, '就绪=1。', '就绪=0。');
    const r = s.run('stats.mjs', '--check');
    assert.equal(r.status, 1, r.stderr);
    assert.ok(r.stderr.includes('SADD stats drift'), r.stderr);
    assert.ok(s.text(APPENDIX).includes('就绪=0。'), '--check must not write');
  } finally {
    s.clean();
  }
});

test('a missing block marker exits 2 instead of guessing a range', () => {
  const s = sandbox();
  try {
    s.edit(APPENDIX, START, '');
    const r = s.run('stats.mjs', '--check');
    assert.equal(r.status, 2, r.stderr);
    assert.ok(r.stderr.includes('Missing stats block'), r.stderr);
  } finally {
    s.clean();
  }
});

test('corrupt reviews JSON exits 2 as a read error, not as a validation error', () => {
  const s = sandbox();
  try {
    s.write('reports/v9.9.9-reviews.json', '{not json');
    const r = s.run('stats.mjs', '--check');
    assert.equal(r.status, 2, r.stderr);
    assert.ok(r.stderr.includes('SADD stats:'), r.stderr);
    assert.ok(!r.stderr.includes('Missing stats block'), r.stderr);
  } finally {
    s.clean();
  }
});

test('without --check only the bytes between the markers are rewritten', () => {
  const s = sandbox();
  try {
    const before = s.text(APPENDIX);
    s.edit(APPENDIX, '总计3卡；', '总计9卡；');
    s.edit(APPENDIX, '| CORE | 2 |', '| CORE | 7 |');
    const tail = '\n## D.14 夹具附加\n\n区块外的哨兵，不得被改写。\n';
    fs.appendFileSync(path.join(s.sadd, APPENDIX), tail);
    const r = s.run('stats.mjs');
    assert.equal(r.status, 0, r.stderr);
    assert.equal(s.text(APPENDIX), before + tail);
    assert.deepEqual(summary(r), {cards: 3, grades: {A: 1, B: 1, '—': 1}, ready: 1});
  } finally {
    s.clean();
  }
});

test('importing stats.mjs runs no CLI: no output, no rewrite, unchanged bytes (U76-N3)', () => {
  const s = sandbox();
  try {
    // 区块过期：若 import 触发 main()，无 --check 时会就地改写附录D。
    s.edit(APPENDIX, '就绪=1。', '就绪=0。');
    fs.appendFileSync(path.join(s.sadd, APPENDIX), '\n## D.14 夹具附加\n\n区块外的哨兵，不得被改写。\n');
    const text = s.text(APPENDIX);
    const before = treeHash(s.root);
    const r = importOnly(s, 'stats.mjs');
    assert.equal(r.status, 0, r.stderr);
    assert.equal(r.stdout, '');
    assert.equal(r.stderr, '');
    assert.equal(s.text(APPENDIX), text);
    assert.deepEqual(treeHash(s.root), before);
  } finally {
    s.clean();
  }
});

test('importing stats.mjs leaves no exit code or stderr behind even when the CLI would fail (U76-N3)', () => {
  const s = sandbox();
  try {
    // 等级与复核记录不一致：CLI 会退 1 并打 SADD-12；import 不得继承这个退出码或 stderr。
    s.edit(APPENDIX, '| CORE-02 | S0 | — | B |', '| CORE-02 | S0 | — | A |');
    const before = treeHash(s.root);
    const r = importOnly(s, 'stats.mjs');
    assert.equal(r.status, 0, 'import must not inherit the CLI exit code');
    assert.equal(r.stdout, '');
    assert.equal(r.stderr, '');
    assert.deepEqual(treeHash(s.root), before);
  } finally {
    s.clean();
  }
});
