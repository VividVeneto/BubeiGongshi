import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {validateReservations,compareActual,routeOwner} from './reservations.mjs';
const cards=new Map([['CORE-01',{}],['CORE-02',{}]]);
const row={kind:'startup',key:'10',owner:'CORE-01',point:'FeatureRegistry.startupHooks'};
const policy={version:1,entries:[row]};
test('reject duplicate allocation, malformed fields and unknown owners',()=>{
  assert.deepEqual(validateReservations(policy,cards),[]);
  for(const changed of [{...policy,version:2},{...policy,unknown:1},{...policy,entries:[row,row]},
    {...policy,entries:[{...row,owner:'CORE-999'}]},{...policy,entries:[{...row,key:'010'}]},
    {...policy,entries:[{...row,kind:'route',key:'/settings/../admin'}]},
    {...policy,entries:[{...row,extra:true}]}])assert.ok(validateReservations(changed,cards).length);
});
test('actual subset is valid while wrong owner, point and new keys fail',()=>{
  assert.deepEqual(compareActual(policy,{version:1,entries:[]},cards),[]);
  assert.deepEqual(compareActual(policy,policy,cards),[]);
  for(const change of [{owner:'CORE-02'},{point:'other'},{key:'20'}])assert.ok(compareActual(policy,{version:1,entries:[{...row,...change}]},cards).length);
});
test('CLI distinguishes design success and input error',()=>{
  const design=spawnSync(process.execPath,['tools/sadd/reservations.mjs'],{encoding:'utf8'});
  assert.equal(design.status,0,design.stdout+design.stderr);
  assert.equal(JSON.parse(design.stdout).mode,'design');
  const missing=spawnSync(process.execPath,['tools/sadd/reservations.mjs','--policy','temp/P2temp/nonexistent-reservation.json'],{encoding:'utf8'});
  assert.equal(missing.status,2);
});

test('root and parameter paths use longest whole-segment ownership',()=>{
 const route=(key,owner='CORE-01')=>({kind:'route',key,owner,point:'routes'});
 const p={version:1,entries:[route('/'),route('/study'),route('/study/books/:bookId'),route('/study/stats','CORE-02'),route('/study/books/new','CORE-02'),route('/library'),route('/library/units','CORE-02')]};
 assert.deepEqual(validateReservations(p,cards),[]);
 assert.equal(routeOwner(p,'/study/stats').owner,'CORE-02');
 assert.equal(routeOwner(p,'/study/books/new').owner,'CORE-02');
 assert.equal(routeOwner(p,'/study/books/abc').owner,'CORE-01');
 assert.equal(routeOwner(p,'/').key,'/');
 assert.equal(routeOwner(p,'/libraryx'),undefined);
 assert.ok(compareActual(p,{version:1,entries:[route('/study/stats','CORE-01')]},cards).length);
 assert.deepEqual(compareActual(p,{version:1,entries:[route('/library/units/new','CORE-02')]},cards),[]);
 assert.ok(validateReservations({version:1,entries:[route('/study/:a'),route('/study/:b')]},cards).length);
});
