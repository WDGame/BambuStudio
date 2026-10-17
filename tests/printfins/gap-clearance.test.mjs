import test from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../resources/printfins/adapter.mjs';
import { computeFins, optionsFromDialog } from '../../resources/printfins/vendor/plugins/shared/engine/fins_entry.js';
import { fixtures } from './geometry-fixtures.mjs';

const shelf = fixtures.find(f => f.id === 'shelf');

for (const gap of [0.04, 1.00]) test(`gap ${gap}: original validators reject the requested extension`, () => {
    const options = { ...shelf.options, gap };
    assert.throws(() => optionsFromDialog(options), /gap must be 0.1\.\.0.4/);
    assert.throws(() => computeFins(shelf.positions, options), /gap must be 0.1\.\.0.4/);
    assert.throws(() => generate({ positions: shelf.positions, options }), /gap must be 0.1\.\.0.4/);
    // This is a confirmed conflict, not successful geometry generation at this gap.
});

test('real original engine: measure shelf clearance at 0.10, 0.20 and 0.40 mm', t => {
    // Horizontal shelf underside is z=20. No tines or bed pad: the wall's top
    // surface gives the vertical air gap without intentional grip contacts.
    const measured = [];
    for (const gap of [0.10, 0.20, 0.40]) {
        const result = generate({ positions: shelf.positions, options: { ...shelf.options, gap } });
        assert.ok(result.triangles.length > 0);
        assert.ok(result.pieces.every(p => p.kind !== 'pad' && p.kind !== 'sway'));
        let highest = -Infinity;
        for (let i = 2; i < result.triangles.length; i += 3)
            highest = Math.max(highest, result.triangles[i] - result.offset.z);
        const clearance = 20 - highest;
        assert.ok(Math.abs(clearance - gap) < 0.00001, `${gap}: measured ${clearance}`);
        measured.push(clearance);
        t.diagnostic(JSON.stringify({ requested_mm: gap, measured_mm: clearance, triangles: result.triangles.length / 9 }));
    }
    assert.ok(measured[0] < measured[1] && measured[1] < measured[2]);
});
