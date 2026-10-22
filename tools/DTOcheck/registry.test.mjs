import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {ROOT, loadCards, printReport, exitCodeFor} from './lib.mjs';
import {checkRegistry, versionRecord, DEFAULT_BASELINE, REGISTRY_REL, ENTRY_KEYS} from './registry.mjs';
import {parseYaml} from './yaml-lite.mjs';
import {tmpRoot, makeSadd, write, defTable, entry, makeErrors} from './fixture.mjs';

const ids = r => r.errors.map(e => e.id);
const msgs = (r, id) => r.errors.filter(e => e.id === id).map(e => e.msg).join('\n');

/** 临时仓库：CORE-05 卡内放错误码定义表（默认一条 DEMO_FAIL），并按需写 registry 与向量。 */
const fixture = ({defs = null, codes = ['DEMO_FAIL'], entries = ['DEMO_FAIL'], registry_version = 1, error_version = 1,
  shape = undefined, yaml = undefined} = {}) => {
  const root = tmpRoot();
  makeSadd(root, {extra05: defs ?? defTable(codes)});
  const list = entries.map(c => (typeof c === 'string' ? entry(c) : c));
  makeErrors(root, {entries: list, registry_version, error_version, yaml, ...(shape ? {shape} : {})});
  return {root, cards: loadCards(path.join(root, 'SADD'))};
};
const check = f => checkRegistry({root: f.root, cards: f.cards});

test('真实仓库数据：REG-01 三项判定通过，registry 集合与 SADD 定义集合相等（不写死条目数）', () => {
  const cards = loadCards(path.join(ROOT, 'SADD'));
  const r = checkRegistry({root: ROOT, cards, baselinePath: DEFAULT_BASELINE});
  assert.deepEqual(r.errors, [], printReport(r));
  assert.deepEqual(r.skipped, [], printReport(r));
  assert.equal(r.stats.extra, 0);                       // registry 多余
  assert.equal(r.stats.missing, 0);                     // registry 缺失
  assert.equal(r.stats.defined, r.stats.entries);       // 双向全集：两侧条数相等（不写死 238）
  assert.ok(r.stats.entries > 0);
  assert.equal(r.stats.dupDef, 0);                      // 同码多卡定义
  assert.equal(r.stats.columnDiffs, 0);                 // REG-02 逐列一致

  // registry 条目只含字典字段，不含逐 op 错误集合（ADR-V5-58 ⑥）
  const doc = parseYaml(fs.readFileSync(path.join(ROOT, REGISTRY_REL), 'utf8'), {file: 'registry.yaml'});
  for (const e of doc.entries) {
    for (const k of Object.keys(e)) {
      assert.ok(ENTRY_KEYS.includes(k), `${e.code} 含非字典字段 ${k}`);
      assert.ok(!/error_codes|error_set|errors|ops/.test(k), `${e.code} 含逐 op 错误集合字段 ${k}`);
    }
  }
});

test('registry 未创建时输出“未执行”，任何模式都不算通过', () => {
  const root = tmpRoot();
  makeSadd(root);
  const r = checkRegistry({root, cards: loadCards(path.join(root, 'SADD'))});
  assert.deepEqual(r.errors, []);
  assert.equal(r.skipped.length, 1);
  assert.equal(r.skipped[0].id, 'REG-00');
  assert.ok(r.skipped[0].msg.includes('未执行'));
  assert.ok(printReport(r).includes('未执行'));
  assert.equal(r.ok, false);
  assert.equal(exitCodeFor([r]), 1);                    // 非 --strict 也不放过
  assert.equal(exitCodeFor([r], {strict: true}), 1);
});

test('REG-01：owner 格式非法、指向不存在或已撤销的卡都失败', () => {
  const ok = fixture();
  assert.deepEqual(check(ok).errors, [], printReport(check(ok)));

  const bad = fixture({entries: [entry('DEMO_FAIL', {owner: 'CORE-99'})]});
  assert.ok(msgs(check(bad), 'REG-01').includes('不是现行模块卡'), msgs(check(bad), 'REG-01'));

  const fmt = fixture({entries: [entry('DEMO_FAIL', {owner: 'core-05'})]});
  assert.ok(msgs(check(fmt), 'REG-01').includes('owner 格式不合法'), msgs(check(fmt), 'REG-01'));
});

test('REG-02：registry 与所有者卡错误表的 owner/级别/可重试/HTTP 不一致都失败；纯端侧条目的卡表声明 HTTP 也失败', () => {
  const col = (defs, over) => {
    const f = fixture({defs, entries: [entry('DEMO_FAIL', over)]});
    const r = check(f);
    return {r, text: msgs(r, 'REG-02')};
  };
  // 级别
  const sev = col(defTable([{code: 'DEMO_FAIL', severity: 'error'}]), {severity: 'warning'});
  assert.ok(sev.text.includes('级别不一致 registry=warning 卡表="error"'), sev.text);
  // 可重试
  const ret = col(defTable([{code: 'DEMO_FAIL', retryable: '否'}]), {retryable: true});
  assert.ok(ret.text.includes('可重试不一致 registry=true 卡表=false'), ret.text);
  // HTTP：registry 声明 409，卡表 400
  const http = col(defTable([{code: 'DEMO_FAIL', http: 400}]), {surface: 'server', http_status: 409});
  assert.ok(http.text.includes('HTTP 不一致 registry=409 卡表=400'), http.text);
  // HTTP：registry 声明 409，卡表未声明（缺省即 400 语义）
  const httpMissing = col(defTable([{code: 'DEMO_FAIL', http: '—'}]), {surface: 'server', http_status: 409});
  assert.ok(httpMissing.text.includes('卡表未声明（缺省即 400）'), httpMissing.text);
  // 纯端侧码在卡表声明 HTTP
  const clientHttp = col(defTable([{code: 'DEMO_FAIL', http: 400}]), {surface: 'client'});
  assert.ok(clientHttp.text.includes('纯端侧码（surface=client）不得在卡表声明 HTTP'), clientHttp.text);
  // owner：registry 归 CORE-01，卡表定义在 CORE-05
  const ownerMis = col(defTable('DEMO_FAIL'), {owner: 'CORE-01'});
  assert.ok(ownerMis.text.includes('owner 不一致 registry=CORE-01 卡表定义在 CORE-05'), ownerMis.text);
  // 一致时不报
  const same = col(defTable([{code: 'DEMO_FAIL', severity: 'warning', retryable: '是'}]), {severity: 'warning', retryable: true});
  assert.equal(same.text, '', same.text);
});

test('REG-03：registry 多余、registry 缺失、同码多张卡定义都失败', () => {
  const extra = fixture({entries: ['DEMO_FAIL', 'DEMO_GHOST']});
  assert.ok(msgs(check(extra), 'REG-03').includes('registry 有码但 SADD 任何卡的定义表都没有：DEMO_GHOST'), msgs(check(extra), 'REG-03'));

  const missing = fixture({codes: ['DEMO_FAIL', 'DEMO_CARD'], entries: ['DEMO_FAIL']});
  assert.ok(msgs(check(missing), 'REG-03').includes('SADD 卡内定义了但 registry 没有：DEMO_CARD'), msgs(check(missing), 'REG-03'));

  const dup = fixture();
  dup.cards.get('CORE-01').body += defTable('DEMO_FAIL');
  const dupText = msgs(check(dup), 'REG-03');
  assert.ok(dupText.includes('同码在多张卡定义：DEMO_FAIL') && dupText.includes('CORE-05') && dupText.includes('CORE-01'), dupText);
});

test('REG-05：条目字段白名单/必填/取值，以及 registry 不支持的 YAML 语法', () => {
  // 逐 op 错误集合字段不得写进 registry
  const withOps = fixture({entries: [{...entry('DEMO_FAIL'), error_codes: 'DEMO_FAIL'}]});
  assert.ok(msgs(check(withOps), 'REG-05').includes('未知字段 error_codes'), msgs(check(withOps), 'REG-05'));

  const noSurface = {code: 'DEMO_FAIL', namespace: 'demo', owner: 'CORE-05', severity: 'error', message_key: 'errors.demo_fail', retryable: false, since: 1};
  const missing = fixture({entries: [noSurface]});
  assert.ok(msgs(check(missing), 'REG-05').includes('缺必填字段 surface'), msgs(check(missing), 'REG-05'));

  const badSev = fixture({entries: [entry('DEMO_FAIL', {severity: 'fatal'})]});
  assert.ok(msgs(check(badSev), 'REG-05').includes('severity 应为 error|warning|info'), msgs(check(badSev), 'REG-05'));

  const badSurface = fixture({entries: [entry('DEMO_FAIL', {surface: 'edge'})]});
  assert.ok(msgs(check(badSurface), 'REG-05').includes('surface 应为 client|server|both'), msgs(check(badSurface), 'REG-05'));

  const badSince = fixture({entries: [entry('DEMO_FAIL', {since: 2})]});
  assert.ok(msgs(check(badSince), 'REG-05').includes('since 应为 1..1'), msgs(check(badSince), 'REG-05'));

  const clientStatus = fixture({entries: [entry('DEMO_FAIL', {http_status: 400})]});
  assert.ok(msgs(check(clientStatus), 'REG-05').includes('不得声明 http_status'), msgs(check(clientStatus), 'REG-05'));

  const badStatus = fixture({entries: [entry('DEMO_FAIL', {surface: 'server', http_status: 200})]});
  assert.ok(msgs(check(badStatus), 'REG-05').includes('http_status 应为 400..599'), msgs(check(badStatus), 'REG-05'));

  // 嵌套列表（逐 op 错误集合的写法）不在支持的子集内：报解析错误而不是猜
  const nested = fixture({yaml: ['registry_version: 1', 'entries:', '  - code: DEMO_FAIL', '    namespace: demo', '    owner: CORE-05',
    '    severity: error', '    message_key: errors.demo_fail', '    retryable: false', '    since: 1', '    surface: client',
    '    error_codes:', '      - DEMO_FAIL', ''].join('\n')});
  const bad = check(nested);
  assert.ok(ids(bad).includes('REG-00'), JSON.stringify(bad.errors));
  assert.ok(msgs(bad, 'REG-00').includes('解析失败'), msgs(bad, 'REG-00'));
});

test('REG-04：增码只递增 registry_version 时 error_version 保持不变；反过来都失败', () => {
  const f = fixture();
  const bp = path.join(f.root, 'baseline.json');
  fs.writeFileSync(bp, JSON.stringify(versionRecord({root: f.root}), null, 1));
  const at = () => msgs(checkRegistry({root: f.root, cards: f.cards, baselinePath: bp}), 'REG-04');

  const seeded = versionRecord({root: f.root});
  assert.equal(seeded.registry_version, 1); assert.equal(seeded.error_version, 1);
  assert.equal(at(), '');                                     // 基线自洽

  // 增码：条目增一条、registry_version 递增、error_version 不变（ADR-V5-58 ⑦）→ 通过
  const grown = () => makeErrors(f.root, {entries: [entry('DEMO_FAIL'), entry('DEMO_NEW')], registry_version: 2, error_version: 1});
  grown();
  f.cards.get('CORE-05').body += defTable('DEMO_NEW');
  assert.equal(at(), '');

  // 形状未变却把 error_version 一起递增 → 失败
  grown();
  makeErrors(f.root, {entries: [entry('DEMO_FAIL'), entry('DEMO_NEW')], registry_version: 2, error_version: 2});
  assert.ok(at().includes('error_version 不得随 registry_version 改动'), at());

  // 条目改了但 registry_version 未递增（仍等于基线值）→ 失败
  makeErrors(f.root, {entries: [entry('DEMO_FAIL'), entry('DEMO_NEW'), entry('DEMO_NEW2')], registry_version: 1, error_version: 1});
  assert.ok(at().includes('registry_version 未递增'), at());

  // 错误对象形状变了但 error_version 未递增 → 失败
  makeErrors(f.root, {entries: [entry('DEMO_FAIL')], registry_version: 1, error_version: 1,
    shape: {code: 'DEMO_FAIL', domain: 'demo', retryable: false, trace_id: 't'}});
  assert.ok(at().includes('形状已变'), at());
  assert.deepEqual(versionRecord({root: f.root}).errorShapes.length > 0, true);
});

test('REG-04 缺基线时输出“未执行”，不当作通过', () => {
  const f = fixture();
  const r = check(f);
  assert.deepEqual(r.errors, []);
  assert.deepEqual(r.skipped.map(s => s.id), ['REG-04']);
  assert.equal(r.ok, false);
});
