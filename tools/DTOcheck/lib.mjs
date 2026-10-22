// DTOcheck 共享工具：报告、卡片读取、错误码与类型定义提取。仅用 Node 标准库。
import fs from 'node:fs';
import path from 'node:path';
import {load, ROOT, FILES} from '../sadd/pack.mjs';

export {load, ROOT, FILES};

/**
 * 一次检查的结果；error 使退出码为 1，warn 仅提示（--strict 时也算失败），
 * skip 表示该项“未执行”（例如 registry 尚未创建）：输出“未执行”，任何模式下都不算通过。
 */
export class Report {
  constructor(name) { this.name = name; this.errors = []; this.warnings = []; this.skipped = []; this.stats = {}; }
  error(id, msg) { this.errors.push({id, msg}); }
  warn(id, msg) { this.warnings.push({id, msg}); }
  skip(id, msg) { this.skipped.push({id, msg}); }
  get ok() { return this.errors.length === 0 && this.skipped.length === 0; }
}

export function printReport(r, {verbose = false, limit = 40} = {}) {
  const skipped = r.skipped?.length ? ` skipped=${r.skipped.length}` : '';
  const head = `[${r.name}] errors=${r.errors.length} warnings=${r.warnings.length}${skipped} ${JSON.stringify(r.stats)}`;
  const out = [head];
  for (const e of r.errors) out.push(`  ERROR ${e.id}: ${e.msg}`);
  for (const e of r.skipped ?? []) out.push(`  SKIP  ${e.id}: 未执行：${e.msg}`);
  const shown = verbose ? r.warnings : r.warnings.slice(0, limit);
  for (const w of shown) out.push(`  warn  ${w.id}: ${w.msg}`);
  if (!verbose && r.warnings.length > limit) out.push(`  ... 另有 ${r.warnings.length - limit} 条 warning，加 --verbose 查看`);
  return out.join('\n');
}

export function exitCodeFor(reports, {strict = false} = {}) {
  if (reports.some(r => r.errors.length)) return 1;
  if (reports.some(r => r.skipped?.length)) return 1;   // “未执行”不是通过，任何模式都失败
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
      const m = (cells[1] ?? '').match(/^`([A-Z][A-Z0-9_]*)`(?:（\d+）)?$/);   // 允许“`CODE`（HTTP 状态）”写法
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

/**
 * 提取“错误码引用”表中的引用：每行 {card: 引用所在卡, codes: [...], owners: [被声明的唯一定义卡...]}。
 * 带通配的写法（如 `IMG_*`）不展开；“CORE-33/34”展开为两张卡。
 */
export function errorRefs(cards) {
  const refs = [];
  for (const c of cards.values()) {
    let mode = null;
    for (const line of c.body.split('\n')) {
      if (!line.startsWith('|')) { mode = null; continue; }
      const cells = line.split('|').map(x => x.trim());
      if (/^错误码/.test(cells[1] ?? '')) { mode = /引用/.test(cells[1]) ? 'ref' : 'def'; continue; }
      if (mode !== 'ref' || /^-+$/.test(cells[1] ?? '')) continue;
      const codes = [...(cells[1] ?? '').matchAll(/`([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)`/g)].map(m => m[1]);
      const owners = [];
      for (const m of (cells[2] ?? '').matchAll(/(CORE|AND|WIN)-(\d+)((?:\/\d+)*)/g)) {
        owners.push(`${m[1]}-${m[2]}`);
        for (const extra of m[3].split('/').filter(Boolean)) owners.push(`${m[1]}-${extra}`);
      }
      if (codes.length && owners.length) refs.push({card: c.id, codes, owners});
    }
  }
  return refs;
}

/**
 * 提取带列的错误码定义表：Map<code, [{card, line, severity, retryable, http}]>。
 * 表头首格以“错误码”开头且不含“引用”的表才算定义表；列按表头文字定位（级别 / 可重试 / HTTP），
 * 没有该列时为 null。HTTP 单元格原样返回（数字或“—”，没有 HTTP 列时为 null）。
 */
export function errorTableRows(cards) {
  const rows = new Map();
  for (const c of cards.values()) {
    let mode = null, cols = null;
    const lines = c.body.split('\n');
    for (const [i, line] of lines.entries()) {
      if (!line.startsWith('|')) { mode = null; cols = null; continue; }
      const cells = line.split('|').map(x => x.trim());
      const head = cells[1] ?? '';
      if (/^错误码/.test(head)) {
        mode = /引用/.test(head) ? 'ref' : 'def';
        const at = name => cells.findIndex(x => x.includes(name));
        cols = mode === 'def' ? {severity: at('级别'), retryable: at('可重试'), http: at('HTTP')} : null;
        continue;
      }
      if (mode !== 'def' || /^-+$/.test(cells[1] ?? '')) continue;
      const m = (cells[1] ?? '').match(/^`([A-Z][A-Z0-9_]*)`(?:（\d+）)?$/);
      if (!m || !isErrorCode(m[1])) continue;
      const list = rows.get(m[1]) ?? [];
      list.push({
        card: c.id, file: c.file ?? null, line: i + 1,
        severity: cols.severity > 0 ? (cells[cols.severity] ?? null) : null,
        retryable: cols.retryable > 0 ? (cells[cols.retryable] ?? null) : null,
        http: cols.http > 0 ? (cells[cols.http] ?? null) : null,
      });
      rows.set(m[1], list);
    }
  }
  return rows;
}

/**
 * 提取逐 op 错误镜像（DTO-06 的对照源，ADR-V5-55）：Map<op, [{card, line, basis, codes:Set}]>。
 * 两种写法都认：表头为“op | 本卡业务/诊断代码及依赖透传”的表行，或“错误镜像（不重定义）：op = 码、码”内联句。
 * 码用 `OP = A、B（CORE-05）` 的注记只取错误码本身；单元格写“无业务错误”时集合为空。
 */
export function opMirrors(cards) {
  const out = new Map();
  const add = (op, entry) => {
    if (!op) return;
    const list = out.get(op) ?? [];
    list.push(entry);
    out.set(op, list);
  };
  const codesOf = text => new Set([...(text ?? '').matchAll(/`?([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)`?/g)].map(m => m[1]).filter(isErrorCode));
  for (const c of cards.values()) {
    const lines = c.body.split('\n');
    let inTable = false;
    for (const [i, line] of lines.entries()) {
      const inline = line.match(/错误镜像[^\n]*?：\s*(.+)$/);
      if (inline) {
        for (const part of inline[1].split('；')) {
          const m = part.match(/^\s*`?([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)`?\s*=\s*(.+)$/);
          if (!m) continue;                       // 尾部的“信封/句柄/取消复用 CORE-03”等说明不算镜像
          add(m[1], {card: c.id, file: c.file ?? null, line: i + 1, basis: 'inline', codes: codesOf(m[2])});
        }
      }
      if (!line.startsWith('|')) { inTable = false; continue; }
      const cells = line.split('|').map(x => x.trim());
      if (cells[1] === 'op' && /本卡业务\/诊断代码/.test(cells[2] ?? '')) { inTable = true; continue; }
      if (!inTable || /^-+$/.test(cells[1] ?? '')) continue;
      const op = (cells[1] ?? '').replace(/`/g, '').trim();
      if (!/^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$/.test(op)) continue;
      add(op, {card: c.id, file: c.file ?? null, line: i + 1, basis: 'row', codes: codesOf(cells[2])});
    }
  }
  return out;
}
