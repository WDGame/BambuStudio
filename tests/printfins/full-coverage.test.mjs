import test from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../resources/printfins/adapter.mjs';
import { optionsFromSettings, GENERATION_MODE } from '../../resources/printfins/schema.mjs';
import { computeFins, optionsFromDialog } from '../../resources/printfins/vendor/plugins/shared/engine/fins_entry.js';
import { fixtures, fullCoverageSwayFixture } from './geometry-fixtures.mjs';

test('host mode is stripped before upstream dialog validation, only Auto and Full are accepted', () => {
    assert.equal(GENERATION_MODE.default, 'auto');
    assert.throws(() => optionsFromDialog({ mode: 'full' }), /unknown dialog option/);
    assert.deepEqual(optionsFromSettings({ mode: 'full', coverage: 0.75 }), { mode: 'full', coverage: 0.75 });
    for (const mode of ['', null, false, 1, {}, [], 'Auto', 'FULL', 'draw', 'hybrid'])
        assert.throws(() => generate({ positions: fixtures[0].positions, options: { mode } }), /generation mode/);
    assert.throws(() => optionsFromSettings({ mode: 'full', longWalls: false }), /unknown dialog option/);
});

test('both modes match the original engine, preserve Auto across calls and cover every triangle exactly once', () => {
    for (const fixture of [...fixtures, fullCoverageSwayFixture]) {
        const automatic = generate(fixture);
        assert.equal(automatic.settings.mode, 'auto');
        for (const mode of ['auto', 'full']) {
            const options = { ...fixture.options, mode };
            const actual = generate({ positions: fixture.positions, options });
            // Native dialog keys are dotted; computeFins takes a nested sway object.
            const original = computeFins(Float64Array.from(fixture.positions), { ...optionsFromDialog(fixture.options), mode });
            assert.deepEqual(actual.triangles, Array.from(original.triangles), fixture.id);
            assert.deepEqual(actual.pieces, original.pieces);
            assert.deepEqual(actual.offset, original.offset);
            assert.deepEqual(actual.stats, original.stats);
            assert.ok(actual.triangles.every(Number.isFinite));
            const used = new Set();
            for (const piece of actual.pieces) for (const [a,b] of piece.ranges) {
                assert.ok(Number.isInteger(a) && Number.isInteger(b) && a >= 0 && a < b && b <= actual.triangles.length / 9);
                for (let t = a; t < b; t++) { assert.ok(!used.has(t)); used.add(t); }
            }
            assert.equal(used.size, actual.triangles.length / 9);
            if (mode === 'auto') assert.deepEqual(actual.triangles, automatic.triangles);
        }
        assert.deepEqual(generate(fixture).triangles, automatic.triangles);
    }
});

test('Full Coverage adds original fill walls on the shelf without changing density', () => {
    const shelf = fixtures.find(f => f.id === 'shelf');
    const auto = generate(shelf);
    const full = generate({ ...shelf, options: { ...shelf.options, mode: 'full' } });
    assert.ok(full.pieces.length > auto.pieces.length);
    assert.ok(full.triangles.length > auto.triangles.length);
    assert.equal(full.settings.coverage, auto.settings.coverage);
});

test('Full Coverage fill walls and Sway braces remain separate original model pieces', () => {
    const auto = generate(fullCoverageSwayFixture);
    const full = generate({ ...fullCoverageSwayFixture, options: { ...fullCoverageSwayFixture.options, mode: 'full' } });
    assert.ok(full.pieces.filter(p => p.kind === 'prop').length > auto.pieces.filter(p => p.kind === 'prop').length);
    assert.equal(full.stats.swayBraces, 2);
    assert.equal(full.pieces.filter(p => p.kind === 'sway').length, full.stats.swayBraces);
    assert.equal(new Set(full.pieces.map(p => p.id)).size, full.pieces.length);
});
