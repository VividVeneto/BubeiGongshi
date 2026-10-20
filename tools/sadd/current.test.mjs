import test from 'node:test';
import assert from 'node:assert/strict';
import {validateCurrent} from './current.mjs';

const cards = new Map([['CORE-01', {}], ['CORE-02', {}]]);
const columns = ['', '编号', 'v5.3.2 复核', ''];
test('same-sized unknown, duplicate and missing inventories fail', () => {
  const errors = validateCurrent(['| CORE-01 | A |', '| CORE-999 | B |'], columns, cards);
  assert.ok(errors.some(x => x.includes('unknown current card CORE-999')));
  assert.ok(errors.some(x => x.includes('missing current card CORE-02')));
  assert.ok(validateCurrent(['| CORE-01 | A |', '| CORE-01 | A |'], columns, cards)
    .some(x => x.includes('duplicate current card')));
});
test('only independent grades and the explicit unreviewed marker are valid', () => {
  assert.deepEqual(validateCurrent(['| CORE-01 | A |', '| CORE-02 | — |'], columns, cards), []);
  assert.ok(validateCurrent(['| CORE-01 | PASS |', '| CORE-02 | C |'], columns, cards)
    .some(x => x.includes('invalid independent grade')));
});
