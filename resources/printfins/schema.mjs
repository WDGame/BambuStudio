import { OPTIONS_SCHEMA, optionsFromDialog } from './vendor/plugins/shared/engine/fins_entry.js';

// Host control for the existing computeFins mode; not an upstream dialog option.
export const GENERATION_MODE = { key: 'mode', section: 'setup', type: 'choice', default: 'auto',
    label: 'Generation mode', choices: [{ value: 'auto', label: 'Auto' }, { value: 'full', label: 'Full Coverage' }],
    tooltip: 'Auto places fins automatically. Full Coverage adds original fill walls under overhangs left by Auto. Wide-face coverage controls density separately.' };

export function optionsFromSettings({ mode = 'auto', ...values } = {}) {
    if (mode !== 'auto' && mode !== 'full') throw new Error('Invalid PrintFins generation mode');
    // Never pass the host-only key to upstream optionsFromDialog().
    return { ...optionsFromDialog(values), mode };
}

// Host presentation only: Bambu's current integration is FDM, not resin.
export const FDM_SCHEMA = { ...OPTIONS_SCHEMA,
    options: [GENERATION_MODE, ...OPTIONS_SCHEMA.options.filter(o => o.key !== 'tineDir' && o.key !== 'pinDepth')] };
