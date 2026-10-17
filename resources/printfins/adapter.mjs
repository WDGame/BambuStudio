// Host transport only: geometry and defaults belong to the unchanged upstream engine.
import { computeFins, optionsFromDialog, ENGINE_DEFAULTS } from './vendor/plugins/shared/engine/fins_entry.js';

export function generate({ positions, options = {} }) {
    if (!Array.isArray(positions) || !positions.length || positions.length % 9 ||
        positions.length > 900000 || !positions.every(Number.isFinite))
        throw new Error('PoC requires 1..100000 finite input triangles');
    if (!options || typeof options !== 'object' || Array.isArray(options))
        throw new Error('PoC options must be an object');
    if (options.tineDir !== undefined && options.tineDir !== 'horizontal')
        throw new Error('Bambu Studio PrintFins supports horizontal FDM tines only');
    // Native contour checks use the actual first-layer plane. Upstream only
    // accepts the regular layer height; no custom layer-grid algorithm is added.
    const { firstLayerHeight, ...values } = options;
    const engineOptions = optionsFromDialog(values);
    const layerHeight = engineOptions.layerHeight ?? ENGINE_DEFAULTS.layerHeight;
    const first = firstLayerHeight ?? layerHeight;
    if (!Number.isFinite(first) || first <= 0)
        throw new Error('PoC requires a positive finite first-layer height');
    const result = computeFins(Float64Array.from(positions), engineOptions);
    return { triangles: Array.from(result.triangles), offset: result.offset,
        pieces: result.pieces, stats: result.stats,
        settings: { ...ENGINE_DEFAULTS, ...engineOptions, firstLayerHeight: first } };
}
