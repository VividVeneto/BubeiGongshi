// 测试夹具：在临时目录生成最小 SADD 与 contracts，供 DTOcheck 的测试变异使用。
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export const tmpRoot = () => fs.mkdtempSync(path.join(os.tmpdir(), 'dtocheck-'));
export const write = (file, text) => { fs.mkdirSync(path.dirname(file), {recursive: true}); fs.writeFileSync(file, text); };

const card = (id, name, deps, scale, extra = '') => `### ${id} ${name}

**目标**：测试卡

**依赖**：${deps}

**接口契约**

${extra}

**实现约束**
- 无

**规模**：${scale}
`;

/** 合法的最小 SADD：CORE-01/02/05、AND-01、WIN-01。overrides 可替换各文件文本。 */
export function makeSadd(root, over = {}) {
  const dir = path.join(root, 'SADD');
  const core = over.core ?? `# 01 公共核心 v1.0.0

> 版本：v1.0.0 ｜ 修订日期：2026-10-20

## 1. 模块依赖图

\`\`\`mermaid
graph TD
  C01["CORE-01 骨架"]
  C02["CORE-02 错误码"]
  C05["CORE-05 类型"]
  C05 --> C01
  C05 --> C02
\`\`\`

## 2. 建议实施顺序

| 阶段 | 模块 | 出口 |
| --- | --- | --- |
| S0 骨架 | CORE-01、CORE-02 | x |
| S1 引擎 | CORE-05 | x |

## 3. 模块索引

| 编号 | 名称 | 代码位置 | 直接依赖 | 预估规模 |
| --- | --- | --- | --- | --- |
| CORE-01 | 骨架 | 仓库根 | — | 100 |
| CORE-02 | 错误码 | \`crates/fml-error/\` | 01 | 120 |
| CORE-05 | 类型 | \`crates/fml-type/\` | 01、02 | 150 |

## 4. 正文

${card('CORE-01', '骨架', '—', '约 100 行；仓库根。')}
${card('CORE-02', '错误码', 'CORE-01', '约 120 行；\`crates/fml-error/\`。')}
${card('CORE-05', '类型', 'CORE-01、CORE-02', '约 150 行；\`crates/fml-type/\`。', over.extra05 ?? '')}`;
  const android = over.android ?? `# 02 Android 端 v1.0.0

> 版本：v1.0.0 ｜ 修订日期：2026-10-20

## 1. 模块依赖图

\`\`\`mermaid
graph TD
  A01["AND-01 工程"]
  A01 --> C05
\`\`\`

## 2. 建议实施顺序

| 阶段 | 模块 | 出口 |
| --- | --- | --- |
| S2 平台 | AND-01 | x |

## 3. 模块索引

| 编号 | 名称 | 代码位置 | 直接依赖 | 预估规模 |
| --- | --- | --- | --- | --- |
| AND-01 | 工程 | \`app/android/\` | CORE-01、CORE-02、CORE-05 | 200 |

## 4. 正文

${card('AND-01', '工程', 'CORE-01、CORE-02、CORE-05', '约 200 行；\`app/android/\`。')}`;
  const win = over.win ?? `# 03 Windows 端 v1.0.0

> 版本：v1.0.0 ｜ 修订日期：2026-10-20

## 1. 模块依赖图

\`\`\`mermaid
graph TD
  W01["WIN-01 工程"]
\`\`\`

## 2. 建议实施顺序

| 阶段 | 模块 | 出口 |
| --- | --- | --- |
| S0 骨架 | WIN-01 | x |

## 3. 模块索引

| 编号 | 名称 | 代码位置 | 直接依赖 | 预估规模 |
| --- | --- | --- | --- | --- |
| WIN-01 | 工程 | \`app/windows/\` | CORE-01、CORE-02 | 300 |

## 4. 正文

${card('WIN-01', '工程', 'CORE-01、CORE-02', '约 300 行；\`app/windows/\`。')}`;
  const readme = over.readme ?? `# SADD：测试 v1.0.0

> 版本：v1.0.0　修订日期：2026-10-20

7. **按模块卡实施**：5 张模块卡（公共核心 3、Android 1、Windows 1；撤销不复用）。

- 统计：共 5 张卡——前端 1 张，端侧核心 3 张，后端 0 张，工程与发布 1 张。

#### 前端（1 张）

#### 端侧核心（3 张）

#### 后端（0 张）

#### 工程与发布（1 张）

| 编号 | 名称 | 主类 | 子类 | 代码目录 | 阶段 |
| --- | --- | --- | --- | --- | --- |
| CORE-01 | 骨架 | 端侧核心 | Rust | \`crates/\` | S0 |
| CORE-02 | 错误码 | 端侧核心 | Rust | \`crates/fml-error/\` | S0 |
| CORE-05 | 类型 | 端侧核心 | Rust | \`crates/fml-type/\` | S1 |
| AND-01 | 工程 | 前端 | 平台层 | \`app/android/\` | S2 |
| WIN-01 | 工程 | 工程与发布 | 平台层 | \`app/windows/\` | S0 |
`;
  write(path.join(dir, '01-公共核心-v5.md'), core);
  write(path.join(dir, '02-Android端-v5.md'), android);
  write(path.join(dir, '03-Windows端-v5.md'), win);
  write(path.join(dir, 'README.md'), readme);
  return dir;
}

/** 修改 SADD 文件中的一处文本；找不到就抛错，避免测试静默失效。 */
export function mutate(root, file, from, to) {
  const p = path.join(root, 'SADD', file);
  const t = fs.readFileSync(p, 'utf8');
  if (!t.includes(from)) throw new Error(`夹具中找不到: ${from}`);
  fs.writeFileSync(p, t.replace(from, to));
}

/** 合法的最小 contracts/dto。 */
export function makeDto(root) {
  const dir = path.join(root, 'contracts', 'dto');
  const s = (title, defs, examples) => ({$schema: 'https://json-schema.org/draft/2020-12/schema', title, $defs: defs, ...(examples ? {examples} : {})});
  write(path.join(dir, 'types.schema.json'), JSON.stringify(s('SharedTypes', {Uuid: {type: 'string', format: 'uuid'}})));
  write(path.join(dir, 'ast.schema.json'), JSON.stringify({$schema: 'https://json-schema.org/draft/2020-12/schema', title: 'AstSchema', $ref: 'types.schema.json#/$defs/Uuid'}));
  write(path.join(dir, 'demo.open.schema.json'), JSON.stringify(s('DemoOpenSchema', {
    request: {title: 'DemoOpenRequest', type: 'object', properties: {id: {$ref: 'types.schema.json#/$defs/Uuid'}, key: {type: 'string', 'x-sensitive': true}}, required: ['id', 'key'], additionalProperties: false},
    ok: {title: 'DemoOpenOk', type: 'object', properties: {n: {type: 'integer', minimum: 0, maximum: 10}}, required: ['n'], additionalProperties: false},
  }, [{request: {id: '00000000-0000-4000-8000-000000000001', key: 'k'}, ok: {n: 1}}])));
  write(path.join(dir, 'manifest.json'), JSON.stringify({version: 1, ops: [
    {op: 'demo.open', owner: 'CORE-05', status: 'ready', mode: 'call', scope: 'none', schema: 'demo.open.schema.json', error_codes: ['DEMO_FAIL'], sensitive_paths: ['/body/key']},
    {op: 'demo.later', owner: 'CORE-05', status: 'pending', mode: null, scope: 'none', schema: null, error_codes: [], sensitive_paths: [], blocked_reason: '待补'},
  ]}, null, 2));
  return dir;
}
