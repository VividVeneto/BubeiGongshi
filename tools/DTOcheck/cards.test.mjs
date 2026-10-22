import test from 'node:test';
import assert from 'node:assert/strict';
import {tmpRoot, makeSadd, mutate} from './fixture.mjs';
import {checkCards, parseDeps, buildUnits, checkMigrations} from './cards.mjs';

const run = (root) => checkCards({sadd: root + '/SADD'});
const ids = r => r.errors.map(e => e.id);
const fresh = (over) => { const root = tmpRoot(); makeSadd(root, over); return root; };
const CORE = '01-公共核心-v5.md', AND = '02-Android端-v5.md', README = 'README.md';

test('合法夹具无错误', () => {
  const r = run(fresh());
  assert.deepEqual(r.errors, []);
  assert.equal(r.stats.cards, 5);
});

test('依赖解析：缩写沿用前缀、全称切换前缀、破折号为空', () => {
  assert.deepEqual(parseDeps('01、02、05', 'CORE'), ['CORE-01', 'CORE-02', 'CORE-05']);
  assert.deepEqual(parseDeps('CORE-01、AND-02、03', 'WIN'), ['CORE-01', 'AND-02', 'AND-03']);
  assert.deepEqual(parseDeps('—', 'CORE'), []);
});

test('构建单元：多个 crate / 跨 app 与 server 才算多单元，裸文件名不算', () => {
  assert.equal(buildUnits('约 100 行；`crates/fml-store/src/sync/`、`crates/fml-store/migrations/0078.sql`').size, 1);
  assert.equal(buildUnits('主包 `crates/fml-type/src/{rules,infer}.rs`（含 `lib.rs`、`dim.rs`）').size, 1);
  assert.equal(buildUnits('主包 `crates/fml-ffi/`，`app/lib/binding/`').size, 2);
});

test('规模：与索引不一致、超过 800 或超过 500 未分阶段、含“另计”、多构建单元无附属', () => {
  let root = fresh(); mutate(root, CORE, '**规模**：约 150 行', '**规模**：约 160 行');
  assert.ok(ids(run(root)).includes('CARD-05'));
  root = fresh(); mutate(root, CORE, '**规模**：约 150 行；`crates/fml-type/`。', '**规模**：约 150 行（规则表另计约 50 行）；`crates/fml-type/`。');
  assert.ok(ids(run(root)).includes('CARD-07'));
  root = fresh(); mutate(root, CORE, '| CORE-05 | 类型 | `crates/fml-type/` | 01、02 | 150 |', '| CORE-05 | 类型 | `crates/fml-type/` | 01、02 | 600 |'); mutate(root, CORE, '**规模**：约 150 行', '**规模**：约 600 行');
  assert.ok(ids(run(root)).includes('CARD-06'));
  root = fresh(); mutate(root, CORE, '| CORE-05 | 类型 | `crates/fml-type/` | 01、02 | 150 |', '| CORE-05 | 类型 | `crates/fml-type/` | 01、02 | 600 |'); mutate(root, CORE, '**规模**：约 150 行；`crates/fml-type/`。', '**规模**：约 600 行；`crates/fml-type/`；分阶段：① 规则 300；② 推断 300。');
  assert.ok(!ids(run(root)).includes('CARD-06'));
  root = fresh(); mutate(root, CORE, '| CORE-05 | 类型 | `crates/fml-type/` | 01、02 | 150 |', '| CORE-05 | 类型 | `crates/fml-type/` | 01、02 | 900 |'); mutate(root, CORE, '**规模**：约 150 行；`crates/fml-type/`。', '**规模**：约 900 行；`crates/fml-type/`；分阶段：① 400；② 500。');
  assert.ok(ids(run(root)).includes('CARD-06'));
  root = fresh(); mutate(root, CORE, '**规模**：约 150 行；`crates/fml-type/`。', '**规模**：约 150 行；`crates/fml-type/`、`app/lib/x/`。');
  assert.ok(ids(run(root)).includes('CARD-08'));
  root = fresh(); mutate(root, CORE, '**规模**：约 150 行；`crates/fml-type/`。', '**规模**：约 150 行；主包 `crates/fml-type/`，附属 `app/lib/x/`。');
  assert.ok(!ids(run(root)).includes('CARD-08'));
});

test('依赖：卡与索引不一致、依赖不存在的卡、依赖环', () => {
  let root = fresh(); mutate(root, CORE, '**依赖**：CORE-01、CORE-02\n\n**接口契约**\n\n\n\n**实现约束**\n- 无\n\n**规模**：约 150', '**依赖**：CORE-01\n\n**接口契约**\n\n\n\n**实现约束**\n- 无\n\n**规模**：约 150');
  assert.ok(ids(run(root)).includes('CARD-04'));
  root = fresh(); mutate(root, AND, '| AND-01 | 工程 | `app/android/` | CORE-01、CORE-02、CORE-05 | 200 |', '| AND-01 | 工程 | `app/android/` | CORE-01、CORE-02、CORE-05、CORE-99 | 200 |');
  assert.ok(ids(run(root)).includes('CARD-04'));
  root = fresh(); mutate(root, CORE, '| CORE-01 | 骨架 | 仓库根 | — | 100 |', '| CORE-01 | 骨架 | 仓库根 | 05 | 100 |'); mutate(root, CORE, '### CORE-01 骨架\n\n**目标**：测试卡\n\n**依赖**：—', '### CORE-01 骨架\n\n**目标**：测试卡\n\n**依赖**：CORE-05');
  assert.ok(ids(run(root)).includes('CARD-10'));
});

test('依赖图：边不在依赖里、缺少直接依赖的可达路径、节点标签错误、缺节点', () => {
  let root = fresh(); mutate(root, AND, '  A01 --> C05\n', '  A01 --> C05\n  A01 --> C99\n');
  assert.ok(ids(run(root)).includes('GRAPH-02'));
  root = fresh(); mutate(root, AND, '  A01 --> C05\n', '');
  assert.ok(ids(run(root)).includes('GRAPH-05'));
  root = fresh(); mutate(root, CORE, 'C05["CORE-05 类型"]', 'C05["CORE-06 类型"]');
  assert.ok(ids(run(root)).includes('GRAPH-01'));
  root = fresh(); mutate(root, CORE, '  C05["CORE-05 类型"]\n', '');
  assert.ok(ids(run(root)).includes('GRAPH-04'));
  root = fresh(); mutate(root, CORE, '  C05 --> C02\n', '  C05 --> C02\n  C05 --> C05\n');
  assert.ok(ids(run(root)).includes('GRAPH-03'));
});

test('阶段：缺失、重复、依赖晚于自身', () => {
  let root = fresh(); mutate(root, CORE, '| S1 引擎 | CORE-05 | x |', '| S1 引擎 | | x |');
  assert.ok(ids(run(root)).includes('STAGE-02'));
  root = fresh(); mutate(root, CORE, '| S1 引擎 | CORE-05 | x |', '| S1 引擎 | CORE-05、CORE-02 | x |');
  assert.ok(ids(run(root)).includes('STAGE-01'));
  root = fresh(); mutate(root, CORE, '| S0 骨架 | CORE-01、CORE-02 | x |\n| S1 引擎 | CORE-05 | x |', '| S0 骨架 | CORE-01、CORE-05 | x |\n| S2 引擎 | CORE-02 | x |');
  assert.ok(ids(run(root)).includes('STAGE-03'));
});
test('阶段表一行都解析不出时：报 STAGE-00 并停止下游阶段/布局检查（F-14）', () => {
  const root = fresh();
  mutate(root, CORE, '| S0 骨架 |', '| 骨架 |');
  mutate(root, CORE, '| S1 引擎 |', '| 引擎 |');
  mutate(root, AND, '| S2 平台 |', '| 平台 |');
  mutate(root, '03-Windows端-v5.md', '| S0 骨架 |', '| 骨架 |');
  const got = ids(run(root));
  assert.ok(got.includes('STAGE-00'), got.join(','));
  assert.ok(!got.includes('STAGE-01') && !got.includes('STAGE-02') && !got.includes('STAGE-03') && !got.includes('LAYOUT-02'), got.join(','));
});

test('README：卡数、分类统计、小节标题、阶段、重复/缺失、版本', () => {
  let root = fresh(); mutate(root, README, '5 张模块卡（公共核心 3', '5 张模块卡（公共核心 4');
  assert.ok(ids(run(root)).includes('README-04'));
  root = fresh(); mutate(root, README, '端侧核心 3 张，后端', '端侧核心 4 张，后端');
  assert.ok(ids(run(root)).includes('README-05'));
  root = fresh(); mutate(root, README, '#### 端侧核心（3 张）', '#### 端侧核心（4 张）');
  assert.ok(ids(run(root)).includes('README-06'));
  root = fresh(); mutate(root, README, '| CORE-05 | 类型 | 端侧核心 | Rust | `crates/fml-type/` | S1 |', '| CORE-05 | 类型 | 端侧核心 | Rust | `crates/fml-type/` | S3 |');
  assert.ok(ids(run(root)).includes('README-03'));
  root = fresh(); mutate(root, README, '| AND-01 | 工程 | 前端 | 平台层 | `app/android/` | S2 |\n', '');
  assert.ok(ids(run(root)).includes('README-02'));
  root = fresh(); mutate(root, AND, '# 02 Android 端 v1.0.0', '# 02 Android 端 v1.0.1');
  assert.ok(ids(run(root)).includes('VER-01'));
});

test('卡号重复与索引缺行', () => {
  let root = fresh(); mutate(root, CORE, '| CORE-02 | 错误码 | `crates/fml-error/` | 01 | 120 |\n', '');
  assert.ok(ids(run(root)).includes('CARD-02'));
});

test('迁移序号：取归属卡编号且归属卡须声明；registry/ 与其他 crate 独立库不查；同目录序号重复报错', () => {
  const cards = new Map([
    ['CORE-13', {body: '迁移 `crates/fml-store/migrations/0013_core.sql`；归属：0086_calculation_plan.sql 由 CORE-86 提交'}],
    ['CORE-86', {body: '表（`crates/fml-store/migrations/0086_calculation_plan.sql`）'}],
    ['CORE-23', {body: '`crates/fml-store/migrations/registry/0023_registry.sql`、`crates/fml-pack/migrations/0001_pack_meta.sql`'}],
    ['CORE-22', {body: '`server/migrations/0022_auth.sql`'}],
  ]);
  assert.deepEqual(checkMigrations(cards), []);
  cards.set('CORE-85', {body: '`crates/fml-store/migrations/0032_recognition.sql`；0032_recognition.sql 数据迁移归本卡'});
  assert.deepEqual(checkMigrations(cards).map(x => x.id), ['MIG-01']);
  cards.set('CORE-85', {body: '`crates/fml-store/migrations/0085_recognition.sql`'});
  assert.deepEqual(checkMigrations(cards), []);
  cards.set('CORE-14', {body: '`server/migrations/0099_x.sql`'});
  assert.match(checkMigrations(cards)[0].msg, /没有对应的归属卡 CORE-99/);
  cards.delete('CORE-14');
  cards.set('CORE-13', {body: '`crates/fml-store/migrations/0013_core.sql`、`crates/fml-store/migrations/0013_extra.sql`'});
  assert.deepEqual(checkMigrations(cards).map(x => x.id), ['MIG-02']);
});
