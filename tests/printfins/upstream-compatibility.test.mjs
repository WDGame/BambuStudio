import test from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../resources/printfins/adapter.mjs';
import { FDM_SCHEMA } from '../../resources/printfins/schema.mjs';
import { computeFins, ENGINE_DEFAULTS } from '../../resources/printfins/vendor/plugins/shared/engine/fins_entry.js';
import { fixtures } from './geometry-fixtures.mjs';

test('FDM host keeps original horizontal tines after an upstream resin call', () => {
    const positions = fixtures[0].positions;
    computeFins(Float64Array.from(positions), { tineDir: 'vertical', pinDepth: 0.7 });
    const actual = generate({ positions });
    const expected = computeFins(Float64Array.from(positions), { tineDir: 'horizontal' });
    assert.deepEqual(actual.triangles, Array.from(expected.triangles));
    assert.equal(actual.stats.pins, false);
    assert.equal(actual.settings.tineDir, 'horizontal');
    assert.equal(ENGINE_DEFAULTS.gap, 0.2);
    assert.equal(ENGINE_DEFAULTS.mode, 'auto');
    assert.ok(!FDM_SCHEMA.options.some(o => ['tineDir','pinDepth','mode'].includes(o.key)));
    assert.throws(() => generate({ positions, options: { tineDir: 'vertical' } }), /FDM/);
    for (const options of [{ mode: 'full' }, { mode: 'draw' }, { hybrid: true },
        { curvedWalls: true }, { tallRibs: false }, { longWalls: true }])
        assert.throws(() => generate({ positions, options }), /unknown dialog option/);
});
