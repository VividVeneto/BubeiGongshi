import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {parseYaml, YamlLiteError} from './yaml-lite.mjs';
import {ROOT} from './lib.mjs';

const kinds = doc => Object.fromEntries(Object.entries(doc).map(([k, v]) => [k, Array.isArray(v) ? 'list' : typeof v]));

test('标量：字符串/整数/布尔/null，整行注释与空行忽略', () => {
  const doc = parseYaml(['# 头注释', 'name: registry', 'count: 12', 'ok: true', 'no: false', 'nil: null', 'tilde: ~', '', '  # 缩进注释也算整行注释', 'zero: 0'].join('\n'));
  assert.deepEqual(doc, {name: 'registry', count: 12, ok: true, no: false, nil: null, tilde: null, zero: 0});
});

test('列表下的扁平映射（registry 实际用到的结构）', () => {
  const doc = parseYaml(['version: 1', 'entries:', '  - code: A_B', '    owner: CORE-05', '    retryable: false', '  - code: C_D', '    owner: AND-01'].join('\n'));
  assert.equal(doc.version, 1);
  assert.deepEqual(doc.entries, [{code: 'A_B', owner: 'CORE-05', retryable: false}, {code: 'C_D', owner: 'AND-01'}]);
});

test('不支持的语法一律报错，不猜', () => {
  const bad = {
    引号: 'name: "quoted"',
    单引号: "name: 'quoted'",
    flow序列: 'list: [a, b]',
    flow映射: 'map: {a: 1}',
    锚点: 'a: &x 1',
    别名: 'b: *x',
    块标量: 'text: |',
    小数: 'ratio: 1.5',
    行尾注释: 'name: registry  # 注释',
    tab缩进: 'entries:\n\t- code: A_B',
    多文档: 'a: 1\n---\nb: 2',
    嵌套映射: 'entries:\n  - code: A_B\n    meta:\n      x: 1',
    空值: 'name:',
    续键缩进错: 'entries:\n  - code: A_B\n   owner: CORE-05',
    重复键: 'a: 1\na: 2',
  };
  for (const [why, text] of Object.entries(bad)) {
    assert.throws(() => parseYaml(text), (e) => e instanceof YamlLiteError && /\S/.test(e.message), why);
  }
});

test('报错带文件与行号', () => {
  try {
    parseYaml('a: 1\nb: [1]', {file: 'x.yaml'});
    assert.fail('应当抛错');
  } catch (e) {
    assert.ok(e instanceof YamlLiteError);
    assert.equal(e.line, 2);
    assert.ok(e.message.includes('x.yaml:2'), e.message);
  }
});

test('真实仓库：registry.yaml 与 ownership.yaml 都能解析，条目数与版本取自文件而非写死', () => {
  const reg = parseYaml(fs.readFileSync(path.join(ROOT, 'contracts', 'errors', 'registry.yaml'), 'utf8'), {file: 'registry.yaml'});
  const own = parseYaml(fs.readFileSync(path.join(ROOT, 'contracts', 'errors', 'ownership.yaml'), 'utf8'), {file: 'ownership.yaml'});
  assert.equal(typeof reg.registry_version, 'number');
  assert.ok(Array.isArray(reg.entries) && reg.entries.length > 0);
  assert.equal(own.version, reg.registry_version);
  assert.equal(own.entries.length, reg.entries.length);              // registry 的生成镜像
  for (const e of own.entries) assert.ok(reg.entries.some(x => x.code === e.code && x.owner === e.owner), JSON.stringify(e));
});
