import test from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../resources/printfins/adapter.mjs';
import { computeFins, ENGINE_DEFAULTS } from '../../resources/printfins/vendor/plugins/shared/engine/fins_entry.js';

// Independent closed box fixture; this is input geometry, not a support algorithm.
export function box(x0, x1, y0, y1, z0, z1) {
    const v = [[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],
        [x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]];
    return [[0,3,2,1],[4,5,6,7],[0,1,5,4],[2,3,7,6],[1,2,6,5],[0,4,7,3]]
        .flatMap(([a,b,c,d]) => [...v[a],...v[b],...v[c],...v[a],...v[c],...v[d]]);
}
const shelf = [...box(-20,20,-8,8,0,5), ...box(-20,20,-8,8,20,24), ...box(18,20,-8,8,5,20)];
const options = { padStyle: 'off', tines: false };

test('adapter returns the unchanged original computeFins output and defaults', () => {
    const native = generate({ positions: shelf });
    const original = computeFins(Float64Array.from(shelf));
    assert.ok(native.triangles.length > 0);
    assert.deepEqual(native.triangles, Array.from(original.triangles));
    assert.deepEqual(native.offset, original.offset);
    assert.deepEqual(native.pieces, original.pieces);
    assert.deepEqual(native.stats, original.stats);
    assert.equal(native.settings.gap, ENGINE_DEFAULTS.gap);
});

test('original piece ranges cover each returned triangle exactly once', () => {
    const result = generate({ positions: shelf, options });
    const covered = new Set();
    for (const piece of result.pieces) for (const [a, b] of piece.ranges) {
        assert.ok(Number.isInteger(a) && Number.isInteger(b) && a < b);
        assert.ok(a >= 0 && b <= result.triangles.length / 9);
        for (let t = a; t < b; ++t) { assert.ok(!covered.has(t)); covered.add(t); }
    }
    assert.equal(covered.size, result.triangles.length / 9);
});

test('seating offset maps original output back to a translated Bambu mesh', () => {
    const a = generate({ positions: shelf, options });
    const shift = [137.25, 88.125, 0];
    const b = generate({ positions: shelf.map((v, i) => v + shift[i % 3]), options });
    assert.deepEqual(a.triangles, b.triangles);
    for (const [i, key] of ['x', 'y', 'z'].entries())
        assert.ok(Math.abs(a.offset[key] - b.offset[key] - shift[i]) < 1e-9);
});

test('uses the original support-gap option without leaking between calls', () => {
    const a = generate({ positions: shelf, options: { ...options, gap: 0.1 } });
    const b = generate({ positions: shelf, options: { ...options, gap: 0.3 } });
    assert.notDeepEqual(a.triangles, b.triangles);
    assert.deepEqual(a.triangles, generate({ positions: shelf, options: { ...options, gap: 0.1 } }).triangles);
});

test('rejects the removed modified-project options instead of applying them', () => {
    for (const options of [{ lowerFootGap: 0.16 }, { alignLowerLayers: true },
        { material: 'pla' }, { nozzle: 0.4 }, { bodyThickness: 1 }])
        assert.throws(() => generate({ positions: shelf, options }), /unknown dialog option/);
});

test('preserves native first-layer metadata without a custom engine layer grid', () => {
    const r = generate({ positions: shelf, options: { ...options, layerHeight: 0.16, firstLayerHeight: 0.2 } });
    const original = computeFins(Float64Array.from(shelf), { ...options, layerHeight: 0.16 });
    assert.deepEqual(r.triangles, Array.from(original.triangles));
    assert.equal(r.settings.firstLayerHeight, 0.2);
});

test('rejects malformed host geometry and invalid original engine options', () => {
    for (const positions of [[], [0, 1, 2], Array(9).fill(NaN)])
        assert.throws(() => generate({ positions }));
    for (const options of [null, [], { gap: 3 }, { layerHeight: 0 }, { firstLayerHeight: 0 }])
        assert.throws(() => generate({ positions: shelf, options }));
});
