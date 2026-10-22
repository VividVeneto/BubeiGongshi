import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {tmpRoot, makeDto, makeSadd, write, defTable, mirrorTable, mirrorInline} from './fixture.mjs';
import {checkDto, uuidv5} from './dto.mjs';
import {validate, lintSchema, FORMATS} from './schema.mjs';
import {loadCards} from './lib.mjs';

const codes = r => r.errors.map(e => e.id);
const dto = root => path.join(root, 'contracts', 'dto');
const edit = (root, file, fn) => { const p = path.join(dto(root), file); const j = JSON.parse(fs.readFileSync(p, 'utf8')); fn(j); fs.writeFileSync(p, JSON.stringify(j, null, 2)); };
const fresh = () => { const root = tmpRoot(); makeDto(root); return root; };

test('合法夹具通过并统计', () => {
  const r = checkDto({root: fresh()});
  assert.deepEqual(r.errors, []);
  assert.equal(r.stats.ready, 1); assert.equal(r.stats.pending, 1); assert.equal(r.stats.examples, 1);
});

test('UUIDv5 与 RFC 4122 附录已知向量一致', () => {
  assert.equal(uuidv5('python.org', '6ba7b810-9dad-11d1-80b4-00c04fd430c8'), '886313e1-3b8a-5372-9b90-0c9aee199e5d');
});

test('manifest 规则：重复 op、pending 无原因、ready 缺 schema 文件、scope 非法、错误码未排序', () => {
  const root = fresh();
  edit(root, 'manifest.json', m => {
    m.ops.push({...m.ops[1]});                         // 重复
    m.ops[1].blocked_reason = '  ';                    // 空原因
    m.ops[0].schema = 'missing.schema.json';           // 文件不存在
    m.ops[0].scope = 'global';
    m.ops[0].error_codes = ['B_X', 'A_X'];
  });
  const c = codes(checkDto({root}));
  for (const want of ['DTO-02', 'DTO-04', 'DTO-05', 'DTO-08', 'DTO-09']) assert.ok(c.includes(want), want + ' ' + c);
});

test('sensitive_paths 必须与 x-sensitive 一致', () => {
  const root = fresh();
  edit(root, 'manifest.json', m => { m.ops[0].sensitive_paths = []; });
  assert.ok(codes(checkDto({root})).includes('DTO-12'));
});

test('示例必须满足自己的 schema（类型、必填、额外字段、格式、范围）', () => {
  const root = fresh();
  edit(root, 'demo.open.schema.json', s => { s.examples = [{request: {id: 'not-a-uuid', key: 1, extra: true}, ok: {n: 99}}]; });
  const msgs = checkDto({root}).errors.filter(e => e.id === 'DTO-14').map(e => e.msg).join('\n');
  for (const frag of ['不是合法的 uuid', '类型应为 string', '不允许的额外字段', '大于 maximum']) assert.ok(msgs.includes(frag), frag + '\n' + msgs);
});

test('schema 结构：未知关键字、缺 additionalProperties、孤儿文件、坏 $ref、required 不在 properties', () => {
  const root = fresh();
  edit(root, 'demo.open.schema.json', s => {
    s.$defs.ok.properties.n.bogus = 1;
    delete s.$defs.ok.additionalProperties;
    s.$defs.request.required.push('ghost');
    s.$defs.request.properties.id = {$ref: 'types.schema.json#/$defs/Nope'};
  });
  write(path.join(dto(root), 'orphan.schema.json'), JSON.stringify({$schema: 'https://json-schema.org/draft/2020-12/schema', title: 'OrphanSchema', $defs: {}}));
  const c = codes(checkDto({root}));
  for (const want of ['DTO-15', 'DTO-16', 'DTO-17']) assert.ok(c.includes(want), want);
  const msgs = checkDto({root}).errors.map(e => e.msg).join('\n');
  assert.ok(msgs.includes('bogus')); assert.ok(msgs.includes('additionalProperties')); assert.ok(msgs.includes('ghost'));
});

test('整数范围：超过 2^53-1 登记为 i64，超过 i64 报错', () => {
  const issues = []; lintSchema({type: 'integer', maximum: 9223372036854775807}, '/a', (p, m, l) => issues.push([l, m]));
  assert.deepEqual(issues.map(x => x[0]), ['i64']);
  const bad = []; lintSchema({type: 'integer', maximum: 1e30}, '/b', (p, m, l) => bad.push(l));
  assert.deepEqual(bad, [undefined]);
});

test('最小校验器：oneOf、prefixItems、items:false、数组长度、pattern、枚举', () => {
  const ctx = {files: new Map(), file: 'x'};
  const s = {oneOf: [{type: 'string', enum: ['a']}, {type: 'object', properties: {v: {type: 'integer'}}, required: ['v'], additionalProperties: false}]};
  assert.deepEqual(validate(s, 'a', ctx), []);
  assert.deepEqual(validate(s, {v: 1}, ctx), []);
  assert.ok(validate(s, 'b', ctx).length); assert.ok(validate(s, {v: 1.5}, ctx).length);
  const tup = {type: 'array', prefixItems: [{type: 'string'}, {type: 'integer'}], items: false, minItems: 2, maxItems: 2};
  assert.deepEqual(validate(tup, ['x', 1], ctx), []);
  assert.ok(validate(tup, ['x', 1, 2], ctx).length); assert.ok(validate(tup, ['x'], ctx).length);
  assert.ok(validate({type: 'string', pattern: '^\\d+$'}, 'ab', ctx).length);
});

test('共享 Diagnostic.code 与 CORE-02 大写命名空间规则一致', () => {
  const shared = JSON.parse(fs.readFileSync(new URL('../../contracts/dto/types.schema.json', import.meta.url), 'utf8'));
  const schema = shared.$defs.Diagnostic;
  const ctx = {files: new Map(), file: 'types.schema.json'};
  const diagnostic = code => ({code, severity: 'error', args: {}, needs_confirm: false});
  assert.equal(schema.properties.code.pattern, '^[A-Z]+(_[A-Z0-9]+)+$');
  for (const code of ['TYPE_DIM_CONFLICT', 'FFI_BAD_ARG', 'GRADE_TIMEOUT', 'TYPE_X2']) {
    assert.deepEqual(validate(schema, diagnostic(code), ctx), [], code);
  }
  for (const code of ['TYPE', 'A', 'TYPE_', 'TYPE__DIM', '_TYPE_DIM', 'TYPE_dim', 'T9_X']) {
    assert.ok(validate(schema, diagnostic(code), ctx).length, code);
  }
});

test('格式：int128 / uint64 / base64 / decimal 边界', () => {
  assert.ok(FORMATS.int128('170141183460469231731687303715884105727'));
  assert.ok(!FORMATS.int128('170141183460469231731687303715884105728'));
  assert.ok(FORMATS.uint64('18446744073709551615')); assert.ok(!FORMATS.uint64('18446744073709551616')); assert.ok(!FORMATS.uint64('-1'));
  assert.ok(FORMATS['positive-int128']('1')); assert.ok(!FORMATS['positive-int128']('0'));
  assert.ok(FORMATS.base64('QUJD')); assert.ok(!FORMATS.base64('QUJ'));
  assert.ok(FORMATS.decimal('-1.50')); assert.ok(!FORMATS.decimal('01'));
});

test('向量：幂等键按 UUIDv5 重算，被改动即失败', () => {
  const root = fresh();
  const ns = uuidv5('urn:fml:cloud', '6ba7b811-9dad-11d1-80b4-00c04fd430c8');
  const sid = '00000000-0000-4000-8000-000000000001', h = '0'.repeat(64), name = sid + ':' + h;
  const vec = {version: 1, namespace: ns, vectors: [{session_id: sid, image_hash: h, name_utf8: name, idempotency_key: uuidv5(name, ns)}]};
  write(path.join(root, 'contracts', 'vectors', 'cloud-idempotency-v1.json'), JSON.stringify(vec));
  assert.deepEqual(checkDto({root}).errors, []);
  vec.vectors[0].idempotency_key = '00000000-0000-5000-8000-000000000000';
  write(path.join(root, 'contracts', 'vectors', 'cloud-idempotency-v1.json'), JSON.stringify(vec));
  assert.ok(codes(checkDto({root})).includes('DTO-21'));
});

test('阶段字段：缺失、非法取值、与 owner 卡实施阶段不一致', () => {
  const root = fresh();
  edit(root, 'manifest.json', m => { delete m.ops[0].stage; m.ops[1].stage = 'S9'; });
  const msgs = checkDto({root}).errors.filter(e => e.id === 'DTO-22').map(e => e.msg).join('\n');
  assert.ok(msgs.includes('demo.open')); assert.ok(msgs.includes('"S9"'), msgs);

  // 取值合法但来源不符：来源是 §2 实施阶段表中的 owner 卡阶段
  const root2 = fresh();
  const cards = loadCards(makeSadd(root2));
  const stages = new Map([['CORE-05', 'S2']]);
  const bad = checkDto({root: root2, cards, stages: new Map([['CORE-05', 'S2']])}).errors.filter(e => e.id === 'DTO-23');
  assert.ok(bad.length && bad[0].msg.includes('S2'), JSON.stringify(bad));
  // owner 不在阶段表即无法核对，也要失败
  assert.ok(codes(checkDto({root: root2, cards, stages: new Map()})).includes('DTO-23'));
  // 一致时除“错误码未在卡内登记”（本夹具 SADD 无错误码表）外不再有其它错误
  assert.deepEqual(checkDto({root: root2, cards, stages: new Map([['CORE-05', 'S1']])}).errors.filter(e => e.id !== 'DTO-06'), []);
});

test('引擎快照集合：ready 必须显式布尔，且与该 op 的 ENGINE_UNAVAILABLE 双向一致；pending 不得声明', () => {
  const absent = fresh();
  edit(absent, 'manifest.json', m => { delete m.ops[0].reads_engine_snapshot; });
  assert.ok(checkDto({root: absent}).errors.some(e => e.id === 'DTO-24' && e.msg.includes('必须显式声明')));

  const noCode = fresh();
  edit(noCode, 'manifest.json', m => { m.ops[0].reads_engine_snapshot = true; });
  assert.ok(checkDto({root: noCode}).errors.some(e => e.id === 'DTO-24' && e.msg.includes('未含 ENGINE_UNAVAILABLE')));

  const noFlag = fresh();
  edit(noFlag, 'manifest.json', m => { m.ops[0].error_codes = ['DEMO_FAIL', 'ENGINE_UNAVAILABLE']; });
  assert.ok(checkDto({root: noFlag}).errors.some(e => e.id === 'DTO-24' && e.msg.includes('不为 true')));

  const pending = fresh();
  edit(pending, 'manifest.json', m => { m.ops[1].reads_engine_snapshot = false; });
  assert.ok(checkDto({root: pending}).errors.some(e => e.id === 'DTO-24' && e.msg.includes('pending 不得声明')));
});
test('DTO-26：engine.generation / engine.wait_generation 必须 reads_engine_snapshot=false（按 op 名判，CORE-100 不判）', () => {
  const root = fresh();
  edit(root, 'manifest.json', m => {
    m.ops[0].op = 'engine.generation';
    m.ops[0].reads_engine_snapshot = true;
    m.ops[0].error_codes = ['DEMO_FAIL', 'ENGINE_UNAVAILABLE'];
  });
  const errs = checkDto({root}).errors;
  assert.ok(errs.some(e => e.id === 'DTO-26' && e.msg.includes('必须为 false')), JSON.stringify(errs));
  // 布尔与错误码仍双向一致：DTO-24 不报，由 DTO-26 单独承担这条不变量
  assert.deepEqual(errs.filter(e => e.id === 'DTO-24'), []);

  const ok = fresh();
  edit(ok, 'manifest.json', m => { m.ops[0].op = 'engine.wait_generation'; });
  assert.deepEqual(checkDto({root: ok}).errors.filter(e => e.id === 'DTO-26'), []);
});

test('条目字段冻结：未知字段失败，ready 不得带 blocked_reason 以外的额外键', () => {
  const root = fresh();
  edit(root, 'manifest.json', m => { m.ops[0].stages = 'S1'; m.ops[1].snapshot = false; });
  const msgs = checkDto({root}).errors.filter(e => e.id === 'DTO-25').map(e => e.msg).join('\n');
  assert.ok(msgs.includes('stages') && msgs.includes('snapshot'), msgs);
});

test('错误集合来源：未注册、重复归属、CORE-03 信封码都失败，登记正确的码通过', () => {
  const root = fresh();
  const cards = loadCards(makeSadd(root));
  const def = (code) => `\n\n**错误码**\n\n| 错误码 | 说明 |\n| --- | --- |\n| \`${code}\` | 测试 |\n`;
  // 唯一注册且逐 op 镜像齐全时通过（DTO-06 双向比对）
  cards.get('CORE-05').body += def('DEMO_FAIL') + mirrorTable({'demo.open': ['DEMO_FAIL']});
  assert.deepEqual(checkDto({root, cards}).errors, []);
  cards.get('CORE-01').body += def('DEMO_FAIL');                 // 重复归属
  const dup = checkDto({root, cards}).errors.filter(e => e.id === 'DTO-06');
  assert.ok(dup.some(e => e.msg.includes('多张卡定义')), JSON.stringify(dup));

  const root2 = fresh();
  const cards2 = loadCards(makeSadd(root2));
  cards2.get('CORE-05').body += def('ENGINE_UNAVAILABLE');
  cards2.set('CORE-03', {id: 'CORE-03', body: def('FFI_BAD_ARG')});
  edit(root2, 'manifest.json', m => { m.ops[0].error_codes = ['ENGINE_UNAVAILABLE']; });
  const noEngine = codes(checkDto({root: root2, cards: cards2}));
  assert.ok(noEngine.includes('DTO-24'));                        // 含 ENGINE_UNAVAILABLE 却未标记快照
  edit(root2, 'manifest.json', m => { m.ops[0].error_codes = ['FFI_BAD_ARG']; });
  const envelope = codes(checkDto({root: root2, cards: cards2}));
  assert.ok(envelope.includes('DTO-18'));                        // CORE-03 信封码混入业务错误集合
  edit(root2, 'manifest.json', m => { m.ops[0].error_codes = ['NOPE_UNREGISTERED']; });
  assert.ok(checkDto({root: root2, cards: cards2}).errors.some(e => e.id === 'DTO-06' && e.msg.includes('未注册')));
});

test('DTO-06 双向比对：卡行与 error_codes 任一侧缺码都失败', () => {
  const root = fresh();
  const cards = loadCards(makeSadd(root, {extra05: defTable(['DEMO_FAIL', 'DEMO_OTHER'])}));
  cards.get('CORE-05').body += mirrorTable({'demo.open': ['DEMO_FAIL']});
  assert.deepEqual(checkDto({root, cards}).errors, []);                    // 两侧一致时通过

  edit(root, 'manifest.json', m => { m.ops[0].error_codes = ['DEMO_FAIL', 'DEMO_OTHER']; });
  const onlyManifest = checkDto({root, cards}).errors.filter(e => e.id === 'DTO-06');
  assert.ok(onlyManifest.some(e => e.msg.includes('error_codes 有码但所有者卡 CORE-05 的逐 op 镜像没有：DEMO_OTHER')), JSON.stringify(onlyManifest));

  edit(root, 'manifest.json', m => { m.ops[0].error_codes = ['DEMO_FAIL']; });
  cards.get('CORE-05').body = cards.get('CORE-05').body.replace('| `demo.open` | DEMO_FAIL |', '| `demo.open` | DEMO_FAIL、DEMO_OTHER |');
  const onlyCard = checkDto({root, cards}).errors.filter(e => e.id === 'DTO-06');
  assert.ok(onlyCard.some(e => e.msg.includes('镜像有码但 error_codes 没有：DEMO_OTHER')), JSON.stringify(onlyCard));
});

test('DTO-06：ready op 必须有所有者卡的逐 op 镜像，pending 不要求；镜像写在非所有者卡失败', () => {
  const root = fresh();
  const cards = loadCards(makeSadd(root, {extra05: defTable('DEMO_FAIL')}));
  const bare = checkDto({root, cards}).errors.filter(e => e.id === 'DTO-06');
  assert.ok(bare.some(e => e.msg.includes('所有者 CORE-05 的卡没有 demo.open 的逐 op 错误镜像')), JSON.stringify(bare));
  assert.ok(!bare.some(e => e.msg.includes('demo.later')), 'pending 无逐 op 契约，不应报错');

  const root2 = fresh();
  const cards2 = loadCards(makeSadd(root2, {extra05: defTable('DEMO_FAIL')}));
  cards2.get('CORE-01').body += mirrorTable({'demo.open': ['DEMO_FAIL']});   // 写在了非所有者卡
  const wrongCard = checkDto({root: root2, cards: cards2}).errors.filter(e => e.id === 'DTO-06');
  assert.ok(wrongCard.some(e => e.msg.includes('逐 op 错误镜像写在 CORE-01，应由 op 所有者 CORE-05')), JSON.stringify(wrongCard));
});

test('DTO-06：内联句也是对照源；ENGINE_UNAVAILABLE 与 CORE-03 信封码不算差集', () => {
  const root = fresh();
  const cards = loadCards(makeSadd(root, {extra05: defTable(['DEMO_FAIL', 'ENGINE_UNAVAILABLE'])}));
  // 内联句：只列 DEMO_FAIL；信封码写在说明段之后（不被当作镜像）
  cards.get('CORE-05').body += mirrorInline({'demo.open': ['DEMO_FAIL']});
  edit(root, 'manifest.json', m => { m.ops[0].reads_engine_snapshot = true; m.ops[0].error_codes = ['DEMO_FAIL', 'ENGINE_UNAVAILABLE']; });
  assert.deepEqual(checkDto({root, cards}).errors.filter(e => e.id.startsWith('DTO-06')), []);   // ENGINE_UNAVAILABLE 由 DTO-24 管

  const root2 = fresh();
  const cards2 = loadCards(makeSadd(root2, {extra05: defTable('DEMO_FAIL')}));
  cards2.set('CORE-03', {id: 'CORE-03', body: '\n\n**错误码**\n\n| 错误码 | 说明 |\n| --- | --- |\n| `FFI_BAD_ARG` | 测试 |\n'});
  cards2.get('CORE-05').body += mirrorTable({'demo.open': ['DEMO_FAIL', 'FFI_BAD_ARG']});
  assert.deepEqual(checkDto({root: root2, cards: cards2}).errors.filter(e => e.id === 'DTO-06'), []);   // CORE-03 码由 DTO-18 管
});
