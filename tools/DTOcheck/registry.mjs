#!/usr/bin/env node
// registry 与所有者卡错误表的机械对照（CORE-02 的 REG-01 规则）与版本不变式。
// REG-01 owner 必须是 SADD 现存卡；REG-02 所有者卡错误表逐列一致；REG-03 双向全集；
// REG-04 registry_version 与 error_version 互不替代（基线对比）；REG-05 条目字段白名单。
// registry.yaml 不存在时输出“未执行”，不按通过计。用法：
//   node tools/DTOcheck/registry.mjs [--root DIR] [--baseline FILE] [--update-baseline FILE] [--json] [--verbose]
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {Report, ROOT, loadCards, errorTableRows, readJson, printReport, argOf, isErrorCode} from './lib.mjs';
import {parseYaml, YamlLiteError} from './yaml-lite.mjs';

export const DEFAULT_BASELINE = path.join(path.dirname(fileURLToPath(import.meta.url)), 'baseline', 'registry.json');
export const REGISTRY_REL = path.join('contracts', 'errors', 'registry.yaml');
export const VECTORS_REL = path.join('contracts', 'vectors', 'errors-v1.json');
export const ENTRY_KEYS = ['code', 'namespace', 'owner', 'severity', 'message_key', 'retryable', 'since', 'surface', 'http_status', 'fix_hint'];
const REQUIRED_KEYS = ['code', 'namespace', 'owner', 'severity', 'message_key', 'retryable', 'since', 'surface'];
const SEVERITIES = new Set(['error', 'warning', 'info']);
const SURFACES = new Set(['client', 'server', 'both']);
const OWNER_RE = /^(?:CORE|AND|WIN)-\d{2}$/;

const loc = r => (r.file ? 'SADD/' + r.file : '卡 ' + r.card) + ':' + r.line;

/** registry.yaml 里每条码的行号：Map<code, line>。 */
export function entryLines(text) {
  const out = new Map();
  for (const [i, line] of String(text).split(/\r?\n/).entries()) {
    const m = line.match(/^\s+- code: (\S+)\s*$/);
    if (m) out.set(m[1], i + 1);
  }
  return out;
}

/** error 对象的形状指纹（errors-v1.json 中出现的对象键集合）：形状变了 error_version 才该变。 */
export function errorShapes(vec) {
  const shapes = new Set();
  const keys = o => '[' + Object.keys(o).sort().join(',') + ']';
  for (const c of vec?.cases ?? []) {
    const e = c?.input?.error;
    if (!e || typeof e !== 'object') continue;
    shapes.add('error' + keys(e));
    for (const d of e.diagnostics ?? []) if (d && typeof d === 'object') shapes.add('diagnostic' + keys(d));
  }
  return [...shapes].sort();
}

/** 条目集合的指纹（含全部字段与顺序）：条目增删或字段改动都会改变。 */
export function entryDigest(entries) {
  const canonical = JSON.stringify(entries.map(e => Object.fromEntries(ENTRY_KEYS.filter(k => k in e).sort().map(k => [k, e[k]]))));
  return crypto.createHash('sha256').update(canonical).digest('hex').slice(0, 16);
}

/** 生成版本基线记录（--update-baseline 写它，REG-04 读它）。 */
export function versionRecord({root = ROOT, registry = null} = {}) {
  const file = path.join(root, REGISTRY_REL);
  const doc = registry ?? parseYaml(fs.readFileSync(file, 'utf8'), {file: 'contracts/errors/registry.yaml'});
  const vec = readJson(path.join(root, VECTORS_REL));
  return {
    version: 1,
    note: 'registry 版本基线：registry_version 随条目增删/字段改动递增，error_version 只随错误对象形状变；只允许在语义确认后更新',
    registry_version: doc.registry_version,
    error_version: vec.error_version,
    entryDigest: entryDigest(doc.entries),
    errorShapes: errorShapes(vec),
  };
}

/**
 * registry ↔ 所有者卡错误表。
 * @param {{root?: string, cards?: Map|null, baselinePath?: string|null}} opts cards 由 loadCards 取得（测试可传临时 SADD 的卡）。
 */
export function checkRegistry({root = ROOT, cards = null, baselinePath = null} = {}) {
  const r = new Report('reg');
  const file = path.join(root, REGISTRY_REL);
  if (!fs.existsSync(file)) {
    r.skip('REG-00', 'contracts/errors/registry.yaml 未创建，REG-01 三项判定（owner 有效性、逐列一致、双向全集）未执行');
    return r;
  }
  let doc;
  try { doc = parseYaml(fs.readFileSync(file, 'utf8'), {file: 'contracts/errors/registry.yaml'}); }
  catch (e) {
    r.error('REG-00', e instanceof YamlLiteError ? 'registry.yaml 解析失败：' + e.message : 'registry.yaml 读取失败：' + e.message);
    return r;
  }
  if (!Number.isInteger(doc.registry_version) || doc.registry_version < 1) {
    r.error('REG-00', 'registry_version 必须是正整数，实际 ' + JSON.stringify(doc.registry_version));
    return r;
  }
  if (!Array.isArray(doc.entries)) { r.error('REG-00', 'registry.entries 必须是映射列表'); return r; }
  if (!cards) { r.skip('REG-00', '无法读取 SADD 卡片，REG-01 未执行'); return r; }

  const version = doc.registry_version;
  const lines = entryLines(fs.readFileSync(file, 'utf8'));
  const rows = errorTableRows(cards);
  const seen = new Map();                       // code → 出现次数
  const reported = new Set();
  const once = (id, msg) => { if (reported.has(id + msg)) return; reported.add(id + msg); r.error(id, msg); };

  // REG-05：条目字段白名单与取值（registry 不承载逐 op 错误集合，ADR-V5-58 ⑥）
  for (const [i, e] of doc.entries.entries()) {
    const at = '第 ' + (lines.get(e?.code) ?? i + 1) + ' 行';
    if (!e || typeof e !== 'object' || Array.isArray(e)) { once('REG-05', at + '：条目必须是映射'); continue; }
    for (const k of Object.keys(e)) if (!ENTRY_KEYS.includes(k)) {
      once('REG-05', at + ' ' + (e.code ?? '(无 code)') + '：未知字段 ' + k + '（registry 不承载逐 op 错误集合，逐 op 集合在 manifest 与所有者卡镜像）');
    }
    for (const k of REQUIRED_KEYS) if (!(k in e)) once('REG-05', at + ' ' + (e.code ?? '(无 code)') + '：缺必填字段 ' + k);
    if (!isErrorCode(String(e.code ?? ''))) once('REG-05', at + '：code 不合法 ' + JSON.stringify(e.code));
    else { seen.set(e.code, (seen.get(e.code) ?? 0) + 1); if (seen.get(e.code) > 1) once('REG-05', at + ' ' + e.code + '：code 重复登记'); }
    if (typeof e.namespace !== 'string' || !e.namespace) once('REG-05', at + ' ' + (e.code ?? '') + '：namespace 必须是非空字符串');
    if (typeof e.message_key !== 'string' || !e.message_key) once('REG-05', at + ' ' + (e.code ?? '') + '：message_key 必须是非空字符串');
    if (!SEVERITIES.has(e.severity)) once('REG-05', at + ' ' + (e.code ?? '') + '：severity 应为 error|warning|info，实际 ' + JSON.stringify(e.severity));
    if (typeof e.retryable !== 'boolean') once('REG-05', at + ' ' + (e.code ?? '') + '：retryable 必须是布尔');
    if (!SURFACES.has(e.surface)) once('REG-05', at + ' ' + (e.code ?? '') + '：surface 应为 client|server|both，实际 ' + JSON.stringify(e.surface));
    if (!Number.isInteger(e.since) || e.since < 1 || e.since > version) once('REG-05', at + ' ' + (e.code ?? '') + '：since 应为 1..' + version + '，实际 ' + JSON.stringify(e.since));
    if ('http_status' in e) {
      if (!Number.isInteger(e.http_status) || e.http_status < 400 || e.http_status > 599) once('REG-05', at + ' ' + (e.code ?? '') + '：http_status 应为 400..599，实际 ' + JSON.stringify(e.http_status));
      else if (e.surface === 'client') once('REG-05', at + ' ' + e.code + '：纯端侧码（surface=client）不得声明 http_status');
    }
  }

  // REG-01：owner 必须是现行卡（撤销/不存在的卡号即失败；owner 有效性唯一检查点）
  for (const e of doc.entries) {
    const owner = e?.owner;
    if (typeof owner !== 'string' || !OWNER_RE.test(owner)) { once('REG-01', (e?.code ?? '?') + '：owner 格式不合法 ' + JSON.stringify(owner)); continue; }
    if (!cards.has(owner)) once('REG-01', (e?.code ?? '?') + '：owner ' + owner + ' 不是现行模块卡（卡不存在或已撤销）');
  }

  // REG-02：所有者卡错误表逐列一致（owner / 级别 / 可重试 / HTTP）
  let columnDiffs = 0;
  for (const e of doc.entries) {
    if (!isErrorCode(String(e?.code ?? ''))) continue;
    const defs = rows.get(e.code) ?? [];
    if (!defs.length) continue;                       // 缺定义归 REG-03
    const owners = [...new Set(defs.map(d => d.card))];
    if (owners.length === 1 && owners[0] !== e.owner) {
      columnDiffs++;
      once('REG-02', e.code + '：owner 不一致 registry=' + e.owner + ' 卡表定义在 ' + owners[0] + '（' + loc(defs[0]) + '）');
    }
    for (const d of defs) {
      if (d.severity !== null && d.severity !== e.severity) {
        columnDiffs++;
        once('REG-02', e.code + '：级别不一致 registry=' + e.severity + ' 卡表=' + JSON.stringify(d.severity) + '（' + loc(d) + '）');
      }
      if (d.retryable !== null) {
        const ret = d.retryable === '是' ? true : d.retryable === '否' ? false : undefined;
        if (ret === undefined) { columnDiffs++; once('REG-02', e.code + '：可重试列只接受 是/否，卡表写的是 ' + JSON.stringify(d.retryable) + '（' + loc(d) + '）'); }
        else if (ret !== e.retryable) { columnDiffs++; once('REG-02', e.code + '：可重试不一致 registry=' + e.retryable + ' 卡表=' + ret + '（' + loc(d) + '）'); }
      }
      const effective = e.http_status ?? 400;
      if (e.surface === 'client') {
        if (d.http !== null && d.http !== '—') { columnDiffs++; once('REG-02', e.code + '：纯端侧码（surface=client）不得在卡表声明 HTTP，实际 ' + JSON.stringify(d.http) + '（' + loc(d) + '）'); }
        continue;
      }
      if (d.http === null || d.http === '—') {
        if (effective !== 400) { columnDiffs++; once('REG-02', e.code + '：HTTP 不一致 registry=' + effective + ' 卡表未声明（缺省即 400）（' + loc(d) + '）'); }
      } else if (String(d.http) !== String(effective)) {
        columnDiffs++; once('REG-02', e.code + '：HTTP 不一致 registry=' + effective + ' 卡表=' + d.http + '（' + loc(d) + '）');
      }
    }
  }

  // REG-03：双向全集（registry 多余或缺失都失败；同码多卡定义也失败）
  const regCodes = new Set(doc.entries.map(e => e?.code));
  const extra = [...regCodes].filter(c => !rows.has(c));
  const missing = [...rows.keys()].filter(c => !regCodes.has(c));
  const dupDef = [...rows].filter(([, list]) => new Set(list.map(d => d.card)).size > 1).map(([code, list]) => code + '：' + [...new Set(list.map(d => d.card))].join('、'));
  for (const c of extra) once('REG-03', 'registry 有码但 SADD 任何卡的定义表都没有：' + c + '（registry 第 ' + (lines.get(c) ?? '?') + ' 行）');
  for (const c of missing) once('REG-03', 'SADD 卡内定义了但 registry 没有：' + c + '（' + loc(rows.get(c)[0]) + '）');
  for (const d of dupDef) { const code = d.split('：')[0]; once('REG-03', '同码在多张卡定义：' + d + '（' + rows.get(code).map(loc).join('、') + '）'); }

  // REG-04：registry_version 与 error_version 互不替代（基线对比；形状未变时 error_version 必须不变）
  const vecPath = path.join(root, VECTORS_REL);
  const base = baselinePath && fs.existsSync(baselinePath) ? readJson(baselinePath) : null;
  let errorVersion = null;
  if (!fs.existsSync(vecPath)) r.error('REG-04', '缺少 contracts/vectors/errors-v1.json，无法核对 error_version');
  else {
    let vec = null;
    try { vec = readJson(vecPath); } catch (e) { r.error('REG-04', 'errors-v1.json 不是合法 JSON：' + e.message); }
    if (vec) {
      errorVersion = vec.error_version;
      if (!Number.isInteger(errorVersion) || errorVersion < 1) r.error('REG-04', 'errors-v1.json 的 error_version 必须是正整数，实际 ' + JSON.stringify(errorVersion));
      else if (!base) r.skip('REG-04', '缺少基线 ' + path.relative(ROOT, baselinePath ?? DEFAULT_BASELINE) + '（用 --update-baseline 生成），版本不变式未执行');
      else {
        const shapes = errorShapes(vec);
        const digest = entryDigest(doc.entries);
        if (digest !== base.entryDigest && version <= (base.registry_version ?? 0)) {
          r.error('REG-04', '条目已增删或字段已改（指纹 ' + base.entryDigest + '→' + digest + '）但 registry_version 未递增（' + base.registry_version + '→' + version + '）');
        }
        if (version < (base.registry_version ?? 0)) r.error('REG-04', 'registry_version 回退：基线 ' + base.registry_version + '，当前 ' + version);
        if (shapes.join('|') !== (base.errorShapes ?? []).join('|')) {
          if (errorVersion === base.error_version) r.error('REG-04', '错误对象形状已变（' + JSON.stringify(base.errorShapes) + '→' + JSON.stringify(shapes) + '）但 error_version 未递增（仍为 ' + errorVersion + '）');
        } else if (errorVersion !== base.error_version) {
          r.error('REG-04', '错误对象形状未变，error_version 不得随 registry_version 改动：基线 ' + base.error_version + '，当前 ' + errorVersion);
        }
      }
    }
  }

  r.stats = {
    cards: cards.size, entries: doc.entries.length, defined: rows.size, extra: extra.length, missing: missing.length,
    dupDef: dupDef.length, columnDiffs, limit: 0, registry_version: version, error_version: errorVersion,
    baseline: base ? 'applied' : 'none',
  };
  delete r.stats.limit;
  return r;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const a = process.argv;
  const root = path.resolve(argOf(a, '--root') ?? ROOT);
  const upd = argOf(a, '--update-baseline');
  if (upd) {
    const rec = versionRecord({root});
    const target = path.resolve(upd === '1' ? DEFAULT_BASELINE : upd);
    fs.mkdirSync(path.dirname(target), {recursive: true});
    fs.writeFileSync(target, JSON.stringify(rec, null, 1) + '\n');
    console.log('baseline written: ' + target + ' ' + JSON.stringify({registry_version: rec.registry_version, error_version: rec.error_version, entryDigest: rec.entryDigest}));
  } else {
    let cards = null;
    try { cards = loadCards(path.join(root, 'SADD')); } catch { /* 由 cards 检查报告 */ }
    const bp = argOf(a, '--baseline') ?? (fs.existsSync(DEFAULT_BASELINE) ? DEFAULT_BASELINE : null);
    const r = checkRegistry({root, cards, baselinePath: bp});
    console.log(a.includes('--json') ? JSON.stringify(r, null, 2) : printReport(r, {verbose: a.includes('--verbose')}));
    process.exitCode = r.ok ? 0 : 1;
  }
}
