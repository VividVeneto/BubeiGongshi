import fs from 'node:fs';
import path from 'node:path';
import {load, ROOT} from './pack.mjs';

// Only this bounded generated block changes; historical batches stay intact.
const sadd = path.join(ROOT, 'SADD');
const file = path.join(sadd, '附录D-编码就绪检查记录.md');
const cards = load(sadd);
const text = fs.readFileSync(file, 'utf8');
const current = text.split('## D.10 ')[1].split('### D.10.1')[0];
const lines = current.split('\n').filter(l => /^\| (CORE|AND|WIN)-\d+ \|/.test(l));
if (lines.length !== cards.size) throw new Error('D.10/card count mismatch');
const header = current.split('\n').find(l => l.startsWith('| 卡号 |'));
const columns = header?.split('|').map(c => c.trim()) ?? [];
const gradeIndex = columns.indexOf('v5.3.2 复核');
const grades = {};
let ready = 0;
for (const line of lines) {
  const cells = line.split('|').map(c => c.trim());
  const grade = gradeIndex < 0 ? '未独立复核' : cells[gradeIndex];
  grades[grade] = (grades[grade] ?? 0) + 1;
  if (cells.some(c => /^就绪（/.test(c))) ready++;
}
const body = ['<!-- sadd-current-stats:start -->',
  '由 `node tools/sadd/stats.mjs` 从现行卡与D.10生成；不代表实现或真机验收通过。',
  '', '| 文档 | 当前有效卡 | 历史撤销 |', '| --- | --- | --- |'];
for (const prefix of ['CORE', 'AND', 'WIN']) {
  body.push(`| ${prefix} | ${[...cards.keys()].filter(id => id.startsWith(prefix + '-')).length} | ${prefix === 'AND' ? 'AND-10' : prefix === 'WIN' ? 'WIN-11' : '无'} |`);
}
body.push('', `总计${cards.size}卡；当前独立复核等级：${Object.entries(grades).map(([k,v]) => `${k}=${v}`).join('、')}；就绪=${ready}。`,
  '<!-- sadd-current-stats:end -->');
const result = text.replace(/<!-- sadd-current-stats:start -->[\s\S]*?<!-- sadd-current-stats:end -->/, body.join('\n'));
if (result === text && !text.includes('<!-- sadd-current-stats:start -->')) throw new Error('Missing stats block');
if (process.argv.includes('--check')) {
  if (result !== text) { console.error('SADD stats drift'); process.exitCode = 1; }
} else fs.writeFileSync(file, result);
console.log(JSON.stringify({cards:cards.size, grades, ready}));
