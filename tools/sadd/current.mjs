// D.10 grades require matching machine evidence and a D.12 record.
export const reviewColumn = columns => columns.findLastIndex(c => /^v\d+\.\d+\.\d+ 复核$/.test(c));
const checks=['a','b','c','d','e','f','g','S1','S2','S3','S4','S5','S6'];
const flag={pass:'P',fail:'F',pending:'?'};
export function validateCurrent(rows, columns, cards, reviews, appendix='') {
  const errors=[],seen=new Set(),reviewed=new Map();
  const gradeColumn=reviewColumn(columns),statusColumn=columns.indexOf('当前状态');
  if(gradeColumn<0)errors.push('SADD-12: missing current review column');
  const statusCount=columns.filter(c=>c==='当前状态').length;
  if(statusCount!==1)errors.push(`SADD-12: expected exactly one 当前状态 column, found ${statusCount}`);
  const idCount=columns.filter(c=>c==='编号').length;
  if(idCount!==1)errors.push(`SADD-12: expected exactly one 编号 column, found ${idCount}`);
  const records=new Map();
  const section=appendix.split('## D.12 ')[1]?.split('## D.13 ')[0]??'';
  for(const line of section.split('\n')) {
    const cells=line.split('|').map(x=>x.trim());
    if(!/^P2-(?:CORE|AND|WIN)-\d+$/.test(cells[1]??''))continue;
    if(records.has(cells[1]))errors.push(`SADD-12: duplicate D.12 record ${cells[1]}`);
    records.set(cells[1],cells);
  }
  if(reviews && (reviews.version!==1 || !Array.isArray(reviews.entries)))errors.push('SADD-12: invalid review root/version');
  for(const r of Array.isArray(reviews?.entries)?reviews.entries:[]) {
    if(!r || typeof r!=='object'){errors.push('SADD-12: malformed review');continue;}
    if(reviewed.has(r.card))errors.push(`SADD-12: duplicate review ${r.card}`);
    reviewed.set(r.card,r);
    if(!cards.has(r.card) || !['A','B','C'].includes(r.grade) || typeof r.reviewer!=='string' || !r.reviewer.trim() ||
      !/^\d{4}-\d{2}-\d{2}$/.test(r.date??'') || !Number.isSafeInteger(r.materialChars) || r.materialChars<0 ||
      !Number.isSafeInteger(r.segments) || r.segments<1 || !['pass','fail','pending'].includes(r.conclusion) ||
      !Array.isArray(r.blockers) || r.blockers.some(x=>typeof x!=='string'||!x.trim()) ||
      checks.some(k=>!Object.hasOwn(flag,r.checks?.[k])) || r.record!==`P2-${r.card}` ||
      !(r.consumerConfirmation===null || typeof r.consumerConfirmation==='string'))errors.push(`SADD-12: malformed review ${r.card}`);
    const cells=records.get(r.record);
    if(!cells || cells[2]!==r.card || cells[3]!==`${r.reviewer} / ${r.date}` ||
      cells[4]!==`${r.materialChars} / ${r.segments}` || cells[5]!==checks.slice(0,7).map(k=>flag[r.checks?.[k]]??'!').join('') ||
      cells[6]!==checks.slice(7).map(k=>flag[r.checks?.[k]]??'!').join('') || cells[8]!==r.conclusion)errors.push(`SADD-12: missing or mismatched D.12 record ${r.card}`);
  }
  for(const row of rows) {
    const cells=row.split('|').map(x=>x.trim()),id=cells[1];
    if(statusColumn>=0 && cells.length!==columns.length)errors.push(`SADD-12: row width ${cells.length} differs from header width ${columns.length} for ${id}`);
    if(seen.has(id))errors.push(`SADD-12: duplicate current card ${id}`);
    seen.add(id);
    if(!cards.has(id))errors.push(`SADD-12: unknown current card ${id}`);
    if(gradeColumn>=0 && !['A','B','C','—'].includes(cells[gradeColumn]))errors.push(`SADD-12: invalid independent grade ${id}: ${cells[gradeColumn]}`);
    const review=reviewed.get(id);
    if(reviews && cells[gradeColumn]!=='—' && (!review || review.grade!==cells[gradeColumn]))errors.push(`SADD-12: grade lacks matching review ${id}`);
    if(statusColumn>=0 && /^就绪/.test(cells[statusColumn])) {
      const publicContract=id.startsWith('CORE-') && [...cards.values()].some(c=>c.deps?.includes(id));
      if(!review || cells[statusColumn]!==`就绪（D.12 ${review.record}）` || !['A','B'].includes(review.grade) ||
        review.conclusion!=='pass' || checks.some(k=>review.checks?.[k]!=='pass') ||
        (publicContract && !review.consumerConfirmation?.trim()))errors.push(`SADD-12: ready without complete independent evidence ${id}`);
    }
  }
  for(const id of cards.keys())if(!seen.has(id))errors.push(`SADD-12: missing current card ${id}`);
  return errors;
}
