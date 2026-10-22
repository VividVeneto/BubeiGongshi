// CORE-76 夹具装载器：读通过基准，或把工具脚本与夹具复制到临时目录得到可写沙箱。
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
/** 通过基准：三张假卡、D.10/D.12 与 reports/v9.9.9-reviews.json。 */
export const FIXTURE = path.join(here, 'pass');
const TOOLS = path.join(here, '../..');
export const APPENDIX = '附录D-编码就绪检查记录.md';

/** 按 stats/audit 的口径从附录D 取出 D.10 表头与数据行。 */
export function read(sadd = FIXTURE) {
  const appendix = fs.readFileSync(path.join(sadd, APPENDIX), 'utf8');
  const lines = (appendix.split('## D.10 ')[1]?.split('### D.10.1')[0] ?? '').split('\n');
  return {
    appendix,
    rows: lines.filter(line => /^\| (?:CORE|AND|WIN)-\d+ \|/.test(line)),
    columns: lines.find(line => line.startsWith('| 编号 |'))?.split('|').map(x => x.trim()) ?? [],
  };
}

export function reviews(sadd = FIXTURE, version = 'v9.9.9') {
  return JSON.parse(fs.readFileSync(path.join(sadd, 'reports', `${version}-reviews.json`), 'utf8'));
}

/** 临时目录内复制 tools/sadd/*.mjs 与夹具 SADD；脚本的 ROOT 即该临时目录。 */
export function sandbox() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'core76-'));
  const tools = path.join(root, 'tools', 'sadd');
  fs.mkdirSync(tools, {recursive: true});
  for (const name of fs.readdirSync(TOOLS)) {
    if (name.endsWith('.mjs') && !name.endsWith('.test.mjs')) fs.copyFileSync(path.join(TOOLS, name), path.join(tools, name));
  }
  const sadd = path.join(root, 'SADD');
  fs.cpSync(FIXTURE, sadd, {recursive: true});
  return {
    root,
    sadd,
    run: (script, ...args) => spawnSync(process.execPath, [path.join(tools, script), ...args], {cwd: root, encoding: 'utf8'}),
    text: rel => fs.readFileSync(path.join(sadd, rel), 'utf8'),
    write: (rel, text) => fs.writeFileSync(path.join(sadd, rel), text),
    /** 只改沙箱内一处文本；改不到就抛错，避免“反例其实没改到”的假通过。 */
    edit: (rel, from, to) => {
      const file = path.join(sadd, rel);
      const text = fs.readFileSync(file, 'utf8');
      if (!text.includes(from)) throw new Error(`fixture text not found in ${rel}: ${from}`);
      fs.writeFileSync(file, text.replace(from, to));
    },
    clean: () => fs.rmSync(root, {recursive: true, force: true}),
  };
}

