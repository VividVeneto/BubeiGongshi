#!/usr/bin/env node
// 模块卡结构与文档一致性检查：卡片 ↔ §3 索引 ↔ 依赖图 ↔ 实施阶段 ↔ README §8.6 与计数/版本。
// 用法：node tools/DTOcheck/cards.mjs [--sadd DIR] [--json] [--verbose]
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Report, ROOT, FILES, loadCards, scaleLine, scaleNumber, printReport, argOf} from './lib.mjs';
import {readDocs, folderFor} from '../sadd/layout.mjs';

const LIMIT = 800;
const STAGE_LIMIT = 500;
const STAGES = ['S0', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7'];
const PREFIX = {C: 'CORE', A: 'AND', W: 'WIN'};

/** 解析“01、02、AND-01、CORE-03”形式的依赖列表；缩写沿用最近的前缀（默认 defaultPrefix）。 */
export function parseDeps(text, defaultPrefix) {
  const out = []; let prefix = defaultPrefix;
  for (const m of text.matchAll(/(CORE|AND|WIN)-(\d+)|(\d{2,3})/g)) {
    if (m[1]) { prefix = m[1]; out.push(`${prefix}-${m[2]}`); } else out.push(`${prefix}-${m[3]}`);
  }
  return [...new Set(out)];
}

const section = (text, num) => {
  const m = text.match(new RegExp(`^## ${num}\\. .*$`, 'm'));
  if (!m) return '';
  const rest = text.slice(m.index + m[0].length);
  const n = rest.search(/^## /m);
  return n < 0 ? rest : rest.slice(0, n);
};

/** 构建单元：crates/<名>、server、app、tools、contracts、installer、.github。 */
function unitOf(p) {
  const parts = p.replace(/^\.?\//, '').split('/');
  if (parts[0] === 'crates' && parts[1]) return `crates/${parts[1].replace(/\{.*$/, '')}`;
  return parts[0].replace(/\{.*$/, '');
}
export function buildUnits(scale) {
  const units = new Set();
  for (const m of scale.matchAll(/`([^`]+)`/g)) {
    const t = m[1].trim();
    if (!t.includes('/') || /^https?:/.test(t)) continue;
    if (!/^(?:crates|server|app|tools|contracts|installer|\.github|仓库根)/.test(t)) continue;
    units.add(unitOf(t));
  }
  return units;
}

export function checkCards({sadd = path.join(ROOT, 'SADD')} = {}) {
  const r = new Report('cards');
  let cards;
  try { cards = loadCards(sadd); } catch (e) { r.error('CARD-00', `读取模块卡失败: ${e.message}`); return r; }
  const docs = readDocs(sadd);
  const texts = docs.texts;
  for (const x of docs.issues) r.error(x.id, x.msg);
  const readmePath = path.join(sadd, 'README.md');
  const readme = fs.existsSync(readmePath) ? fs.readFileSync(readmePath, 'utf8') : '';

  // 重复卡号
  const headings = new Map();
  for (const f of FILES) for (const m of texts[f].matchAll(/^### ((?:CORE|AND|WIN)-\d+) /gm)) headings.set(m[1], (headings.get(m[1]) ?? 0) + 1);
  for (const [id, n] of headings) if (n > 1) r.error('CARD-01', `${id}: 卡号重复 ${n} 次`);

  // §3 索引
  const index = new Map();
  for (const f of FILES) {
    const dp = f.startsWith('01') ? 'CORE' : f.startsWith('02') ? 'AND' : 'WIN';
    for (const line of section(texts[f], 3).split('\n')) {
      const m = line.match(/^\| ((?:CORE|AND|WIN)-\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| (\d+) \|/);
      if (!m) continue;
      if (index.has(m[1])) r.error('CARD-02', `${m[1]}: §3 索引重复`);
      index.set(m[1], {name: m[2].trim(), paths: m[3], deps: parseDeps(m[4], dp), scale: Number(m[5])});
    }
  }
  for (const id of cards.keys()) if (!index.has(id)) r.error('CARD-02', `${id}: §3 索引缺少该卡`);
  for (const id of index.keys()) if (!cards.has(id)) r.error('CARD-02', `${id}: §3 索引有该卡但正文没有`);

  for (const [id, c] of cards) {
    const ix = index.get(id); if (!ix) continue;
    const title = c.body.match(/^### \S+ (.+)$/m)?.[1]?.trim();
    if (title !== ix.name) r.error('CARD-03', `${id}: 名称与索引不一致：卡=${title} 索引=${ix.name}`);
    const a = [...c.deps].sort().join(), b = [...ix.deps].sort().join();
    if (a !== b) r.error('CARD-04', `${id}: 依赖与 §3 索引不一致：卡=${c.deps.join(',')} 索引=${ix.deps.join(',')}`);
    const sl = scaleLine(c.body), n = scaleNumber(c.body);
    if (!sl) r.error('CARD-05', `${id}: 缺少“规模”行`);
    else if (Number.isNaN(n)) r.error('CARD-05', `${id}: 规模行没有“约 N 行”`);
    else {
      if (n !== ix.scale) r.error('CARD-05', `${id}: 规模与索引不一致：卡=${n} 索引=${ix.scale}`);
      if (n > LIMIT) r.error('CARD-06', `${id}: 规模 ${n} 行超过 ${LIMIT}，先拆卡`);
      else if (n > STAGE_LIMIT && !/分阶段/.test(sl)) r.error('CARD-06', `${id}: 规模 ${n} 行超过 ${STAGE_LIMIT}，规模行须写“分阶段”`);
    }
    if (/另计|不计入本卡规模|额外约\s*\d+\s*行/.test(sl)) r.error('CARD-07', `${id}: 规模行含“另计/额外”代码，应拆卡或并入估算`);
    const units = buildUnits(sl);
    if (units.size > 1 && !/附属|跨语言/.test(sl)) r.error('CARD-08', `${id}: 规模落在多个构建单元且未声明附属：${[...units].join(' | ')}`);
  }

  // 依赖闭合与环
  for (const [id, c] of cards) for (const d of c.deps) if (!cards.has(d)) r.error('CARD-09', `${id}: 依赖了不存在的卡 ${d}`);
  const state = new Map();
  const dfs = (id, stack) => {
    if (state.get(id) === 2) return;
    if (state.get(id) === 1) { r.error('CARD-10', `依赖环：${[...stack.slice(stack.indexOf(id)), id].join(' -> ')}`); return; }
    state.set(id, 1);
    for (const d of cards.get(id)?.deps ?? []) if (cards.has(d)) dfs(d, [...stack, id]);
    state.set(id, 2);
  };
  for (const id of cards.keys()) dfs(id, []);

  // 依赖图（mermaid）
  const edges = new Map();
  for (const f of FILES) {
    const g = section(texts[f], 1);
    const nodes = new Map();
    for (const m of g.matchAll(/^\s+([CAW]\d+)\["((?:CORE|AND|WIN)-\d+) [^"]*"\]/gm)) {
      const want = `${PREFIX[m[1][0]]}-${m[1].slice(1)}`;
      if (want !== m[2]) r.error('GRAPH-01', `${f}: 节点 ${m[1]} 的标签是 ${m[2]}，应为 ${want}`);
      nodes.set(m[1], m[2]);
    }
    for (const m of g.matchAll(/^\s+([CAW]\d+) --> ([CAW]\d+)\s*$/gm)) {
      const from = `${PREFIX[m[1][0]]}-${m[1].slice(1)}`, to = `${PREFIX[m[2][0]]}-${m[2].slice(1)}`;
      if (!cards.has(from) || !cards.has(to)) { r.error('GRAPH-02', `${f}: 边 ${m[1]} --> ${m[2]} 指向不存在的卡`); continue; }
      if (!edges.has(from)) edges.set(from, new Set());
      edges.get(from).add(to);
      if (!cards.get(from).deps.includes(to)) r.error('GRAPH-03', `${from}: 依赖图边 --> ${to} 不在依赖字段中`);
    }
    for (const id of cards.keys()) if (id.startsWith(f.startsWith('01') ? 'CORE' : f.startsWith('02') ? 'AND' : 'WIN') && !g.includes(`${id[0]}${id.split('-')[1]}[`)) r.error('GRAPH-04', `${id}: 依赖图缺少节点`);
  }
  const reach = (from, to, seen = new Set()) => {
    for (const n of edges.get(from) ?? []) { if (n === to) return true; if (!seen.has(n)) { seen.add(n); if (reach(n, to, seen)) return true; } }
    return false;
  };
  for (const [id, c] of cards) for (const d of c.deps) {
    if (d === 'CORE-01' || d === 'CORE-02') continue;
    if (!reach(id, d)) r.error('GRAPH-05', `${id}: 依赖图未体现直接依赖 ${d}`);
  }

  // 实施阶段
  const stageOf = new Map();
  for (const f of FILES) for (const line of section(texts[f], 2).split('\n')) {
    const m = line.match(/^\| (S\d) [^|]*\| ([^|]+) \|/);
    if (!m) continue;
    for (const id of m[2].match(/(?:CORE|AND|WIN)-\d+/g) ?? []) {
      if (stageOf.has(id) && stageOf.get(id) !== m[1]) r.error('STAGE-01', `${id}: 同时出现在 ${stageOf.get(id)} 与 ${m[1]}`);
      stageOf.set(id, m[1]);
    }
  }
  for (const id of cards.keys()) if (!stageOf.has(id)) r.error('STAGE-02', `${id}: 未出现在任何实施阶段`);
  // 拆分布局：文件名中的 S 编号与所在文件夹必须与实施阶段表一致
  for (const [id, f] of docs.cardFiles) {
    const stage = stageOf.get(id); if (!stage) continue;
    if (f.stage !== stage) r.error('LAYOUT-02', `${f.rel}: 文件名阶段 ${f.stage} 与实施阶段表 ${stage} 不一致`);
    const want = folderFor(id, stage);
    if (f.folder !== want) r.error('LAYOUT-03', `${f.rel}: 应放在 ${want}/`);
  }
  const rank = s => STAGES.indexOf(s);
  for (const [id, c] of cards) for (const d of c.deps) {
    const a = stageOf.get(id), b = stageOf.get(d);
    if (a && b && rank(b) > rank(a)) r.error('STAGE-03', `${id}(${a}): 依赖的 ${d} 在更晚的阶段 ${b}`);
  }

  // README §8.6 与计数
  const classes = new Map(); const readmeStage = new Map(); const seenIn = new Map();
  for (const line of readme.split('\n')) {
    const m = line.match(/^\| ((?:CORE|AND|WIN)-\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| (S\d) \|/);
    if (!m) continue;
    seenIn.set(m[1], (seenIn.get(m[1]) ?? 0) + 1);
    const cls = m[3].trim().replace(/（.*$/, '');
    classes.set(cls, (classes.get(cls) ?? 0) + 1);
    readmeStage.set(m[1], m[6]);
    if (m[2].trim() !== index.get(m[1])?.name) r.error('README-01', `${m[1]}: README §8.6 名称与索引不一致：${m[2].trim()} vs ${index.get(m[1])?.name}`);
  }
  if (readme) {
    for (const id of cards.keys()) { const n = seenIn.get(id) ?? 0; if (n !== 1) r.error('README-02', `${id}: 在 README §8.6 表中出现 ${n} 次（应为 1）`); }
    for (const [id, s] of readmeStage) if (stageOf.has(id) && stageOf.get(id) !== s) r.error('README-03', `${id}: README 阶段 ${s} 与实施阶段表 ${stageOf.get(id)} 不一致`);
    const total = cards.size, by = p => [...cards.keys()].filter(k => k.startsWith(p)).length;
    const m1 = readme.match(/(\d+) 张模块卡（公共核心 (\d+)、Android (\d+)、Windows (\d+)/);
    if (!m1) r.warn('README-04', '找不到“N 张模块卡（公共核心…）”计数句');
    else if ([+m1[1], +m1[2], +m1[3], +m1[4]].join() !== [total, by('CORE'), by('AND'), by('WIN')].join()) r.error('README-04', `README 卡数 ${m1.slice(1, 5).join('/')} 与实际 ${[total, by('CORE'), by('AND'), by('WIN')].join('/')} 不符`);
    const m2 = readme.match(/共\s*(\d+)\s*张卡——前端\s*(\d+)\s*张，端侧核心\s*(\d+)\s*张，后端\s*(\d+)\s*张，工程与发布\s*(\d+)\s*张/);
    const actual = ['前端', '端侧核心', '后端', '工程与发布'].map(k => classes.get(k) ?? 0);
    if (!m2) r.warn('README-05', '找不到“共 N 张卡——前端…”统计句');
    else if ([+m2[1], +m2[2], +m2[3], +m2[4], +m2[5]].join() !== [total, ...actual].join()) r.error('README-05', `README §8.6 统计句 ${m2.slice(1, 6).join('/')} 与表中实际 ${[total, ...actual].join('/')} 不符`);
    for (const m of readme.matchAll(/^#### (前端|端侧核心|后端|工程与发布)（(\d+) 张）/gm)) if (Number(m[2]) !== (classes.get(m[1]) ?? 0)) r.error('README-06', `README 小节“${m[1]}（${m[2]} 张）”与表中实际 ${classes.get(m[1]) ?? 0} 不符`);
    const top = readme.match(/CORE-01～CORE-(\d+)/);
    const maxCore = Math.max(...[...cards.keys()].filter(k => k.startsWith('CORE')).map(k => Number(k.slice(5))));
    if (top && Number(top[1]) !== maxCore) r.error('README-07', `README 写 CORE-01～CORE-${top[1]}，实际最大 CORE-${maxCore}`);
    // 版本一致
    const vers = new Map();
    const v0 = readme.match(/^# SADD[^\n]* v(\d+\.\d+\.\d+)/m)?.[1]; const v1 = readme.match(/^> 版本：v(\d+\.\d+\.\d+)/m)?.[1];
    vers.set('README 标题', v0); vers.set('README 版本行', v1);
    for (const f of FILES) { vers.set(`${f} 标题`, texts[f].match(/^# .* v(\d+\.\d+\.\d+)/m)?.[1]); vers.set(`${f} 版本行`, texts[f].match(/^> 版本：v(\d+\.\d+\.\d+)/m)?.[1]); }
    const distinct = new Set(vers.values());
    if (distinct.size !== 1) r.error('VER-01', `版本号不一致：${[...vers].map(([k, v]) => `${k}=${v}`).join('；')}`);
  }
  r.stats = {cards: cards.size, indexRows: index.size, edges: [...edges.values()].reduce((s, x) => s + x.size, 0), stages: stageOf.size};
  if (docs.layout === 'split') r.stats.cardFiles = docs.cardFiles.size;
  return r;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const r = checkCards({sadd: path.resolve(argOf(process.argv, '--sadd') ?? path.join(ROOT, 'SADD'))});
  console.log(process.argv.includes('--json') ? JSON.stringify(r, null, 2) : printReport(r, {verbose: process.argv.includes('--verbose')}));
  process.exitCode = r.ok ? 0 : 1;
}
