import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {tmpRoot, makeSadd, mutate, makeDto} from './fixture.mjs';
import {collectXref, checkXref} from './xref.mjs';

const CORE = '01-公共核心-v5.md';
const table = (...codes) => '| 错误码 | 级别 | 可重试 | 触发条件 |\n| --- | --- | --- | --- |\n' + codes.map(c => `| \`${c}\` | error | 否 | x |`).join('\n');
const fresh = (extra05 = '') => { const root = tmpRoot(); makeSadd(root, {extra05}); return root; };

test('错误码：同一代码在两张卡的定义表中出现是硬错误，引用表不算定义', () => {
  const root = fresh(table('DEMO_ONE'));
  mutate(root, CORE, '**接口契约**\n\n\n\n**实现约束**\n- 无\n\n**规模**：约 120', '**接口契约**\n\n' + table('DEMO_ONE') + '\n\n**实现约束**\n- 无\n\n**规模**：约 120');
  const r = checkXref({sadd: root + '/SADD', root});
  assert.ok(r.errors.some(e => e.id === 'XREF-01' && e.msg.includes('DEMO_ONE')));
  const refRoot = fresh(table('DEMO_ONE'));
  mutate(refRoot, CORE, '**接口契约**\n\n\n\n**实现约束**\n- 无\n\n**规模**：约 120', '**接口契约**\n\n| 错误码引用 | 唯一定义卡 | 本卡处理 |\n| --- | --- | --- |\n| `DEMO_ONE` | CORE-05 | 透传 |\n\n**实现约束**\n- 无\n\n**规模**：约 120');
  assert.deepEqual(checkXref({sadd: refRoot + '/SADD', root: refRoot}).errors, []);
});

test('未定义错误码、未定义类型、跨卡未声明依赖会进入候选', () => {
  const root = fresh(table('DEMO_ONE') + '\n\n```rust\npub struct Alpha { pub b: BetaThing }\n```\n\n引用 DEMO_TWO。');
  mutate(root, CORE, '**接口契约**\n\n\n\n**实现约束**\n- 无\n\n**规模**：约 120', '**接口契约**\n\n```rust\npub fn f(a: Alpha, c: GammaThing);\n```\n\n**实现约束**\n- 无\n\n**规模**：约 120');
  const x = collectXref({sadd: root + '/SADD', root});
  assert.deepEqual(x.undefErr, ['DEMO_TWO@CORE-05']);
  assert.ok(x.undefTypes.includes('BetaThing@CORE-05') && x.undefTypes.includes('GammaThing@CORE-02'));
  // CORE-02 不依赖 CORE-05，却使用了 CORE-05 定义的 Alpha
  assert.ok(x.crossDep.includes('CORE-02 uses Alpha (CORE-05)'));
});

test('基线：已有候选通过，新增候选报错，消失候选提示', () => {
  const root = fresh(table('DEMO_ONE') + '\n\n引用 DEMO_TWO。');
  const bp = path.join(root, 'baseline.json');
  const x = collectXref({sadd: root + '/SADD', root});
  fs.writeFileSync(bp, JSON.stringify({undefErr: x.undefErr, undefTypes: x.undefTypes, crossDep: x.crossDep, multiDefTypes: x.multiDefTypes, undefOps: x.undefOps, opsNoOwnerMention: x.opsNoOwnerMention}));
  assert.deepEqual(checkXref({sadd: root + '/SADD', root, baselinePath: bp}).errors, []);
  mutate(root, CORE, '引用 DEMO_TWO。', '引用 DEMO_TWO 与 DEMO_THREE。');
  const r = checkXref({sadd: root + '/SADD', root, baselinePath: bp});
  assert.deepEqual(r.errors.map(e => e.msg), ['相对基线新增：DEMO_THREE@CORE-05']);
  mutate(root, CORE, '引用 DEMO_TWO 与 DEMO_THREE。', '无。');
  assert.ok(checkXref({sadd: root + '/SADD', root, baselinePath: bp}).warnings.some(w => w.id === 'XREF-GONE-undefErr'));
});

test('op：manifest 域内但未登记的 op 名会被发现；owner 卡必须提到自己的 op', () => {
  const root = fresh('调用 `demo.open` 与 `demo.ghost`，另有 `demo.later`。');
  makeDto(root);
  const x = collectXref({sadd: root + '/SADD', root});
  assert.deepEqual(x.undefOps, ['demo.ghost@CORE-05']);
  assert.deepEqual(x.opsNoOwnerMention, []);
  const manifest = path.join(root, 'contracts', 'dto', 'manifest.json');
  const m = JSON.parse(fs.readFileSync(manifest, 'utf8'));
  m.ops[0].owner = 'CORE-02';
  fs.writeFileSync(manifest, JSON.stringify(m));
  assert.deepEqual(collectXref({sadd: root + '/SADD', root}).opsNoOwnerMention, ['demo.open (owner CORE-02)']);
});

test('预分配登记：owner 不一致、缺登记、登记了无定义的错误码都是硬错误', () => {
  const root = fresh(table('DEMO_ONE', 'DEMO_TWO'));
  const sw = path.join(root, 'contracts', 'policies', 'shared-writes.json');
  const write = entries => { fs.mkdirSync(path.dirname(sw), {recursive: true}); fs.writeFileSync(sw, JSON.stringify({version: 1, entries})); };
  const e = (key, owner) => ({kind: 'error', key, owner, point: 'contracts/errors/registry.yaml'});
  write([e('DEMO_ONE', 'CORE-05'), e('DEMO_TWO', 'CORE-05')]);
  assert.deepEqual(checkXref({sadd: root + '/SADD', root}).errors, []);
  write([e('DEMO_ONE', 'CORE-02'), e('GHOST_CODE', 'CORE-05')]);
  const ids = checkXref({sadd: root + '/SADD', root}).errors.map(x => x.id).sort();
  assert.deepEqual(ids, ['XREF-02', 'XREF-03', 'XREF-04']);
});

test('错误码单元格允许“（HTTP 状态）”后缀；引用表声明的唯一定义卡必须是真定义卡', () => {
  const root = fresh('| 错误码 | 级别 | 可重试 | 触发条件 |\n| --- | --- | --- | --- |\n| `DEMO_HTTP`（503） | error | 是 | x |');
  assert.deepEqual(collectXref({sadd: root + '/SADD', root}).undefErr, []);
  const ok = fresh('| 错误码 | 级别 | 可重试 | 触发条件 |\n| --- | --- | --- | --- |\n| `DEMO_HTTP`（503） | error | 是 | x |');
  mutate(ok, CORE, '**接口契约**\n\n\n\n**实现约束**\n- 无\n\n**规模**：约 120', '**接口契约**\n\n| 错误码引用 | 唯一定义卡 | 本卡处理 |\n| --- | --- | --- |\n| `DEMO_HTTP` | CORE-05 | 透传 |\n\n**实现约束**\n- 无\n\n**规模**：约 120');
  assert.deepEqual(collectXref({sadd: ok + '/SADD', root: ok}).refOwner, []);
  mutate(ok, CORE, '| `DEMO_HTTP` | CORE-05 | 透传 |', '| `DEMO_HTTP` | CORE-01 | 透传 |');
  const bad = collectXref({sadd: ok + '/SADD', root: ok}).refOwner;
  assert.equal(bad.length, 1); assert.ok(bad[0].includes('DEMO_HTTP'));
  mutate(ok, CORE, '| `DEMO_HTTP` | CORE-01 | 透传 |', '| `DEMO_HTTP` | CORE-01/05 | 透传 |');
  assert.deepEqual(collectXref({sadd: ok + '/SADD', root: ok}).refOwner, []);
});
