// DTOcheck 共享工具：报告、卡片读取、错误码与类型定义提取。仅用 Node 标准库。
import fs from 'node:fs';
import path from 'node:path';
import {load, ROOT, FILES} from '../sadd/pack.mjs';

export {load, ROOT, FILES};

/** 一次检查的结果；error 使退出码为 1，warn 仅提示（--strict 时也算失败）。 */
export class Report {
  constructor(name) { this.name = name; this.errors = []; this.warnings = []; this.stats = {}; }
  error(id, msg) { this.errors.push({id, msg}); }
  warn(id, msg) { this.warnings.push({id, msg}); }
  get ok() { return this.errors.length === 0; }
}

export function printReport(r, {verbose = false, limit = 40} = {}) {
  const head = `[${r.name}] errors=${r.errors.length} warnings=${r.warnings.length} ${JSON.stringify(r.stats)}`;
  const out = [head];
  for (const e of r.errors) out.push(`  ERROR ${e.id}: ${e.msg}`);
  const shown = verbose ? r.warnings : r.warnings.slice(0, limit);
  for (const w of shown) out.push(`  warn  ${w.id}: ${w.msg}`);
  if (!verbose && r.warnings.length > limit) out.push(`  ... 另有 ${r.warnings.length - limit} 条 warning，加 --verbose 查看`);
  return out.join('\n');
}

export function exitCodeFor(reports, {strict = false} = {}) {
  if (reports.some(r => r.errors.length)) return 1;
  if (strict && reports.some(r => r.warnings.length)) return 1;
  return 0;
}

export function argOf(argv, name) {
  const i = argv.indexOf(name);
  return i < 0 ? undefined : argv[i + 1];
}

export function readJson(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }

/** 取得卡片表；sadd 目录默认 <ROOT>/SADD，测试可传临时目录。 */
export function loadCards(sadd) { return load(sadd ?? path.join(ROOT, 'SADD')); }

/** 依赖传递闭包（不含自身）。 */
export function closureOf(cards, id, seen = new Set()) {
  for (const d of cards.get(id)?.deps ?? []) if (!seen.has(d)) { seen.add(d); closureOf(cards, d, seen); }
  return seen;
}

const CODE_RE = /^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$/;
export const isErrorCode = s => CODE_RE.test(s);

/**
 * 从卡片正文提取错误码定义：表头首格为“错误码”的表，行首为 `CODE`；
 * 表头首格含“引用”的表是引用表，不算定义。
 * 返回 Map<code, 卡号[]>。
 */
export function errorDefs(cards) {
  const defs = new Map();
  for (const c of cards.values()) {
    let mode = null;
    for (const line of c.body.split('\n')) {
      if (!line.startsWith('|')) { mode = null; continue; }
      const cells = line.split('|').map(x => x.trim());
      if (/^错误码/.test(cells[1] ?? '')) { mode = /引用/.test(cells[1]) ? 'ref' : 'def'; continue; }
      if (mode !== 'def') continue;
      const m = (cells[1] ?? '').match(/^`([A-Z][A-Z0-9_]*)`$/);
      if (m && isErrorCode(m[1])) {
        const list = defs.get(m[1]) ?? [];
        if (!list.includes(c.id)) list.push(c.id);
        defs.set(m[1], list);
      }
    }
  }
  return defs;
}

/** 提取类型定义（Rust 与 Dart）。返回 Map<类型名, 卡号[]>。 */
export function typeDefs(cards) {
  const defs = new Map();
  const re = /(?:^|\s)(?:pub(?:\([a-z]+\))?\s+)?(?:struct|enum|trait|type|(?:abstract |final |sealed |base )?class|mixin|typedef)\s+([A-Z][A-Za-z0-9_]*)/gm;
  for (const c of cards.values()) {
    for (const block of c.body.matchAll(/```[a-z]*\n([\s\S]*?)```/g)) {
      for (const m of block[1].matchAll(re)) {
        const list = defs.get(m[1]) ?? [];
        if (!list.includes(c.id)) list.push(c.id);
        defs.set(m[1], list);
      }
    }
  }
  return defs;
}

/** 从卡片中提取版本/规模文本等常用字段。 */
export function scaleLine(body) { return body.match(/^\*\*规模\*\*[^\n]*/m)?.[0] ?? ''; }
export function scaleNumber(body) { return Number(scaleLine(body).match(/约\s*(\d+)\s*行/)?.[1] ?? NaN); }
