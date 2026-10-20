import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {tmpRoot, makeDto, write} from './fixture.mjs';
import {checkDto, uuidv5} from './dto.mjs';
import {validate, lintSchema, FORMATS} from './schema.mjs';

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
