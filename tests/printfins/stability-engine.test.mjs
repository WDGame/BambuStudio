import test from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../resources/printfins/adapter.mjs';
import { OPTIONS_SCHEMA, computeFins } from '../../resources/printfins/vendor/plugins/shared/engine/fins_entry.js';
import { fixtures, stl } from './geometry-fixtures.mjs';

for(const fixture of fixtures) test(`engine geometry: ${fixture.id}`,()=>{
    const options={...fixture.options,layerHeight:0.16,firstLayerHeight:0.2};
    const result=generate({positions:fixture.positions,options});
    const original=computeFins(Float64Array.from(fixture.positions),{...fixture.options,layerHeight:0.16});
    assert.deepEqual(result.triangles,Array.from(original.triangles));
    assert.deepEqual(result.pieces,original.pieces);
    assert.ok(result.triangles.every(Number.isFinite));
    assert.equal(result.triangles.length%9,0);
    assert.equal(result.triangles.length===0,fixture.expected==='empty');
    const covered=new Set();
    for(const piece of result.pieces) for(const [a,b] of piece.ranges) {
        assert.ok(Number.isInteger(a)&&Number.isInteger(b)&&a>=0&&a<b&&b<=result.triangles.length/9);
        for(let t=a;t<b;++t) { assert.ok(!covered.has(t)); covered.add(t); }
    }
    assert.equal(covered.size,result.triangles.length/9);
    assert.deepEqual(generate({positions:fixture.positions,options}),result,'repeat generation must not retain engine state');
    const binary=stl(fixture.positions);
    assert.equal(binary.readUInt32LE(80),fixture.positions.length/9);
    assert.equal(binary.length,84+fixture.positions.length/9*50);
});

const source=fixtures[0].positions;
for(const option of OPTIONS_SCHEMA.options.filter(o=>o.type==='number'&&!o.hostSupplied)) {
    test(`engine invalid range: ${option.key}`,()=>{
        for(const value of [option.min-option.step,option.max+option.step,NaN,Infinity,-Infinity,{},[]])
            assert.throws(()=>generate({positions:source,options:{[option.key]:value}}));
    });
}
test('engine invalid host geometry: type, size, nonfinite and triangle count',()=>{
    for(const positions of [null,{},'mesh',new Float64Array(9),[],[1],Array(9).fill(Infinity),Array(9).fill(null),Array(900009).fill(0)])
        assert.throws(()=>generate({positions}));
});
test('engine choices, booleans and slicer heights reject malformed values',()=>{
    for(const options of [{tines:1},{plateOnly:'yes'},{padStyle:'custom'},{cutout:'custom'},{layerHeight:NaN},
        {layerHeight:-1},{firstLayerHeight:Infinity},{firstLayerHeight:0},{sway:{on:true}}])
        assert.throws(()=>generate({positions:source,options}));
});
