#!/usr/bin/env node
// 依次运行 DTOcheck 的三项检查并汇总。退出码：0 全部通过；1 有 error（--strict 时 warning 也算）；2 工具自身异常。
// 用法：node tools/DTOcheck/run.mjs [--strict] [--json] [--verbose] [--only dto,cards,xref]
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {ROOT, loadCards, printReport, exitCodeFor, argOf} from './lib.mjs';
import {checkDto} from './dto.mjs';
import {checkCards} from './cards.mjs';
import {checkXref, DEFAULT_BASELINE} from './xref.mjs';
import fs from 'node:fs';

export function runAll({root = ROOT, only = null} = {}) {
  const sadd = path.join(root, 'SADD');
  const want = n => !only || only.includes(n);
  const reports = [];
  if (want('cards')) reports.push(checkCards({sadd}));
  if (want('dto')) { let cards = null; try { cards = loadCards(sadd); } catch { /* 交给 cards 检查报告 */ } reports.push(checkDto({root, cards})); }
  if (want('xref')) reports.push(checkXref({sadd, root, baselinePath: fs.existsSync(DEFAULT_BASELINE) ? DEFAULT_BASELINE : null}));
  return reports;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const a = process.argv;
    const only = argOf(a, '--only')?.split(',');
    const reports = runAll({only});
    for (const r of reports) delete r.data;
    if (a.includes('--json')) console.log(JSON.stringify(reports, null, 2));
    else for (const r of reports) console.log(printReport(r, {verbose: a.includes('--verbose')}));
    process.exitCode = exitCodeFor(reports, {strict: a.includes('--strict')});
  } catch (e) { console.error(`DTOcheck 异常: ${e.stack}`); process.exitCode = 2; }
}
