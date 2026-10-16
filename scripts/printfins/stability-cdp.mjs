// Test-only CDP driver, using Node's built-in WebSocket. Attaches only to the
// PrintFins page of the isolated process; never sends invented success to C++.
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';

const [portText, directory] = process.argv.slice(2);
if (!/^\d+$/.test(portText || '') || !directory) throw new Error('Usage: node stability-cdp.mjs PORT LOG_DIRECTORY');
const port=Number(portText), logdir=path.resolve(directory);
if (port<1024 || port>65535) throw new Error('Invalid loopback debug port');
let socket, sequence=0, requestSequence=0;
const pending=new Map();
const log=entry=>fs.appendFileSync(path.join(logdir,'cdp.jsonl'),JSON.stringify({time:new Date().toISOString(),...entry})+'\n');
function call(method,params={}) {
    if(!socket || socket.readyState!==WebSocket.OPEN) return Promise.reject(new Error('CDP target closed'));
    return new Promise((resolve,reject)=>{
        const id=++sequence;
        const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout: '+method));},10000);
        pending.set(id,{resolve,reject,timer});
        socket.send(JSON.stringify({id,method,params}));
    });
}
async function attach(mode='normal') {
    socket?.close();
    const targets=await (await fetch(`http://127.0.0.1:${port}/json/list`,{signal:AbortSignal.timeout(3000)})).json();
    const page=targets.find(t=>t.type==='page' && t.url==='https://printfins-poc.invalid/tool.html');
    if (!page) throw new Error('PrintFins CDP page not available');
    const url=new URL(page.webSocketDebuggerUrl);
    if (!['127.0.0.1','localhost','[::1]'].includes(url.hostname) || Number(url.port)!==port) throw new Error('Refusing nonlocal CDP target');
    socket=new WebSocket(url);
    const connection=socket;
    await new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>reject(new Error('CDP connect timeout')),5000);
        socket.addEventListener('open',()=>{clearTimeout(timer);resolve();},{once:true});
        socket.addEventListener('error',()=>{clearTimeout(timer);reject(new Error('CDP connection failed'));},{once:true});
    });
    socket.addEventListener('message',event=>{
        const message=JSON.parse(event.data);
        if (message.id) {
            const p=pending.get(message.id); if(!p) return;
            pending.delete(message.id); clearTimeout(p.timer);
            if (message.error) p.reject(new Error(JSON.stringify(message.error))); else p.resolve(message.result);
        } else {
            log(message);
            if(message.method==='Runtime.bindingCalled' && message.params.name==='__printfinsTestTrace') {
                const event=JSON.parse(message.params.payload);
                if(event.kind==='request') fs.writeFileSync(path.join(logdir,`request-${++requestSequence}.json`),JSON.stringify(event.request));
                fs.appendFileSync(path.join(logdir,'trace.jsonl'),JSON.stringify({time:Date.now(),...event})+'\n');
            }
        }
    });
    socket.addEventListener('close',()=>{
        log({event:'target-closed'});
        if (socket!==connection) return;
        for(const p of pending.values()){clearTimeout(p.timer);p.reject(new Error('CDP target closed'));}
        pending.clear();
    });
    await call('Runtime.enable'); await call('Log.enable'); await call('Page.enable');
    await call('Runtime.addBinding',{name:'__printfinsTestTrace'});
    if (!await evaluate("Boolean(window.initPrintFins && window.printFinsMessage && document.getElementById('generate') && !document.getElementById('generate').disabled)"))
        throw new Error('PrintFins initialization is not complete yet');
    const script=`(() => {
        const emit = event => window.__printfinsTestTrace(JSON.stringify(event));
        if (window.__printfinsObserved) return;
        window.__printfinsObserved = true;
        const Worker = window.Worker;
        window.Worker = class extends Worker {
            constructor(...args) {
                super(...args);
                emit({kind:'worker-created',url:String(args[0])});
                this.addEventListener('message', ({data}) => {
                    emit({kind:'engine-result',ok:data.ok,triangles:data.triangles?.length/9,stats:data.stats,error:data.error});
                    if (${JSON.stringify(mode)} === 'malformed-output' && data.triangles?.length) {
                        data.triangles[0] = null;
                        emit({kind:'fault-injected',fault:'non-numeric output vertex'});
                    }
                });
            }
            postMessage(request,...args) {
                emit({kind:'request',request});
                if (${JSON.stringify(mode)} === 'worker-post-failure') throw new Error('Injected test worker post failure');
                return super.postMessage(request,...args);
            }
        };
        const send = window.printFinsMessage;
        window.printFinsMessage = message => {
            emit({kind:'host-action',action:message.action,ok:message.ok,error:message.error});
            return send(message);
        };
        window.addEventListener('error',e=>emit({kind:'page-error',error:e.message}));
        window.addEventListener('unhandledrejection',e=>emit({kind:'page-rejection',error:String(e.reason)}));
        emit({kind:'attached',mode:${JSON.stringify(mode)}});
    })()`;
    await evaluate(script);
    return {url:page.url,mode};
}
async function evaluate(expression) {
    const result=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    if(result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result?.value;
}
async function command(message) {
    if(message.method==='attach') return attach(message.mode);
    if(message.method==='evaluate') return evaluate(message.expression);
    if(message.method==='screenshot') {
        const {data}=await call('Page.captureScreenshot',{format:'png'});
        const name=`webview-${Date.now()}.png`; fs.writeFileSync(path.join(logdir,name),Buffer.from(data,'base64')); return {file:name};
    }
    if(message.method==='detach') {socket?.close();return true;}
    throw new Error('Unknown CDP test command');
}
const lines=readline.createInterface({input:process.stdin});
for await (const line of lines) {
    let message;
    try { message=JSON.parse(line); const result=await command(message); process.stdout.write(JSON.stringify({id:message.id,ok:true,result})+'\n'); }
    catch(error) { process.stdout.write(JSON.stringify({id:message?.id,ok:false,error:String(error.stack||error)})+'\n'); }
}
socket?.close();
