// CORE-70：从唯一文档源校验模块结构、追踪与验收作业索引（单阶段）。
// 只补增量规则；卡 ID 唯一、依赖无环、阶段、索引/依赖图、错误码跨卡唯一由 README §7.1 的文档工具项负责（卡 :7），
// 本卡对它们不输出 finding。卡解析复用 CORE-57 的 load/readDocs，就绪证据复用 CORE-76 的 validateCurrent。
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {load, ROOT} from './pack.mjs';
import {reviewColumn, validateCurrent} from './current.mjs';
import {readDocs} from './layout.mjs';
import {stageTable} from '../DTOcheck/cards.mjs';

// SADD-1 字段顺序（卡 :13）。
export const FIELDS = Object.freeze(['目标', '范围', '依赖', '接口契约', '实现约束', '验收标准', '规模']);
// acceptance_jobs.json 的取值域（卡 :17）。
export const ENVIRONMENTS = Object.freeze(['host-rust', 'host-widget', 'android-host', 'windows-host', 'manual', 'content']);
export const STATUSES = Object.freeze(['active', 'pending-target']);
export const STAGES = Object.freeze(['S0', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7']);
export const MATERIAL_MODES = Object.freeze(['target', 'full-contract', 'symbols', 'outside-context']);
const ROW_FIELDS = Object.freeze(['card', 'requirement', 'criterion', 'stage', 'environment', 'target', 'status']);
const JOB_FILE = '.github/workflows/ci.yml';
const APPENDIX = '附录D-编码就绪检查记录.md';
const JOBS_FILE = 'tools/ci/acceptance_jobs.json';

// 已知文档缺陷的基线豁免（任务卡第④条：真实数据违规且属他卡文档问题时按最小解释留档，不改 SADD）。
// 命中后降为 warning 并保留在 structure.json 的 warnings 中，不影响退出码；修复归所属卡。
export const BASELINE = Object.freeze([
  {rule: 'SADD-1', card: 'CORE-101', message: 'missing field 实现约束',
    reason: 'CORE-101 卡缺“实现约束”字段（S5 卡，属该卡文档修订）'},
  {rule: 'SADD-11', card: 'CORE-85', message: 'Q4',
    reason: 'CORE-85 正文未提 Q4 而 §6 影响列列出（属该卡文档修订）'},
]);

export class UsageError extends Error {}

const abs = (p) => path.resolve(p);
const escaped = (s) => JSON.stringify(s);
const lineAt = (text, index) => text.slice(0, index).split('\n').length;

/** 把代码围栏与 HTML 注释内的文字抹成空格（保留行数），使其中的字段字样不算字段（卡 :13）。 */
export function maskText(text) {
  const out = [];
  let fence = false;
  let comment = false;
  for (const raw of String(text).split('\n')) {
    if (/^\s*(?:```|~~~)/.test(raw)) { fence = !fence; out.push(''); continue; }
    if (fence) { out.push(''); continue; }
    let line = raw;
    if (comment) {
      const end = line.indexOf('-->');
      if (end < 0) { out.push(''); continue; }
      line = ' '.repeat(end + 3) + line.slice(end + 3);
      comment = false;
    }
    let open = line.indexOf('<!--');
    while (open >= 0) {
      const end = line.indexOf('-->', open + 4);
      if (end < 0) { line = line.slice(0, open); comment = true; break; }
      line = line.slice(0, open) + ' '.repeat(end + 3 - open) + line.slice(end + 3);
      open = line.indexOf('<!--', open);
    }
    out.push(line);
  }
  return out.join('\n');
}

/** 卡片七字段的出现位置（1 起行号），只看行首 **名称** 形式的字段标题。 */
export function fieldLines(text) {
  const fields = [];
  maskText(text).split('\n').forEach((line, i) => {
    const m = line.match(/^\*\*([^*]+)\*\*/);
    if (!m) return;
    const name = m[1].split(/[：:]/)[0].trim();
    if (FIELDS.includes(name)) fields.push({name, line: i + 1});
  });
  return fields;
}

/** 测试方案中被计为验收条目的行：“- [Rxx]”开头（卡 :17 criterion 计数口径）。 */
export function criteriaLines(text) {
  const out = [];
  String(text ?? '').split('\n').forEach((line, i) => {
    if (!/^-\s*\[/.test(line)) return;
    const reqs = [...line.matchAll(/\[(R\d+(?:\.[a-z])?)\]/g)].map(m => m[1]);
    if (reqs.length) out.push({line: i + 1, reqs});
  });
  return out;
}

class Findings {
  constructor() { this.findings = []; this.warnings = []; this.skips = []; }

  error(rule, card, file, line, message) {
    const entry = {rule, card: card ?? '', file, line: Number.isInteger(line) ? line : 1, message};
    const base = BASELINE.find(b => b.rule === rule && b.card === card && message.includes(b.message));
    if (base) { this.warnings.push({...entry, reason: base.reason}); return null; }
    this.findings.push(entry);
    return entry;
  }

  warn(rule, card, file, line, message, reason) {
    const entry = {rule, card: card ?? '', file, line: Number.isInteger(line) ? line : 1, message};
    if (reason) entry.reason = reason;
    this.warnings.push(entry);
  }

  skip(message) { if (!this.skips.includes(message)) this.skips.push(message); }
}

const byText = (values) => [...values].sort((a, b) => (JSON.stringify(a) < JSON.stringify(b) ? -1 : 1));

function readJson(file, what) {
  if (!fs.existsSync(file)) throw new UsageError('missing ' + what + '（' + path.basename(file) + '）');
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) { throw new UsageError(what + ' 不是有效 JSON'); }
}

// —— SADD-1：七字段与章节结构（卡 :13）。
function checkStructure(docs, f) {
  for (const [id, own] of docs.cardFiles) {
    const fields = fieldLines(own.raw);
    const first = new Map();
    for (const field of fields) {
      if (first.has(field.name)) f.error('SADD-1', id, docs.docRel(own.rel), field.line, 'duplicate field ' + field.name);
      else first.set(field.name, field);
    }
    for (const name of FIELDS) if (!first.has(name)) f.error('SADD-1', id, docs.docRel(own.rel), 1, 'missing field ' + name);
    let prev = -1;
    for (const field of [...first.values()].sort((a, b) => a.line - b.line)) {
      const index = FIELDS.indexOf(field.name);
      if (index < prev) f.error('SADD-1', id, docs.docRel(own.rel), field.line, 'field order ' + field.name + ' after ' + FIELDS[prev]);
      prev = Math.max(prev, index);
    }
    const scope = first.get('范围');
    if (!scope) continue;
    const lines = maskText(own.raw).split('\n');
    const nextField = [...first.values()].map(x => x.line).filter(x => x > scope.line).sort((a, b) => a - b)[0];
    const block = lines.slice(scope.line, (nextField ?? lines.length + 1) - 1).join('\n');
    for (const item of ['包含', '不包含']) {
      if (!new RegExp('^-\\s*' + item + '[：:]', 'm').test(block)) f.error('SADD-1', id, docs.docRel(own.rel), scope.line, 'missing 范围 item ' + item);
    }
  }
}

// —— SADD-7：卡内相对链接（卡 :13）。
function checkLinks(docs, f) {
  for (const [id, own] of docs.cardFiles) {
    const cardFile = path.join(docs.sadd, own.rel);
    maskText(own.raw).split('\n').forEach((line, i) => {
      for (const m of line.matchAll(/\[[^\]\n]*\]\(([^)\n]+)\)/g)) {
        let target = m[1].trim().replace(/^</, '').replace(/>$/, '');
        if (!target || target.startsWith('#') || /^[a-z][a-z0-9+.-]*:/i.test(target)) continue;
        const anchor = target.indexOf('#');
        target = (anchor < 0 ? target : target.slice(0, anchor)).trim();
        if (!target) continue;
        let decoded = target;
        try { decoded = decodeURIComponent(target); } catch { /* 非法转义按原文查找 */ }
        if (!fs.existsSync(path.resolve(path.dirname(cardFile), decoded))) {
          f.error('SADD-7', id, docs.docRel(own.rel), i + 1, 'broken link ' + target);
        }
      }
    });
  }
}

// —— SADD-6：需求双向追踪（卡 :13）。返回 §5 需求表供验收清单复用。
function parseRequirements(sadd) {
  const readmePath = path.join(sadd, 'README.md');
  if (!fs.existsSync(readmePath)) throw new UsageError('missing SADD/README.md');
  const text = fs.readFileSync(readmePath, 'utf8');
  const requirements = new Map();
  text.split('\n').forEach((line, i) => {
    const m = line.match(/^\| (R\d+(?:\.[a-z])?) \|/);
    if (!m) return;
    const cells = line.split('|').map(c => c.trim());
    const cardCell = cells.at(-2) ?? '';
    requirements.set(m[1], {line: i + 1, cards: cardCell.match(/(?:CORE|AND|WIN)-\d+/g) ?? []});
  });
  if (!requirements.size) throw new UsageError('README §5 需求追踪表未解析出任何 [Rxx]');
  return {text, requirements};
}

function checkTracking(docs, requirements, f) {
  const reqs = requirements.requirements;
  const readme = docs.docRel('README.md');
  const refs = new Map();
  for (const [id, own] of docs.cardFiles) {
    if (!own.test) continue;
    for (const entry of criteriaLines(own.test.text)) {
      for (const req of entry.reqs) {
        if (!refs.has(req)) refs.set(req, []);
        refs.get(req).push({card: id, file: docs.docRel(own.test.rel), line: entry.line});
      }
    }
  }
  for (const [req, list] of refs) {
    if (reqs.has(req)) continue;
    for (const where of list) f.error('SADD-6', where.card, where.file, where.line, 'test plan references unknown requirement ' + req);
  }
  for (const [req, row] of reqs) {
    for (const card of row.cards) {
      if (!docs.cardFiles.has(card)) f.error('SADD-6', card, readme, row.line, 'tracking row ' + req + ' lists unknown card ' + card);
    }
    const covered = refs.has(req) || [...refs.keys()].some(k => k.startsWith(req + '.'));
    if (!covered && ![...refs.keys()].some(k => req.startsWith(k + '.'))) {
      f.error('SADD-6', '', readme, row.line, 'requirement ' + req + ' is not referenced by any test plan');
    }
  }
}

// —— SADD-8：错误表结构（卡 :13）。HTTP 列与级别取值域按 CORE-02 的 registry 判定。
function errorRegistry(root) {
  const file = path.join(root, 'contracts/errors/registry.yaml');
  if (!fs.existsSync(file)) return null;
  const registry = new Map();
  let code = null;
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    const hit = line.match(/^\s*-\s*code:\s*([A-Za-z0-9_.-]+)\s*$/);
    if (hit) { code = hit[1]; registry.set(code, {severity: 'error', surface: 'client'}); continue; }
    if (!code) continue;
    const severity = line.match(/^\s*severity:\s*([a-z]+)\s*$/);
    if (severity) registry.get(code).severity = severity[1];
    const surface = line.match(/^\s*surface:\s*([a-z]+)\s*$/);
    if (surface) registry.get(code).surface = surface[1];
  }
  return registry.size ? registry : null;
}

const bare = (cell) => String(cell ?? '').replace(/（[^）]*）\s*$/, '').trim();
const codeOf = (cell) => bare(String(cell ?? '').replace(/[\s`]/g, ''));

function checkErrorTables(root, docs, f) {
  const registry = errorRegistry(root);
  // 级别取值域以 CORE-02 注册表为准（含 info）；注册表缺失时退化为卡面所列 error/warning。
  const levels = registry ? new Set([...registry.values()].map(e => e.severity)) : new Set(['error', 'warning']);
  const unregistered = new Set();
  for (const [id, own] of docs.cardFiles) {
    const lines = maskText(own.raw).split('\n');
    let needsHttp = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (!line.startsWith('|')) continue;
      const head = line.split('|').map(c => c.trim()).slice(1, -1);
      if (bare(head[0]) !== '错误码') continue;
      // 只处理本卡自有错误表：须声明 级别/可重试 列；他卡错误码引用表（错误码/定义卡/触发条件）不属本规则。
      if (!head.slice(1).some(cell => ['级别', '可重试'].includes(bare(cell)))) continue;
      const file = docs.docRel(own.rel);
      const headerLine = i + 1;
      if (head[1] !== '级别' || head[2] !== '可重试') {
        f.error('SADD-8', id, file, headerLine, 'error table must start with 错误码/级别/可重试 columns');
      }
      const tail = head.slice(3);
      const http = tail.filter(cell => cell === 'HTTP').length;
      const trigger = tail.filter(cell => /^触发条件/.test(cell)).length;
      if (!tail.length) f.error('SADD-8', id, file, headerLine, 'error table lacks 触发条件 column');
      else if (!(tail[0] === 'HTTP' || /^触发条件/.test(tail[0]))) {
        f.error('SADD-8', id, file, headerLine, 'error table column 4 must be HTTP or 触发条件…');
      }
      if (trigger !== 1) f.error('SADD-8', id, file, headerLine, 'error table must have exactly one 触发条件 column');
      else if (!/^触发条件/.test(tail.at(-1))) f.error('SADD-8', id, file, headerLine, '触发条件 column must be last');
      if (http > 1) f.error('SADD-8', id, file, headerLine, 'error table has more than one HTTP column');
      for (const cell of tail) {
        if (cell === 'HTTP' || /^触发条件/.test(cell)) continue;
        f.error('SADD-8', id, file, headerLine, 'unexpected tail column ' + cell);
      }
      const codes = new Set();
      for (let j = i + 1; j < lines.length && lines[j].startsWith('|'); j++) {
        if (/^\|\s*:?-{3}/.test(lines[j])) continue;
        const cells = lines[j].split('|').map(c => c.trim()).slice(1, -1);
        const rowLine = j + 1;
        if (cells.length !== head.length) {
          f.error('SADD-8', id, file, rowLine, 'row width ' + cells.length + ' differs from header width ' + head.length + ' for ' + (codeOf(cells[0]) || '(empty)'));
          continue;
        }
        const code = codeOf(cells[0]);
        if (!code) { f.error('SADD-8', id, file, rowLine, 'error table row without 错误码'); continue; }
        if (codes.has(code)) f.error('SADD-8', id, file, rowLine, 'duplicate error code ' + code + ' in one table');
        codes.add(code);
        if (!levels.has(cells[1])) f.error('SADD-8', id, file, rowLine, 'invalid 级别 for ' + code + ': ' + cells[1]);
        if (!['是', '否'].includes(cells[2])) f.error('SADD-8', id, file, rowLine, 'invalid 可重试 for ' + code + ': ' + cells[2]);
        const entry = registry?.get(code);
        if (!entry) unregistered.add(code);
        else if (['server', 'both'].includes(entry.surface)) needsHttp = true;
      }
      if (needsHttp && !tail.includes('HTTP')) {
        f.error('SADD-8', id, file, headerLine, 'server-side error table lacks HTTP column');
      }
    }
  }
  if (unregistered.size) {
    f.skip('SKIP pending SADD-8 HTTP column: ' + [...unregistered].sort().join('、') + ' 未在 registry 登记');
  } else if (!registry) {
    f.skip('SKIP pending SADD-8 HTTP column: contracts/errors/registry.yaml 缺失或为空');
  }
}

// —— SADD-11：Q 影响列与正文一致（卡 :13）。
function checkQImpact(readmeText, docs, f) {
  const rows = new Map();
  readmeText.split('\n').forEach((line, i) => {
    const m = line.match(/^\| (Q\d+) \|/);
    if (!m) return;
    const cells = line.split('|').map(c => c.trim());
    rows.set(m[1], {line: i + 1, cards: (cells.at(-2) ?? '').match(/(?:CORE|AND|WIN)-\d+/g) ?? []});
  });
  if (!rows.size) return;
  for (const [q, row] of rows) {
    for (const card of row.cards) {
      const own = docs.cardFiles.get(card);
      if (!own) { f.error('SADD-11', card, docs.docRel('README.md'), row.line, q + ' lists unknown card ' + card); continue; }
      if (!new RegExp('\\b' + q + '\\b').test(own.raw)) {
        f.error('SADD-11', card, docs.docRel('README.md'), row.line, q + ' is listed as affecting ' + card + ' but the card body does not mention it');
      }
    }
  }
  for (const [id, own] of docs.cardFiles) {
    for (const q of new Set([...own.raw.matchAll(/\bQ\d+\b/g)].map(m => m[0]))) {
      const row = rows.get(q);
      if (!row) { f.warn('SADD-11', id, docs.docRel(own.rel), 1, 'card mentions ' + q + ' which §6 does not define'); continue; }
      if (!row.cards.includes(id)) f.warn('SADD-11', id, docs.docRel('README.md'), row.line, 'card mentions ' + q + ' but the Q row does not list it as affected', '说明性引用，仅提示');
    }
  }
}

// —— SADD-12：D.10/D.12 证据适配（卡 :13）。等级、旗标与结论只由 CORE-76 判定。
function currentVersionDate(readmeText) {
  for (const line of String(readmeText).split('\n')) {
    if (!line.startsWith('|') || !line.includes('现行')) continue;
    for (const cell of line.split('|').map(c => c.trim())) {
      const hit = cell.replace(/\*/g, '');
      if (/^\d{4}-\d{2}-\d{2}$/.test(hit)) return hit;
    }
  }
  return null;
}

function checkCurrent(sadd, docs, cards, readmeText, f) {
  const appendixPath = path.join(sadd, APPENDIX);
  if (!fs.existsSync(appendixPath)) throw new UsageError('missing ' + APPENDIX);
  const text = fs.readFileSync(appendixPath, 'utf8');
  const section = text.split('## D.10 ')[1];
  const block = section ? section.split(/\n## /)[0].split('### D.10.1')[0] : '';
  if (!block) throw new UsageError(APPENDIX + ' 缺少 D.10 区块');
  const offset = lineAt(text, text.indexOf('## D.10 ')) - 1;
  const blockLines = block.split('\n');
  const rows = blockLines.filter(line => /^\| (?:CORE|AND|WIN)-\d+ \|/.test(line));
  const header = blockLines.find(line => line.startsWith('| 编号 |'));
  const columns = header ? header.split('|').map(c => c.trim()) : [];
  const gradeColumn = reviewColumn(columns);
  const version = gradeColumn >= 0 ? String(columns[gradeColumn]).split(' ')[0] : '';
  const reviewFile = version ? path.join(sadd, 'reports', version + '-reviews.json') : '';
  let reviews = {version: 1, entries: []};
  if (reviewFile && fs.existsSync(reviewFile)) {
    try { reviews = JSON.parse(fs.readFileSync(reviewFile, 'utf8')); } catch { throw new UsageError('reviews JSON 损坏（' + path.basename(reviewFile) + '）'); }
  }
  if (!rows.length) throw new UsageError(APPENDIX + ' 的 D.10 未解析出任何卡行');

  const cardLine = (id) => {
    const index = blockLines.findIndex(line => line.startsWith('| ' + id + ' |'));
    return index < 0 ? 1 : offset + index + 1;
  };
  for (const message of validateCurrent(rows, columns, cards, reviews, text)) {
    const card = message.match(/(?:CORE|AND|WIN)-\d+/)?.[0] ?? '';
    f.error('SADD-12', card, docs.docRel(APPENDIX), card ? cardLine(card) : 1, message.replace(/^SADD-12: /, ''));
  }

  const baseline = currentVersionDate(readmeText);
  const dated = (Array.isArray(reviews.entries) ? reviews.entries : [])
    .filter(review => review && typeof review.card === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(review.date ?? ''));
  // 取不到 README 现行版本日期时无从比较：不许静默跳过，按既有 warning 通道显式报“未校验”（C70-N6）。
  if (!baseline && dated.length) {
    f.warn('SADD-12', '', docs.docRel('README.md'), 1,
      'review date ordering is not checked: README has no 现行 version date row',
      'README 缺带“现行”的版本日期行，日期先后校验未执行（只提示，不判通过）');
  }
  for (const review of Array.isArray(reviews.entries) ? reviews.entries : []) {
    if (!review || typeof review.card !== 'string') continue;
    const line = cardLine(review.card);
    const previous = Array.isArray(review.history) ? review.history.at(-1) : null;
    if (previous && typeof previous.reviewer === 'string' && previous.reviewer.trim() &&
      previous.reviewer === review.reviewer) {
      f.error('SADD-12', review.card, docs.docRel(APPENDIX), line, 'reviewer ' + review.reviewer + ' repeats the preceding record');
    }
    if (baseline && /^\d{4}-\d{2}-\d{2}$/.test(review.date ?? '') && review.date < baseline) {
      f.error('SADD-12', review.card, docs.docRel(APPENDIX), line, 'review date ' + review.date + ' is earlier than the current version date ' + baseline);
    }
  }
}

// —— SADD-9/10：材料输入（卡 :13）。
function checkMaterial(material, cards, docs, f) {
  if (!material) { f.skip('SKIP pending SADD-9'); return; }
  const dir = abs(material);
  const stat = fs.statSync(dir, {throwIfNoEntry: false});
  if (!stat || !stat.isDirectory()) throw new UsageError('material 目录不可读');
  const file = path.join(dir, 'report.json');
  if (!fs.existsSync(file)) throw new UsageError('material 目录缺 report.json');
  let report;
  try { report = JSON.parse(fs.readFileSync(file, 'utf8')); } catch { throw new UsageError('material report.json 损坏（不是有效 JSON）'); }
  const broken = [];
  if (!report || typeof report !== 'object') broken.push('root');
  else for (const key of ['id', 'manifest', 'filteredFiles', 'missingFromMaterials']) {
    if (key === 'id' ? typeof report.id !== 'string' : !Array.isArray(report[key])) broken.push(key);
  }
  if (broken.length) throw new UsageError('material report.json 缺字段: ' + broken.join(', '));

  const where = (card) => docs.cardFiles.get(card)?.rel ?? 'report.json';
  if (!cards.has(report.id)) f.error('SADD-9', report.id, 'report.json', 1, 'material target is not a known card: ' + report.id);
  const listed = new Set();
  for (const entry of report.manifest) {
    const card = typeof entry?.card === 'string' ? entry.card : '';
    listed.add(card);
    if (!card || !cards.has(card)) f.error('SADD-9', card, where(card), 1, 'material manifest lists unknown card ' + (card || '(missing)'));
    if (!MATERIAL_MODES.includes(entry?.mode)) f.error('SADD-9', card, where(card), 1, 'material manifest mode invalid: ' + String(entry?.mode));
    if (!Array.isArray(entry?.retained)) f.error('SADD-9', card, where(card), 1, 'material manifest entry lacks retained list');
    if (entry?.mode === 'symbols' && !Number.isInteger(entry?.mentionOnly)) {
      f.error('SADD-9', card, where(card), 1, 'symbol-only material entry lacks mentionOnly accounting');
    }
  }
  for (const id of [report.id, ...(Array.isArray(report.closure) ? report.closure : [])]) {
    if (!listed.has(id)) f.error('SADD-9', id, where(id), 1, 'closure card ' + id + ' is absent from the material manifest');
  }
  for (const miss of report.missingFromMaterials) {
    const symbol = String(miss?.symbol ?? '(missing)');
    const sources = Array.isArray(miss?.sources) ? miss.sources : [];
    const resolvable = sources.length > 0 && sources.every(s => typeof s?.card === 'string' && cards.has(s.card) &&
      typeof s?.file === 'string' && s.file.trim() && Number.isInteger(s?.line) && s.line >= 1);
    if (!resolvable) f.error('SADD-9', '', 'report.json', 1, 'symbol ' + symbol + ' is omitted without a resolvable source');
    f.warn('SADD-10', '', 'report.json', 1, 'symbol ' + symbol + ' is referenced but not included in the materials; confirm semantic coverage');
  }
  for (const symbol of Array.isArray(report.undefinedIdentifiers) ? report.undefinedIdentifiers : []) {
    f.warn('SADD-10', '', 'report.json', 1, 'undefined identifier ' + String(symbol) + ' needs review');
  }
}

// —— 清单抄录（卡 :15）。
function readLists(root) {
  const manifest = readJson(path.join(root, 'contracts/dto/manifest.json'), 'contracts/dto/manifest.json');
  const shared = readJson(path.join(root, 'contracts/policies/shared-writes.json'), 'contracts/policies/shared-writes.json');
  if (!Array.isArray(manifest?.ops)) throw new UsageError('contracts/dto/manifest.json 的 ops 必须是数组');
  if (!Array.isArray(shared?.entries)) throw new UsageError('contracts/policies/shared-writes.json 的 entries 必须是数组');
  const ops = manifest.ops.map(o => ({op: String(o?.op ?? ''), owner: String(o?.owner ?? ''), mode: String(o?.mode ?? '')}));
  const owners = shared.entries.map(e => ({kind: String(e?.kind ?? ''), key: String(e?.key ?? ''), owner: String(e?.owner ?? ''), point: String(e?.point ?? '')}));
  return {ops: byText(ops), owners: byText(owners)};
}

// —— acceptance_jobs.json 容器与发布门禁（卡 :17、:19）。
function ciJobs(root) {
  const file = path.join(root, JOB_FILE);
  if (!fs.existsSync(file)) return null;
  const lines = fs.readFileSync(file, 'utf8').split('\n');
  const start = lines.findIndex(line => /^jobs:\s*$/.test(line));
  if (start < 0) return null;
  const jobs = new Set();
  for (let i = start + 1; i < lines.length; i++) {
    const line = lines[i];
    if (/^\S/.test(line)) break;
    const m = line.match(/^ {2}([A-Za-z0-9_.-]+):/);
    if (m) jobs.add(m[1]);
  }
  return jobs;
}

function targetExists(root, target, jobs) {
  if (target.startsWith('path:')) {
    const rel = target.slice(5);
    if (!rel || rel.includes('\\') || rel.startsWith('/') || /^[A-Za-z]:/.test(rel) || rel.split('/').includes('..')) return false;
    const stat = fs.statSync(path.resolve(root, rel), {throwIfNoEntry: false});
    return Boolean(stat && stat.isFile());
  }
  return Boolean(jobs && jobs.has(target.slice(4)));
}

function checkAcceptance(root, docs, requirements, stageOf, release, f) {
  const file = path.join(root, JOBS_FILE);
  const label = JOBS_FILE;
  let doc = {version: 1, rows: []};
  let text = '';
  if (!fs.existsSync(file)) {
    f.skip('SKIP pending acceptance_jobs.json（CORE-41 未创建）');
  } else {
    text = fs.readFileSync(file, 'utf8');
    try { doc = JSON.parse(text); } catch { throw new UsageError(label + ' 不是有效 JSON'); }
    if (!doc || typeof doc !== 'object' || Array.isArray(doc)) throw new UsageError(label + ' 顶层必须是对象');
    if (doc.version !== 1) throw new UsageError(label + ' 的 version 必须为 1');
    if (!Array.isArray(doc.rows)) throw new UsageError(label + ' 缺少 rows 数组');
    for (const key of Object.keys(doc)) {
      if (key !== 'version' && key !== 'rows') f.error('SADD-13', '', label, 1, 'unexpected top-level key ' + key);
    }
  }
  const jobs = ciJobs(root);
  if (jobs === null) f.warn('SADD-13', '', JOB_FILE, 1, 'ci.yml 不存在或没有顶层 jobs 键，job: 目标一律视为不存在');
  let cursor = 0;
  const rowLine = (row) => {
    const index = text.indexOf(escaped(String(row?.card ?? '')), cursor);
    if (index < 0) return 1;
    cursor = index;
    return lineAt(text, index);
  };
  const seen = new Set();
  for (const row of doc.rows) {
    const line = rowLine(row);
    if (!row || typeof row !== 'object' || Array.isArray(row)) { f.error('SADD-13', '', label, line, 'row must be an object'); continue; }
    const card = String(row.card ?? '');
    for (const key of ROW_FIELDS) if (!Object.hasOwn(row, key)) f.error('SADD-13', card, label, line, 'row lacks field ' + key);
    for (const key of Object.keys(row)) if (!ROW_FIELDS.includes(key)) f.error('SADD-13', card, label, line, 'row has unexpected field ' + key);
    const own = docs.cardFiles.get(card);
    if (!own) f.error('SADD-13', card, label, line, 'row names unknown card ' + card);
    if (typeof row.requirement !== 'string' || !/^\[R\d+(?:\.[a-z])?\]$/.test(row.requirement)) {
      f.error('SADD-13', card, label, line, 'requirement must be [Rxx]: ' + String(row.requirement));
    } else if (!requirements.requirements.has(row.requirement.replace(/[\[\]]/g, ''))) {
      f.error('SADD-13', card, label, line, 'requirement ' + String(row.requirement) + ' is not in README §5');
    }
    if (typeof row.criterion !== 'string' || !/^[1-9]\d*$/.test(row.criterion)) {
      f.error('SADD-13', card, label, line, 'criterion must be a 1-based index string: ' + String(row.criterion));
    } else if (own?.test) {
      const count = criteriaLines(own.test.text).length;
      if (Number(row.criterion) > count) f.error('SADD-13', card, label, line, 'criterion ' + row.criterion + ' exceeds the test plan criteria (' + count + ')');
    }
    if (!ENVIRONMENTS.includes(row.environment)) f.error('SADD-13', card, label, line, 'environment out of range: ' + String(row.environment));
    if (!STATUSES.includes(row.status)) f.error('SADD-13', card, label, line, 'status out of range: ' + String(row.status));
    if (!STAGES.includes(row.stage)) f.error('SADD-13', card, label, line, 'stage out of range: ' + String(row.stage));
    else if (stageOf.size) {
      const stage = stageOf.get(card);
      if (stage !== row.stage) f.error('SADD-13', card, label, line, 'stage ' + row.stage + ' differs from the §2 stage table (' + String(stage) + ') for ' + card);
    } else f.skip('SKIP pending SADD-13 stage comparison: §2 阶段表未解析出任何卡');
    const key = [card, String(row.criterion), String(row.environment)].join('|');
    if (seen.has(key)) f.error('SADD-13', card, label, line, 'duplicate acceptance key ' + key);
    seen.add(key);
    const target = String(row.target ?? '');
    if (!/^(path|job):/.test(target)) {
      f.error('SADD-13', card, label, line, 'target must start with path: or job:: ' + target);
      continue;
    }
    const exists = targetExists(root, target, jobs);
    if (exists) continue;
    if (row.status === 'active') f.error('SADD-13', card, label, line, 'active target does not exist: ' + target);
    else f.skip('SKIP pending ' + card + ': ' + target);
  }
  if (!release) return;
  if (!fs.existsSync(file)) throw new UsageError('release 门禁需要 ' + label + '（缺文件）');
  const s7 = doc.rows.filter(row => row && row.stage === 'S7');
  if (!s7.length) f.error('SADD-13', '', label, 1, 'release gate: rows 中没有 stage=S7 的发布验收行');
  for (const row of s7) {
    const card = String(row.card ?? '');
    const index = text.indexOf(escaped(card));
    const line = index < 0 ? 1 : lineAt(text, index);
    const key = '(' + card + ', ' + String(row.criterion) + ', ' + String(row.environment) + ')';
    if (row.status === 'pending-target') f.error('SADD-13', card, label, line, 'release gate: pending-target ' + key);
    else if (!targetExists(root, String(row.target ?? ''), jobs)) {
      f.error('SADD-13', card, label, line, 'release gate: active target does not exist ' + key + ': ' + String(row.target ?? ''));
    }
  }
}

const sortKey = (entry) => [entry.card ?? '', entry.rule, entry.file, String(entry.line).padStart(8, '0')].join('\u0000');
const sorted = (list) => [...list].sort((a, b) => (sortKey(a) < sortKey(b) ? -1 : sortKey(a) > sortKey(b) ? 1 : 0));

/** 运行全部增量规则；退出码 0 无 error、1 违例；读写/解析错误抛 UsageError（CLI 退出 2）。 */
export function run({root = ROOT, sadd = null, material = null, release = false, out = null} = {}) {
  const rootPath = abs(root);
  const saddPath = sadd ? abs(sadd) : path.join(rootPath, 'SADD');
  const stat = fs.statSync(saddPath, {throwIfNoEntry: false});
  if (!stat || !stat.isDirectory()) throw new UsageError('SADD 目录不可读');
  const docs = readDocs(saddPath, {tests: true});
  docs.sadd = saddPath;
  const saddRel = path.relative(rootPath, saddPath).split(path.sep).join('/');
  docs.docRel = (rel) => (saddRel ? saddRel + '/' + String(rel) : String(rel));
  if (docs.layout !== 'split') throw new UsageError('SADD 不是拆分布局（缺 00-总览.md）');
  const cards = load(saddPath, {tests: true}); // CORE-57：卡集合与依赖
  if (!cards.size) throw new UsageError('未从 SADD 解析出任何模块卡');

  const f = new Findings();
  let stageOf = new Map();
  try { ({stageOf} = stageTable(saddPath, docs)); } catch (error) {
    f.warn('SADD-13', '', docs.docRel('00-总览.md'), 1, '§2 阶段表不可用（' + error.message + '）');
  }
  const requirements = parseRequirements(saddPath);
  checkStructure(docs, f);
  checkTracking(docs, requirements, f);
  checkLinks(docs, f);
  checkErrorTables(rootPath, docs, f);
  checkQImpact(requirements.text, docs, f);
  checkCurrent(saddPath, docs, cards, requirements.text, f);
  checkMaterial(material, cards, docs, f);
  checkAcceptance(rootPath, docs, requirements, stageOf, release, f);
  const {ops, owners} = readLists(rootPath);

  const structure = {
    version: 1,
    generatedAt: new Date().toISOString(),
    cards: byText([...docs.cardFiles.values()].map(own => ({id: own.id, stage: own.stage, file: docs.docRel(own.rel)}))),
    findings: sorted(f.findings),
    ops,
    owners,
  };
  if (out) {
    const dir = abs(out);
    fs.mkdirSync(dir, {recursive: true});
    fs.writeFileSync(path.join(dir, 'structure.json'), JSON.stringify(structure, null, 2) + '\n');
  }
  return {code: structure.findings.length ? 1 : 0, findings: structure.findings, warnings: f.warnings, skips: f.skips, structure};
}

/** 终端渲染：逐条 finding 行，SKIP 行与末行计数（卡 :13）。 */
export function render(result) {
  const lines = result.findings.map(f => f.file + ':' + f.line + ': ' + f.rule + ' ' + f.message);
  lines.push(...result.warnings.map(w => 'warning ' + w.file + ':' + w.line + ': ' + w.rule + ' ' + w.message + (w.reason ? '（' + w.reason + '）' : '')));
  lines.push(...result.skips);
  lines.push('共 ' + result.findings.length + ' 项违例，' + result.warnings.length + ' 项 warning，' + result.skips.length + ' 项 SKIP');
  return lines.join('\n') + '\n';
}

/** CLI：--sadd <目录> [--material <目录>] --out <目录> [--release]；--root 仅供测试指定仓库根。 */
export function main(argv = process.argv.slice(2)) {
  const opts = {root: ROOT, sadd: null, material: null, release: false, out: null};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    const value = () => {
      const next = argv[++i];
      if (next === undefined || next.startsWith('--')) throw new UsageError('参数 ' + arg + ' 缺少取值');
      return next;
    };
    try {
      if (arg === '--release') { opts.release = true; continue; }
      if (arg === '--sadd') { opts.sadd = value(); continue; }
      if (arg === '--material') { opts.material = value(); continue; }
      if (arg === '--out') { opts.out = value(); continue; }
      if (arg === '--root') { opts.root = value(); continue; }
    } catch (error) { process.stderr.write('check-sadd: ' + error.message + '\n'); return 2; }
    process.stderr.write('check-sadd: 未知参数 ' + arg + '\n');
    return 2;
  }
  try {
    const result = run(opts);
    process.stdout.write(render(result));
    return result.code;
  } catch (error) {
    process.stderr.write('check-sadd: ' + error.message + '\n');
    return 2;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))) {
  process.exitCode = main();
}
