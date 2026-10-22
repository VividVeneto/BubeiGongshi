// D.10 等级须有配套的机器复核记录与 D.12 行（CORE-76，卡 :44 接口）。
// 表头最右一个“vX.Y.Z 复核”列即当前等级列；旧列不覆盖新列。
export const reviewColumn = columns =>
  (Array.isArray(columns) ? columns : []).findLastIndex(c => /^v\d+\.\d+\.\d+ 复核$/.test(c ?? ''));

const checks = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6'];
const flag = {pass: 'P', fail: 'F', pending: '?'};
// 记录编号只认 P2-<卡号>；早期序号表等其他行整行忽略（卡 :20）。
const RECORD = /^P2-(?:CORE|AND|WIN)-\d+$/;
const D12_HEADER = ['记录', '卡', '复核人 / 日期', '复核输入字符 / 段', 'a～g', 'S1～S6', '发现、处理及调用方确认', 'conclusion'];

// 表头与数据行按 | 切分，丢弃首尾空单元格后逐格 trim。
const cells = line => {
  const out = line.split('|').map(x => x.trim());
  if (out[0] === '') out.shift();
  if (out.at(-1) === '') out.pop();
  return out;
};
// D.10 行保留首尾空串，使列下标与表头一致。
const rowCells = line => line.split('|').map(x => x.trim());

/** 解析 D.12 区块的 P2 记录；表头只用于宽度校验，字段名改名即失败（卡 :20）。 */
function d12Records(appendix, errors) {
  const records = new Map();
  const lines = appendix.split('\n');
  const start = lines.findIndex(line => /^## D\.12 /.test(line));
  if (start < 0) {
    errors.push('SADD-12: missing D.12 section');
    return records;
  }
  let end = lines.findIndex((line, index) => index > start && /^## D\.13 /.test(line));
  if (end < 0) end = lines.length;
  let width = 0, header = false;
  for (const line of lines.slice(start + 1, end)) {
    if (!line.startsWith('|') || /^\|\s*:?-{3}/.test(line)) continue;
    const row = cells(line);
    if (row[0] === '记录') {
      if (row.join(' | ') !== D12_HEADER.join(' | ')) errors.push(`SADD-12: D.12 header fields changed: ${row.join(' | ')}`);
      width = row.length; header = true;
      continue;
    }
    if (!RECORD.test(row[0] ?? '')) continue;
    if (!header) { errors.push(`SADD-12: D.12 header missing before ${row[0]}`); continue; }
    if (row.length !== width) { errors.push(`SADD-12: D.12 row width ${row.length} differs from header width ${width} for ${row[0]}`); continue; }
    if (records.has(row[0])) errors.push(`SADD-12: duplicate D.12 record ${row[0]}`);
    records.set(row[0], row);
  }
  return records;
}

/**
 * 校验 D.10 现行卡表与复核记录的一致性；返回以 "SADD-12: " 开头的错误数组，空数组为通过，不抛异常。
 * cards 为 pack.mjs load() 的卡号 → 卡对象 Map；reviews 为 reports/<v>-reviews.json 根对象。
 */
export function validateCurrent(rows, columns, cards, reviews, appendix = '') {
  const errors = [];
  try {
    if (!(cards instanceof Map)) return ['SADD-12: cards must be a Map of card ids'];
    const list = Array.isArray(rows) ? rows : [];
    const cols = Array.isArray(columns) ? columns : [];
    const gradeColumn = reviewColumn(cols), statusColumn = cols.indexOf('当前状态');
    if (gradeColumn < 0) errors.push('SADD-12: missing current review column');
    // 状态无从判断时必须失败，不能因缺列而跳过就绪证据检查（T1-F10）。
    const statusCount = cols.filter(c => c === '当前状态').length;
    if (statusCount !== 1) errors.push(`SADD-12: expected exactly one 当前状态 column, found ${statusCount}`);
    const idCount = cols.filter(c => c === '编号').length;
    if (idCount !== 1) errors.push(`SADD-12: expected exactly one 编号 column, found ${idCount}`);
    const records = appendix ? d12Records(appendix, errors) : new Map();
    if (reviews !== undefined && reviews !== null && (reviews.version !== 1 || !Array.isArray(reviews.entries))) {
      errors.push('SADD-12: invalid review root/version');
    }
    const reviewed = new Map();
    for (const review of Array.isArray(reviews?.entries) ? reviews.entries : []) {
      if (!review || typeof review !== 'object') { errors.push('SADD-12: malformed review'); continue; }
      if (reviewed.has(review.card)) errors.push(`SADD-12: duplicate review ${review.card}`);
      reviewed.set(review.card, review);
      if (!cards.has(review.card) || !['A', 'B', 'C'].includes(review.grade) ||
        typeof review.reviewer !== 'string' || !review.reviewer.trim() ||
        !/^\d{4}-\d{2}-\d{2}$/.test(review.date ?? '') ||
        !Number.isSafeInteger(review.materialChars) || review.materialChars < 0 ||
        !Number.isSafeInteger(review.segments) || review.segments < 1 ||
        !['pass', 'fail', 'pending'].includes(review.conclusion) ||
        !Array.isArray(review.blockers) || review.blockers.some(x => typeof x !== 'string' || !x.trim()) ||
        checks.some(k => !Object.hasOwn(flag, review.checks?.[k])) || review.record !== `P2-${review.card}` ||
        !(review.consumerConfirmation === null || typeof review.consumerConfirmation === 'string')) {
        errors.push(`SADD-12: malformed review ${review.card}`);
      }
      const row = records.get(review.record);
      if (!row || row[1] !== review.card || row[2] !== `${review.reviewer} / ${review.date}` ||
        row[3] !== `${review.materialChars} / ${review.segments}` ||
        row[4] !== checks.slice(0, 7).map(k => flag[review.checks?.[k]] ?? '!').join('') ||
        row[5] !== checks.slice(7).map(k => flag[review.checks?.[k]] ?? '!').join('') ||
        row[7] !== review.conclusion) {
        errors.push(`SADD-12: missing or mismatched D.12 record ${review.card}`);
      }
    }
    const seen = new Set();
    for (const row of list) {
      const line = rowCells(row), id = line[1];
      if (line.length !== cols.length) errors.push(`SADD-12: row width ${line.length} differs from header width ${cols.length} for ${id}`);
      if (seen.has(id)) errors.push(`SADD-12: duplicate current card ${id}`);
      seen.add(id);
      if (!cards.has(id)) errors.push(`SADD-12: unknown current card ${id}`);
      const grade = gradeColumn < 0 ? undefined : line[gradeColumn];
      if (gradeColumn >= 0 && !['A', 'B', 'C', '—'].includes(grade)) errors.push(`SADD-12: invalid independent grade ${id}: ${grade}`);
      const review = reviewed.get(id);
      // 每个非“—”等级都须有独立复核记录；反向不成立（占位行可带上一轮记录）。
      if (reviews && grade !== '—' && (!review || review.grade !== grade)) errors.push(`SADD-12: grade lacks matching review ${id}`);
      const status = statusColumn < 0 ? undefined : line[statusColumn];
      if (status !== undefined && /^就绪/.test(status)) {
        const isPublicContract = id.startsWith('CORE-') && [...cards.values()].some(c => c.deps?.includes(id));
        const complete = review && ['A', 'B'].includes(review.grade) && review.conclusion === 'pass' &&
          checks.every(k => review.checks?.[k] === 'pass') &&
          (!isPublicContract || Boolean(review.consumerConfirmation?.trim()));
        // 就绪字符串唯一：必须精确等于“就绪（D.12 P2-<card>）”，前缀匹配不算（卡 :44）。
        if (status !== `就绪（D.12 P2-${id}）` || !complete) errors.push(`SADD-12: ready without complete independent evidence ${id}`);
      }
    }
    for (const id of cards.keys()) if (!seen.has(id)) errors.push(`SADD-12: missing current card ${id}`);
  } catch (error) {
    errors.push(`SADD-12: validation aborted: ${error.message}`);
  }
  return errors;
}

