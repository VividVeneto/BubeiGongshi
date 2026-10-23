// CORE-76：逐卡 pack 后报告 D.10/D.12 校验、材料量与复核警告；不写 SADD/reports/（卡 :23）。
// 退出码 0 无错误、1 校验错误、2 读写/解析错误（卡 :15）。
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {load, pack, ROOT} from './pack.mjs';
import {reviewColumn, validateCurrent} from './current.mjs';

const option = name => {
  const index = process.argv.indexOf(name);
  return index < 0 ? undefined : process.argv[index + 1];
};
// kind 为闭集（卡 :13）：其余 pack 提示（contracts 过滤说明、材料超量）不进 warnings。
const KINDS = [
  [/^Outside dependency closure:|^Missing referenced card/, 'outside-closure'],
  [/^Local definitions absent/, 'missing-local-definition'],
  [/^SDK\/third-party/, 'sdk-unknown'],
];

// 复核列版本与 D.10 标题/说明声明的版本不一致时只在 stderr 警告，不自动改列名（卡 :24）。
function versionWarning(appendix, version) {
  const head = (appendix.split('## D.10 ')[1] ?? '').split('| 编号 |')[0];
  const others = [...new Set([...head.matchAll(/v\d+\.\d+\.\d+/g)].map(m => m[0]))].filter(v => v !== version).sort();
  if (others.length) console.error(`SADD audit: 复核列版本 ${version} 与 D.10 标题/说明中的 ${others.join(', ')} 不一致；不自动改列名（迁移见 CORE-76 卡 :24）`);
}

// README §6 的 Q 行受影响卡与正文提及不一致即 q-drift（evidence 带 q 与两个布尔）。
function qDrift(warnings, id, card, readme) {
  for (const row of readme.split('\n')) {
    const q = row.match(/^\| (Q\d+) \|/)?.[1];
    if (!q) continue;
    const affected = (row.split('|').at(-2) ?? '').match(/(?:CORE|AND|WIN)-\d+/g) ?? [];
    const mentioned = new RegExp(`\\b${q}\\b`).test(card.body ?? '');
    if (affected.includes(id) !== mentioned) warnings.push({id, kind: 'q-drift', evidence: {q, affected: affected.includes(id), mentioned}});
  }
}

function main() {
  try {
    const sadd = path.resolve(option('--sadd') ?? path.join(ROOT, 'SADD'));
    const out = path.resolve(option('--out') ?? path.join(ROOT, 'build/sadd/audit.json'));
    const snapshots = path.join(sadd, 'reports');
    // 历史快照只读：拒绝把报告写到 SADD/reports/ 下。
    if (out === snapshots || out.startsWith(snapshots + path.sep)) {
      console.error(`SADD audit: refusing to write into ${snapshots}`);
      process.exitCode = 2;
      return;
    }
    const cards = load(sadd);
    const readme = fs.readFileSync(path.join(sadd, 'README.md'), 'utf8');
    const appendix = fs.readFileSync(path.join(sadd, '附录D-编码就绪检查记录.md'), 'utf8');
    // D.10 数据行止于下一个三级小节（D.10.1 统计口径）与 D.11；子节内的合法卡号表行不是现行卡行（U76-N2）。
    const current = appendix.split('## D.10 ')[1]?.split('### D.10.1')[0]?.split('## D.11 ')[0] ?? '';
    const rows = current.split('\n').filter(line => /^\| (?:CORE|AND|WIN)-\d+ \|/.test(line));
    const columns = current.split('\n').find(line => line.startsWith('| 编号 |'))?.split('|').map(c => c.trim()) ?? [];
    const gradeColumn = reviewColumn(columns), statusColumn = columns.indexOf('当前状态');
    const version = columns[gradeColumn]?.split(' ')[0];
    const reviewFile = path.join(snapshots, `${version}-reviews.json`);
    const reviews = fs.existsSync(reviewFile) ? JSON.parse(fs.readFileSync(reviewFile, 'utf8')) : {version: 1, entries: []};
    const stats = {cards: cards.size, CORE: 0, AND: 0, WIN: 0, currentRows: rows.length, ready: 0, grades: {}};
    for (const id of cards.keys()) stats[id.split('-')[0]]++;
    for (const row of rows) {
      const cells = row.split('|').map(c => c.trim());
      const grade = gradeColumn < 0 ? '未独立复核' : cells[gradeColumn];
      stats.grades[grade] = (stats.grades[grade] ?? 0) + 1;
      // 就绪只认 D.12 精确写法，前缀匹配会把缺证据的“就绪”算成就绪（卡 :44）。
      if (statusColumn >= 0 && cells[statusColumn] === `就绪（D.12 P2-${cells[1]}）`) stats.ready++;
    }
    const errors = validateCurrent(rows, columns, cards, reviews, appendix);
    const generated = appendix.match(/<!-- sadd-current-stats:start -->[\s\S]*?<!-- sadd-current-stats:end -->/)?.[0] ?? '';
    if (!generated.includes(`总计${cards.size}卡；`) || !generated.includes(`就绪=${stats.ready}。`) ||
      Object.entries(stats.grades).some(([k, v]) => !generated.includes(`${k}=${v}`))) errors.push('SADD-12: generated current statistics drift; run stats.mjs');
    if (rows.length !== cards.size) errors.push(`SADD-12: current rows ${rows.length} != cards ${cards.size}`);
    versionWarning(appendix, version);
    const warnings = [], materials = [];
    for (const [id, card] of cards) {
      const result = pack(id, {sadd});
      const chars = result.report.chars;
      materials.push({id, chars, segments: result.chunks.length, overLimit: chars > 80000});
      for (const warning of result.report.warnings) {
        const kind = KINDS.find(([pattern]) => pattern.test(warning))?.[1];
        if (!kind) continue;
        const evidence = kind === 'sdk-unknown' ? {undefinedIdentifiers: result.report.undefinedIdentifiers} : {missingFromMaterials: result.report.missingFromMaterials};
        warnings.push({id, kind, evidence});
      }
      qDrift(warnings, id, card, readme);
    }
    materials.sort((a, b) => b.chars - a.chars);
    const report = {version: 1, toolchain: {node: process.version, sadd}, stats, errors, warnings, materials};
    fs.mkdirSync(path.dirname(out), {recursive: true});
    fs.writeFileSync(out, JSON.stringify(report, null, 2));
    console.log(JSON.stringify({stats, errors: errors.length, warnings: warnings.length, overLimit: materials.filter(m => m.overLimit).length, max: materials[0]}));
    process.exitCode = errors.length ? 1 : 0;
  } catch (error) {
    console.error(`SADD audit: ${error.message}`);
    process.exitCode = 2;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();

