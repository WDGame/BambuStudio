// Synthetic, deterministic test meshes. No PrintFins geometry is implemented here.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export function box(x0, x1, y0, y1, z0, z1) {
    const v = [[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],
        [x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]];
    return [[0,3,2,1],[4,5,6,7],[0,1,5,4],[2,3,7,6],[1,2,6,5],[0,4,7,3]]
        .flatMap(([a,b,c,d]) => [...v[a],...v[b],...v[c],...v[a],...v[c],...v[d]]);
}
function pose(positions, angle = 0, mirror = false, shift = [0,0,0]) {
    const c = Math.cos(angle * Math.PI / 180), s = Math.sin(angle * Math.PI / 180);
    const vertices = [];
    for (let i = 0; i < positions.length; i += 3) {
        const x = positions[i] * (mirror ? -1 : 1), y = positions[i+1], z = positions[i+2];
        vertices.push([c*x+s*z, y, -s*x+c*z]);
    }
    const floor = vertices.reduce((low,p)=>Math.min(low,p[2]),Infinity);
    if (mirror) for (let i=0; i<vertices.length; i+=3) [vertices[i+1], vertices[i+2]] = [vertices[i+2], vertices[i+1]];
    return vertices.flatMap(p => [p[0]+shift[0], p[1]+shift[1], p[2]-floor+shift[2]]);
}
function cylinder(radius, height, segments) {
    const p = [], v = (i,z) => [radius*Math.cos(i*2*Math.PI/segments), radius*Math.sin(i*2*Math.PI/segments), z];
    for (let i=0; i<segments; ++i) p.push(...[0,0,0], ...v(i+1,0), ...v(i,0),
        ...[0,0,height], ...v(i,height), ...v(i+1,height),
        ...v(i,0), ...v(i+1,0), ...v(i+1,height), ...v(i,0), ...v(i+1,height), ...v(i,height));
    return p;
}
const tilted = pose(box(-12,12,-8,8,0,24),35);
export const fixtures = [
    { id: 'tilted-box', positions: tilted, options: {}, expected: 'generated' },
    { id: 'shelf', positions: [...box(-20,20,-8,8,0,5), ...box(-20,20,-8,8,20,24), ...box(18,20,-8,8,5,20)], options: { padStyle:'off', tines:false }, expected:'generated' },
    { id: 'round-foot', positions: pose(cylinder(8,30,24),40), options:{}, expected:'generated' },
    { id: 'thin-tilted-wall', positions: pose(box(-0.8,0.8,-12,12,0,25),35), options:{}, expected:'generated' },
    { id: 'mirrored-translated', positions: pose(box(-12,12,-8,8,0,24),35,true,[93.25,118.125,0]), options:{}, expected:'generated' },
    { id: 'two-overhangs', positions: [...box(-15,15,-6,6,0,3), ...box(-15,-12,-6,6,3,29), ...box(-15,15,-6,6,13,16), ...box(-15,15,-6,6,29,32)], options:{ padStyle:'off',tines:false }, expected:'generated' },
    { id: 'flat-no-support', positions:box(-10,10,-10,10,0,5), options:{padStyle:'off',tines:false}, expected:'empty' },
];
export function cancellationFixture() {
    const positions=[];
    const small=pose(box(-1.5,1.5,-1.5,1.5,0,5),35);
    for(let x=0;x<24;++x) for(let y=0;y<24;++y)
        for(let i=0;i<small.length;++i) positions.push(small[i] + (i%3===0 ? x*7 : i%3===1 ? y*7 : 0));
    return {id:'cancel-grid',positions,options:{},expected:'cancelled',cancelOnly:true};
}
export function oversizedFixture() {
    return {id:'oversized-input',positions:pose(cylinder(8,30,25001),35),options:{},expected:'rejected',rejectOnly:true};
}
export function stl(positions) {
    const bytes=Buffer.alloc(84+positions.length/9*50);
    bytes.write('Synthetic PrintFins stability fixture'); bytes.writeUInt32LE(positions.length/9,80);
    for(let t=0;t<positions.length/9;++t) for(let j=0;j<9;++j) bytes.writeFloatLE(positions[t*9+j],84+t*50+12+j*4);
    return bytes;
}
if (process.argv[1] && import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href) {
    const destination=path.resolve(process.argv[2]); fs.mkdirSync(destination,{recursive:true});
    const manifest=[];
    for(const f of [...fixtures,cancellationFixture(),oversizedFixture()]) {
        fs.writeFileSync(path.join(destination,f.id+'.stl'),stl(f.positions),{flag:'wx'});
        fs.writeFileSync(path.join(destination,f.id+'.json'),JSON.stringify(f),{flag:'wx'});
        manifest.push({id:f.id,options:f.options,expected:f.expected,cancelOnly:!!f.cancelOnly,rejectOnly:!!f.rejectOnly,triangles:f.positions.length/9});
    }
    fs.writeFileSync(path.join(destination,'manifest.json'),JSON.stringify(manifest,null,2),{flag:'wx'});
}
