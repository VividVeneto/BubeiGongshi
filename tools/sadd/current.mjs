// D.10 is a keyed inventory: matching row counts alone cannot prove coverage.
export const reviewColumn = columns => columns.findLastIndex(c => /^v\d+\.\d+\.\d+ 复核$/.test(c));
export function validateCurrent(rows, columns, cards, reviews) {
  const errors = [];
  const seen = new Set();
  const gradeColumn = reviewColumn(columns);
  const statusColumn=columns.indexOf('当前状态');
  const reviewed=new Map();
  const checks=['a','b','c','d','e','f','g','S1','S2','S3','S4','S5','S6'];
  for(const r of reviews?.entries??[]) {
    if(reviewed.has(r.card))errors.push(`SADD-12: duplicate review ${r.card}`);
    reviewed.set(r.card,r);
    if(!cards.has(r.card) || !['A','B','C'].includes(r.grade) || !r.reviewer || !/^\d{4}-\d{2}-\d{2}$/.test(r.date??'') ||
      !Number.isSafeInteger(r.materialChars) || r.materialChars<0 || !Number.isSafeInteger(r.segments) || r.segments<1 ||
      !['pass','fail','pending'].includes(r.conclusion) || !Array.isArray(r.blockers) ||
      checks.some(k=>!['pass','fail','pending'].includes(r.checks?.[k]))) errors.push(`SADD-12: malformed review ${r.card}`);
  }
  for (const row of rows) {
    const cells = row.split('|').map(x => x.trim());
    const id = cells[1];
    if (seen.has(id)) errors.push(`SADD-12: duplicate current card ${id}`);
    seen.add(id);
    if (!cards.has(id)) errors.push(`SADD-12: unknown current card ${id}`);
    if (gradeColumn >= 0 && !['A', 'B', 'C', '—'].includes(cells[gradeColumn])) {
      errors.push(`SADD-12: invalid independent grade ${id}: ${cells[gradeColumn]}`);
    }
    const review=reviewed.get(id);
    if(reviews && cells[gradeColumn]!=='—' && (!review || review.grade!==cells[gradeColumn]))errors.push(`SADD-12: grade lacks matching review ${id}`);
    if(statusColumn>=0 && /^就绪（/.test(cells[statusColumn])) {
      const publicContract=id.startsWith('CORE-') && [...cards.values()].some(c=>c.deps?.includes(id));
      if(!review || !['A','B'].includes(review.grade) || review.conclusion!=='pass' ||
        checks.some(k=>review.checks?.[k]!=='pass') || (publicContract && !review.consumerConfirmation))errors.push(`SADD-12: ready without complete independent evidence ${id}`);
    }
  }
  for (const id of cards.keys()) if (!seen.has(id)) errors.push(`SADD-12: missing current card ${id}`);
  return errors;
}
