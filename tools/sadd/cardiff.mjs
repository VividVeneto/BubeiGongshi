#!/usr/bin/env node
// 卡片差异：把基线提交里的旧三份文档与当前工作区的卡片（卡片文件 + 其测试方案）逐卡比较，
// 只报告内容变化。用法：node tools/sadd/cardiff.mjs <卡号|--all> [--base 0773cd3] [--repo DIR]
// 退出码：0 正常；2 基线不存在/缺少旧文档、卡号未知或参数错误。
//   - 当前文本取 layout.readDocs 拼回后的版本：卡片里的“验收标准”引用行已按引用换回 Test/ 文件全文，
//     所以“验收标准从卡片搬到 Test/”不产生差异；章节标题、引言与 <!-- sadd:card --> 标记在卡片之外，不参与比较。
//   - “**规模**”行单独处理：其余内容完全相同而只有规模行不同的卡归入“仅规模口径”。
// 工具项（不属于正式代码），见 SADD/README.md §7.1。
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {DOCS, readDocs} from './layout.mjs';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const DEFAULT_BASE = '0773cd3';
export class CardiffError extends Error {}

const SCALE_LINE = /^\*\*规模\*\*/;
const nl = text => text.replace(/\r\n/g, '\n');

/** 把一份文档切成卡片：Map<卡号, {id, title, text}>。卡片从“### 卡号 名称”到下一个（围栏外）1～3 级标题之前。 */
export function cutCards(text) {
  const cards = new Map(); let card = null; let fence = false;
  const flush = () => { if (card) { cards.set(card.id, {id: card.id, title: card.title, text: card.lines.join('')}); card = null; } };
  for (const line of nl(text).split(/(?<=\n)/)) {
    if (line.startsWith('```')) fence = !fence;
    const head = !fence && /^#{1,3} /.test(line);
    const m = !fence && line.match(/^### ((?:CORE|AND|WIN)-\d+) (.*?)\s*$/);
    if (head) flush();
    if (m) card = {id: m[1], title: m[2], lines: [line]};
    else if (card) card.lines.push(line);
  }
  flush();
  return cards;
}

const git = (repo, args) => execFileSync('git', ['-C', repo, ...args], {encoding: 'utf8', maxBuffer: 1 << 29, stdio: ['ignore', 'pipe', 'pipe']});

/** 读基线提交里的旧三份文档并切卡。基线不存在或没有任何旧文档时抛 CardiffError。 */
export function baseCards(repo, base) {
  try { git(repo, ['rev-parse', '--verify', '--quiet', base + '^{commit}']); }
  catch { throw new CardiffError('基线提交不存在：' + base); }
  const cards = new Map(); let found = 0;
  for (const d of DOCS) {
    let text;
    try { text = git(repo, ['show', base + ':SADD/' + d.doc]); } catch { continue; }
    found++;
    for (const [id, c] of cutCards(text)) cards.set(id, c);
  }
  if (!found) throw new CardiffError('基线 ' + base + ' 中没有旧三份文档（SADD/' + DOCS.map(d => d.doc).join('、') + '）');
  return cards;
}

/** 当前工作区的卡片（拆分布局按标记与测试方案引用拼回）。issues 是布局问题（如测试方案引用不可解析）。 */
export function currentCards(repo) {
  const {texts, issues} = readDocs(path.join(repo, 'SADD'));
  const cards = new Map();
  for (const d of DOCS) for (const [id, c] of cutCards(texts[d.doc])) cards.set(id, c);
  return {cards, issues};
}

/** 去掉规模行与行尾空白，作为“内容”比较的文本。 */
export const contentOf = text => nl(text).split('\n').filter(l => !SCALE_LINE.test(l)).map(l => l.replace(/[ \t]+$/, '')).join('\n').trimEnd();
export const scaleOf = text => nl(text).split('\n').filter(l => SCALE_LINE.test(l)).map(l => l.trimEnd());

/** 行级差异（先去公共首尾，再对中段做 LCS）；返回 [{t: ' '|'-'|'+', s}]。 */
export function diffLines(a, b) {
  let head = 0; while (head < a.length && head < b.length && a[head] === b[head]) head++;
  let tail = 0; while (tail < a.length - head && tail < b.length - head && a[a.length - 1 - tail] === b[b.length - 1 - tail]) tail++;
  const x = a.slice(head, a.length - tail), y = b.slice(head, b.length - tail);
  const w = y.length + 1; const L = new Uint32Array((x.length + 1) * w);
  for (let i = x.length - 1; i >= 0; i--) for (let j = y.length - 1; j >= 0; j--)
    L[i * w + j] = x[i] === y[j] ? L[(i + 1) * w + j + 1] + 1 : Math.max(L[(i + 1) * w + j], L[i * w + j + 1]);
  const ops = a.slice(0, head).map(s => ({t: ' ', s}));
  let i = 0, j = 0;
  while (i < x.length && j < y.length) {
    if (x[i] === y[j]) { ops.push({t: ' ', s: x[i]}); i++; j++; }
    else if (L[(i + 1) * w + j] >= L[i * w + j + 1]) ops.push({t: '-', s: x[i++]});
    else ops.push({t: '+', s: y[j++]});
  }
  while (i < x.length) ops.push({t: '-', s: x[i++]});
  while (j < y.length) ops.push({t: '+', s: y[j++]});
  for (const s of a.slice(a.length - tail)) ops.push({t: ' ', s});
  return ops;
}

/** unified diff 文本（3 行上下文）；无差异返回空串。 */
export function unified(oldText, newText, oldName, newName, context = 3) {
  const ops = diffLines(nl(oldText).split('\n'), nl(newText).split('\n'));
  const changed = ops.map((o, i) => o.t === ' ' ? -1 : i).filter(i => i >= 0);
  if (!changed.length) return '';
  const out = ['--- ' + oldName, '+++ ' + newName];
  const pos = []; let o = 0, n = 0; // 每个 op 之前的旧/新行号（0 起）
  for (const op of ops) { pos.push([o, n]); if (op.t !== '+') o++; if (op.t !== '-') n++; }
  let k = 0;
  while (k < changed.length) {
    let start = Math.max(0, changed[k] - context), end = Math.min(ops.length, changed[k] + context + 1);
    while (k + 1 < changed.length && changed[k + 1] - context <= end) { k++; end = Math.min(ops.length, changed[k] + context + 1); }
    k++;
    const seg = ops.slice(start, end);
    const oc = seg.filter(x => x.t !== '+').length, nc = seg.filter(x => x.t !== '-').length;
    out.push('@@ -' + (oc ? pos[start][0] + 1 : pos[start][0]) + ',' + oc + ' +' + (nc ? pos[start][1] + 1 : pos[start][1]) + ',' + nc + ' @@');
    for (const x of seg) out.push(x.t + x.s);
  }
  return out.join('\n');
}

/** 比较一张卡：unchanged | scale-only | changed，并给出增删行数与字符数（规模行不计入）。 */
export function compareCard(oldText, newText) {
  const a = contentOf(oldText), b = contentOf(newText);
  const scale = {old: scaleOf(oldText), new: scaleOf(newText)};
  const scaleSame = scale.old.join('\n') === scale.new.join('\n');
  if (a === b) return {kind: scaleSame ? 'unchanged' : 'scale-only', scale};
  let addLines = 0, delLines = 0, addChars = 0, delChars = 0;
  for (const o of diffLines(a.split('\n'), b.split('\n'))) {
    if (o.t === '+') { addLines++; addChars += o.s.length; } else if (o.t === '-') { delLines++; delChars += o.s.length; }
  }
  return {kind: 'changed', scale, addLines, delLines, addChars, delChars};
}

/** 比较全部卡片；返回分类结果与布局问题。 */
export function cardiffAll({repo = ROOT, base = DEFAULT_BASE} = {}) {
  const before = baseCards(repo, base); const {cards: now, issues} = currentCards(repo);
  const res = {base, baseCount: before.size, nowCount: now.size, changed: [], scaleOnly: [], added: [], removed: [], unchanged: [], issues};
  for (const [id, c] of now) {
    const old = before.get(id);
    if (!old) { res.added.push({id, title: c.title}); continue; }
    const r = compareCard(old.text, c.text);
    if (r.kind === 'changed') res.changed.push({id, title: c.title, ...r});
    else if (r.kind === 'scale-only') res.scaleOnly.push({id, title: c.title, scale: r.scale});
    else res.unchanged.push(id);
  }
  for (const [id, c] of before) if (!now.has(id)) res.removed.push({id, title: c.title});
  return res;
}

export function formatAll(r) {
  const out = ['基线 ' + r.base + '（' + r.baseCount + ' 张卡）→ 当前工作区（' + r.nowCount + ' 张卡）；无变化 ' + r.unchanged.length + ' 张'];
  out.push('', '## 内容变化（' + r.changed.length + '）');
  for (const c of r.changed) out.push(c.id + ' ' + c.title + '：+' + c.addChars + ' / -' + c.delChars + ' 字符（+' + c.addLines + ' / -' + c.delLines + ' 行）' + (c.scale.old.join() === c.scale.new.join() ? '' : '；规模行也有变化'));
  out.push('', '## 仅规模口径（' + r.scaleOnly.length + '）');
  for (const c of r.scaleOnly) out.push(c.id + ' ' + c.title);
  out.push('', '## 新增卡（' + r.added.length + '）');
  for (const c of r.added) out.push(c.id + ' ' + c.title);
  if (r.removed.length) { out.push('', '## 删除卡（' + r.removed.length + '）'); for (const c of r.removed) out.push(c.id + ' ' + c.title); }
  if (r.issues.length) { out.push('', '## 布局问题（' + r.issues.length + '，会使比较失真）'); for (const i of r.issues) out.push(i.id + ' ' + i.msg); }
  return out.join('\n') + '\n';
}

/** 单卡输出：行级 unified diff（含规模行，便于看到全部差异）。 */
export function cardiffOne(id, {repo = ROOT, base = DEFAULT_BASE} = {}) {
  const before = baseCards(repo, base); const {cards: now, issues} = currentCards(repo);
  const o = before.get(id), n = now.get(id);
  if (!o && !n) throw new CardiffError('基线与当前都没有这张卡：' + id);
  const warn = issues.length ? '\n注意：布局问题会使比较失真：\n' + issues.map(i => '  ' + i.id + ' ' + i.msg).join('\n') + '\n' : '';
  if (!o) return id + ' ' + n.title + '：新增卡（基线 ' + base + ' 没有）。\n' + warn;
  if (!n) return id + ' ' + o.title + '：当前工作区已没有这张卡（基线 ' + base + ' 有）。\n' + warn;
  const r = compareCard(o.text, n.text);
  if (r.kind === 'unchanged') return id + ' ' + n.title + '：相对基线 ' + base + ' 无内容变化。\n' + warn;
  const head = id + ' ' + n.title + '：' + (r.kind === 'scale-only' ? '仅规模口径变化' : '内容变化 +' + r.addChars + ' / -' + r.delChars + ' 字符（+' + r.addLines + ' / -' + r.delLines + ' 行）') + '\n';
  return head + unified(o.text.trimEnd(), n.text.trimEnd(), base + ':' + id, '工作区:' + id) + '\n' + warn;
}

function main(argv) {
  const opt = name => { const i = argv.indexOf(name); return i < 0 ? undefined : argv[i + 1]; };
  const base = opt('--base') ?? DEFAULT_BASE; const repo = path.resolve(opt('--repo') ?? ROOT);
  const skip = new Set(['--base', '--repo']); const rest = argv.filter((a, i) => !skip.has(a) && !skip.has(argv[i - 1]));
  const target = rest[0];
  if (!target || rest.length > 1) throw new CardiffError('用法：node tools/sadd/cardiff.mjs <卡号|--all> [--base 0773cd3]');
  if (target === '--all') return formatAll(cardiffAll({repo, base}));
  if (!/^(?:CORE|AND|WIN)-\d+$/.test(target)) throw new CardiffError('卡号格式应为 CORE-NN、AND-NN 或 WIN-NN：' + target);
  return cardiffOne(target, {repo, base});
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { process.stdout.write(main(process.argv.slice(2))); }
  catch (e) {
    if (e instanceof CardiffError) { console.error(e.message); process.exit(2); }
    throw e;
  }
}
