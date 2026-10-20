#!/usr/bin/env node
// 把三份 SADD 文档拆为 S0/、core/、and/、win/ 四个文件夹（每卡一个文件，命名 S编号_卡号_分组.md）。
// 用法：node tools/sadd/split.mjs [--sadd DIR] [--dry-run]
// 拆分是无损的：写盘后用 layout.mjs 拼回，必须与原文档逐字节一致，才删除原文档。
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {DOCS, OVERVIEW, GROUPS, marker, folderFor, cardFileName, readDocs, layoutOf} from './layout.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

/** 按实际功能的分组（2026-10-20 定稿）；分组此后以文件名为准，不另存映射。 */
const range = (p, ...xs) => xs.map(x => `${p}-${String(x).padStart(2, '0')}`);
export const GROUP_OF = new Map(Object.entries({
  基座: [...range('CORE', 1, 2, 3, 4, 41, 57, 67, 69, 70, 71, 74, 75, 76), 'AND-01', 'WIN-01', 'AND-15', 'WIN-17'],
  引擎: range('CORE', 5, 6, 7, 8, 9, 10, 11, 12, 52, 56, 73, 77),
  界面: range('CORE', 36, 37, 38, 39, 40, 47, 48, 49, 50, 51, 53, 54, 55, 58, 59, 60, 63, 64),
  功能: range('CORE', 13, 14, 15, 16, 17, 18, 19, 20, 61),
  账户: range('CORE', 21, 22, 23, 28, 45, 62, 65),
  扩展: range('CORE', 24, 25, 26, 27, 46, 66, 68, 78, 29, 30, 31, 32, 33, 34, 35, 72),
  平台: [...range('AND', 2, 3, 4, 5, 6, 7, 8, 9, 13, 14), ...range('WIN', 4, 5, 6, 7, 8, 9, 10, 14, 15)],
  发布: [...range('CORE', 42, 43, 44), ...range('AND', 11, 12), ...range('WIN', 2, 3, 12, 13, 16)],
}).flatMap(([g, ids]) => ids.map(id => [id, g])));

/** 从各文档 §2 阶段表取得卡片阶段（与 DTOcheck STAGE 检查同一规则）。 */
export function stagesOf(texts) {
  const stageOf = new Map();
  for (const d of DOCS) {
    const t = texts[d.doc]; const m = t.match(/^## 2\. .*$/m); if (!m) continue;
    const rest = t.slice(m.index + m[0].length); const end = rest.search(/^## /m);
    for (const line of (end < 0 ? rest : rest.slice(0, end)).split('\n')) {
      const s = line.match(/^\| (S\d) [^|]*\| ([^|]+) \|/); if (!s) continue;
      for (const id of s[2].match(/(?:CORE|AND|WIN)-\d+/g) ?? []) stageOf.set(id, s[1]);
    }
  }
  return stageOf;
}

/** 计算拆分结果：Map<相对 SADD 的路径, 内容>。卡片从标题行到下一个 ##/### 卡片标题之前（围栏外）。 */
export function splitTexts(texts, {stageOf = stagesOf(texts), groupOf = GROUP_OF} = {}) {
  const files = new Map(); const errors = [];
  for (const d of DOCS) {
    const lines = texts[d.doc].split(/(?<=\n)/);
    const overview = []; let card = null; let fence = false;
    const flush = () => {
      if (!card) return;
      const stage = stageOf.get(card.id), group = groupOf.get(card.id);
      if (!stage) errors.push(`${card.id}: 未出现在 §2 阶段表`);
      if (!group || !GROUPS.includes(group)) errors.push(`${card.id}: 没有分组`);
      const rel = `${folderFor(card.id, stage)}/${cardFileName(stage, card.id, group)}`;
      if (files.has(rel)) errors.push(`${rel}: 重复`);
      files.set(rel, card.lines.join(''));
      card = null;
    };
    for (const line of lines) {
      if (line.startsWith('```')) fence = !fence;
      const head = !fence && line.match(/^(#{1,3}) /);
      const id = !fence && line.match(/^### ((?:CORE|AND|WIN)-\d+) /)?.[1];
      if (id || head) flush();
      if (id) { card = {id, lines: [line]}; overview.push(marker(id) + '\n'); continue; }
      if (card) card.lines.push(line); else overview.push(line);
    }
    flush();
    files.set(`${d.dir}/${OVERVIEW}`, overview.join(''));
  }
  for (const id of groupOf.keys()) if (![...files.keys()].some(f => f.includes(`_${id}_`))) errors.push(`${id}: 分组表中有该卡，但文档中没有`);
  return {files, errors};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const opt = name => { const i = process.argv.indexOf(name); return i < 0 ? undefined : process.argv[i + 1]; };
  const sadd = path.resolve(opt('--sadd') ?? path.join(ROOT, 'SADD'));
  const dry = process.argv.includes('--dry-run');
  if (layoutOf(sadd) !== 'legacy') { console.error('SADD 已是拆分布局'); process.exit(2); }
  const {texts} = readDocs(sadd);
  const {files, errors} = splitTexts(texts);
  if (errors.length) { console.error(errors.join('\n')); process.exit(1); }
  const count = {}; for (const f of files.keys()) { const k = f.split('/')[0]; count[k] = (count[k] ?? 0) + (f.endsWith(OVERVIEW) ? 0 : 1); }
  for (const f of files.keys()) if (fs.existsSync(path.join(sadd, f))) { console.error(`目标已存在：${f}`); process.exit(1); }
  if (dry) {
    // 在临时目录完整演练一遍：写盘、拼回、比对。
    const tmp = fs.mkdtempSync(path.join(fs.realpathSync(process.env.TMPDIR ?? process.env.TEMP ?? '/tmp'), 'sadd-split-'));
    for (const [f, t] of files) { fs.mkdirSync(path.dirname(path.join(tmp, f)), {recursive: true}); fs.writeFileSync(path.join(tmp, f), t); }
    const back = readDocs(tmp);
    const same = DOCS.every(d => back.texts[d.doc] === texts[d.doc]);
    fs.rmSync(tmp, {recursive: true});
    console.log(JSON.stringify({dryRun: true, files: files.size, cards: count, identical: same, issues: back.issues}));
    process.exit(same && !back.issues.length ? 0 : 1);
  }
  for (const [f, t] of files) { fs.mkdirSync(path.dirname(path.join(sadd, f)), {recursive: true}); fs.writeFileSync(path.join(sadd, f), t); }
  // 拼回前先把原文档移开，否则 layoutOf 会判定为混合布局。
  const moved = DOCS.map(d => [path.join(sadd, d.doc), path.join(sadd, d.doc + '.split-tmp')]);
  for (const [a, b] of moved) fs.renameSync(a, b);
  let back, ok = false;
  try { back = readDocs(sadd); ok = DOCS.every(d => back.texts[d.doc] === texts[d.doc]) && !back.issues.length; }
  finally {
    if (ok) for (const [, b] of moved) fs.rmSync(b);
    else {
      for (const f of files.keys()) fs.rmSync(path.join(sadd, f), {force: true});
      for (const [a, b] of moved) fs.renameSync(b, a);
    }
  }
  console.log(JSON.stringify({files: files.size, cards: count, identical: ok, issues: back?.issues ?? []}));
  if (!ok) { console.error('拼回结果与原文档不一致，已回滚'); process.exit(1); }
}
