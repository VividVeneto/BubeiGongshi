// SADD 模块卡的物理布局：旧布局为三份文档；拆分布局为 S0/、core/、and/、win/ 四个文件夹。
// 拆分布局下，core/and/win 的 00-总览.md 保留原文档中卡片以外的全部内容，并在卡片原位置写
// “<!-- sadd:card 卡号 -->”标记；按标记把卡片文件原样拼回，即得到与旧文档逐字节一致的文本。
import fs from 'node:fs';
import path from 'node:path';

export const DOCS = [
  {doc: '01-公共核心-v5.md', dir: 'core', prefix: 'CORE'},
  {doc: '02-Android端-v5.md', dir: 'and', prefix: 'AND'},
  {doc: '03-Windows端-v5.md', dir: 'win', prefix: 'WIN'},
];
export const FILES = DOCS.map(d => d.doc);
export const FOLDERS = ['S0', 'core', 'and', 'win'];
export const OVERVIEW = '00-总览.md';
export const GROUPS = ['基座', '引擎', '界面', '功能', '账户', '扩展', '平台', '发布'];
export const CARD_FILE = /^(S\d)_((?:CORE|AND|WIN)-\d+)_([^_.]+)\.md$/;
export const MARKER = /^<!-- sadd:card ((?:CORE|AND|WIN)-\d+) -->$/;
export const marker = id => `<!-- sadd:card ${id} -->`;
export const docOf = id => DOCS.find(d => id.startsWith(d.prefix + '-'));
/** 卡片应在的文件夹：S0 阶段统一进 S0/，其余按卡号前缀进 core/and/win。 */
export const folderFor = (id, stage) => stage === 'S0' ? 'S0' : docOf(id).dir;
export const cardFileName = (stage, id, group) => `${stage}_${id}_${group}.md`;

export function layoutOf(sadd) {
  const legacy = FILES.some(f => fs.existsSync(path.join(sadd, f)));
  const split = DOCS.some(d => fs.existsSync(path.join(sadd, d.dir, OVERVIEW)));
  if (legacy && split) throw new Error('SADD 同时存在旧文档与拆分文件夹，无法确定布局');
  return split ? 'split' : 'legacy';
}

/** 列出拆分布局中的卡片文件；issues 记录命名与位置问题，由 DTOcheck 报告。 */
export function listCardFiles(sadd) {
  const cards = new Map(); const issues = [];
  for (const folder of FOLDERS) {
    const dir = path.join(sadd, folder);
    if (!fs.existsSync(dir)) continue;
    for (const name of fs.readdirSync(dir).sort()) {
      const rel = `${folder}/${name}`;
      if (fs.statSync(path.join(dir, name)).isDirectory()) { issues.push({id: 'LAYOUT-01', msg: `${rel}: 卡片文件夹内不应有子目录`}); continue; }
      if (name === OVERVIEW && folder !== 'S0') continue;
      const m = name.match(CARD_FILE);
      if (!m) { issues.push({id: 'LAYOUT-01', msg: `${rel}: 文件名不符合“S编号_卡号_分组.md”`}); continue; }
      const [, stage, id, group] = m;
      if (!GROUPS.includes(group)) issues.push({id: 'LAYOUT-01', msg: `${rel}: 分组“${group}”不在 ${GROUPS.join('、')} 之内`});
      if (cards.has(id)) throw new Error(`卡片 ${id} 有多个文件：${cards.get(id).rel}、${rel}`);
      cards.set(id, {id, rel, folder, stage, group, text: fs.readFileSync(path.join(dir, name), 'utf8')});
    }
  }
  return {cards, issues};
}

/** 读取三份文档的完整文本（拆分布局按标记拼回）。 */
export function readDocs(sadd) {
  const layout = layoutOf(sadd);
  if (layout === 'legacy') return {layout, texts: Object.fromEntries(FILES.map(f => [f, fs.readFileSync(path.join(sadd, f), 'utf8')])), cardFiles: new Map(), issues: []};
  const {cards, issues} = listCardFiles(sadd);
  const used = new Set(); const texts = {};
  for (const d of DOCS) {
    const overview = fs.readFileSync(path.join(sadd, d.dir, OVERVIEW), 'utf8');
    texts[d.doc] = overview.split(/(?<=\n)/).map(line => {
      const m = line.replace(/\n$/, '').match(MARKER);
      if (!m) return line;
      const card = cards.get(m[1]);
      if (!card) throw new Error(`${d.dir}/${OVERVIEW}: 标记 ${m[1]} 找不到卡片文件`);
      if (used.has(m[1])) throw new Error(`${m[1]}: 在总览中被标记了多次`);
      if (docOf(m[1]) !== d) issues.push({id: 'LAYOUT-05', msg: `${m[1]}: 标记应在 ${docOf(m[1]).dir}/${OVERVIEW}，实际在 ${d.dir}/${OVERVIEW}`});
      used.add(m[1]);
      return card.text;
    }).join('');
  }
  for (const id of cards.keys()) if (!used.has(id)) issues.push({id: 'LAYOUT-05', msg: `${cards.get(id).rel}: 没有任何总览标记引用该卡片`});
  for (const c of cards.values()) {
    const heads = [...c.text.matchAll(/^### ((?:CORE|AND|WIN)-\d+) /gm)].map(m => m[1]);
    if (!c.text.startsWith(`### ${c.id} `) || heads.length !== 1) issues.push({id: 'LAYOUT-04', msg: `${c.rel}: 文件必须以“### ${c.id} 名称”开头且只含这一张卡`});
  }
  return {layout, texts, cardFiles: cards, issues};
}
