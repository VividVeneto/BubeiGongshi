// D.10 is a keyed inventory: matching row counts alone cannot prove coverage.
export function validateCurrent(rows, columns, cards) {
  const errors = [];
  const seen = new Set();
  const gradeColumn = columns.indexOf('v5.3.2 复核');
  for (const row of rows) {
    const cells = row.split('|').map(x => x.trim());
    const id = cells[1];
    if (seen.has(id)) errors.push(`SADD-12: duplicate current card ${id}`);
    seen.add(id);
    if (!cards.has(id)) errors.push(`SADD-12: unknown current card ${id}`);
    if (gradeColumn >= 0 && !['A', 'B', 'C', '—'].includes(cells[gradeColumn])) {
      errors.push(`SADD-12: invalid independent grade ${id}: ${cells[gradeColumn]}`);
    }
  }
  for (const id of cards.keys()) if (!seen.has(id)) errors.push(`SADD-12: missing current card ${id}`);
  return errors;
}
