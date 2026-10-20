import test from 'node:test';
import assert from 'node:assert/strict';
import {pack, load, blocks} from './pack.mjs';

test('fences and tables remain atomic', () => {
  const input='```rust\nstruct A {\n\n x: u8\n}\n```\n\n| a | b |\n| - | - |\n| 1 | 2 |\n';
  const result=blocks(input);
  assert.equal(result.length,2); assert.match(result[0],/x: u8/); assert.match(result[1],/1 \| 2/);
});
test('all cards retain full direct contracts and target, bounded segments lose no text', () => {
  const cards=load();
  for(const [id,card] of cards) {
    const result=pack(id);
    assert.ok(result.text.includes(card.body.trim()),id+' target');
    for(const dep of card.deps) assert.ok(result.text.includes(cards.get(dep).contract.trim()),id+' -> '+dep);
    for(const segment of result.chunks) assert.ok([...segment].length<=80000,id+' segment');
    assert.equal(result.chunks.join('').replace(/\s/g,''),result.text.replace(/\s/g,''),id+' lossless');
  }
});
test('unknown cards and paths outside workspace are rejected', () => {
  assert.throws(()=>pack('CORE-999'),/Unknown card/);
  assert.throws(()=>pack('CORE-01',{extra:['../outside.txt']}),/outside workspace/);
});
