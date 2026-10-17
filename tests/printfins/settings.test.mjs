import test from 'node:test';
import assert from 'node:assert/strict';
import { buildSettings } from '../../resources/printfins/settings.mjs';
import { optionsFromDialog } from '../../resources/printfins/vendor/plugins/shared/engine/fins_entry.js';
import { FDM_SCHEMA as OPTIONS_SCHEMA } from '../../resources/printfins/schema.mjs';
import { generate } from '../../resources/printfins/adapter.mjs';

// Small DOM double for schema/transport tests. Native WebView rendering and
// project mutation still require the separate Bambu Studio desktop checklist.
class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.listeners = {}; this.value = ''; this.disabled = false; this.hidden = false; }
    append(...children) { for (const child of children) { child.parent = this; this.children.push(child); } }
    addEventListener(type, handler) { (this.listeners[type] ??= []).push(handler); }
    emit(type, event = { preventDefault() {} }) {
        for (const handler of this.listeners[type] || []) handler(event);
        if (type === 'input' || type === 'change') this.parent?.emit(type, event);
    }
    get elements() { return this.children.flatMap(child => [child, ...child.elements]); }
}
function setup() {
    const form = new Element('form');
    const document = { createElement: tag => new Element(tag) };
    const read = buildSettings(form, document);
    const control = key => form.elements.find(element => element.id === key);
    const set = (key, value) => {
        const element = control(key);
        if (element.type === 'checkbox') element.checked = value; else element.value = String(value);
        element.emit('input');
    };
    return { form, read, control, set };
}

test('dialog controls use every editable upstream default, range, step and choice', () => {
    const { read, control } = setup();
    assert.equal(control('layerHeight'), undefined);
    assert.equal(control('tineDir'), undefined);
    assert.equal(control('pinDepth'), undefined);
    for (const option of OPTIONS_SCHEMA.options.filter(o => o.hostSupplied !== 'slicer')) {
        const element = control(option.key);
        assert.ok(element, option.key);
        if (option.type === 'bool') assert.equal(element.checked, option.default);
        else if (option.type === 'choice') {
            assert.equal(element.value, option.default);
            assert.deepEqual(element.children.map(c => c.value), option.choices.map(c => c.value));
        } else {
            const scale = option.percent ? 100 : 1;
            for (const key of ['min', 'max', 'step']) assert.equal(Number(element[key]), option[key] * scale);
            assert.equal(Number(element.value), option.default * scale);
        }
    }
    const options = optionsFromDialog(read());
    assert.equal(options.threshold, 45);
    assert.equal(options.padStyle, 'auto');
    assert.equal(options.sway, undefined);
});

test('original dependencies follow tines/sway and hidden invalid values do not block generation', () => {
    const { set, control, read } = setup();
    assert.equal(control('sway.gripFrom').parent.hidden, true);
    set('sway.on', true);
    assert.equal(control('sway.gripFrom').parent.hidden, false);
    assert.equal(control('sway.reach').parent.hidden, false);
    set('sway.gripFrom', 'bad');
    assert.throws(read, /must be a number/);
    set('tines', false);
    assert.equal(control('tineDensity').parent.hidden, true);
    assert.equal(control('sway.gripFrom').parent.hidden, true);
    assert.equal(control('sway.tineSpacing').parent.hidden, true);
    assert.equal(control('sway.reach').parent.hidden, false);
    assert.doesNotThrow(read);
    set('sway.on', false);
    assert.equal(control('sway.reach').parent.hidden, true);
});

test('percent fields reach upstream in engine units and invalid visible values are rejected', () => {
    const { set, read } = setup();
    set('coverage', 75);
    set('tineDensity', 20);
    set('sway.on', true);
    set('sway.reach', 24);
    const options = optionsFromDialog(read());
    assert.equal(options.coverage, 0.75);
    assert.equal(options.tineDensity, 0.2);
    assert.equal(options.sway.reach, 0.24);
    for (const [key, value] of [['gap', 0.41], ['gap', ''], ['cutout', 'custom'], ['sway.reach', 51]]) {
        const original = read()[key];
        set(key, value);
        assert.throws(read);
        set(key, key === 'sway.reach' ? original * 100 : original);
    }
});

test('tool waits for an explicit submit, uses slicer heights, forwards results and terminates on close', async () => {
    const ids = Object.fromEntries(['settings', 'generate', 'error', 'context'].map(key => [key, new Element(key)]));
    const messages = [];
    const events = {};
    const workers = [];
    const saved = { window: globalThis.window, document: globalThis.document, Worker: globalThis.Worker };
    globalThis.document = { createElement: tag => new Element(tag), getElementById: key => ids[key] };
    globalThis.window = { printFinsMessage: message => messages.push(message), addEventListener: (type, fn) => { events[type] = fn; } };
    globalThis.Worker = class {
        constructor(url, options) { this.url = url; this.options = options; workers.push(this); }
        terminate() { this.terminated = true; }
        postMessage(request) { this.request = request; }
    };
    try {
        await import('../../resources/printfins/tool.mjs');
        assert.deepEqual(messages, [{ action: 'ready' }]);
        assert.equal(workers.length, 0);
        const positions = [0,0,0, 20,0,0, 0,20,0, 0,0,0, 0,0,20, 20,0,0,
            0,0,0, 0,20,0, 0,0,20, 20,0,0, 0,0,20, 0,20,0];
        window.initPrintFins({ positions, options: { layerHeight: 0.16, firstLayerHeight: 0.2 } });
        assert.equal(ids.generate.disabled, false);
        const gap = ids.settings.elements.find(c => c.id === 'gap');
        gap.value = '5';
        ids.settings.emit('submit');
        assert.equal(workers.length, 0);
        assert.match(ids.error.textContent, /gap/);
        gap.value = '0.2';
        ids.settings.emit('submit');
        ids.settings.emit('submit');
        assert.equal(workers.length, 1);
        const worker = workers[0];
        assert.equal(worker.request.options.layerHeight, 0.16);
        assert.equal(worker.request.options.firstLayerHeight, 0.2);
        assert.deepEqual(messages.at(-1), { action: 'computing' });
        const result = generate(worker.request);
        worker.onmessage({ data: { ok: true, ...result } });
        assert.equal(worker.terminated, true);
        assert.equal(messages.at(-1).action, 'result');
        assert.deepEqual(messages.at(-1).triangles, result.triangles);
        // A separate dialog instance is cancelled while computation is pending.
        await import('../../resources/printfins/tool.mjs?cancel');
        window.initPrintFins({ positions, options: { layerHeight: 0.2, firstLayerHeight: 0.2 } });
        ids.settings.emit('submit');
        const pending = workers.at(-1);
        assert.notEqual(pending, worker);
        assert.equal(pending.terminated, undefined);
        const beforeClose = messages.length;
        events.pagehide();
        assert.equal(pending.terminated, true);
        assert.equal(messages.length, beforeClose);
        pending.onerror({ message: 'worker unavailable' });
        assert.deepEqual(messages.at(-1), { action: 'error', error: 'worker unavailable' });
        pending.onmessageerror();
        assert.equal(messages.at(-1).action, 'error');
        let prevented = false;
        events.keydown({ key: 'Escape', preventDefault() { prevented = true; } });
        assert.equal(prevented, true);
        assert.deepEqual(messages.at(-1), { action: 'cancel' });
    } finally {
        for (const [key, value] of Object.entries(saved)) {
            if (value === undefined) delete globalThis[key]; else globalThis[key] = value;
        }
    }
});
