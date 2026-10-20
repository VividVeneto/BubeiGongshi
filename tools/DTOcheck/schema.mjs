// 最小 JSON Schema（2020-12 子集）校验与关键字检查。覆盖 contracts/dto 实际用到的关键字，
// 遇到不支持的关键字报错而不是静默通过。add(path, msg, level)：level 为 'i64' 表示合法但需登记的 i64 整数字段。仅用 Node 标准库。
export const SUPPORTED = new Set([
  '$schema', '$ref', '$defs', 'title', 'description', 'examples', 'default',
  'type', 'properties', 'required', 'additionalProperties', 'items', 'prefixItems',
  'minItems', 'maxItems', 'minLength', 'maxLength', 'minimum', 'maximum',
  'pattern', 'format', 'enum', 'const', 'oneOf', 'anyOf', 'allOf', 'x-sensitive',
]);
export const TYPES = new Set(['string', 'integer', 'number', 'boolean', 'object', 'array', 'null']);
const U64 = (1n << 64n) - 1n, I128_MAX = (1n << 127n) - 1n, I128_MIN = -(1n << 127n);
const DEC = /^-?(?:0|[1-9]\d*)$/;

export const FORMATS = {
  uuid: s => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s),
  base64: s => /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(s),
  uint64: s => /^(?:0|[1-9]\d*)$/.test(s) && BigInt(s) <= U64,
  decimal: s => /^-?(?:0|[1-9]\d*)(?:\.\d+)?$/.test(s),
  int128: s => DEC.test(s) && BigInt(s) >= I128_MIN && BigInt(s) <= I128_MAX,
  'positive-int128': s => DEC.test(s) && BigInt(s) > 0n && BigInt(s) <= I128_MAX,
  latex: () => true,
};

const typeOf = v => v === null ? 'null' : Array.isArray(v) ? 'array' : Number.isInteger(v) ? 'integer' : typeof v;
const matchesType = (t, v) => t === 'number' ? typeof v === 'number' : t === 'integer' ? Number.isInteger(v) : typeOf(v) === t || (t === 'number' && typeof v === 'number');
const deepEq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

/**
 * 解析 $ref（"file.json#/pointer" 或 "#/pointer"）。files: Map<文件名, 文档>。
 * 返回 {schema, file}，找不到返回 null。
 */
export function resolveRef(ref, file, files) {
  const [f, ptr = ''] = ref.split('#');
  const target = f || file;
  let node = files.get(target);
  if (node === undefined) return null;
  for (const raw of ptr.split('/').filter(Boolean)) {
    const key = raw.replace(/~1/g, '/').replace(/~0/g, '~');
    if (node === null || typeof node !== 'object' || !(key in node)) return null;
    node = node[key];
  }
  return {schema: node, file: target};
}

/** 校验 value 是否满足 schema；返回错误字符串数组（空表示通过）。 */
export function validate(schema, value, ctx, p = '') {
  const {files, file} = ctx;
  if (schema === true) return [];
  if (schema === false) return [`${p || '/'}: 此处不允许任何值`];
  const errs = [];
  if (schema.$ref !== undefined) {
    const r = resolveRef(schema.$ref, file, files);
    if (!r) return [`${p || '/'}: 无法解析 $ref ${schema.$ref}`];
    errs.push(...validate(r.schema, value, {files, file: r.file}, p));
  }
  const at = p || '/';
  if (schema.type !== undefined) {
    const ts = Array.isArray(schema.type) ? schema.type : [schema.type];
    if (!ts.some(t => matchesType(t, value))) { errs.push(`${at}: 类型应为 ${ts.join('|')}，实际 ${typeOf(value)}`); return errs; }
  }
  if (schema.const !== undefined && !deepEq(schema.const, value)) errs.push(`${at}: 应等于 ${JSON.stringify(schema.const)}`);
  if (schema.enum && !schema.enum.some(e => deepEq(e, value))) errs.push(`${at}: 不在枚举 ${JSON.stringify(schema.enum)} 中`);
  if (typeof value === 'string') {
    if (schema.minLength !== undefined && [...value].length < schema.minLength) errs.push(`${at}: 长度小于 ${schema.minLength}`);
    if (schema.maxLength !== undefined && [...value].length > schema.maxLength) errs.push(`${at}: 长度大于 ${schema.maxLength}`);
    if (schema.pattern !== undefined && !new RegExp(schema.pattern, 'u').test(value)) errs.push(`${at}: 不匹配 pattern ${schema.pattern}`);
    if (schema.format !== undefined) {
      const f = FORMATS[schema.format];
      if (!f) errs.push(`${at}: 未知 format ${schema.format}`);
      else if (!f(value)) errs.push(`${at}: 不是合法的 ${schema.format}`);
    }
  }
  if (typeof value === 'number') {
    if (schema.minimum !== undefined && value < schema.minimum) errs.push(`${at}: 小于 minimum ${schema.minimum}`);
    if (schema.maximum !== undefined && value > schema.maximum) errs.push(`${at}: 大于 maximum ${schema.maximum}`);
  }
  if (Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < schema.minItems) errs.push(`${at}: 元素少于 ${schema.minItems}`);
    if (schema.maxItems !== undefined && value.length > schema.maxItems) errs.push(`${at}: 元素多于 ${schema.maxItems}`);
    const prefix = schema.prefixItems ?? [];
    value.forEach((item, i) => {
      if (i < prefix.length) errs.push(...validate(prefix[i], item, ctx, `${p}/${i}`));
      else if (schema.items !== undefined) errs.push(...validate(schema.items, item, ctx, `${p}/${i}`));
    });
  }
  if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
    const props = schema.properties ?? {};
    for (const k of schema.required ?? []) if (!(k in value)) errs.push(`${at}: 缺少必填字段 ${k}`);
    for (const [k, v] of Object.entries(value)) {
      if (k in props) errs.push(...validate(props[k], v, ctx, `${p}/${k}`));
      else if (schema.additionalProperties === false) errs.push(`${p}/${k}: 不允许的额外字段`);
      else if (schema.additionalProperties && typeof schema.additionalProperties === 'object') errs.push(...validate(schema.additionalProperties, v, ctx, `${p}/${k}`));
    }
  }
  if (schema.allOf) for (const s of schema.allOf) errs.push(...validate(s, value, ctx, p));
  if (schema.anyOf && !schema.anyOf.some(s => validate(s, value, ctx, p).length === 0)) errs.push(`${at}: 不满足 anyOf 任一分支`);
  if (schema.oneOf) {
    const n = schema.oneOf.filter(s => validate(s, value, ctx, p).length === 0).length;
    if (n !== 1) errs.push(`${at}: oneOf 应恰好匹配 1 个分支，实际 ${n}`);
  }
  return errs;
}

/**
 * 关键字与结构检查（不涉及数据）。回调 add(path, msg) 收集问题。
 * 规则：未知关键字、type 非法、required ⊄ properties、min>max、integer 上界超过 2^53-1（应改用字符串 int128/uint64）、
 * 无效 pattern、空 enum、带 properties 的对象缺少 additionalProperties:false。
 */
export function lintSchema(node, p, add) {
  if (node === true || node === false || node === null || typeof node !== 'object') return;
  for (const k of Object.keys(node)) if (!SUPPORTED.has(k)) add(p, `不支持的关键字 ${k}`);
  if (node.type !== undefined) for (const t of [].concat(node.type)) if (!TYPES.has(t)) add(p, `未知 type ${t}`);
  if (node.properties) {
    for (const k of node.required ?? []) if (!(k in node.properties)) add(p, `required 中的 ${k} 不在 properties 内`);
    if (node.additionalProperties !== false) add(p, '带 properties 的对象必须声明 additionalProperties:false');
  } else if (node.required) add(p, 'required 没有对应的 properties');
  if (node.minItems !== undefined && node.maxItems !== undefined && node.minItems > node.maxItems) add(p, 'minItems 大于 maxItems');
  if (node.minimum !== undefined && node.maximum !== undefined && node.minimum > node.maximum) add(p, 'minimum 大于 maximum');
  if (node.type === 'integer') {
    const hi = node.maximum, lo = node.minimum;
    if ((hi !== undefined && hi > 2 ** 63) || (lo !== undefined && lo < -(2 ** 63))) add(p, '整数范围超出 i64：应使用字符串 format uint64/int128');
    else if ((hi !== undefined && hi > Number.MAX_SAFE_INTEGER) || (lo !== undefined && lo < Number.MIN_SAFE_INTEGER)) add(p, 'i64 整数字段（超出 2^53-1，Dart VM 原生 64 位可用，Web/JS 会丢精度）', 'i64');
  }
  if (node.pattern !== undefined) { try { new RegExp(node.pattern, 'u'); } catch { add(p, `pattern 无法编译: ${node.pattern}`); } }
  if (node.enum !== undefined && (!Array.isArray(node.enum) || node.enum.length === 0)) add(p, 'enum 必须是非空数组');
  if (node.format !== undefined && !FORMATS[node.format]) add(p, `未知 format ${node.format}`);
  for (const [k, v] of Object.entries(node.properties ?? {})) lintSchema(v, `${p}/properties/${k}`, add);
  for (const [k, v] of Object.entries(node.$defs ?? {})) lintSchema(v, `${p}/$defs/${k}`, add);
  if (node.items !== undefined) lintSchema(node.items, `${p}/items`, add);
  (node.prefixItems ?? []).forEach((v, i) => lintSchema(v, `${p}/prefixItems/${i}`, add));
  if (node.additionalProperties && typeof node.additionalProperties === 'object') lintSchema(node.additionalProperties, `${p}/additionalProperties`, add);
  for (const key of ['oneOf', 'anyOf', 'allOf']) (node[key] ?? []).forEach((v, i) => lintSchema(v, `${p}/${key}/${i}`, add));
}

/** 遍历所有 $ref 字符串。 */
export function collectRefs(node, out = []) {
  if (Array.isArray(node)) node.forEach(x => collectRefs(x, out));
  else if (node && typeof node === 'object') {
    if (typeof node.$ref === 'string') out.push(node.$ref);
    for (const [k, v] of Object.entries(node)) if (k !== 'examples' && k !== 'enum' && k !== 'const' && k !== 'default') collectRefs(v, out);
  }
  return out;
}

/** 收集 x-sensitive 字段路径（properties 链，数组用 *），root 为 '/body' 或 '/ok'。 */
export function sensitivePaths(node, root, out = []) {
  if (!node || typeof node !== 'object') return out;
  for (const [k, v] of Object.entries(node.properties ?? {})) {
    if (v && v['x-sensitive'] === true) out.push(`${root}/${k}`);
    sensitivePaths(v, `${root}/${k}`, out);
  }
  if (node.items && typeof node.items === 'object') sensitivePaths(node.items, `${root}/*`, out);
  return out;
}
