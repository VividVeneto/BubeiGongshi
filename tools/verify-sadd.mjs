// Documentation consistency checks only. This does not test the future app.
// Run from any directory with Node.js 20+: node tools/verify-sadd.mjs
// Checks: one H1 and closed fences per file; local links resolve; no line-number anchors;
// accessible Mermaid; requirement/test/decision IDs resolve against 00 and 13; source
// sample provenance; YOLO plan stays off the mainline (fail-closed).
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sadd = path.join(root, 'SADD');
const DOC = {
  baseline: '00-需求基线与文档效力-v4.md',
  architecture: '10-软件架构设计-v4.md',
  lifecycle: '11-数据安全同步与识别生命周期-v4.md',
  matrix: '13-需求追踪与验收-v4.md',
};
// Read-only history: exempt from ID and line-reference rules, still checked for structure and links.
const ARCHIVE = new Set(['历史归档.md']);
// Generated file: its references are checked like other docs.
const errors = [];
const check = (ok, message) => { if (!ok) errors.push(message); };
const read = p => fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, '');
const files = fs.readdirSync(sadd).filter(p => p.endsWith('.md')).sort();
const texts = new Map(files.map(name => [name, read(path.join(sadd, name))]));
let diagrams = 0;

// Strip fenced code so prose checks do not trip on examples.
const prose = text => {
  const out = [];
  let fence = null;
  for (const line of text.split(/\r?\n/)) {
    const m = line.match(/^(\`{3,}|~{3,})/);
    if (!fence && m) { fence = m[1]; continue; }
    if (fence && line.startsWith(fence)) { fence = null; continue; }
    if (!fence) out.push(line);
  }
  return out.join('\n');
};

for (const name of files) {
  const text = texts.get(name);
  check(!text.includes('\r'), `${name}: CRLF line endings (expected LF)`);
  const lines = text.split(/\r?\n/);
  let fence = null;
  let body = [];
  let headings = 0;
  for (const line of lines) {
    const opening = line.match(/^(\`{3,}|~{3,})(.*)$/);
    if (!fence && opening) { fence = opening[1]; body = [opening[2].trim()]; continue; }
    if (fence && new RegExp(`^${fence[0]}{${fence.length},}\\s*$`).test(line)) {
      if (body[0] === 'mermaid') {
        diagrams++;
        check(body.some(l => /accTitle:/.test(l)), `${name}: Mermaid missing accTitle`);
        check(body.some(l => /accDescr:/.test(l)), `${name}: Mermaid missing accDescr`);
      }
      fence = null;
      continue;
    }
    if (fence) { body.push(line); continue; }
    if (/^# /.test(line)) headings++;
  }
  check(!fence, `${name}: unclosed code fence`);
  check(headings === 1, `${name}: expected one H1, found ${headings}`);
  for (const match of text.matchAll(/!?\[[^\]\n]*\]\(([^)\n]+)\)/g)) {
    let target = match[1].split(/\s+"/)[0].replace(/^<|>$/g, '');
    if (/^(?:https?:|mailto:|app:|codex:|#)/.test(target)) continue;
    const anchor = target.includes('#') ? target.slice(target.indexOf('#')) : '';
    check(!/^#L\d/.test(anchor), `${name}: line-number anchor ${target}`);
    target = decodeURIComponent(target.split('#')[0]);
    if (target) check(fs.existsSync(path.resolve(sadd, target)), `${name}: missing ${target}`);
    check(!/-v3\.md$|^0[1-8]-|历史-v2\.2/.test(target), `${name}: link to retired document ${target}`);
  }
  if (!ARCHIVE.has(name)) {
    // "10:193" or "10-软件架构设计-v4.md:193" style line references are fragile; cite "10 §章节名".
    for (const m of prose(text).matchAll(/(?<![\d.:])((?:0[09]|1[0-4])(?:-[^\s:：|)]*\.md)?):(\d{1,4})(?![\d:])/g)) {
      check(false, `${name}: line-number reference "${m[0]}" (cite "文档号 §章节名" instead)`);
    }
  }
}

// Requirement and acceptance IDs.
const matrix = texts.get(DOC.matrix) ?? '';
check(matrix, `Missing ${DOC.matrix}`);
const requirements = [...matrix.matchAll(/^\| ((?:R|H|A|C)\d{2}) \|(.+)$/gm)];
const ids = requirements.map(x => x[1]);
check(new Set(ids).size === ids.length, 'Duplicate requirement IDs in 13');
for (let i = 1; i <= 31; i++) check(ids.includes(`R${String(i).padStart(2, '0')}`), `Missing requirement R${String(i).padStart(2, '0')}`);
for (const h of ['H01', 'H02']) check(ids.includes(h), `Missing historical requirement ${h}`);
const TEST = /\bT-[A-Z]+(?:-\d{2})?\b/g;
const definedTests = new Set([...matrix.matchAll(/^\| (T-[A-Z]+(?:-\d{2})?) \|/gm)].map(x => x[1]));
const testDefined = id => definedTests.has(id) || definedTests.has(id.replace(/-\d{2}$/, ''));
for (const row of requirements) {
  const refs = row[2].match(TEST) ?? [];
  check(refs.length > 0, `${row[1]}: no acceptance test`);
}
for (const [name, text] of texts) {
  if (ARCHIVE.has(name)) continue;
  for (const id of new Set(prose(text).match(TEST) ?? [])) check(testDefined(id), `${name}: undefined acceptance ID ${id}`);
}

// R04 functional-similarity clauses: defined in 00, traced in 13.
const baseline = texts.get(DOC.baseline) ?? '';
for (const s of 'abcdefghij') {
  check(baseline.includes(`R04.${s}`), `00: missing clause R04.${s}`);
  check(matrix.includes(`R04.${s}`), `13: clause R04.${s} not traced`);
}
// Pending decisions: every D-NN cited anywhere must exist in 00.
const decisions = new Set([...baseline.matchAll(/^\| (D-\d{2}) \|/gm)].map(x => x[1]));
check(decisions.size >= 17, `00: expected at least 17 pending decisions, found ${decisions.size}`);
for (const [name, text] of texts) {
  if (ARCHIVE.has(name)) continue;
  for (const id of new Set(prose(text).match(/\bD-\d{2}\b/g) ?? [])) check(decisions.has(id), `${name}: undefined decision ${id}`);
}
// ADR IDs cited anywhere must be defined in 09.
const adrDoc = files.find(f => f.startsWith('09-'));
const adrs = new Set([...(texts.get(adrDoc) ?? '').matchAll(/^\| (ADR-\d{3}) \|/gm)].map(x => x[1]));
for (const [name, text] of texts) {
  if (ARCHIVE.has(name)) continue;
  for (const id of new Set(prose(text).match(/\bADR-\d{3}\b/g) ?? [])) check(adrs.has(id), `${name}: undefined ${id}`);
}

// Source sample provenance.
const capture = JSON.parse(read(path.join(sadd, 'resources/source-capture.json')));
const sample = JSON.parse(read(path.join(sadd, 'resources/open-physics-samples.json')));
check(sample.samples.length === 3, 'Expected three research samples');
check(sample.upstream_revision === capture.revision, 'Source revision mismatch');
check(sample.upstream_file_sha256 === capture.source_sha256, 'Source hash mismatch');
check(/^[a-f0-9]{64}$/.test(capture.source_sha256), 'Invalid source SHA-256');
const licensePath = path.resolve(sadd, 'resources', sample.license_file);
check(fs.existsSync(licensePath), 'Missing source license');
if (fs.existsSync(licensePath)) {
  const hash = crypto.createHash('sha256').update(fs.readFileSync(licensePath)).digest('hex');
  check(hash === capture.license_sha256, 'License hash mismatch');
}
for (const entry of sample.samples) {
  check(capture.expressions.some(x => x.expression === entry.source_latex && x.line === entry.source_line), `${entry.id}: source expression/line mismatch`);
  check(entry.assumptions.length > 0 && entry.changes.length > 0, `${entry.id}: missing provenance or assumptions`);
  for (const [name, symbol] of Object.entries(entry.symbols)) {
    check(symbol.dimension.length === 7 && symbol.dimension.every(Number.isInteger), `${entry.id}/${name}: invalid dimension annotation`);
  }
}

// History-count contract must stay explicit.
check([DOC.architecture, DOC.lifecycle].some(n => (texts.get(n) ?? '').includes('keep_last')), 'Missing explicit history count contract (keep_last)');

// YOLO plan stays on its experiment branch. Fail closed: only an explicit experiment branch may carry it.
let branch = process.env.SADD_BRANCH || '';
if (!branch) {
  try { branch = execFileSync('git', ['branch', '--show-current'], { cwd: root, encoding: 'utf8' }).trim(); } catch { branch = ''; }
}
const onExperiment = /^codex\/exp-yolo/.test(branch);
if (!onExperiment) {
  check(!fs.existsSync(path.join(sadd, 'experimental')), `YOLO experimental plan must stay on codex/exp-yolo-recognizer (branch "${branch || 'unknown'}")`);
  for (const [name, text] of texts) {
    if (ARCHIVE.has(name)) continue;
    check(!/ultralytics|yolov\d|\.pt\b|onnx.*yolo/i.test(prose(text).replace(/Ultralytics AGPL[^|\n]*/g, '')), `${name}: YOLO implementation detail on mainline`);
  }
}

if (errors.length) {
  errors.forEach(e => process.stderr.write(`ERROR: ${e}\n`));
  process.stderr.write(`${errors.length} error(s).\n`);
  process.exitCode = 1;
} else {
  process.stdout.write(`PASS: ${files.length} Markdown files; ${diagrams} accessible Mermaid blocks; ${requirements.length} requirements; ${definedTests.size} acceptance IDs; ${decisions.size} decisions; ${adrs.size} ADRs; ${sample.samples.length} source samples with matching license hash.\n`);
  process.stdout.write('Scope: document structure and references only; no application, mathematical, security, performance, or visual-rendering claim.\n');
}
