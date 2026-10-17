// Documentation consistency checks only. This does not test the future app.
// Run from any directory with Node.js 20+: node tools/verify-sadd.mjs
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sadd = path.join(root, 'SADD');
const errors = [];
const check = (ok, message) => { if (!ok) errors.push(message); };
const read = p => fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, '');
const files = fs.readdirSync(sadd).filter(p => p.endsWith('.md'));
let diagrams = 0;

for (const name of files) {
  const text = read(path.join(sadd, name));
  const lines = text.split(/\r?\n/);
  let fence = null;
  let body = [];
  let headings = 0;
  for (const line of lines) {
    const opening = line.match(/^(`{3,}|~{3,})(.*)$/);
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
    target = decodeURIComponent(target.split('#')[0]);
    if (target) check(fs.existsSync(path.resolve(sadd, target)), `${name}: missing ${target}`);
  }
}

const matrix = read(path.join(sadd, '13-需求追踪与验收-v3.md'));
const requirements = [...matrix.matchAll(/^\| ((?:R|H|A)\d{2}) \|(.+)$/gm)];
const ids = requirements.map(x => x[1]);
check(new Set(ids).size === ids.length, 'Duplicate requirement IDs');
for (let i = 1; i <= 31; i++) check(ids.includes(`R${String(i).padStart(2, '0')}`), `Missing requirement R${i}`);
const definedTests = new Set([...matrix.matchAll(/^\| (T-[A-Z]+) \|/gm)].map(x => x[1]));
for (const row of requirements) {
  const refs = row[2].match(/T-[A-Z]+/g) ?? [];
  check(refs.length > 0, `${row[1]}: no acceptance test`);
  refs.forEach(id => check(definedTests.has(id), `${row[1]}: undefined ${id}`));
}

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

const mainArchitecture = read(path.join(sadd, '10-软件架构设计-v3.md'));
const branch = execFileSync('git', ['branch', '--show-current'], { cwd: root, encoding: 'utf8' }).trim();
if (branch === 'main') {
  check(!fs.existsSync(path.join(sadd, 'experimental/YOLO-详细预研方案-v3.md')), 'Detailed YOLO plan must remain on the experiment branch');
}
check(mainArchitecture.includes('keep_last=N'), 'Missing explicit history count contract');

if (errors.length) {
  errors.forEach(e => process.stderr.write(`ERROR: ${e}\n`));
  process.exitCode = 1;
} else {
  process.stdout.write(`PASS: ${files.length} Markdown files; ${diagrams} accessible Mermaid blocks; ${requirements.length} requirements; ${definedTests.size} acceptance IDs; ${sample.samples.length} source samples with matching license hash.\n`);
  process.stdout.write('Scope: document structure and local references only; no application, mathematical, security, performance, or visual-rendering claim.\n');
}
