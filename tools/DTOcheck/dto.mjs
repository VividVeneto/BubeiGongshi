#!/usr/bin/env node
// DTO 契约检查：contracts/dto/manifest.json、*.schema.json、示例与 contracts/vectors。
// 用法：node tools/DTOcheck/dto.mjs [--root DIR] [--json] [--verbose]
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {Report, ROOT, loadCards, errorDefs, readJson, printReport, argOf} from './lib.mjs';
import {validate, lintSchema, collectRefs, resolveRef, sensitivePaths} from './schema.mjs';
import {stageTable} from './cards.mjs';

const OP_RE = /^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$/;
const OWNER_RE = /^(?:CORE|AND|WIN)-\d+$/;
const SCOPES = new Set(['none', 'device', 'profile']);
const MODES = new Set(['call', 'submit']);
const SHARED = new Set(['ast.schema.json', 'types.schema.json']);
const STAGE_RE = /^S[0-7]$/;

/** RFC 4122 UUIDv5。 */
export function uuidv5(name, namespaceUuid) {
  const ns = Buffer.from(namespaceUuid.replace(/-/g, ''), 'hex');
  const h = crypto.createHash('sha1').update(ns).update(Buffer.from(name, 'utf8')).digest();
  h[6] = (h[6] & 0x0f) | 0x50; h[8] = (h[8] & 0x3f) | 0x80;
  const x = h.subarray(0, 16).toString('hex');
  return `${x.slice(0, 8)}-${x.slice(8, 12)}-${x.slice(12, 16)}-${x.slice(16, 20)}-${x.slice(20)}`;
}
const NAMESPACE_URL = '6ba7b811-9dad-11d1-80b4-00c04fd430c8';

/**
 * @param stages §2 实施阶段表 Map<卡号, S编号>（由 cards.mjs 的 stageTable 提供）；
 *   传入时核对 manifest 的 stage 是否等于 owner 卡的实施阶段（DTO-23）。不传则只校验 stage 取值。
 */
export function checkDto({root = ROOT, cards = null, stages = null} = {}) {
  const r = new Report('dto');
  const dir = path.join(root, 'contracts', 'dto');
  const manifestPath = path.join(dir, 'manifest.json');
  if (!fs.existsSync(manifestPath)) { r.error('DTO-00', '缺少 contracts/dto/manifest.json'); return r; }
  let manifest;
  try { manifest = readJson(manifestPath); } catch (e) { r.error('DTO-00', `manifest.json 不是合法 JSON: ${e.message}`); return r; }
  if (manifest.version !== 1) r.error('DTO-01', `manifest.version 应为 1，实际 ${manifest.version}`);
  if (!Array.isArray(manifest.ops)) { r.error('DTO-01', 'manifest.ops 必须是数组'); return r; }

  // 读入全部 schema 文件
  const files = new Map();
  for (const f of fs.readdirSync(dir).filter(x => x.endsWith('.schema.json'))) {
    try { files.set(f, readJson(path.join(dir, f))); } catch (e) { r.error('DTO-10', `${f} 不是合法 JSON: ${e.message}`); }
  }
  const codes = cards ? errorDefs(cards) : null;
  const seen = new Set(); const referenced = new Set(); let ready = 0, pending = 0, examples = 0, assertions = 0, snapshotOps = 0; const i64 = []; const stageCount = {};

  for (const [i, op] of manifest.ops.entries()) {
    const id = op?.op ?? `ops[${i}]`;
    const bad = (code, msg) => r.error(code, `${id}: ${msg}`);
    if (typeof op?.op !== 'string' || !OP_RE.test(op.op)) { bad('DTO-02', 'op 名不合法'); continue; }
    if (seen.has(op.op)) bad('DTO-02', 'op 重复'); seen.add(op.op);
    if (!OWNER_RE.test(op.owner ?? '')) bad('DTO-03', `owner 不合法: ${op.owner}`);
    else if (cards && !cards.has(op.owner)) bad('DTO-03', `owner ${op.owner} 不是现行模块卡`);
    // 阶段：manifest 唯一机器字段（DTO-22）；来源为 §2 实施阶段表中 owner 卡的阶段（DTO-23）
    if (typeof op.stage !== 'string' || !STAGE_RE.test(op.stage)) bad('DTO-22', `stage 必须是 S0～S7 之一，实际 ${JSON.stringify(op.stage)}`);
    else {
      stageCount[op.stage] = (stageCount[op.stage] ?? 0) + 1;
      if (stages) {
        const ownerStage = stages.get(op.owner);
        if (!ownerStage) bad('DTO-23', `owner ${op.owner} 未出现在 §2 实施阶段表，无法核对 stage`);
        else if (ownerStage !== op.stage) bad('DTO-23', `stage=${op.stage} 与 owner 卡 ${op.owner} 的实施阶段 ${ownerStage} 不一致`);
      }
    }
    if (!SCOPES.has(op.scope)) bad('DTO-04', `scope 应为 none|device|profile，实际 ${op.scope}`);
    if (!Array.isArray(op.error_codes) || op.error_codes.some(c => typeof c !== 'string')) bad('DTO-05', 'error_codes 必须是字符串数组');
    else {
      if (new Set(op.error_codes).size !== op.error_codes.length) bad('DTO-05', 'error_codes 有重复');
      if (op.error_codes.join() !== [...op.error_codes].sort().join()) bad('DTO-05', 'error_codes 未按字典序排列');
      // 未注册/重复归属是硬错误：registry.yaml 是唯一真源，卡内错误码表在本轮是它的文本镜像（CORE-02）
      if (codes) for (const c of op.error_codes) {
        const owners = codes.get(c);
        if (!owners) bad('DTO-06', `错误码 ${c} 未在任何卡的错误码表定义（未注册）`);
        else if (owners.length > 1) bad('DTO-06', `错误码 ${c} 被多张卡定义：${owners.join('、')}`);
        else if (owners[0] === 'CORE-03') bad('DTO-18', `错误码 ${c} 是 CORE-03 的信封/句柄/取消码，不得写入 op 的业务错误集合`);
      }
    }
    if (!Array.isArray(op.sensitive_paths)) bad('DTO-07', 'sensitive_paths 必须是数组');
    // 条目字段冻结：ready 可带 reads_engine_snapshot，pending 可带 blocked_reason，其余未知字段拒绝（DTO-25）
    const allowed = new Set(['op', 'owner', 'stage', 'status', 'mode', 'scope', 'schema', 'error_codes', 'sensitive_paths']);
    allowed.add(op.status === 'ready' ? 'reads_engine_snapshot' : 'blocked_reason');
    for (const k of Object.keys(op)) if (!allowed.has(k)) bad('DTO-25', `未知字段 ${k}`);
    if (op.status === 'ready') {
      ready++;
      if (!MODES.has(op.mode)) bad('DTO-08', `ready 的 mode 应为 call|submit，实际 ${op.mode}`);
      if (op.blocked_reason !== undefined) bad('DTO-08', 'ready 不应带 blocked_reason');
      // 引擎快照集合：reads_engine_snapshot 与该 op 是否声明 ENGINE_UNAVAILABLE 必须一致（DTO-24）
      if (typeof op.reads_engine_snapshot !== 'boolean') bad('DTO-24', 'ready 必须显式声明 reads_engine_snapshot 布尔值');
      else {
        if (op.reads_engine_snapshot) snapshotOps++;
        const hasEngine = Array.isArray(op.error_codes) && op.error_codes.includes('ENGINE_UNAVAILABLE');
        if (op.reads_engine_snapshot !== hasEngine) bad('DTO-24', op.reads_engine_snapshot
          ? 'reads_engine_snapshot=true 但 error_codes 未含 ENGINE_UNAVAILABLE'
          : 'error_codes 含 ENGINE_UNAVAILABLE 但 reads_engine_snapshot 不为 true');
      }
      if (typeof op.schema !== 'string') { bad('DTO-09', 'ready 必须有 schema'); continue; }
      referenced.add(op.schema);
      const doc = files.get(op.schema);
      if (!doc) { bad('DTO-09', `schema 文件不存在: ${op.schema}`); continue; }
      const defs = doc.$defs ?? {};
      if (!defs.request || !defs.ok) { bad('DTO-11', 'schema 必须同时定义 $defs.request 与 $defs.ok'); continue; }
      const ctx = {files, file: op.schema};
      const got = [...sensitivePaths(defs.request, '/body'), ...sensitivePaths(defs.ok, '/ok')].sort();
      const want = [...(op.sensitive_paths ?? [])].sort();
      if (got.join('|') !== want.join('|')) bad('DTO-12', `sensitive_paths 与 schema 的 x-sensitive 不一致：schema=${JSON.stringify(got)} manifest=${JSON.stringify(want)}`);
      const ex = doc.examples;
      if (!Array.isArray(ex) || ex.length === 0) bad('DTO-13', 'ready 的 schema 至少要有 1 个 examples');
      else for (const [k, e] of ex.entries()) {
        examples++;
        for (const [part, def] of [['request', defs.request], ['ok', defs.ok]]) {
          if (!(part in e)) { bad('DTO-13', `examples[${k}] 缺少 ${part}`); continue; }
          const errs = validate(def, e[part], ctx, `/${part}`);
          assertions++;
          for (const m of errs) bad('DTO-14', `examples[${k}] ${m}`);
        }
      }
    } else if (op.status === 'pending') {
      pending++;
      if (op.schema !== null) bad('DTO-08', 'pending 的 schema 必须为 null');
      if (typeof op.blocked_reason !== 'string' || !op.blocked_reason.trim()) bad('DTO-08', 'pending 必须有非空 blocked_reason');
      if (op.mode !== null && !MODES.has(op.mode)) bad('DTO-08', `pending 的 mode 应为 null|call|submit，实际 ${op.mode}`);
      if ((op.sensitive_paths ?? []).length) r.warn('DTO-07', `${id}: pending 却声明了 sensitive_paths`);
      if ('reads_engine_snapshot' in op) bad('DTO-24', 'pending 不得声明 reads_engine_snapshot（转 ready 时由 owner 卡确定）');
    } else bad('DTO-08', `status 应为 ready|pending，实际 ${op.status}`);
  }

  // schema 文件本身：关键字、$ref、孤儿
  for (const [f, doc] of files) {
    if (doc.$schema !== 'https://json-schema.org/draft/2020-12/schema') r.error('DTO-10', `${f}: $schema 应为 2020-12`);
    if (typeof doc.title !== 'string' || !doc.title) r.error('DTO-10', `${f}: 缺少 title`);
    lintSchema(doc, '', (p, m, level) => { if (level === 'i64') i64.push(`${f}${p}`); else r.error('DTO-15', `${f}${p}: ${m}`); });
    for (const ref of collectRefs(doc)) if (!resolveRef(ref, f, files)) r.error('DTO-16', `${f}: $ref 无法解析 ${ref}`);
    if (!referenced.has(f) && !SHARED.has(f)) r.error('DTO-17', `${f}: 没有任何 ready op 引用（孤儿 schema）`);
  }
  for (const s of SHARED) if (!files.has(s)) r.error('DTO-10', `缺少共享文件 ${s}`);

  // 向量
  const vecDir = path.join(root, 'contracts', 'vectors');
  let vectors = 0;
  if (fs.existsSync(vecDir)) for (const f of fs.readdirSync(vecDir).filter(x => x.endsWith('.json'))) {
    let v; try { v = readJson(path.join(vecDir, f)); } catch (e) { r.error('DTO-20', `${f} 不是合法 JSON: ${e.message}`); continue; }
    vectors++;
    if (v.version !== 1) r.error('DTO-20', `${f}: version 应为 1`);
    if (f.startsWith('cloud-idempotency')) {
      const ns = uuidv5(v.namespace_rule_input ?? 'urn:fml:cloud', NAMESPACE_URL);
      if (ns !== v.namespace) r.error('DTO-21', `${f}: namespace 应为 UUIDv5(NAMESPACE_URL, "urn:fml:cloud") = ${ns}`);
      for (const [k, x] of (v.vectors ?? []).entries()) {
        assertions++;
        if (x.name_utf8 !== `${x.session_id}:${x.image_hash}`) r.error('DTO-21', `${f} vectors[${k}]: name_utf8 应为 session_id:image_hash`);
        if (uuidv5(x.name_utf8, v.namespace) !== x.idempotency_key) r.error('DTO-21', `${f} vectors[${k}]: idempotency_key 与 UUIDv5 重算不符`);
      }
    }
  }
  const stageSummary = Object.fromEntries(Object.entries(stageCount).sort(([a], [b]) => a.localeCompare(b)));
  r.stats = {ops: manifest.ops.length, ready, pending, stages: stageSummary, snapshotOps, schemas: files.size, examples, vectors, assertions, i64Fields: i64.length};
  r.info = {i64Fields: i64};
  return r;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = path.resolve(argOf(process.argv, '--root') ?? ROOT);
  let cards = null, stages = null;
  try { cards = loadCards(path.join(root, 'SADD')); } catch { /* 无 SADD 时跳过卡片交叉检查 */ }
  if (cards) { try { stages = stageTable(path.join(root, 'SADD')).stageOf; } catch { /* 交给 cards 检查报告 */ } }
  const r = checkDto({root, cards, stages});
  console.log(process.argv.includes('--json') ? JSON.stringify(r, null, 2) : printReport(r, {verbose: process.argv.includes('--verbose')}));
  process.exitCode = r.ok ? 0 : 1;
}
