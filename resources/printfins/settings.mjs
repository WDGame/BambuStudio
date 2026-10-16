import { OPTIONS_SCHEMA, optionVisible, optionsFromDialog } from './vendor/plugins/shared/engine/fins_entry.js';

// Only host presentation and unit conversion; defaults, validation and visibility
// remain owned by the original schema and its entry point.
export function buildSettings(form, document) {
    const controls = new Map();
    const rows = new Map();
    for (const section of OPTIONS_SCHEMA.sections) {
        const fieldset = document.createElement('fieldset');
        const legend = document.createElement('legend');
        legend.textContent = section.label;
        fieldset.append(legend);
        for (const option of OPTIONS_SCHEMA.options.filter(o => o.section === section.id && o.hostSupplied !== 'slicer')) {
            const row = document.createElement('label');
            row.className = 'option';
            row.title = option.tooltip || '';
            const caption = document.createElement('span');
            caption.textContent = `${option.label}${option.hint ? ` (${option.hint})` : ''}`;
            const control = document.createElement(option.type === 'choice' ? 'select' : 'input');
            control.id = option.key;
            control.name = option.key;
            if (option.type === 'bool') {
                control.type = 'checkbox';
                control.checked = option.default;
            } else if (option.type === 'choice') {
                for (const choice of option.choices) {
                    const item = document.createElement('option');
                    item.value = choice.value;
                    item.textContent = choice.label;
                    control.append(item);
                }
                control.value = option.default;
            } else {
                const scale = option.percent ? 100 : 1;
                control.type = option.slider ? 'range' : 'number';
                for (const key of ['min', 'max', 'step']) control[key] = String(Number((option[key] * scale).toPrecision(12)));
                control.value = String(option.default * scale);
                control.required = true;
            }
            row.append(caption, control);
            if (option.slider) {
                const readout = document.createElement('output');
                readout.htmlFor = control.id;
                const update = () => { readout.textContent = `${control.value}${option.percent ? '%' : ''}`; };
                control.addEventListener('input', update);
                update();
                row.append(readout);
            }
            controls.set(option.key, control);
            rows.set(option.key, row);
            fieldset.append(row);
        }
        form.append(fieldset);
    }
    const read = () => Object.fromEntries(OPTIONS_SCHEMA.options.filter(o => controls.has(o.key)).map(o => {
        const control = controls.get(o.key);
        const value = o.type === 'bool' ? control.checked : o.type === 'number'
            ? (control.value === '' ? NaN : Number(control.value) / (o.percent ? 100 : 1)) : control.value;
        return [o.key, value];
    }));
    const updateVisibility = () => {
        const values = read();
        for (const [key, row] of rows) {
            row.hidden = !optionVisible(key, values);
            // Hidden fields keep their values, but do not block HTML validity.
            controls.get(key).disabled = row.hidden;
        }
    };
    form.addEventListener('input', updateVisibility);
    form.addEventListener('change', updateVisibility);
    updateVisibility();
    return () => {
        const values = read();
        // Omit hidden controls: dependencies may have made a previously edited
        // field invalid. Upstream uses its own defaults for absent values.
        for (const [key, row] of rows) if (row.hidden) delete values[key];
        optionsFromDialog(values);
        return values;
    };
}
