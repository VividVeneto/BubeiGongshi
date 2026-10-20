import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const FILES = ['01-公共核心-v5.md', '02-Android端-v5.md', '03-Windows端-v5.md'];
export function load(sadd = path.join(ROOT, 'SADD')) {
  const cards = new Map();
  for (const file of FILES) {
    const text = fs.readFileSync(path.join(sadd, file), 'utf8');
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
      cards.set(m[1], {id: m[1], file, line: text.slice(0, m.index).split('\n').length,
        body, contract, deps: [...new Set(deps)]});
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
export function pack(id, {sadd = path.join(ROOT, 'SADD'), extra = []} = {}) {
  const cards = load(sadd); const target = cards.get(id);
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
      if (b.used || ![...tokens(b.text)].some(t => need.has(t))) continue;
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
    manifest.push({card: key, mode: key === id ? 'target' : full.has(key) ? 'full-contract' : !closure.has(key) ? 'outside-context' : 'symbols',
      before: c.contract.length, after: text.length, retained: [...tokens(text)].sort()});
  }
  const readme = fs.readFileSync(path.join(sadd, 'README.md'), 'utf8');
  const reqs = new Set(target.body.match(/R\d+(?:\.[a-j])?/g) ?? []);
  const qs = new Set(target.body.match(/\bQ\d+\b/g) ?? []);
  const rows = readme.split('\n').filter(line => {
    const r = line.match(/^\| (R\d+(?:\.[a-j])?) \|/);
    const q = line.match(/^\| (Q\d+) \|/);
    return r && reqs.has(r[1]) || q && (qs.has(q[1]) || refs(line.split('|').at(-2) ?? '').includes(id));
  });
  sections.push(`## 需求与产品约束\n\n${rows.join('\n')}`);
  const adr = fs.readFileSync(path.join(sadd, '附录A-架构决策与评审记录.md'), 'utf8');
  const adrIds = new Set(target.body.match(/ADR-(?:V5-)?\d+/g) ?? []);
  const adrRows = adr.split('\n').filter(line => /^\| ADR-/.test(line) &&
    (adrIds.has(line.split('|')[1].trim()) || refs(line.split('|').at(-2) ?? '').includes(id)));
  // Keep entire relevant supplements, including source evidence; report excluded titles.
  const relevantAdrs = new Set([...adrIds, ...adrRows.flatMap(row => row.match(/ADR-(?:V5-)?\d+/g) ?? [])]);
  const supplements = [...adr.matchAll(/^### A\.4\.\d+[^\n]*\n[\s\S]*?(?=^### |^## |$(?![\s\S]))/gm)].map(m=>m[0]);
  const applies = text => refs(text).includes(id) || [...relevantAdrs].some(a => new RegExp(`\\b${a}\\b`).test(text));
  const adrExtra = supplements.filter(applies);
  const excludedSupplements = supplements.filter(s => !applies(s)).map(s=>s.split('\n')[0]);
  sections.push(`## 架构决策（相关补充章节全文）\n\n${adrRows.join('\n')}\n\n${adrExtra.join('\n')}`);
  const missing = [];
  const defaults = ['rust-toolchain.toml', 'app/.flutter-version', 'tools/toolchain.versions',
    'tools/requirements.txt', 'Cargo.lock', 'app/pubspec.lock',
    'app/android/toolchain.versions', 'app/windows/toolchain.versions'];
  const paths = new Set([...defaults, ...extra]);
  const files = [];
  // Contracts can be introduced by a dependency, not just the target card.
  for (const key of selected.keys()) {
    const source = key === id ? target.body : cards.get(key).contract;
    for (const m of source.matchAll(/\b(contracts\/[A-Za-z0-9_.\/-]+\.(?:json|yaml|yml|h|toml|txt))/g)) {
      if (!/[<>*{}]/.test(m[1])) paths.add(m[1]);
    }
  }
  for (const file of paths) {
    const resolved = path.resolve(path.dirname(sadd), file);
    const relative = path.relative(path.dirname(sadd), resolved);
    if (relative.startsWith('..') || path.isAbsolute(relative)) throw new Error(`Path outside workspace: ${file}`);
    if (!fs.existsSync(resolved) || !fs.statSync(resolved).isFile()) { missing.push(file); continue; }
    const content=fs.readFileSync(resolved,'utf8');
    files.push(file);
    // A schema is unusable without its referenced definitions. Sets make cycles finite.
    if(file.startsWith('contracts/') && file.endsWith('.json')) {
      const document=JSON.parse(content);
      const visit=value=>{
        if(!value || typeof value!=='object')return;
        if(typeof value.$ref==='string' && !value.$ref.startsWith('#')) {
          const reference=value.$ref.split('#')[0];
          if(/^[a-z]+:/i.test(reference))throw new Error(`External contract reference: ${reference}`);
          const dependency=path.posix.normalize(path.posix.join(path.posix.dirname(file.replaceAll('\\','/')),reference));
          if(!dependency.startsWith('contracts/'))throw new Error(`Contract reference outside contracts: ${dependency}`);
          paths.add(dependency);
        }
        for(const child of Object.values(value))visit(child);
      };
      visit(document);
      // manifest.schema uses filenames relative to the manifest, unlike JSON $ref.
      if(file==='contracts/dto/manifest.json') for(const op of document.ops??[]) {
        if(op.status!=='ready')continue;
        if(typeof op.schema!=='string' || !/^[A-Za-z0-9_.-]+\.schema\.json$/.test(op.schema))throw new Error('Invalid ready schema path: '+op.op);
        paths.add('contracts/dto/'+op.schema);
      }
    }
    sections.push(`## 已有文件 ${file}\n\n\`\`\`text\n${content}\n\`\`\``);
  }
  const inventory = [...tokens(sections.join('\n'))].filter(t => /^[A-Z][a-z]+[A-Z]/.test(t));
  const definitionPattern = /(?:struct|class|enum|trait|typedef|type)\s+(\w+)/g;
  const known = new Set([...sections.join('\n').matchAll(definitionPattern)].map(m=>m[1]));
  const repositoryDefinitions = new Map();
  for (const c of cards.values()) for (const m of c.contract.matchAll(definitionPattern)) {
    const sources = repositoryDefinitions.get(m[1]) ?? [];
    sources.push({card:c.id,file:c.file,line:c.line}); repositoryDefinitions.set(m[1],sources);
  }
  const missingFromMaterials = [...new Set(inventory)].filter(t => !known.has(t) && repositoryDefinitions.has(t))
    .map(symbol => ({symbol,sources:repositoryDefinitions.get(symbol)}));
  if (missingFromMaterials.length) warnings.push('Local definitions absent from material; see missingFromMaterials; resolve dependency or selection before coding');
  const undefinedIdentifiers = inventory.filter(t => !known.has(t) && !repositoryDefinitions.has(t));
  if (undefinedIdentifiers.length) warnings.push('SDK/third-party or undefined identifiers require review; see undefinedIdentifiers');
  const header = `# ${id} 会话材料\n\n生成时间：${new Date().toISOString()}；字符按 Unicode code point 计数。\n`+
    `完整材料由下列分段共同组成，分段不是独立编码会话；全部读完后才能实现。\n\n未创建文件：${missing.join('、') || '无'}。\n`;
  const text = header + '\n' + sections.join('\n\n');
  const chars = [...text].length;
  const chunks = []; let chunk = '';
  for (const block of blocks(text)) {
    if ([...block].length > 80000) throw new Error('Single indivisible block exceeds 80000 characters; split its owning card');
    if ([...chunk].length + [...block].length + 2 > 80000) { chunks.push(chunk); chunk = ''; }
    chunk += block + '\n\n';
  }
  if (chunk) chunks.push(chunk);
  return {text, chunks, report: {id, chars, overLimit: chars > 80000, segments: chunks.length,
    closure: [...closure], manifest, files, missing, warnings, missingFromMaterials,
    undefinedIdentifiers: [...new Set(undefinedIdentifiers)].sort(), classifiedReferences, excludedSupplements}};
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const id = process.argv[2];
  if (!id) { console.error('Usage: node tools/sadd/pack.mjs CARD [--out DIR] [--sadd DIR] [--file PATH]'); process.exit(2); }
  const opt = name => { const i=process.argv.indexOf(name); return i<0?undefined:process.argv[i+1]; };
  const extra = process.argv.flatMap((x,i) => x === '--file' ? [process.argv[i+1]] : []);
  const result = pack(id, {sadd: opt('--sadd'), extra});
  const out = path.resolve(opt('--out') ?? `build/sadd/${id}`); fs.mkdirSync(out, {recursive:true});
  fs.writeFileSync(path.join(out, 'material.md'), result.text);
  fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify({...result.report, node: process.version}, null, 2));
  result.chunks.forEach((text,i) => fs.writeFileSync(path.join(out, `part-${i+1}.md`), text));
  console.log(JSON.stringify({id, chars: result.report.chars, segments: result.chunks.length, warnings:result.report.warnings}));
  if (process.argv.includes('--check-budget') && result.report.overLimit) process.exitCode = 1;
}
