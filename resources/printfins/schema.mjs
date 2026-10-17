import { OPTIONS_SCHEMA } from './vendor/plugins/shared/engine/fins_entry.js';

// Host presentation only: Bambu's current integration is FDM, not resin.
export const FDM_SCHEMA = { ...OPTIONS_SCHEMA,
    options: OPTIONS_SCHEMA.options.filter(o => o.key !== 'tineDir' && o.key !== 'pinDepth') };
