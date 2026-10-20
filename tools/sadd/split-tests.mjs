#!/usr/bin/env node
// 把每张卡的“验收标准”字段剥离到 SADD/Test/<同名文件夹>/S编号_卡号_TEST.md，卡片中只留一行引用。
// 用法：node tools/sadd/split-tests.mjs [--sadd DIR] [--dry-run]
// 剥离是无损的：写盘后用 layout.mjs 拼回，三份文档文本必须与剥离前逐字节一致，否则回滚。
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {DOCS, ACCEPT_LINE, TEST_DIR, testRelOf, testRef, testHeader, readDocs, listCardFiles, layoutOf} from './layout.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

/** 计算剥离结果：Map<相对 SADD 的路径, 新内容>（含改写后的卡片与新建的测试文件）。 */
export function extractTests(sadd) {
  const {cards, issues} = listCardFiles(sadd);
  const files = new Map(); const errors = issues.map(x => `${x.id} ${x.msg}`); const skipped = [];
  for (const c of cards.values()) {
    if (c.test) { skipped.push(c.id); continue; }   // 已剥离
    const lines = c.raw.split(/(?<=\n)/); let fence = false; const heads = [];
    lines.forEach((line, i) => {
      if (line.startsWith('```')) fence = !fence;
      if (!fence && /^\*\*[^*\n]+\*\*/.test(line)) heads.push({i, name: line.match(/^\*\*([^*\n]+)\*\*/)[1], line});
    });
    const at = heads.filter(h => h.name === '验收标准');
    if (!at.length) { skipped.push(c.id); continue; }
    if (at.length > 1 || at[0].line !== ACCEPT_LINE + '\n') { errors.push(`${c.rel}: “验收标准”必须是唯一且独占一行的字段`); continue; }
    const start = at[0].i; const next = heads.find(h => h.i > start); const end = next ? next.i : lines.length;
    let core = lines.slice(start, end).join('');
    const trailing = core.match(/\n*$/)[0].slice(1);   // 保留在卡片中的空行（字段与下一字段之间）
    core = core.slice(0, core.length - trailing.length);
    const rel = testRelOf(c.folder, c.stage, c.id);
    const title = c.raw.match(/^### \S+ (.+)$/m)?.[1]?.trim() ?? '';
    files.set(c.rel, lines.slice(0, start).join('') + testRef(rel) + '\n' + trailing + lines.slice(end).join(''));
    files.set(rel, testHeader(c.id, title, c.folder, path.posix.basename(c.rel)) + core);
  }
  return {files, errors, skipped};
}

function apply(sadd, files) {
  for (const [f, t] of files) { fs.mkdirSync(path.dirname(path.join(sadd, f)), {recursive: true}); fs.writeFileSync(path.join(sadd, f), t); }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const opt = name => { const i = process.argv.indexOf(name); return i < 0 ? undefined : process.argv[i + 1]; };
  const sadd = path.resolve(opt('--sadd') ?? path.join(ROOT, 'SADD'));
  if (layoutOf(sadd) !== 'split') { console.error('需要先拆分为每卡一个文件（tools/sadd/split.mjs）'); process.exit(2); }
  const before = readDocs(sadd).texts;
  const {files, errors, skipped} = extractTests(sadd);
  if (errors.length) { console.error(errors.join('\n')); process.exit(1); }
  const tests = [...files.keys()].filter(f => f.startsWith(TEST_DIR + '/')).length;
  for (const f of files.keys()) if (f.startsWith(TEST_DIR + '/') && fs.existsSync(path.join(sadd, f))) { console.error(`目标已存在：${f}`); process.exit(1); }
  if (process.argv.includes('--dry-run')) {
    // 在临时目录完整演练：复制卡片文件夹与总览，写盘、拼回、比对。
    const tmp = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'sadd-tests-'));
    for (const d of ['S0', ...DOCS.map(x => x.dir)]) fs.cpSync(path.join(sadd, d), path.join(tmp, d), {recursive: true});
    if (fs.existsSync(path.join(sadd, TEST_DIR))) fs.cpSync(path.join(sadd, TEST_DIR), path.join(tmp, TEST_DIR), {recursive: true});
    apply(tmp, files);
    const back = readDocs(tmp);
    const same = DOCS.every(d => back.texts[d.doc] === before[d.doc]);
    fs.rmSync(tmp, {recursive: true});
    console.log(JSON.stringify({dryRun: true, tests, skipped, identical: same, issues: back.issues}));
    process.exit(same && !back.issues.length ? 0 : 1);
  }
  const originals = new Map([...files.keys()].filter(f => !f.startsWith(TEST_DIR + '/')).map(f => [f, fs.readFileSync(path.join(sadd, f), 'utf8')]));
  apply(sadd, files);
  let back, ok = false;
  try { back = readDocs(sadd); ok = DOCS.every(d => back.texts[d.doc] === before[d.doc]) && !back.issues.length; }
  finally {
    if (!ok) {
      for (const f of files.keys()) if (f.startsWith(TEST_DIR + '/')) fs.rmSync(path.join(sadd, f), {force: true});
      for (const [f, t] of originals) fs.writeFileSync(path.join(sadd, f), t);
    }
  }
  console.log(JSON.stringify({tests, skipped, identical: ok, issues: back?.issues ?? []}));
  if (!ok) { console.error('拼回结果与剥离前不一致，已回滚'); process.exit(1); }
}
