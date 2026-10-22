// CORE-76：只重写附录D 的 bounded 统计区块；--check 只比对不写。
// 退出码 0 无错误、1 校验错误或统计漂移、2 读写/解析错误（卡 :15）。
import fs from 'node:fs';
import path from 'node:path';
import {load, ROOT} from './pack.mjs';
import {reviewColumn, validateCurrent} from './current.mjs';

const START = '<!-- sadd-current-stats:start -->';
const END = '<!-- sadd-current-stats:end -->';
const sadd = path.join(ROOT, 'SADD');
const file = path.join(sadd, '附录D-编码就绪检查记录.md');
const gone = {AND: 'AND-10', WIN: 'WIN-11'};

// 区块内容只由现行卡与 D.10 生成，不带实现或真机结论（卡 :13）。
function block(cards, grades, ready) {
  const body = [START, '由 `node tools/sadd/stats.mjs` 从现行卡与D.10生成；不代表实现或真机验收通过。',
    '', '| 文档 | 当前有效卡 | 历史撤销 |', '| --- | --- | --- |'];
  for (const prefix of ['CORE', 'AND', 'WIN']) {
    body.push(`| ${prefix} | ${[...cards.keys()].filter(id => id.startsWith(`${prefix}-`)).length} | ${gone[prefix] ?? '无'} |`);
  }
  body.push('', `总计${cards.size}卡；当前独立复核等级：${Object.entries(grades).map(([k, v]) => `${k}=${v}`).join('、')}；就绪=${ready}。`, END);
  return body.join('\n');
}

function main() {
  try {
    const text = fs.readFileSync(file, 'utf8');
    if (!text.includes(START) || !text.includes(END)) throw new Error('Missing stats block');
    const cards = load(sadd);
    const current = text.split('## D.10 ')[1]?.split('### D.10.1')[0] ?? '';
    const rows = current.split('\n').filter(line => /^\| (?:CORE|AND|WIN)-\d+ \|/.test(line));
    const columns = current.split('\n').find(line => line.startsWith('| 编号 |'))?.split('|').map(c => c.trim()) ?? [];
    const gradeColumn = reviewColumn(columns), statusColumn = columns.indexOf('当前状态');
    const version = columns[gradeColumn]?.split(' ')[0];
    const reviewFile = path.join(sadd, 'reports', `${version}-reviews.json`);
    const reviews = fs.existsSync(reviewFile) ? JSON.parse(fs.readFileSync(reviewFile, 'utf8')) : {version: 1, entries: []};
    const grades = {};
    let ready = 0;
    for (const line of rows) {
      const cells = line.split('|').map(c => c.trim());
      const grade = gradeColumn < 0 ? '未独立复核' : cells[gradeColumn];
      grades[grade] = (grades[grade] ?? 0) + 1;
      // 就绪只认 D.12 精确写法；前缀匹配会把“就绪但缺证据”算成就绪（卡 :44）。
      if (statusColumn >= 0 && cells[statusColumn] === `就绪（D.12 P2-${cells[1]}）`) ready++;
    }
    const errors = validateCurrent(rows, columns, cards, reviews, text);
    if (rows.length !== cards.size) errors.push(`SADD-12: current rows ${rows.length} != cards ${cards.size}`);
    const summary = JSON.stringify({cards: cards.size, grades, ready});
    if (errors.length) {
      for (const error of errors) console.error(error);
      process.exitCode = 1;
      return;
    }
    const result = text.replace(/<!-- sadd-current-stats:start -->[\s\S]*?<!-- sadd-current-stats:end -->/, () => block(cards, grades, ready));
    if (result !== text) {
      if (process.argv.includes('--check')) {
        console.error('SADD stats drift');
        process.exitCode = 1;
        return;
      }
      fs.writeFileSync(file, result);
    }
    console.log(summary);
  } catch (error) {
    console.error(`SADD stats: ${error.message}`);
    process.exitCode = 2;
  }
}

main();


