import { buildSettings } from './settings.mjs';
import { translator } from './i18n.mjs';

const form = document.getElementById('settings');
const button = document.getElementById('generate');
const error = document.getElementById('error');
let readSettings;
let request;
let worker;
const updateMode = () => {
    const t = translator(request?.uiLocale);
    const mode = request?.options.mode ?? [...form.elements].find(e => e.id === 'mode')?.value ?? 'auto';
    button.textContent = `${t('Generate PrintFins')} (${t(mode === 'full' ? 'Full Coverage' : 'Auto')})`;
    if (request) document.getElementById('context').textContent =
        `${mode === 'full' ? t('Full Coverage adds original fill walls under overhangs left by Auto.') : t('Auto places fins automatically.')} ` +
        `${t('Layer height')}: ${request.options.layerHeight} mm; ${t('first layer')}: ${request.options.firstLayerHeight} mm (${t('from Bambu Studio')}).`;
};
form.addEventListener('change', updateMode);
updateMode();
window.initPrintFins = input => {
    if (request) return;
    request = input;
    readSettings = buildSettings(form, document, request.uiLocale);
    updateMode();
    button.disabled = false;
};
form.addEventListener('submit', event => {
    event.preventDefault();
    if (!request || worker) return;
    try {
        const options = { ...readSettings(), ...request.options };
        error.textContent = '';
        worker = new Worker('worker.mjs', { type: 'module' });
        button.disabled = true;
        for (const element of form.elements) element.disabled = true;
        worker.onmessage = ({ data }) => {
            worker.terminate();
            window.printFinsMessage({ ...data, action: 'result' });
        };
        worker.onerror = event => {
            worker.terminate();
            window.printFinsMessage({ action: 'error', error: event.message || 'PrintFins worker failed.' });
        };
        worker.onmessageerror = () => {
            worker.terminate();
            window.printFinsMessage({ action: 'error', error: 'Cannot read the PrintFins worker result.' });
        };
        window.printFinsMessage({ action: 'computing' });
        worker.postMessage({ positions: request.positions, options });
    } catch (failure) {
        if (worker) {
            worker.terminate();
            window.printFinsMessage({ action: 'error', error: String(failure) });
        } else error.textContent = failure.message;
    }
});
window.addEventListener('pagehide', () => worker?.terminate());
window.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
        event.preventDefault();
        worker?.terminate();
        window.printFinsMessage({ action: 'cancel' });
    }
});
window.printFinsMessage({ action: 'ready' });
