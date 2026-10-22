import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtempSync,readFileSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {validateReservations,compareActual,routeOwner} from './reservations.mjs';
const cards=new Map([['CORE-01',{}],['CORE-02',{}]]);
const row={kind:'startup',key:'10',owner:'CORE-01',point:'FeatureRegistry.startupHooks'};
const policy={version:1,entries:[row]};
const policyUrl=new URL('../../contracts/policies/shared-writes.json',import.meta.url);
const shared=()=>JSON.parse(readFileSync(policyUrl,'utf8'));
const owners=p=>new Map(p.entries.map(r=>[r.owner,{id:r.owner}]));
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
 const route=(key,owner='CORE-01',point='accountRoutes')=>({kind:'route',key,owner,point});
 const p={version:1,entries:[route('/','CORE-01','accountRoutes'),route('/study','CORE-01','studyHomeRoutes'),route('/study/books/:bookId','CORE-01','bookReminderRoutes'),route('/study/stats','CORE-02','statsRoutes'),route('/study/books/new','CORE-02','bookReminderRoutes'),route('/library','CORE-01','libraryRoutes'),route('/library/units','CORE-02','libraryToolsRoutes')]};
 assert.deepEqual(validateReservations(p,cards),[]);
 assert.equal(routeOwner(p,'/study/stats').owner,'CORE-02');
 assert.equal(routeOwner(p,'/study/books/new').owner,'CORE-02');
 assert.equal(routeOwner(p,'/study/books/abc').owner,'CORE-01');
 assert.equal(routeOwner(p,'/').key,'/');
 assert.equal(routeOwner(p,'/libraryx'),null);
 assert.ok(compareActual(p,{version:1,entries:[route('/study/stats','CORE-01','statsRoutes')]},cards).length);
 assert.deepEqual(compareActual(p,{version:1,entries:[route('/library/units/new','CORE-02','libraryToolsRoutes')]},cards),[]);
 assert.ok(validateReservations({version:1,entries:[route('/study/:a'),route('/study/:b')]},cards).length);
});

test('routeOwner returns null, not undefined, when no prefix owns a route',()=>{
 const route=(key,owner='CORE-01',point='accountRoutes')=>({kind:'route',key,owner,point});
 const p={version:1,entries:[route('/'),route('/study'),route('/study/books/:bookId')]};
 for(const key of ['/studies','/libraryx','/study2'])assert.strictEqual(routeOwner(p,key),null,key);
 assert.strictEqual(routeOwner({version:1,entries:[]},'/study'),null);
 assert.equal(typeof routeOwner(p,'/libraryx'),'object');
 assert.equal(routeOwner(p,'/study/books').key,'/study');
 assert.equal(routeOwner(p,'/study/books/42').key,'/study/books/:bookId');
});

test('production profile hooks migrate without adding process startup orders',()=>{
  const p=shared();
  const expected=[['30','CORE-99'],['50','CORE-40'],['55','CORE-101'],['60','CORE-34'],['70','CORE-46'],['80','CORE-20']];
  assert.deepEqual(p.entries.filter(r=>r.kind==='profile').map(r=>[r.key,r.owner]),expected);
  for(const [key,owner] of expected){
    assert.equal(p.entries.find(r=>r.kind==='profile' && r.key===key).point,'ProfileHooks');
    assert.equal(p.entries.some(r=>r.kind==='startup' && r.key===key),false);
  }
  assert.equal(p.entries.find(r=>r.kind==='startup' && r.key==='40').owner,'CORE-40');
});

test('profile hook orders form an independent strict registration sequence',()=>{
  const profile={kind:'profile',key:'30',owner:'CORE-02',point:'ProfileHooks'};
  const mixed={version:1,entries:[{...row,key:'30'},profile]};
  assert.deepEqual(validateReservations(mixed,cards),[]);
  assert.deepEqual(compareActual(mixed,{version:1,entries:[profile]},cards),[]);
  assert.ok(validateReservations({...mixed,entries:[profile,{...profile,owner:'CORE-01'}]},cards).length);
  for(const key of ['030','1000','-1','1.0']) assert.ok(validateReservations({version:1,entries:[{...profile,key}]},cards).length);
  assert.ok(compareActual({version:1,entries:[profile]},{version:1,entries:[{...profile,kind:'startup'}]},cards).length);
  assert.ok(compareActual(mixed,{version:1,entries:[{...profile,point:'FeatureRegistry.startupHooks'}]},cards).length);
});

test('point takes one closed form per kind and rejects every category-external spelling',()=>{
  const e=(kind,key,point,owner='CORE-01')=>({kind,key,owner,point});
  const good=[e('error','AUTH_INVALID','contracts/errors/registry.yaml'),e('file','app/lib/x.dart','app/lib/x.dart'),
    e('installer','installStudy','app/lib/composition/installers.dart'),e('installer','installWin','app/lib/composition/ports_windows.dart'),
    e('installer','installAndroid','app/lib/composition/ports_android.dart'),e('route','/account','accountRoutes'),
    e('shortcut','k','defaultKeymap'),e('shortcut','c','StudyCommand'),e('shortcut','b','StudyCommand.member'),
    e('startup','10','FeatureRegistry.startupHooks'),e('firstFrame','10','FeatureRegistry.firstFrameHooks'),
    e('settings','10','SettingsSections'),e('profile','10','ProfileHooks')];
  assert.deepEqual(validateReservations({version:1,entries:good},cards),[]);
  const bad=[e('error','AUTH_INVALID','contracts/errors/other.yaml'),e('file','app/lib/x.dart','app/lib/y.dart'),
    e('installer','installStudy','app/lib/study/install.dart'),e('installer','installX','app/lib/composition/ports.dart'),
    e('route','/account','/account'),e('route','/account','app/lib/composition/routes.dart'),e('route','/account','AccountRoutes'),
    e('shortcut','k','app/lib/windows/keymap.dart'),e('startup','10','startupHooks'),e('startup','10','featureRegistry.startupHooks'),
    e('settings','10','settings_sections'),e('profile','10','profileHooks'),e('profile','10','ProfileHook'),
    e('profile','10','FeatureRegistry.startupHooks'),e('startup','10','FeatureRegistry.startupHooks extra'),
    e('startup','10','../FeatureRegistry'),e('file','app/lib/x.dart','/app/lib/x.dart')];
  for(const bad_row of bad) assert.ok(validateReservations({version:1,entries:[bad_row]},cards).length,JSON.stringify(bad_row));
  const p=shared();
  assert.deepEqual(validateReservations(p,owners(p)),[]);
});

test('production routes keep parent and child prefixes under different owners',()=>{
  const p=shared(),owner=route=>routeOwner(p,route)?.owner;
  assert.deepEqual(validateReservations(p,owners(p)),[]);
  assert.equal(owner('/study'),'CORE-89');
  assert.equal(owner('/study/stats'),'CORE-49');
  assert.equal(owner('/study/books'),'CORE-89');
  assert.equal(owner('/study/books/new'),'CORE-90');
  assert.equal(owner('/study/books/42/edit'),'CORE-90');
  assert.equal(owner('/settings'),'CORE-47');
  assert.equal(owner('/settings/appearance'),'CORE-58');
  assert.equal(owner('/library'),'CORE-38');
  assert.equal(owner('/library/new'),'CORE-88');
  assert.equal(owner('/library/units/new'),'CORE-60');
  assert.equal(owner('/libraryx'),undefined);
  assert.equal(routeOwner(p,'/libraryx'),null);
  assert.equal(owner('/'),'CORE-63');
  assert.deepEqual(compareActual(p,{version:1,entries:[{kind:'route',key:'/study/stats',owner:'CORE-49',point:'statsRoutes'}]},owners(p)),[]);
  assert.ok(compareActual(p,{version:1,entries:[{kind:'route',key:'/study/stats',owner:'CORE-89',point:'studyHomeRoutes'}]},owners(p)).length);
  const dup={version:1,entries:[{kind:'route',key:'/study',owner:'CORE-89',point:'studyHomeRoutes'},{kind:'route',key:'/study',owner:'CORE-49',point:'statsRoutes'}]};
  assert.ok(validateReservations(dup,cards).length);
});

const cli=(args)=>spawnSync(process.execPath,['tools/sadd/reservations.mjs',...args],{encoding:'utf8'});
const scratch=(name,value)=>{
  const dir=mkdtempSync(path.join(tmpdir(),'core75-'));
  const file=path.join(dir,name);
  writeFileSync(file,typeof value==='string'?value:JSON.stringify(value));
  return file;
};
test('CLI prints one JSON verdict and exits 1 on violations, 2 on unreadable input',()=>{
  const p=shared();
  const violating={...p,entries:[...p.entries,{kind:'route',key:'/account',owner:'CORE-63',point:'/account'}]};
  const bad=cli(['--policy',scratch('policy.json',violating)]);
  assert.equal(bad.status,1,bad.stderr);
  const out=JSON.parse(bad.stdout);
  assert.deepEqual(Object.keys(out).sort(),['entries','errors','mode']);
  assert.equal(out.entries,violating.entries.length);
  assert.equal(out.mode,'design');
  assert.ok(out.errors.length&&out.errors.every(x=>/^EXT-[1-4]: /.test(x)));
  const base={version:1,entries:[{kind:'startup',key:'10',owner:'CORE-51',point:'FeatureRegistry.startupHooks'}]};
  const violations=[{...base,version:2},{...base,extra:1},
    {...base,entries:[base.entries[0],base.entries[0]]},
    {...base,entries:[{...base.entries[0],owner:'CORE-999'}]},
    {...base,entries:[{...base.entries[0],kind:'route',key:'/settings/../admin',point:'settingsRoutes'}]},
    {...base,entries:[{...base.entries[0],key:'010'}]}];
  for(const value of violations){
    const verdict=cli(['--policy',scratch('policy.json',value)]);
    assert.equal(verdict.status,1,JSON.stringify(value));
    assert.ok(JSON.parse(verdict.stdout).errors.length);
  }
  const broken=cli(['--policy',scratch('policy.json','{')]);
  assert.equal(broken.status,2);
  assert.equal(broken.stdout,'');
  assert.match(broken.stderr,/EXT-INPUT: /);
  const noReceipt=cli(['--actual','temp/P2temp/nonexistent-extensions.json']);
  assert.equal(noReceipt.status,2);
  assert.match(noReceipt.stderr,/EXT-INPUT: /);
});

test('CLI receipt mode counts registered entries and rejects changed or unallocated rows',()=>{
  const p=shared();
  const allocated=p.entries.find(r=>r.kind==='error'&&r.owner!=='CORE-02');
  const subject={kind:'route',key:'/study/stats',owner:'CORE-49',point:'statsRoutes'};
  const ok=cli(['--actual',scratch('actual.json',{version:1,entries:[allocated,subject]})]);
  assert.equal(ok.status,0,ok.stdout+ok.stderr);
  const receipt=JSON.parse(ok.stdout);
  assert.equal(receipt.mode,'implementation');
  assert.equal(receipt.entries,2);
  assert.deepEqual(receipt.errors,[]);
  for(const change of [{owner:'CORE-02'},{point:'other'}]){
    const changed=cli(['--actual',scratch('actual.json',{version:1,entries:[{...allocated,...change}]})]);
    assert.equal(changed.status,1,JSON.stringify(change));
    assert.ok(JSON.parse(changed.stdout).errors.length);
  }
  const extra=cli(['--actual',scratch('actual.json',{version:1,entries:[{kind:'route',key:'/nope',owner:'CORE-63',point:'accountRoutes'}]})]);
  assert.equal(extra.status,1);
  assert.match(JSON.parse(extra.stdout).errors.join(),/EXT-4: /);
});
