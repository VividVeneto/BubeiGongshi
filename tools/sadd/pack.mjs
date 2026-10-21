import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {FILES, readDocs} from './layout.mjs';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export {FILES};
/** tests=false 时卡片正文不拼回 Test/ 测试方案，只保留引用行（testFile 仍记录路径）。 */
export function load(sadd = path.join(ROOT, 'SADD'), {tests = true} = {}) {
  const cards = new Map();
  const {texts, cardFiles} = readDocs(sadd, {tests});
  for (const doc of FILES) {
    const text = texts[doc];
    const matches = [...text.matchAll(/^### ((?:CORE|AND|WIN)-\d+) (.+)$/gm)];
    for (let i = 0; i < matches.length; i++) {
      const m = matches[i];
      const body = text.slice(m.index, matches[i + 1]?.index ?? text.length);
      const deps = []; let prefix;
      const line = body.match(/^\*\*依赖\*\*[^\n]*/m)?.[0] ?? '';
      for (const d of line.matchAll(/(CORE|AND|WIN)-(\d+)|(?<=[、，])(\d{2})/g)) {
        if (d[1]) { prefix = d[1]; deps.push(`${prefix}-${d[2]}`); }
        else if (prefix) deps.push(`${prefix}-${d[3]}`);
      }
      const contract = body.split('**接口契约**')[1]?.split('**实现约束**')[0] ?? '';
      // 拆分布局下 file/line 指向卡片文件本身；doc 始终是卡片所属的原文档。
      const own = cardFiles.get(m[1]);
      cards.set(m[1], {id: m[1], doc, file: own?.rel ?? doc, line: own ? 1 : text.slice(0, m.index).split('\n').length,
        body, contract, deps: [...new Set(deps)], ...(own?.test ? {testFile: own.test.rel} : {})});
    }
  }
  return cards;
}
// Keep fenced snippets, tables and paragraphs intact. No truncation inside a definition.
export function blocks(text) {
  const out = []; let current = []; let fence = false;
  for (const line of text.split('\n')) {
    if (line.startsWith('```')) fence = !fence;
    current.push(line);
    if (!fence && !line.trim()) { out.push(current.join('\n')); current = []; }
  }
  if (current.length) out.push(current.join('\n'));
  return out.filter(x => x.trim());
}
// Lower-case field names (id, profile_id, etc.) are not definition identities.
const tokens = text => new Set(text.match(/\b(?:[A-Z][a-z]+(?:[A-Z][A-Za-z0-9]*)+|[A-Z]+(?:_[A-Z0-9]+)+|[a-z_]+\.[a-z_]+(?:\.[a-z_]+)*)\b/g) ?? []);
const refs = text => [...new Set(text.match(/\b(?:CORE|AND|WIN)-\d+\b/g) ?? [])];
// 间接依赖只收录“定义”了所需符号的块：类型/trait/接口声明、impl/extension、常量、错误码等表格首列、行首 op 名。
// 只提到符号而未定义它的块（说明、示例、调用方叙述）不收录，在 report.manifest[].mentionOnly 中计数。
const DEFINITION_PATTERNS = [
  /\b(?:struct|enum|class|trait|type|typedef|interface|mixin|union|mod)\s+([A-Za-z_]\w*)/g,
  /\bconst\s+([A-Za-z_]\w*)/g,
  /\bimpl(?:<[^>\n]*>)?\s+(?:[\w:]+(?:<[^>\n]*>)?\s+for\s+)?([A-Za-z_]\w*)/g,
  /\bextension\s+(?:type\s+)?([A-Za-z_]\w*)(?:\s+on\s+([A-Za-z_]\w*))?/g,
  /^\|\s*`?([A-Za-z_][\w.]*)`?\s*\|/gm,
  /^(?:[-*]\s+)?`?([a-z_]+(?:\.[a-z_]+)+)`?(?=[\s:：(（=]|body|例)/gm,
];
const definitionCache = new Map();
export function definedSymbols(text) {
  let out = definitionCache.get(text);
  if (out) return out;
  out = new Set();
  for (const pattern of DEFINITION_PATTERNS) for (const m of text.matchAll(pattern)) for (const name of m.slice(1)) if (name) out.add(name);
  definitionCache.set(text, out);
  return out;
}
export function pack(id, {sadd = path.join(ROOT, 'SADD'), extra = [], withTests = false} = {}) {
  // 默认不收录 Test/ 测试方案（README §8.1）；本卡功能变更须同步修改测试方案时用 withTests 收录。
  const cards = load(sadd, {tests: withTests}); const target = cards.get(id);
  if (!target) throw new Error(`Unknown card: ${id}`);
  const closure = new Set();
  function visit(key, stack = []) {
    if (stack.includes(key)) throw new Error(`Cycle: ${[...stack, key].join(' -> ')}`);
    if (!cards.has(key)) throw new Error(`Missing card: ${key}`);
    if (closure.has(key)) return;
    closure.add(key);
    for (const d of cards.get(key).deps) visit(d, [...stack, key]);
  }
  visit(id); visit('CORE-01'); visit('CORE-02');
  const full = new Set([id, ...target.deps, 'CORE-01', 'CORE-02']);
  const selected = new Map(); const pending = [];
  for (const key of full) {
    const c = cards.get(key); const text = key === id ? c.body : c.contract;
    selected.set(key, [text]);
  }
  const need = tokens([...selected.values()].flat().join('\n'));
  for (const key of closure) if (!full.has(key)) {
    blocks(cards.get(key).contract).forEach((text, index) => pending.push({key, text, index}));
  }
  let change = true;
  while (change) {
    change = false;
    for (const b of pending) {
      if (b.used || ![...definedSymbols(b.text)].some(t => need.has(t))) continue;
      b.used = true; change = true;
      const list = selected.get(b.key) ?? []; list.push(b); selected.set(b.key, list);
      for (const t of tokens(b.text)) need.add(t);
    }
  }
  const warnings = []; const classifiedReferences = [];
  // Explicit references outside the closure are read-only context, never compilation permission.
  for (const key of refs(target.body)) if (key !== id && !closure.has(key)) {
    const c = cards.get(key);
    if (!c) { warnings.push(`Missing referenced card ${key}`); continue; }
    const occurrences = target.body.split('\n').filter(line => refs(line).includes(key));
    if (occurrences.every(line => /下游说明，非契约|只读样本/.test(line))) {
      classifiedReferences.push({card:key, kind:'downstream-explanation', evidence:occurrences});
      continue;
    }
    selected.set(key, blocks(c.contract));
    warnings.push(`Outside dependency closure: ${key}; classify as downstream explanation or add dependency`);
  }
  const sections = [];
  const manifest = [];
  for (const [key, list] of selected) {
    const c = cards.get(key);
    const kept = full.has(key) || !closure.has(key) ? list : list.sort((a,b) => a.index-b.index).map(b=>b.text);
    const text = kept.join('\n');
    sections.push(`## ${key} (${c.file}:${c.line})\n\n${text}`);
    const mode = key === id ? 'target' : full.has(key) ? 'full-contract' : !closure.has(key) ? 'outside-context' : 'symbols';
    // 提到了所需符号、但不定义任何所需符号而未收录的块数（只对间接依赖统计）。
    const mentionOnly = mode !== 'symbols' ? undefined : pending.filter(b => b.key === key && !b.used && [...tokens(b.text)].some(t => need.has(t))).length;
    manifest.push({card: key, mode, before: c.contract.length, after: text.length, retained: [...tokens(text)].sort(), ...(mentionOnly === undefined ? {} : {mentionOnly})});
  }
  // 与本卡相关的卡：目标卡、直接依赖，以及 AGENTS 规定始终整份收录的 CORE-01/02（即 full）。
  const related = full;
  const relatedText = [target.body, ...[...related].filter(k => k !== id).map(k => cards.get(k).contract)].join('\n');
  const relatedBodies = [...related].map(k => cards.get(k).body).join('\n');
  const filteredFiles = [];
  const readme = fs.readFileSync(path.join(sadd, 'README.md'), 'utf8');
  const reqs = new Set(target.body.match(/R\d+(?:\.[a-j])?/g) ?? []);
  const qs = new Set(target.body.match(/\bQ\d+\b/g) ?? []);
  const rows = readme.split('\n').filter(line => {
    const r = line.match(/^\| (R\d+(?:\.[a-j])?) \|/);
    const q = line.match(/^\| (Q\d+) \|/);
    return r && reqs.has(r[1]) || q && (qs.has(q[1]) || refs(line.split('|').at(-2) ?? '').includes(id));
  });
  sections.push(`## 需求与产品约束\n\n${rows.join('\n')}`);
  const adrSelection = selectAdr(sadd, id, relatedText, filteredFiles);
  sections.push(adrSelection.text);
  const missing = [];
  const defaults = ['rust-toolchain.toml', 'app/.flutter-version', 'tools/toolchain.versions',
    'tools/requirements.txt', 'Cargo.lock', 'app/pubspec.lock',
    'app/android/toolchain.versions', 'app/windows/toolchain.versions'];
  const root = path.dirname(sadd);
  const norm = file => {
    const resolved = path.resolve(root, file);
    const relative = path.relative(root, resolved);
    if (relative.startsWith('..') || path.isAbsolute(relative)) throw new Error(`Path outside workspace: ${file}`);
    return relative.split(path.sep).join('/');
  };
  const extraSet = new Set(extra.map(norm));
  // 正文提到的 contracts 路径：目标卡取全文，其余入选卡取其接口契约全文（与去噪前相同，用于“未创建文件”与非 DTO 契约文件）；
  // DTO schema 只认目标卡与直接依赖的收录文本（mentionedRelated）。
  const mentionPattern = /\b(contracts\/[A-Za-z0-9_.\/-]+\.(?:json|yaml|yml|h|toml|txt))/g;
  const mentionsOf = text => [...text.matchAll(mentionPattern)].map(m => m[1]).filter(p => !/[<>*{}]/.test(p));
  const mentionedRelated = new Set(mentionsOf(relatedText));
  const mentionedAll = new Set(mentionedRelated);
  for (const key of selected.keys()) if (!related.has(key)) mentionsOf(cards.get(key).contract).forEach(p => mentionedAll.add(p));
  const exists = file => fs.existsSync(path.join(root, file)) && fs.statSync(path.join(root, file)).isFile();
  const readText = file => fs.readFileSync(path.join(root, file), 'utf8');
  const MANIFEST = 'contracts/dto/manifest.json', SHARED = 'contracts/policies/shared-writes.json', TYPES = 'contracts/dto/types.schema.json';
  const manifestDoc = exists(MANIFEST) ? JSON.parse(readText(MANIFEST)) : {ops: []};
  const ownedSchemas = new Set((manifestDoc.ops ?? []).filter(o => related.has(o.owner) && typeof o.schema === 'string').map(o => 'contracts/dto/' + o.schema));
  const isSchema = f => /^contracts\/dto\/[^/]+\.schema\.json$/.test(f) && f !== TYPES;
  const isVector = f => f.startsWith('contracts/vectors/');
  const vectorReferenced = f => { const stem = path.posix.basename(f).replace(/\.[^.]+$/, ''); return new RegExp(`(?<![A-Za-z0-9_-])${stem.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![A-Za-z0-9_-])`).test(relatedBodies); };
  const inventory = listContracts(root);
  const fullReason = new Map();
  const wantFull = (f, reason) => { if (!fullReason.has(f)) { fullReason.set(f, reason); queue.push(f); } };
  const queue = [];
  for (const f of extraSet) if (f.startsWith('contracts/')) wantFull(f, '--file 指定');
  for (const f of ownedSchemas) wantFull(f, '目标卡/直接依赖拥有的 op');
  for (const f of mentionedRelated) if (isSchema(f)) wantFull(f, '目标卡/直接依赖正文引用');
  for (const f of mentionedAll) if (!isSchema(f) && !isVector(f) && ![MANIFEST, SHARED, TYPES].includes(f)) wantFull(f, '正文引用');
  for (const f of inventory) if (isVector(f) && vectorReferenced(f)) wantFull(f, '目标卡/直接依赖验收引用');
  const typesNeeded = new Set(); let typesFull = extraSet.has(TYPES);
  for (let i = 0; i < queue.length; i++) {
    const f = queue[i];
    if (!exists(f) || !f.endsWith('.json')) continue;
    for (const ref of schemaRefs(JSON.parse(readText(f)))) {
      const [file, fragment] = ref.split('#');
      if (!file) continue;
      if (/^[a-z]+:/i.test(file)) throw new Error(`External contract reference: ${file}`);
      const dependency = path.posix.normalize(path.posix.join(path.posix.dirname(f), file));
      if (!dependency.startsWith('contracts/')) throw new Error(`Contract reference outside contracts: ${dependency}`);
      if (dependency === TYPES && !typesFull) {
        const name = fragment?.match(/^\/\$defs\/([^/]+)$/)?.[1];
        if (name) typesNeeded.add(name); else typesFull = true;
      } else wantFull(dependency, `被 ${f} 通过 $ref 引用`);
    }
  }
  if (typesFull && !fullReason.has(TYPES)) fullReason.set(TYPES, extraSet.has(TYPES) ? '--file 指定' : '被整文件 $ref 引用');
  const files = [];
  const pushFile = (file, content, title = file) => sections.push(`## 已有文件 ${title}\n\n${content}`);
  const fence = text => '```text\n' + text + '\n```';
  for (const file of new Set([...defaults, ...[...extraSet].filter(f => !f.startsWith('contracts/'))])) {
    if (!exists(file)) { missing.push(file); continue; }
    files.push(file); pushFile(file, fence(readText(file)));
  }
  for (const file of [...new Set([...fullReason.keys(), ...mentionedAll])].sort()) {
    if (!exists(file)) { if (!missing.includes(file)) missing.push(file); continue; }
    if (!fullReason.has(file)) continue;
    files.push(file); pushFile(file, fence(readText(file)));
  }
  const ownerList = [...related].join('、');
  for (const file of inventory) {
    if (fullReason.has(file)) continue;
    const content = readText(file); const entry = {path: file, originalBytes: bytes(content), sha256: sha256(content)};
    if (file === MANIFEST || file === SHARED) {
      const key = file === MANIFEST ? 'ops' : 'entries';
      const f = filterJsonArray(content, key, item => related.has(item.owner));
      const note = `已按 owner 过滤：owner ∈ {${ownerList}}，原文件 SHA-256=${entry.sha256}，条目数 ${f.kept}/${f.total}（原 ${entry.originalBytes} 字节，收录 ${bytes(f.text)} 字节）；保留原 JSON 结构，各条目与原文件逐字节一致；全文用 --file ${file}。`;
      pushFile(file, note + '\n\n' + fence(f.text), `${file}（已按 owner 过滤）`);
      filteredFiles.push({...entry, mode: 'filtered', includedBytes: bytes(f.text), reason: `只收录 owner ∈ 目标卡/直接依赖的条目（${f.kept}/${f.total}）`, kept: f.kept, total: f.total});
      continue;
    }
    if (file === TYPES) {
      const names = new Set(typesNeeded);
      const doc = JSON.parse(content); const defs = doc.$defs ?? {};
      for (const name of Object.keys(defs)) if (new RegExp(`\\b${name}\\b`).test(relatedText)) names.add(name);
      for (const name of [...names]) if (!defs[name]) names.delete(name);
      // 闭包：被选条目内部引用的条目一并收录。
      const stack = [...names];
      while (stack.length) for (const ref of schemaRefs(defs[stack.pop()])) {
        const name = ref.match(/^(?:types\.schema\.json)?#\/\$defs\/([^/]+)$/)?.[1];
        if (name && defs[name] && !names.has(name)) { names.add(name); stack.push(name); }
      }
      if (names.size) {
        const f = filterJsonObject(content, '$defs', name => names.has(name));
        const excluded = Object.keys(defs).filter(n => !names.has(n));
        const note = `切片：按 $defs 条目收录 ${f.kept}/${f.total} 条，原文件 SHA-256=${entry.sha256}（原 ${entry.originalBytes} 字节，收录 ${bytes(f.text)} 字节）。收录条目：${[...names].sort().join('、')}（被收录 schema 的 $ref、目标卡/直接依赖正文出现的类型名及其内部引用闭包）。未收录条目只列名：${excluded.join('、') || '无'}。保留完整 JSON 结构与条目原文；全文用 --file ${TYPES}。`;
        pushFile(file, note + '\n\n' + fence(f.text), `${file}（切片）`);
        filteredFiles.push({...entry, mode: 'sliced', includedBytes: bytes(f.text), reason: '按 $defs 条目切片：$ref 引用、正文类型名及闭包', kept: f.kept, total: f.total, entries: [...names].sort()});
        continue;
      }
    }
    const reason = isSchema(file) ? '非目标卡/直接依赖拥有的 op，且未被收录的 schema 引用或正文引用'
      : file === TYPES ? '没有被引用或在正文出现的 $defs 条目'
      : isVector(file) ? '目标卡与直接依赖的正文和验收未引用' : '目标卡与已收录材料未引用';
    filteredFiles.push({...entry, mode: 'listed', includedBytes: 0, reason});
  }
  const listed = filteredFiles.filter(f => f.mode === 'listed' && f.path.startsWith('contracts/'));
  sections.push(`## contracts 清单（未收录正文的文件）\n\n共 ${inventory.length} 个文件：正文收录 ${inventory.filter(f => fullReason.has(f)).length}，切片/过滤 ${filteredFiles.filter(f => f.path.startsWith('contracts/') && f.mode !== 'listed').length}，只列名 ${listed.length}。需要时用 --file 取全文。\n\n| 文件 | 字节 | SHA-256 | 原因 |\n| --- | --- | --- | --- |\n${listed.map(f => `| ${f.path} | ${f.originalBytes} | ${f.sha256} | ${f.reason} |`).join('\n') || '| （无） | — | — | — |'}`);
  const inventoryTokens = [...tokens(sections.join('\n'))].filter(t => /^[A-Z][a-z]+[A-Z]/.test(t));
  const definitionPattern = /(?:struct|class|enum|trait|typedef|type)\s+(\w+)/g;
  const known = new Set([...sections.join('\n').matchAll(definitionPattern)].map(m=>m[1]));
  const repositoryDefinitions = new Map();
  for (const c of cards.values()) for (const m of c.contract.matchAll(definitionPattern)) {
    const sources = repositoryDefinitions.get(m[1]) ?? [];
    sources.push({card:c.id,file:c.file,line:c.line}); repositoryDefinitions.set(m[1],sources);
  }
  const missingFromMaterials = [...new Set(inventoryTokens)].filter(t => !known.has(t) && repositoryDefinitions.has(t))
    .map(symbol => ({symbol,sources:repositoryDefinitions.get(symbol)}));
  if (missingFromMaterials.length) warnings.push('Local definitions absent from material; see missingFromMaterials; resolve dependency or selection before coding');
  const undefinedIdentifiers = inventoryTokens.filter(t => !known.has(t) && !repositoryDefinitions.has(t));
  if (undefinedIdentifiers.length) warnings.push('SDK/third-party or undefined identifiers require review; see undefinedIdentifiers');
  const header = `# ${id} 会话材料\n\n生成时间：${new Date().toISOString()}；字符按 Unicode code point 计数。\n`+
    `完整材料由下列分段共同组成，分段不是独立编码会话；全部读完后才能实现。\n\n未创建文件：${missing.join('、') || '无'}。\n\n`+
    (target.testFile ? (withTests
      ? `目标卡“验收标准”取自测试方案 ${target.testFile}（已按卡片中的引用拼回下方目标卡正文）；实现与测试改动须同步修改该文件。\n\n`
      : `测试方案默认不收录：各卡“验收标准”只保留引用行（目标卡为 ${target.testFile}）。本卡功能变更须同步修改测试方案时，用 --with-tests 重新生成并运行 cardiff 对比变更（README §8.1）。\n\n`) : '')+
    `去噪：contracts 只收录与目标卡及直接依赖（${ownerList}）相关的内容，其余列名并给出 SHA-256，见文末“contracts 清单”与 report.json 的 filteredFiles；附录 A 只收录相关 ADR 行与补充章节。\n`;
  const text = header + '\n' + sections.join('\n\n');
  const chars = [...text].length;
  const chunks = segment(text);
  return {text, chunks, report: {id, chars, overLimit: chars > 80000, segments: chunks.length, tests: withTests ? 'included' : 'excluded',
    closure: [...closure], related: [...related], manifest, files, filteredFiles, adr: adrSelection.report, missing, warnings, missingFromMaterials,
    undefinedIdentifiers: [...new Set(undefinedIdentifiers)].sort(), classifiedReferences, excludedSupplements: adrSelection.report.excludedSupplements}};
}

/** 无损分段：只在围栏外的空行之后切分，各段拼接逐字节等于原文；单段不超过 80000 字符。 */
export function segment(text, limit = 80000) {
  const units = []; let current = ''; let inFence = false;
  for (const line of text.split(/(?<=\n)/)) {
    if (line.startsWith('```')) inFence = !inFence;
    current += line;
    if (!inFence && !line.trim()) { units.push(current); current = ''; }
  }
  if (current) units.push(current);
  const chunks = []; let chunk = ''; let size = 0;
  for (const unit of units) {
    const n = [...unit].length;
    if (n > limit) throw new Error('Single indivisible block exceeds 80000 characters; split its owning card');
    if (size + n > limit && chunk) { chunks.push(chunk); chunk = ''; size = 0; }
    chunk += unit; size += n;
  }
  if (chunk) chunks.push(chunk);
  return chunks;
}

const sha256 = text => crypto.createHash('sha256').update(text).digest('hex');
const bytes = text => Buffer.byteLength(text, 'utf8');

function listContracts(root) {
  const base = path.join(root, 'contracts'); const out = [];
  const walk = dir => { for (const name of fs.readdirSync(dir).sort()) {
    const full = path.join(dir, name);
    if (fs.statSync(full).isDirectory()) walk(full); else out.push(path.relative(root, full).split(path.sep).join('/'));
  } };
  if (fs.existsSync(base)) walk(base);
  return out;
}

/** 收集 JSON 值中全部 $ref 字符串。 */
export function schemaRefs(value, out = []) {
  if (!value || typeof value !== 'object') return out;
  if (typeof value.$ref === 'string') out.push(value.$ref);
  for (const child of Object.values(value)) schemaRefs(child, out);
  return out;
}

// 最小 JSON 扫描器：定位容器内各元素的原文区间，使过滤结果保留条目原字节。
const skipWs = (t, i) => { while (i < t.length && /\s/.test(t[i])) i++; return i; };
function skipString(t, i) {
  for (i++; i < t.length; i++) { if (t[i] === '\\') { i++; continue; } if (t[i] === '"') return i + 1; }
  throw new Error('Unterminated JSON string');
}
function skipValue(t, i) {
  i = skipWs(t, i);
  if (t[i] === '"') return skipString(t, i);
  if (t[i] === '{' || t[i] === '[') return members(t, i).close + 1;
  let j = i; while (j < t.length && !/[\s,\]}]/.test(t[j])) j++;
  if (j === i) throw new Error('Invalid JSON value at ' + i);
  return j;
}
function members(t, open) {
  const object = t[open] === '{'; const close = object ? '}' : ']'; const items = [];
  let i = skipWs(t, open + 1);
  if (t[i] === close) return {items, close: i};
  for (;;) {
    const start = i; let key, valueStart = i;
    if (object) {
      const end = skipString(t, i); key = JSON.parse(t.slice(i, end)); i = skipWs(t, end);
      if (t[i] !== ':') throw new Error('Expected colon at ' + i);
      valueStart = skipWs(t, i + 1);
    }
    i = skipValue(t, valueStart);
    items.push({start, end: i, key, valueStart});
    i = skipWs(t, i);
    if (t[i] === ',') { i = skipWs(t, i + 1); continue; }
    if (t[i] === close) return {items, close: i};
    throw new Error('Invalid JSON container at ' + i);
  }
}
function rebuild(text, container, keep) {
  const {items, close} = members(text, container);
  const chosen = items.filter(keep);
  if (!chosen.length) return {text: text.slice(0, container + 1) + text.slice(close), kept: 0, total: items.length};
  const sep = items.length > 1 ? text.slice(items[0].end, items[1].start) : ',\n';
  return {text: text.slice(0, items[0].start) + chosen.map(x => text.slice(x.start, x.end)).join(sep) + text.slice(items.at(-1).end),
    kept: chosen.length, total: items.length};
}
const memberValue = (text, key) => {
  const top = members(text, skipWs(text, 0)).items.find(x => x.key === key);
  if (!top) throw new Error('Missing JSON member ' + key);
  return top.valueStart;
};
/** 顶层对象中 key 容器（数组或对象）的各元素原文（对象成员含键名）。 */
export function jsonItems(text, key) {
  const {items} = members(text, memberValue(text, key));
  return items.map(x => ({key: x.key, text: text.slice(x.start, x.end)}));
}
/** 过滤顶层对象中 key 数组的元素；保留其余结构与各元素原文。 */
export function filterJsonArray(text, key, predicate) {
  return rebuild(text, memberValue(text, key), x => predicate(JSON.parse(text.slice(x.start, x.end))));
}
/** 过滤顶层对象中 key 对象的成员（按成员名）；保留其余结构与各成员原文。 */
export function filterJsonObject(text, key, predicate) {
  return rebuild(text, memberValue(text, key), x => predicate(x.key));
}

/** 附录 A：只收录相关 ADR 行（目标卡与直接依赖文本引用的 ADR，或“模块卡”列含目标卡）与相关补充章节。 */
function selectAdr(sadd, id, relatedText, filteredFiles) {
  const file = path.join(sadd, '附录A-架构决策与评审记录.md');
  const adr = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
  const lines = adr.split('\n');
  const tableRows = lines.filter(line => /^\| ADR-/.test(line));
  const adrIds = new Set(relatedText.match(/ADR-(?:V5-)?\d+/g) ?? []);
  const adrRows = tableRows.filter(line => adrIds.has(line.split('|')[1].trim()) || refs(line.split('|').at(-2) ?? '').includes(id));
  const relevantAdrs = new Set([...adrIds, ...adrRows.flatMap(row => row.match(/ADR-(?:V5-)?\d+/g) ?? [])]);
  const sectionsA4 = [...adr.matchAll(/^### A\.4\.\d+[^\n]*\n[\s\S]*?(?=^### |^## |$(?![\s\S]))/gm)].map(m => m[0]);
  const isTable = s => /^\| ADR-/m.test(s);
  const applies = s => refs(s).includes(id) || [...relevantAdrs].some(a => new RegExp(`\\b${a}\\b`).test(s));
  const supplements = sectionsA4.filter(s => !isTable(s));
  const included = supplements.filter(applies);
  const excludedSupplements = supplements.filter(s => !applies(s)).map(s => s.split('\n')[0]);
  const headerAt = lines.findIndex(line => /^\| 编号 \| 决策 \|/.test(line));
  const tableHead = headerAt >= 0 ? lines.slice(headerAt, headerAt + 2).join('\n') + '\n' : '';
  const body = adrRows.length ? tableHead + adrRows.join('\n') : '（无相关 ADR 行）';
  const text = `## 架构决策（相关 ADR 行与补充章节）\n\n收录规则：目标卡与直接依赖收录文本引用的 ADR 行、“模块卡”列含目标卡的 ADR 行（${adrRows.length}/${tableRows.length}），以及引用目标卡或上述 ADR 的补充章节全文（${included.length}/${supplements.length}）；ADR 表章节（${sectionsA4.filter(isTable).map(s => s.split('\n')[0].replace(/^### /, '')).join('、') || '无'}）只收录相关行。\n\n${body}\n\n${included.join('\n')}`;
  if (adr) {
    const includedText = body + '\n' + included.join('\n');
    filteredFiles.push({path: path.relative(path.dirname(sadd), file).split(path.sep).join('/'), originalBytes: bytes(adr), includedBytes: bytes(includedText), sha256: sha256(adr),
      mode: 'filtered', reason: '只收录相关 ADR 行与补充章节', kept: adrRows.length, total: tableRows.length});
  }
  return {text, report: {rows: adrRows.map(r => r.split('|')[1].trim()), totalRows: tableRows.length,
    supplements: included.map(s => s.split('\n')[0]), excludedSupplements}};
}

/** 写出材料：先清理目录里全部旧 part-*.md，再写 material.md、part-N.md 与 report.json。 */
export function writeOutput(out, result, extra = {}) {
  fs.mkdirSync(out, {recursive: true});
  const removedParts = fs.readdirSync(out).filter(name => /^part-\d+\.md$/.test(name));
  for (const name of removedParts) fs.rmSync(path.join(out, name));
  const parts = result.chunks.map((_, i) => `part-${i + 1}.md`);
  fs.writeFileSync(path.join(out, 'material.md'), result.text);
  result.chunks.forEach((text, i) => fs.writeFileSync(path.join(out, parts[i]), text));
  const reading = {material: 'material.md', parts,
    relation: `material.md 是完整材料；${parts.join('、')} 是同一内容按 ≤80000 字符在围栏外空行处的无损切分，按序拼接逐字节等于 material.md。二者择一阅读，不要重复阅读或重复计数。`};
  const stale = removedParts.filter(name => !parts.includes(name));
  fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify({...result.report, reading, removedStaleParts: stale, ...extra}, null, 2));
  return {parts, removedStaleParts: stale};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const id = process.argv[2];
  if (!id) { console.error('Usage: node tools/sadd/pack.mjs CARD [--out DIR] [--sadd DIR] [--file PATH] [--with-tests] [--check-budget]'); process.exit(2); }
  const opt = name => { const i=process.argv.indexOf(name); return i<0?undefined:process.argv[i+1]; };
  const extra = process.argv.flatMap((x,i) => x === '--file' ? [process.argv[i+1]] : []);
  const result = pack(id, {sadd: opt('--sadd'), extra, withTests: process.argv.includes('--with-tests')});
  const out = path.resolve(opt('--out') ?? `build/sadd/${id}`);
  writeOutput(out, result, {node: process.version});
  console.log(JSON.stringify({id, chars: result.report.chars, segments: result.chunks.length, warnings:result.report.warnings}));
  if (process.argv.includes('--check-budget') && result.report.overLimit) process.exitCode = 1;
}
