// Exercise the existing production page/worker transport with values supplied by
// native controls. This is a DOM double, not a native Bambu UI test.
import test from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../resources/printfins/adapter.mjs';
import { fixtures } from './geometry-fixtures.mjs';
import { FDM_SCHEMA as OPTIONS_SCHEMA, optionsFromSettings } from '../../resources/printfins/schema.mjs';

class Element {
    constructor(tag) { this.tag=tag; this.children=[]; this.listeners={}; this.value=''; this.disabled=false; }
    append(...children) { for (const child of children) { child.parent=this; this.children.push(child); } }
    addEventListener(type,listener) { (this.listeners[type]??=[]).push(listener); }
    emit(type) { for (const fn of this.listeners[type]??[]) fn({preventDefault(){}}); }
    get elements() { return this.children.flatMap(c=>[c,...c.elements]); }
}

for (const mode of ['auto', 'full']) test(`native ${mode} settings cross the real transport unchanged and reach the original engine`,async()=>{
    const previous={window:globalThis.window,document:globalThis.document,Worker:globalThis.Worker};
    const ids=Object.fromEntries(['settings','generate','error','context'].map(id=>[id,new Element(id)]));
    const workers=[],messages=[];
    globalThis.document={createElement:tag=>new Element(tag),getElementById:id=>ids[id]};
    globalThis.window={addEventListener(){},printFinsMessage:message=>messages.push(message)};
    globalThis.Worker=class {
        constructor(){ workers.push(this); }
        postMessage(request){this.request=request;}
        terminate(){this.terminated=true;}
    };
    try {
        await import(`../../resources/printfins/tool.mjs?native-transport-${mode}`);
        const values=Object.fromEntries(OPTIONS_SCHEMA.options.filter(o=>!o.hostSupplied).map(o=>[o.key,o.default]));
        Object.assign(values,{mode,gap:0.3,coverage:0.75,'sway.on':true,'sway.gripFrom':5,'sway.reach':0.2});
        const request={positions:fixtures[0].positions,options:{...values,layerHeight:0.16,firstLayerHeight:0.2}};
        window.initPrintFins(request);
        assert.equal(ids.generate.textContent, `Generate PrintFins (${mode === 'full' ? 'Full Coverage' : 'Auto'})`);
        ids.settings.emit('submit');
        assert.equal(workers.length,1);
        assert.deepEqual(workers[0].request,request);
        assert.deepEqual(optionsFromSettings(values).sway,{on:true,gripFrom:5,tineSpacing:6,reach:0.2});
        const result=generate(workers[0].request);
        assert.equal(result.settings.gap,0.3);
        assert.equal(result.settings.mode,mode);
        assert.equal(result.settings.coverage,0.75);
        assert.equal(result.settings.layerHeight,0.16);
        assert.equal(result.settings.firstLayerHeight,0.2);
        assert.ok(result.triangles.length>0);
        workers[0].onmessage({data:{ok:true,...result}});
        assert.equal(messages.at(-1).action,'result');
        assert.equal(workers[0].terminated,true);
        assert.deepEqual(messages.at(-1).triangles,result.triangles);
    } finally {
        for (const [key,value] of Object.entries(previous)) {
            if(value===undefined) delete globalThis[key]; else globalThis[key]=value;
        }
    }
});
