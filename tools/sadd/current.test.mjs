import test from 'node:test';
import assert from 'node:assert/strict';
import {validateCurrent} from './current.mjs';

const cards = new Map([['CORE-01', {}], ['CORE-02', {}]]);
const columns = ['', '编号', 'v5.3.2 复核', '当前状态', ''];
test('same-sized unknown, duplicate and missing inventories fail', () => {
  const errors = validateCurrent(['| CORE-01 | A | 待复核 |', '| CORE-999 | B | 待复核 |'], columns, cards);
  assert.ok(errors.some(x => x.includes('unknown current card CORE-999')));
  assert.ok(errors.some(x => x.includes('missing current card CORE-02')));
  assert.ok(validateCurrent(['| CORE-01 | A | 待复核 |', '| CORE-01 | A | 待复核 |'], columns, cards)
    .some(x => x.includes('duplicate current card')));
});
test('only independent grades and the explicit unreviewed marker are valid', () => {
  assert.deepEqual(validateCurrent(['| CORE-01 | A | 待复核 |', '| CORE-02 | — | 待复核 |'], columns, cards), []);
  assert.ok(validateCurrent(['| CORE-01 | PASS | 待复核 |', '| CORE-02 | C | 待复核 |'], columns, cards)
    .some(x => x.includes('invalid independent grade')));
});

test('latest grade and exact D.12 record gate every ready spelling',()=>{
  const columns=['','编号','v5.3.2 复核','v5.3.3 复核','当前状态',''];
  const rows=['| CORE-01 | C | A | 就绪（D.12 P2-CORE-01） |','| CORE-02 | C | B | 待复核 |'];
  const keys=['a','b','c','d','e','f','g','S1','S2','S3','S4','S5','S6'];
  const entry=card=>({record:'P2-'+card,card,grade:card==='CORE-01'?'A':'B',reviewer:'independent-fixture',date:'2026-10-20',materialChars:123,segments:1,checks:Object.fromEntries(keys.map(k=>[k,'pass'])),conclusion:'pass',blockers:[],consumerConfirmation:'consumer-fixture'});
  const evidence={version:1,entries:[entry('CORE-01'),entry('CORE-02')]};
  const appendix='## D.12 复核\n'+evidence.entries.map(r=>'| '+r.record+' | '+r.card+' | '+r.reviewer+' / '+r.date+' | 123 / 1 | PPPPPPP | PPPPPP | fixture | pass |').join('\n')+'\n## D.13 历史';
  const graph=new Map([['CORE-01',{}],['CORE-02',{deps:['CORE-01']}] ]);
  assert.deepEqual(validateCurrent(rows,columns,graph,evidence,appendix),[]);
  assert.ok(validateCurrent(rows,columns,graph).some(e=>e.includes('ready without')));
  for(const mutation of [r=>r.checks.S2='pending',r=>r.conclusion='fail',r=>r.consumerConfirmation=null,r=>r.grade='C',r=>r.record='nonexistent']){
    const changed=structuredClone(evidence);mutation(changed.entries[0]);
    assert.ok(validateCurrent(rows,columns,graph,changed,appendix).length);
  }
  assert.ok(validateCurrent(rows,columns,graph,{...evidence,version:999},appendix).some(e=>e.includes('root/version')));
  assert.ok(validateCurrent(rows,columns,graph,evidence,appendix.replace('PPPPPPP','PFFFFFF')).some(e=>e.includes('mismatched D.12')));
  assert.ok(validateCurrent(rows,columns,graph,evidence,'').some(e=>e.includes('D.12 record')));
  for(const status of ['就绪','就绪（D.12 nonexistent）','就绪 - 检查通过']){
    assert.ok(validateCurrent([rows[0].replace('就绪（D.12 P2-CORE-01）',status),rows[1]],columns,graph,evidence,appendix).some(e=>e.includes('ready without')));
  }
  assert.ok(validateCurrent(rows,columns,graph,{version:1,entries:[evidence.entries[0]]},appendix).some(e=>e.includes('grade lacks')));
});

test('status header drift or malformed rows cannot bypass ready evidence checks',()=>{
  const ok=['','编号','v5.3.3 复核','当前状态',''];
  const rows=['| CORE-01 | A | 就绪 |','| CORE-02 | — | 待复核 |'];
  // Baseline: bare ready must be rejected.
  assert.ok(validateCurrent(rows,ok,cards).some(e=>e.includes('ready without')));
  // Renamed, missing and duplicated status headers fail instead of silently skipping the ready check.
  assert.ok(validateCurrent(rows,['','编号','v5.3.3 复核','状态',''],cards).some(e=>e.includes('exactly one 当前状态')));
  assert.ok(validateCurrent(rows,['','编号','v5.3.3 复核',''],cards).some(e=>e.includes('exactly one 当前状态')));
  assert.ok(validateCurrent(rows,['','编号','v5.3.3 复核','当前状态','当前状态',''],cards).some(e=>e.includes('exactly one 当前状态')));
  // Missing or duplicated id header.
  assert.ok(validateCurrent(rows,['','卡号','v5.3.3 复核','当前状态',''],cards).some(e=>e.includes('exactly one 编号')));
  // A row narrower or wider than the header is a malformed table, not a silently shifted status.
  assert.ok(validateCurrent(['| CORE-01 | A |','| CORE-02 | — | 待复核 |'],ok,cards).some(e=>e.includes('row width')));
  assert.ok(validateCurrent(['| CORE-01 | A | 待复核 | x |','| CORE-02 | — | 待复核 |'],ok,cards).some(e=>e.includes('row width')));
});
