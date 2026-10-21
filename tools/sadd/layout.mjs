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

// 测试方案（验收标准）剥离到 SADD/Test/<同名文件夹>/S编号_卡号_TEST.md；卡片中“验收标准”字段只留一行引用，
// 读取时按引用把测试文件自“**验收标准**”行起的内容原样拼回，工具看到的卡片全文与剥离前逐字节一致。
export const TEST_DIR = 'Test';
export const TEST_FILE = /^(S\d)_((?:CORE|AND|WIN)-\d+)_TEST\.md$/;
export const ACCEPT_LINE = '**验收标准**';
export const testFileName = (stage, id) => `${stage}_${id}_TEST.md`;
export const testRelOf = (folder, stage, id) => `${TEST_DIR}/${folder}/${testFileName(stage, id)}`;
const TEST_REF = /^\*\*验收标准\*\*：测试方案全文见 \[([^\]\n]+)\]\(([^)\n]+)\)[^\n]*\n/m;
/** 卡片中替代“验收标准”字段的引用行（不含换行）。 */
export const testRef = rel => `**验收标准**：测试方案全文见 [${rel}](../${rel})；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。`;
/** 测试文件开头（拼回时不含这部分）。 */
export const testHeader = (id, title, folder, cardName) =>
  `# ${id} 测试方案\n\n> 来源卡：[${cardName}](../../${folder}/${cardName})（${title}）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（` + '`S编号_卡号_TEST.md`' + `）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。\n\n`;
/** 测试文件中拼回卡片的部分：自“**验收标准**”行起到文件末尾。 */
export function testBody(text) {
  const i = text.indexOf('\n' + ACCEPT_LINE + '\n');
  return i < 0 ? null : text.slice(i + 1);
}

export function layoutOf(sadd) {
  const legacy = FILES.some(f => fs.existsSync(path.join(sadd, f)));
  const split = DOCS.some(d => fs.existsSync(path.join(sadd, d.dir, OVERVIEW)));
  if (legacy && split) throw new Error('SADD 同时存在旧文档与拆分文件夹，无法确定布局');
  return split ? 'split' : 'legacy';
}

/** 列出拆分布局中的卡片文件；issues 记录命名与位置问题，由 DTOcheck 报告。 */
export function listCardFiles(sadd) {
  const cards = new Map(); const issues = []; const referenced = new Set();
  const testRoot = path.join(sadd, TEST_DIR); const testsExist = fs.existsSync(testRoot);
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
      const raw = fs.readFileSync(path.join(dir, name), 'utf8');
      const card = {id, rel, folder, stage, group, raw, text: raw};
      const ref = raw.match(TEST_REF); const want = testRelOf(folder, stage, id);
      if (ref) {
        if (ref[1] !== want || ref[2] !== `../${want}`) issues.push({id: 'LAYOUT-06', msg: `${rel}: 测试方案引用应为 [${want}](../${want})，实际为 [${ref[1]}](${ref[2]})`});
        const file = path.join(sadd, want);
        const test = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : null;
        const body = test && testBody(test);
        if (!test) issues.push({id: 'LAYOUT-06', msg: `${rel}: 引用的测试方案 ${want} 不存在`});
        else if (!body || !test.startsWith(`# ${id} 测试方案\n`)) issues.push({id: 'LAYOUT-06', msg: `${want}: 必须以“# ${id} 测试方案”开头并含独立一行“${ACCEPT_LINE}”`});
        else { card.text = raw.replace(ref[0], () => body); card.test = {rel: want, text: test}; referenced.add(want); }
      } else if (testsExist && new RegExp(`^\\*\\*验收标准\\*\\*$`, 'm').test(raw)) {
        issues.push({id: 'LAYOUT-07', msg: `${rel}: “验收标准”应剥离到 ${want}，卡片只留引用行`});
      }
      cards.set(id, card);
    }
  }
  if (testsExist) for (const entry of fs.readdirSync(testRoot).sort()) {
    const sub = path.join(testRoot, entry);
    if (!FOLDERS.includes(entry) || !fs.statSync(sub).isDirectory()) { issues.push({id: 'LAYOUT-06', msg: `${TEST_DIR}/${entry}: ${TEST_DIR}/ 下只允许 ${FOLDERS.join('、')} 文件夹`}); continue; }
    for (const name of fs.readdirSync(sub).sort()) {
      const rel = `${TEST_DIR}/${entry}/${name}`;
      if (!TEST_FILE.test(name)) issues.push({id: 'LAYOUT-06', msg: `${rel}: 文件名不符合“S编号_卡号_TEST.md”`});
      else if (!referenced.has(rel)) issues.push({id: 'LAYOUT-06', msg: `${rel}: 没有卡片引用该测试方案（卡片改名后测试文件应同步改名）`});
    }
  }
  return {cards, issues};
}

/**
 * 读取三份文档的完整文本（拆分布局按标记拼回）。
 * tests=true（默认）时卡片的“验收标准”引用行换回 Test/ 测试方案全文，供往返校验与 cardiff 使用；
 * tests=false 时保留卡片原文（只含引用行），供会话材料默认不收录测试方案（README §8.1）。
 */
export function readDocs(sadd, {tests = true} = {}) {
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
      return tests ? card.text : card.raw;
    }).join('');
  }
  for (const id of cards.keys()) if (!used.has(id)) issues.push({id: 'LAYOUT-05', msg: `${cards.get(id).rel}: 没有任何总览标记引用该卡片`});
  for (const c of cards.values()) {
    const heads = [...c.text.matchAll(/^### ((?:CORE|AND|WIN)-\d+) /gm)].map(m => m[1]);
    if (!c.text.startsWith(`### ${c.id} `) || heads.length !== 1) issues.push({id: 'LAYOUT-04', msg: `${c.rel}: 文件必须以“### ${c.id} 名称”开头且只含这一张卡`});
  }
  return {layout, texts, cardFiles: cards, issues};
}
