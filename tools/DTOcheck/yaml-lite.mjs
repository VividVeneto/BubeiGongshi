// 最小 YAML 子集读取器：只支持 contracts/errors/*.yaml 实际用到的结构，不引第三方依赖。
// 支持：顶层 `键: 标量`；顶层 `键:` 后跟一层“映射列表”（`  - 键: 标量` 起项，续行缩进 +2 的 `键: 标量`）；
//       整行注释（# 开头）、空行、空格缩进。
// 标量只支持字符串、整数、true/false、null/~。其余语法（引号标量、flow 集合、锚点/别名、块标量、
// 嵌套更深的映射、tab 缩进、多文档标记、行尾注释）一律报错，不猜。
export class YamlLiteError extends Error {
  constructor(file, line, message) {
    super(`${file}:${line}: ${message}`);
    this.name = 'YamlLiteError';
    this.file = file;
    this.line = line;
  }
}

const KEY_RE = /^([A-Za-z_][A-Za-z0-9_-]*):(?: (.*))?$/;
const UNSAFE_FIRST = new Set(["'", '"', '[', ']', '{', '}', '&', '*', '!', '|', '>', '?', '#', '%', '@', '`', ',']);

function scalar(raw, fail) {
  const s = raw.trim();
  if (!s) fail('空值不支持（本工具只接受显式标量）');
  if (UNSAFE_FIRST.has(s[0])) fail(`不支持的标量开头 ${JSON.stringify(s[0])}（引号/flow/锚点/块标量等）`);
  if (s.includes(': ')) fail('标量中出现“: ”，疑似嵌套结构');
  if (/:$/.test(s)) fail('标量以“:”结尾，疑似嵌套结构');
  if (/ #/.test(s)) fail('行尾注释不支持');
  if (s === 'null' || s === '~') return null;
  if (s === 'true') return true;
  if (s === 'false') return false;
  if (/^-?\d+$/.test(s)) return Number(s);
  if (/^[+-]?\d*\.\d+$/.test(s)) fail('小数不支持（只支持字符串/整数/布尔/null）');
  return s;
}

/**
 * 解析最小 YAML 子集。返回顶层键 → 标量或映射数组的普通对象。
 * @param {string} text
 * @param {{file?: string}} opts file 仅用于错误定位
 */
export function parseYaml(text, {file = '<yaml>'} = {}) {
  const lines = String(text).split(/\r?\n/);
  const doc = {};
  let i = 0;
  const failAt = (n, msg) => { throw new YamlLiteError(file, n, msg); };
  const skipBlank = () => { while (i < lines.length && (lines[i].trim() === '' || /^\s*#/.test(lines[i]))) i++; };

  while (true) {
    skipBlank();
    if (i >= lines.length) break;
    const raw = lines[i];
    if (/^\t/.test(raw) || /^ *\t/.test(raw)) failAt(i + 1, '缩进不得使用 tab');
    if (/^(---|\.\.\.)\s*$/.test(raw)) failAt(i + 1, '多文档标记不支持');
    const m = raw.match(KEY_RE);
    if (!m) failAt(i + 1, `顶部只支持“键: 标量”或“键:”，实际 ${JSON.stringify(raw)}`);
    const key = m[1];
    if (key in doc) failAt(i + 1, `顶层键重复：${key}`);
    const ln = i + 1;
    i++;
    if (m[2] !== undefined) { doc[key] = scalar(m[2], msg => failAt(ln, msg)); continue; }

    // 顶层键的值为容器：只支持一层映射列表
    skipBlank();
    if (i >= lines.length) failAt(ln, `键 ${key} 的值为空`);
    const ind = lines[i].match(/^ */)[0].length;
    if (ind === 0) failAt(i + 1, `键 ${key} 的值为空`);
    if (!/^- /.test(lines[i].slice(ind))) failAt(i + 1, `键 ${key} 只支持映射列表（“- 键: 值”），不支持嵌套映射`);
    const items = [];
    while (true) {
      skipBlank();
      if (i >= lines.length) break;
      const line = lines[i];
      if (/^\t/.test(line) || /^ *\t/.test(line)) failAt(i + 1, '缩进不得使用 tab');
      const cur = line.match(/^ */)[0].length;
      if (cur < ind) break;                       // 回到外层
      if (cur === ind) {
        if (!/^- /.test(line.slice(cur))) failAt(i + 1, `列表项必须以“- 键: 值”开头，实际 ${JSON.stringify(line)}`);
        const item = {};
        const body = line.slice(cur + 2);
        const km = body.match(KEY_RE);
        if (!km || km[2] === undefined) failAt(i + 1, '列表项首键必须有标量值');
        item[km[1]] = scalar(km[2], msg => failAt(i + 1, msg));
        i++;
        // 续行
        while (true) {
          skipBlank();
          if (i >= lines.length) break;
          const l2 = lines[i];
          if (/^\t/.test(l2) || /^ *\t/.test(l2)) failAt(i + 1, '缩进不得使用 tab');
          const c2 = l2.match(/^ */)[0].length;
          if (c2 <= ind) break;
          if (c2 !== ind + 2) failAt(i + 1, `列表项续键缩进必须是 ${ind + 2} 个空格，实际 ${c2}`);
          const km2 = l2.slice(c2).match(KEY_RE);
          if (!km2 || km2[2] === undefined) failAt(i + 1, `只支持“键: 标量”形式的续键，实际 ${JSON.stringify(l2)}`);
          if (km2[1] in item) failAt(i + 1, `列表项内键重复：${km2[1]}`);
          item[km2[1]] = scalar(km2[2], msg => failAt(i + 1, msg));
          i++;
        }
        items.push(item);
        continue;
      }
      failAt(i + 1, `缩进 ${cur} 超出列表项范围`);
    }
    if (!items.length) failAt(ln, `键 ${key} 的列表为空`);
    doc[key] = items;
  }
  if (!Object.keys(doc).length) throw new YamlLiteError(file, 1, '空文档');
  return doc;
}

export default parseYaml;
