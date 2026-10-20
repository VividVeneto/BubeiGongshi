#!/usr/bin/env node
// 交叉引用检查（启发式 + 基线）：错误码、op、类型在各卡之间的定义与使用。
// 硬错误：错误码在多张卡的“错误码”表中重复定义；shared-writes.json 的 error 登记与卡内定义不一致（owner、缺登记、无定义）。
// 启发式候选（undefErr / undefTypes / crossDep / multiDefTypes）写入基线，只有“新增”才报错。
// 用法：node tools/DTOcheck/xref.mjs [--sadd DIR] [--baseline FILE] [--update-baseline FILE] [--json] [--verbose]
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Report, ROOT, loadCards, closureOf, errorDefs, errorRefs, typeDefs, isErrorCode, readJson, printReport, argOf} from './lib.mjs';

export const DEFAULT_BASELINE = path.join(path.dirname(fileURLToPath(import.meta.url)), 'baseline', 'xref.json');
const MULTI_HUMP = /^[A-Z][a-z0-9]+(?:[A-Z][A-Za-z0-9]*)+$/;
// 常见语言/SDK 标识：不当作“未定义的项目类型”
const KNOWN = new Set(['Option', 'Result', 'String', 'Vec', 'HashMap', 'BTreeMap', 'BTreeSet', 'HashSet', 'PathBuf', 'Uuid', 'Zeroizing', 'FmlError',
  'Future', 'FutureOr', 'Stream', 'Uint8List', 'DateTime', 'Duration', 'BuildContext', 'Widget', 'StatelessWidget', 'StatefulWidget',
  'ChangeNotifier', 'ValueNotifier', 'Navigator', 'GoRoute', 'MaterialApp', 'ThemeData', 'ThemeExtension', 'TextStyle', 'EdgeInsets',
  'AtomicBool', 'RwLock', 'Mutex', 'SystemTime', 'NaN', 'PostgreSQL', 'SQLite', 'SQLCipher', 'LaTeX', 'MathML', 'GitHub']);

const bodyBlocks = body => [...body.matchAll(/```[a-z]*\n([\s\S]*?)```/g)].map(m => m[1]);

export function collectXref({sadd = path.join(ROOT, 'SADD'), root = ROOT} = {}) {
  const cards = loadCards(sadd);
  const eDefs = errorDefs(cards), tDefs = typeDefs(cards);
  const prefixes = new Set([...eDefs.keys()].map(c => c.split('_')[0]));
  const out = {dupErr: [], undefErr: new Set(), undefTypes: new Set(), multiDefTypes: [], crossDep: new Set(), undefOps: [], opsNoOwnerMention: [], policyOwner: [], policyUndefined: [], unregistered: [], refOwner: []};
  for (const [code, list] of eDefs) if (list.length > 1) out.dupErr.push(`${code}: ${list.join(',')}`);
  for (const [t, list] of tDefs) if (list.length > 1) out.multiDefTypes.push(`${t}: ${list.join(',')}`);

  for (const c of cards.values()) {
    for (const m of c.body.matchAll(/\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b/g)) {
      const code = m[0];
      if (isErrorCode(code) && prefixes.has(code.split('_')[0]) && !eDefs.has(code)) out.undefErr.add(`${code}@${c.id}`);
    }
    const deps = closureOf(cards, c.id);
    // 已定义的类型（含单词类型名如 Rational）在代码块中被使用才算引用；未定义的只统计多驼峰候选
    const used = new Set(bodyBlocks(c.body).flatMap(b => b.match(/\b[A-Z][A-Za-z0-9]{2,}\b/g) ?? []));
    for (const t of used) {
      if (KNOWN.has(t)) continue;
      const owners = tDefs.get(t);
      if (!owners) { if (MULTI_HUMP.test(t)) out.undefTypes.add(`${t}@${c.id}`); continue; }
      if (owners.includes(c.id)) continue;
      if (owners.length === 1 && !deps.has(owners[0])) out.crossDep.add(`${c.id} uses ${t} (${owners[0]})`);
    }
  }

  // 错误码引用表声明的“唯一定义卡”必须真是定义该码的卡
  for (const ref of errorRefs(cards)) for (const code of ref.codes) {
    const defs = eDefs.get(code);
    if (defs && !ref.owners.some(o => defs.includes(o))) out.refOwner.push(`${ref.card} 引用 ${code} 声明唯一定义卡 ${ref.owners.join('/')}，实际定义在 ${defs.join(',')}`);
  }

  // 预分配登记（shared-writes.json 的 error 项）与卡片中的错误码定义必须一致
  const sw = path.join(root, 'contracts', 'policies', 'shared-writes.json');
  if (fs.existsSync(sw)) {
    const reg = new Map(readJson(sw).entries.filter(e => e.kind === 'error').map(e => [e.key, e.owner]));
    for (const [code, owner] of reg) {
      const defs = eDefs.get(code);
      if (!defs) out.policyUndefined.push(`${code} (登记 owner ${owner})`);
      else if (!defs.includes(owner)) out.policyOwner.push(`${code}: 登记 owner=${owner}，卡内定义=${defs.join(',')}`);
    }
    for (const [code, defs] of eDefs) if (!reg.has(code)) out.unregistered.push(`${code} (${defs.join(',')})`);
  }

  // op：manifest 与卡片
  const mp = path.join(root, 'contracts', 'dto', 'manifest.json');
  if (fs.existsSync(mp)) {
    const ops = readJson(mp).ops ?? [];
    const names = new Set(ops.map(o => o.op));
    const domains = new Set(ops.map(o => o.op.split('.')[0]));
    for (const c of cards.values()) {
      for (const m of c.body.matchAll(/`([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)`/g)) {
        const full = m[1];
        if (!domains.has(full.split('.')[0]) || names.has(full)) continue;
        // 前缀写法（如 recog.session）和带点的字段/文件名不算 op
        if ([...names].some(n => n.startsWith(full + '.'))) continue;
        out.undefOps.push(`${full}@${c.id}`);
      }
    }
    for (const o of ops) {
      const owner = cards.get(o.owner);
      if (!owner) continue;
      const parts = o.op.split('.'), last = parts.pop(), head = parts.join('.');
      if (!owner.body.includes(o.op) && !(owner.body.includes(head) && owner.body.includes(last))) out.opsNoOwnerMention.push(`${o.op} (owner ${o.owner})`);
    }
  }
  for (const k of ['undefErr', 'undefTypes', 'crossDep']) out[k] = [...out[k]].sort();
  out.refOwner.sort(); out.policyOwner.sort(); out.policyUndefined.sort(); out.unregistered.sort(); out.dupErr.sort(); out.multiDefTypes.sort(); out.undefOps = [...new Set(out.undefOps)].sort(); out.opsNoOwnerMention.sort();
  return out;
}

const BASELINE_KEYS = ['undefErr', 'undefTypes', 'crossDep', 'multiDefTypes', 'undefOps', 'opsNoOwnerMention'];

export function checkXref({sadd, root, baselinePath = null} = {}) {
  const r = new Report('xref');
  const x = collectXref({sadd, root});
  for (const d of x.dupErr) r.error('XREF-01', `错误码在多张卡的定义表中重复：${d}`);
  for (const d of x.refOwner) r.error('XREF-05', `错误码引用表的唯一定义卡写错：${d}`);
  for (const d of x.policyOwner) r.error('XREF-02', `预分配登记与卡内定义的 owner 不一致：${d}`);
  for (const d of x.unregistered) r.error('XREF-03', `卡内定义的错误码未在 shared-writes.json 登记：${d}`);
  for (const d of x.policyUndefined) r.error('XREF-04', `shared-writes.json 登记了卡内没有定义的错误码：${d}`);
  const base = baselinePath && fs.existsSync(baselinePath) ? readJson(baselinePath) : null;
  for (const k of BASELINE_KEYS) {
    const known = new Set(base?.[k] ?? []);
    const fresh = x[k].filter(i => !known.has(i));
    const gone = [...known].filter(i => !x[k].includes(i));
    if (base) {
      for (const i of fresh) r.error(`XREF-NEW-${k}`, `相对基线新增：${i}`);
      if (gone.length) r.warn(`XREF-GONE-${k}`, `${gone.length} 条基线项已消失，可用 --update-baseline 更新`);
    } else for (const i of x[k]) r.warn(`XREF-${k}`, i);
  }
  r.stats = Object.fromEntries([['dupErr', x.dupErr.length], ['refOwner', x.refOwner.length], ['policyOwner', x.policyOwner.length], ['unregistered', x.unregistered.length], ['policyUndefined', x.policyUndefined.length], ...BASELINE_KEYS.map(k => [k, x[k].length])]);
  r.stats.baseline = base ? 'applied' : 'none';
  r.data = x;
  return r;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const a = process.argv;
  const sadd = path.resolve(argOf(a, '--sadd') ?? path.join(ROOT, 'SADD'));
  const upd = argOf(a, '--update-baseline');
  if (upd) {
    const x = collectXref({sadd});
    const body = Object.fromEntries(BASELINE_KEYS.map(k => [k, x[k]]));
    fs.mkdirSync(path.dirname(path.resolve(upd)), {recursive: true});
    fs.writeFileSync(path.resolve(upd), JSON.stringify({version: 1, note: 'xref 启发式候选基线：只允许减少；新增项需语义确认后再更新', ...body}, null, 1) + '\n');
    console.log(`baseline written: ${upd} ${JSON.stringify(Object.fromEntries(BASELINE_KEYS.map(k => [k, x[k].length])))}`);
  } else {
    const bp = argOf(a, '--baseline') ?? (fs.existsSync(DEFAULT_BASELINE) ? DEFAULT_BASELINE : null);
    const r = checkXref({sadd, baselinePath: bp});
    delete r.data;
    console.log(a.includes('--json') ? JSON.stringify(r, null, 2) : printReport(r, {verbose: a.includes('--verbose')}));
    process.exitCode = r.ok ? 0 : 1;
  }
}
