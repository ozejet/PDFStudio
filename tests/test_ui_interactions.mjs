import assert from 'node:assert/strict';
import {after, test} from 'node:test';
import {readFile, mkdir, writeFile, rm} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {JSDOM} from '../web/node_modules/jsdom/lib/api.js';
import React, {act} from '../web/node_modules/react/index.js';
import {transformWithOxc} from '../web/node_modules/vite/dist/node/index.js';
import {attachDocumentZoom} from '../web/src/documentZoom.ts';
import {importDropFiles} from '../web/src/fileDrop.ts';
import {importProblem,partitionImportErrors} from '../web/src/importPolicy.ts';
import {attachDocumentPan} from '../web/src/documentPan.ts';
import {newObject} from '../web/src/types.ts';
import {captureReadingPosition,restoreReadingPosition} from '../web/src/readingPosition.ts';

const dom = new JSDOM('<!doctype html><div id="root"></div>', {url: 'http://localhost/', pretendToBeVisual: true});
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
// Initialize the DOM before React DOM detects supported input/focus events.
const {createRoot}=await import('../web/node_modules/react-dom/client.js');
const cache = resolve('web/node_modules/.cache/pdfstudio-ui-check');
await mkdir(cache, {recursive: true});
async function component(name, rewrite = value => value) {
  const source = rewrite(await readFile(`web/src/${name}.tsx`, 'utf8'));
  const compiled = await transformWithOxc(source, `${name}.tsx`, {jsx: {runtime: 'automatic'}});
  await writeFile(resolve(cache, `${name}.mjs`), compiled.code);
  return import(pathToFileURL(resolve(cache, `${name}.mjs`)).href);
}
const {DropWarning} = await component('DropWarning');
const {Notifications}=await component('Notifications');
await writeFile(resolve(cache, 'pdfjs-test.mjs'), `export class TextLayer {textDivs=[];constructor({textContentSource,container}){for(const item of textContentSource.items||[])if(typeof item.str==='string'){const span=document.createElement('span');span.textContent=item.str;container.append(span);this.textDivs.push(span);}}async render(){}cancel(){}}`);
const speechCompiled=await transformWithOxc(await readFile('web/src/speech.ts','utf8'),'speech.ts');
await writeFile(resolve(cache,'speech.mjs'),speechCompiled.code);
const {paragraphGroups,speechChunks,ParagraphSpeaker}=await import(pathToFileURL(resolve(cache,'speech.mjs')).href);
await component('ReadAloud',source=>source.replace("from './speech'","from './speech.mjs'").replace("from './types'",`from '${pathToFileURL(resolve('web/src/types.ts')).href}'`));
const {PdfPage} = await component('PdfPage', source => source.replace("from 'pdfjs-dist'", "from './pdfjs-test.mjs'"));
const closeWarning = await transformWithOxc(await readFile('web/src/useCloseWarning.ts', 'utf8'), 'useCloseWarning.ts');
await writeFile(resolve(cache, 'useCloseWarning.mjs'), closeWarning.code);
const {useCloseWarning} = await import(pathToFileURL(resolve(cache, 'useCloseWarning.mjs')).href);
const focusSource=(await readFile('web/src/useFocusView.ts','utf8')).replace("from './readingPosition'",`from '${pathToFileURL(resolve('web/src/readingPosition.ts')).href}'`);
const focusCompiled=await transformWithOxc(focusSource,'useFocusView.ts');
await writeFile(resolve(cache,'useFocusView.mjs'),focusCompiled.code);
const {useFocusView}=await import(pathToFileURL(resolve(cache,'useFocusView.mjs')).href);
await writeFile(resolve(cache,'reader-pdf-test.mjs'),'export function loadPdf(){globalThis.readerLoads++;return {promise:Promise.resolve(globalThis.readerPdf),destroy(){globalThis.readerDestroys++;return Promise.resolve();}}}');
const {Reader}=await component('Reader',source=>source
 .replace("from './pdf'","from './reader-pdf-test.mjs'")
 .replaceAll("from './PdfPage'","from './PdfPage.mjs'")
 .replace("from './ReadAloud'","from './ReadAloud.mjs'")
 .replace("from './useFocusView'","from './useFocusView.mjs'")
 .replace("from './documentZoom'",`from '${pathToFileURL(resolve('web/src/documentZoom.ts')).href}'`)
 .replace("from './documentPan'",`from '${pathToFileURL(resolve('web/src/documentPan.ts')).href}'`)
 .replace("from './documentKeyboard'",`from '${pathToFileURL(resolve('web/src/documentKeyboard.ts')).href}'`));

const {BrandLogo}=await component('BrandLogo');
await component('ui',source=>source.replace("from './BrandLogo'","from './BrandLogo.mjs'"));
const {EditorToolbar}=await component('EditorToolbar');
const {Inspector}=await component('Inspector',source=>source.replace("from './ui'","from './ui.mjs'"));
await writeFile(resolve(cache,'api-test.mjs'),`export const api=(...args)=>globalThis.studioApi(...args);export const uploadFiles=(...args)=>globalThis.studioUpload(...args);export function setToken(){}export const nativeSave=(...args)=>globalThis.studioNativeSave?globalThis.studioNativeSave(...args):Promise.resolve({cancelled:true});`);
const {SourceReader}=await component('SourceReader',source=>source.replace("from './api'","from './api-test.mjs'").replace("from './Reader'","from './Reader.mjs'").replace("from './ui'","from './ui.mjs'"));
const {FeedbackPanel}=await component('Feedback',source=>source.replace("from './api'","from './api-test.mjs'").replace("from './ui'","from './ui.mjs'"));
const {Tools}=await component('Tools',source=>source.replace("from './api'","from './api-test.mjs'").replace("from './ui'","from './ui.mjs'"));
await writeFile(resolve(cache,'app-stubs.mjs'),`import React from 'react';import {EditorToolbar} from './EditorToolbar.mjs';export {Inspector} from './Inspector.mjs';export const Editor=React.forwardRef((props,ref)=>{globalThis.editorProps=props;return React.createElement(EditorToolbar,{tool:props.tool,onTool:props.onTool,onText(){},onImage(){}});});export const Organize=()=>React.createElement('div',null,'Organize test workspace');export const TemplateControls=()=>null;`);
const {default:App}=await component('App',source=>source
 .replace("from './api'","from './api-test.mjs'")
 .replace("from './ui'","from './ui.mjs'")
 .replace("from './BrandLogo'","from './BrandLogo.mjs'")
 .replace("from './Reader'","from './Reader.mjs'")
 .replace("from './SourceReader'","from './SourceReader.mjs'")
 .replace("from './Tools'","from './Tools.mjs'")
 .replace("from './Feedback'","from './Feedback.mjs'")
 .replace("from './DropWarning'","from './DropWarning.mjs'")
 .replace("from './Notifications'","from './Notifications.mjs'")
 .replace("from './useCloseWarning'","from './useCloseWarning.mjs'")
 .replace(/from '\.\/(Organize|Editor|Inspector|Templates)'/g,"from './app-stubs.mjs'")
 .replace("from './types'",`from '${pathToFileURL(resolve('web/src/types.ts')).href}'`)
 .replace("from './fileDrop'",`from '${pathToFileURL(resolve('web/src/fileDrop.ts')).href}'`)
 .replace("from './importPolicy'",`from '${pathToFileURL(resolve('web/src/importPolicy.ts')).href}'`));

after(async () => {dom.window.close(); await rm(cache, {recursive: true, force: true});});

test('mixed drops pass every file to the same local content validator as the picker',()=>{
 const files=['a.pdf','image.png','slides.pptx','report.html','notes.md','server.log','captions.vtt','data.unknown','binary.exe'].map(name=>new File(['sample'],name));
 assert.deepEqual(importDropFiles(files),{accepted:files,ignored:[]});assert.deepEqual(importDropFiles([]),{accepted:[],ignored:[]});
});

function zoomFixture({percent = 100, count = 1} = {}) {
  const viewport = document.createElement('div');
  const pageWidth = 1000, pageHeight = 1400;
  Object.defineProperty(viewport, 'clientHeight', {value: 600});
  viewport.scrollLeft = 150;
  viewport.scrollTop = count > 1 ? 1800 : 300;
  let scale = percent / 100, requested = percent, callbacks = 0, reads = 0;
  let nextFrame = 0;
  const frames = new Map();
  const requestFrame = window.requestAnimationFrame, cancelFrame = window.cancelAnimationFrame;
  window.requestAnimationFrame = callback => {frames.set(++nextFrame, callback); return nextFrame;};
  window.cancelAnimationFrame = id => frames.delete(id);
  const frame = () => {const callbacks = [...frames.values()]; frames.clear(); callbacks.forEach(callback => callback());};
  const pages = Array.from({length: count}, (_, i) => {
    const page = document.createElement('div');
    page.dataset.readerPage = String(i + 1);
    page.dataset.readerWidth = String(pageWidth);
    page.getBoundingClientRect = () => {
      reads++;
      const left = 100 + 24 - viewport.scrollLeft;
      const top = 50 + 24 + i * (pageHeight * scale + 24) - viewport.scrollTop;
      const width = pageWidth * scale, height = pageHeight * scale;
      return {left, top, width, height, right: left + width, bottom: top + height};
    };
    viewport.append(page);
    return page;
  });
  const control = attachDocumentZoom(viewport, value => {requested = value; callbacks++;});
  const wheel = (extra = {}) => {
    const event = new dom.window.WheelEvent('wheel', {cancelable: true, deltaY: -100, clientX: 450, clientY: 350, ...extra});
    viewport.dispatchEvent(event);
    return event;
  };
  const commit = () => {scale = requested / 100; control.restore();};
  const point = (page, x, y) => {
    const rect = page.getBoundingClientRect();
    return [rect.left + x * rect.width, rect.top + y * rect.height];
  };
  const dispose = control.dispose;
  control.dispose = () => {dispose(); window.requestAnimationFrame = requestFrame; window.cancelAnimationFrame = cancelFrame;};
  return {viewport, pages, control, wheel, commit, point, frame, percent: () => requested, callbacks: () => callbacks, reads: () => reads};
}

test('ordinary wheel scrolls normally; Ctrl+wheel zooms only the document', () => {
  const f = zoomFixture();
  assert.equal(f.wheel().defaultPrevented, false);
  assert.equal(f.percent(), 100);
  const rect = f.pages[0].getBoundingClientRect();
  const x = (450 - rect.left) / rect.width, y = (350 - rect.top) / rect.height;
  assert.equal(f.wheel({ctrlKey: true}).defaultPrevented, true);
  f.frame();
  assert.ok(f.percent() > 100);
  f.commit();
  const [left, top] = f.point(f.pages[0], x, y);
  assert.ok(Math.abs(left - 450) < .001);
  assert.ok(Math.abs(top - 350) < .001);
  f.control.dispose();
  assert.equal(f.wheel({ctrlKey: true}).defaultPrevented, false);
});

test('continuous zoom anchors a later page and accumulates rapid wheel events', () => {
  const f = zoomFixture({count: 400});
  const rect = f.pages[1].getBoundingClientRect();
  const x = (450 - rect.left) / rect.width, y = (350 - rect.top) / rect.height;
  f.wheel({ctrlKey: true});
  f.wheel({ctrlKey: true});
  assert.equal(f.callbacks(), 0);
  f.frame();
  assert.equal(f.callbacks(), 1);
  assert.ok(f.percent() > 122);
  assert.ok(f.reads() < 30, 'Large documents should not measure every page per wheel event');
  f.commit();
  const [left, top] = f.point(f.pages[1], x, y);
  assert.ok(Math.abs(left - 450) < .001);
  assert.ok(Math.abs(top - 350) < .001);
  f.control.dispose();
});

test('PDF limits still consume browser zoom; line-mode wheel and zoom out work', () => {
  for (const [percent, deltaY] of [[500, -100], [25, 100]]) {
    const f = zoomFixture({percent});
    assert.equal(f.wheel({ctrlKey: true, deltaY}).defaultPrevented, true);
    assert.equal(f.percent(), percent);
    f.control.dispose();
  }
  const f = zoomFixture();
  f.wheel({ctrlKey: true, deltaY: 3, deltaMode: 1});
  f.frame();
  assert.ok(f.percent() < 100);
  f.control.dispose();
});

test('wheel input arriving before the previous layout commit is retained', () => {
  const f = zoomFixture();
  f.wheel({ctrlKey: true});
  f.frame();
  const first = f.percent();
  f.wheel({ctrlKey: true});
  f.commit();
  f.frame();
  assert.ok(f.percent() > first);
  f.commit();
  f.control.dispose();
});

function pointer(target, type, extra = {}) {
  const event = new dom.window.MouseEvent(type, {bubbles: true, cancelable: true, button: 0, buttons: 1, clientX: 400, clientY: 400, ...extra});
  Object.defineProperty(event, 'pointerId', {value: 1});
  target.dispatchEvent(event);
  return event;
}

function panFixture(hand = true, editor = false) {
  const viewport = document.createElement('div'), canvas = document.createElement('canvas');
  const scroll = editor ? document.createElement('div') : viewport;
  viewport.tabIndex = 0;
  viewport.append(canvas);
  document.body.append(viewport);
  scroll.scrollLeft = 100; scroll.scrollTop = 200;
  const control = attachDocumentPan(viewport, {isHand: () => hand, scrollTarget: scroll});
  const key = (type, target = window) => {
    const event = new dom.window.KeyboardEvent(type, {bubbles: true, cancelable: true, code: 'Space', key: ' '});
    target.dispatchEvent(event);
    return event;
  };
  return {viewport, canvas, scroll, control, key, setHand(value) {hand = value; control.update();}, dispose() {control.dispose(); viewport.remove();}};
}

test('Hand drag pans both axes without reaching drawing/selection handlers', () => {
  const f = panFixture();
  let drawings = 0;
  f.canvas.addEventListener('pointerdown', () => drawings++);
  assert.ok(f.viewport.classList.contains('document-pan-ready'));
  assert.equal(pointer(f.canvas, 'pointerdown').defaultPrevented, true);
  assert.ok(f.viewport.classList.contains('document-panning'));
  pointer(window, 'pointermove', {clientX: 310, clientY: 260});
  assert.equal(f.scroll.scrollLeft, 190);
  assert.equal(f.scroll.scrollTop, 340);
  pointer(window, 'pointerup');
  assert.equal(drawings, 0);
  assert.ok(!f.viewport.classList.contains('document-panning'));
  assert.ok(f.viewport.classList.contains('document-pan-ready'));
  f.setHand(false);
  assert.equal(pointer(f.canvas, 'pointerdown').defaultPrevented, false);
  assert.equal(drawings, 1);
  pointer(window, 'pointerup');
  f.dispose();
});

test('Space pans the editor scroll container, then restores text/drawing interaction', () => {
  const f = panFixture(false, true);
  pointer(f.viewport, 'pointerenter');
  assert.equal(f.key('keydown').defaultPrevented, true);
  assert.equal(pointer(f.canvas, 'mousedown').defaultPrevented, true);
  pointer(f.canvas, 'pointerdown');
  pointer(window, 'pointermove', {clientX: 350, clientY: 300});
  assert.equal(f.scroll.scrollTop, 300);
  assert.equal(f.scroll.scrollLeft, 150);
  f.key('keyup');
  assert.ok(f.viewport.classList.contains('document-panning'), 'Releasing Space mid-drag must not start drawing');
  pointer(window, 'pointerup');
  assert.ok(!f.viewport.classList.contains('document-pan-ready'));
  assert.equal(pointer(f.canvas, 'pointerdown').defaultPrevented, false);
  pointer(window, 'pointerup');
  f.dispose();
});

test('panning preserves Space typing, ignores an existing stroke, and resets on blur/cancel', () => {
  const f = panFixture(false);
  pointer(f.viewport, 'pointerenter');
  const input = document.createElement('textarea'); f.viewport.append(input);
  assert.equal(f.key('keydown', input).defaultPrevented, false);
  assert.ok(!f.viewport.classList.contains('document-pan-ready'));
  pointer(f.canvas, 'pointerdown');
  f.key('keydown');
  assert.ok(!f.viewport.classList.contains('document-pan-ready'));
  pointer(window, 'pointerup');
  f.key('keydown');
  pointer(f.canvas, 'pointerdown');
  window.dispatchEvent(new dom.window.Event('blur'));
  assert.ok(!f.viewport.classList.contains('document-pan-ready'));
  f.setHand(true);
  pointer(f.canvas, 'pointerdown');
  pointer(window, 'pointercancel');
  assert.ok(!f.viewport.classList.contains('document-panning'));
  f.dispose();
  assert.equal(pointer(f.canvas, 'pointerdown').defaultPrevented, false);
});

test('PDF bitmaps are reused during zoom, rendered after idle, and swapped only when ready', async () => {
  const originalContext = window.HTMLCanvasElement.prototype.getContext;
  const originalSetTimeout = window.setTimeout, originalClearTimeout = window.clearTimeout;
  const timers = new Map(); let id = 0, copies = 0, ready = 0;
  globalThis.devicePixelRatio = 2;
  window.HTMLCanvasElement.prototype.getContext = () => ({drawImage() {copies++;}});
  window.setTimeout = (callback, delay) => {assert.equal(delay, 160); timers.set(++id, callback); return id;};
  window.clearTimeout = timer => timers.delete(timer);
  const jobs = [];
  const page = {
    rotate: 0,
    getViewport({scale, rotation}) {return {width:600*scale, height:800*scale, scale, rotation};},
    async getTextContent() {return {items: []};},
    render({canvas, viewport}) {
      let resolve, reject;
      const promise = new Promise((yes, no) => {resolve = yes; reject = no;});
      const job = {viewport, pixels:canvas.width*canvas.height, done:false, canceled:false,
        resolve() {this.done=true; resolve();},
        cancel() {if(!this.done) {this.canceled=true; const error=new Error('canceled'); error.name='RenderingCancelledException'; reject(error);}},
      };
      jobs.push(job);
      return {promise, cancel:() => job.cancel()};
    },
  };
  const pdf = {async getPage() {return page;}};
  const container = document.createElement('div'); document.body.append(container);
  const root = createRoot(container);
  const render = (width, query = '') => act(async () => {root.render(React.createElement(PdfPage, {pdf, number:1, width, query, deferRender:true, onReady:() => ready++}));});
  const idle = () => act(async () => {const callbacks=[...timers.values()]; timers.clear(); callbacks.forEach(callback=>callback());});
  try {
    await render(600);
    assert.equal(jobs.length, 1);
    await act(async () => {jobs[0].resolve();});
    const front = container.querySelector('canvas');
    assert.equal(front.width, 1200);
    await render(900); await render(1200);
    assert.equal(jobs.length, 1, 'Wheel movement must not repeatedly render the PDF');
    assert.equal(front.width, 1200);
    assert.equal(container.querySelector('.pdf-page').style.width, '1200px');
    assert.equal(container.querySelector('.pdf-text-scale').style.transform, 'scale(2)');
    assert.equal(container.querySelector('.textLayer').style.transform, '', 'PDF.js must retain ownership of text rotation');
    await idle();
    assert.equal(jobs.length, 2);
    assert.equal(front.width, 1200, 'Keep the existing page visible until the new render finishes');
    await render(1500); await idle();
    assert.equal(jobs[1].canceled, true);
    assert.equal(jobs.length, 3);
    await act(async () => {jobs[2].resolve();});
    assert.equal(copies, 2);
    assert.equal(ready, 2);
    assert.ok(front.width*front.height <= 8000000);
    assert.ok(jobs.every(job=>job.pixels <= 8000000));
    await render(1500, 'search');
    assert.equal(jobs.length, 3, 'Searching must not redraw the bitmap');
    await render(1800); await idle();
    await act(() => root.unmount());
    assert.equal(jobs[3].canceled, true);
    assert.equal(timers.size, 0);
  } finally {
    await act(() => root.unmount());
    container.remove();
    window.HTMLCanvasElement.prototype.getContext = originalContext;
    window.setTimeout = originalSetTimeout; window.clearTimeout = originalClearTimeout;
  }
});

test('browser-close guard blocks closing with work and removes itself after Quit/cleanup', async () => {
  function Guard({hasWork}) {useCloseWarning(hasWork); return null;}
  const container = document.createElement('div'), root = createRoot(container);
  const close = () => {const event = new dom.window.Event('beforeunload', {cancelable:true}); window.dispatchEvent(event); return event.defaultPrevented;};
  try {
    await act(() => root.render(React.createElement(Guard, {hasWork:false})));
    assert.equal(close(), false);
    await act(() => root.render(React.createElement(Guard, {hasWork:true})));
    assert.equal(close(), true);
    await act(() => root.render(React.createElement(Guard, {hasWork:false})));
    assert.equal(close(), false);
  } finally {await act(() => root.unmount());}
  assert.equal(close(), false);
});

test('desktop title-bar close opens the save reminder and Keep working preserves the session',async()=>{
 globalThis.localStorage=window.localStorage;globalThis.ResizeObserver=class{observe(){}disconnect(){}};
 const originalShow=window.HTMLDialogElement.prototype.showModal,originalClose=window.HTMLDialogElement.prototype.close;
 window.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};window.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
 const calls=[];globalThis.studioApi=async path=>{calls.push(path);return path==='/config'?{token:'test',version:'0.1.012',profiles:[],documents:[]}:{};};
 const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 try{
  await act(async()=>root.render(React.createElement(App)));
  assert.equal(window.__pdfStudioReady,true);
  await act(async()=>window.dispatchEvent(new window.Event('pdfstudio:close-request')));
  assert.match(container.querySelector('dialog').textContent,/Save any results/);
  await act(async()=>[...container.querySelectorAll('dialog button')].find(b=>b.textContent==='Keep working').click());
  assert.equal(container.querySelector('dialog'),null);assert.ok(!calls.includes('/quit'));
  await act(async()=>window.dispatchEvent(new window.Event('pdfstudio:close-request')));
  await act(async()=>[...container.querySelectorAll('dialog button')].find(b=>b.textContent==='Quit PDF Studio').click());
  assert.equal(calls.filter(path=>path==='/quit').length,1);
 }finally{await act(async()=>root.unmount());container.remove();window.HTMLDialogElement.prototype.showModal=originalShow;window.HTMLDialogElement.prototype.close=originalClose;}
 assert.equal(window.__pdfStudioReady,false);
});

test('reading position survives viewport movement and page rescaling in both directions', () => {
 const viewport=document.createElement('div'),page=document.createElement('div');
 viewport.append(page);page.dataset.readerPage='12';
 viewport.scrollLeft=180;viewport.scrollTop=700;
 let left=225,top=350,scale=1;
 viewport.getBoundingClientRect=()=>({left,top,width:700,height:600});
 page.getBoundingClientRect=()=>{
  const x=left+24-viewport.scrollLeft,y=top+24-viewport.scrollTop,w=1200*scale,h=1800*scale;
  return {left:x,top:y,right:x+w,bottom:y+h,width:w,height:h};
 };
 const snapshot=captureReadingPosition(viewport);
 assert.ok(snapshot);
 left=0;top=0;scale=1.4;
 restoreReadingPosition(viewport,snapshot);
 const moved=captureReadingPosition(viewport);
 assert.ok(Math.abs(moved.x-snapshot.x)<.00001);
 assert.ok(Math.abs(moved.y-snapshot.y)<.00001);
 left=225;top=350;scale=1;
 restoreReadingPosition(viewport,moved);
 assert.ok(Math.abs(viewport.scrollLeft-180)<.00001);
 assert.ok(Math.abs(viewport.scrollTop-700)<.00001);
});

test('leaving Focus recovers clamped offsets, while retaining movement made in Focus', async () => {
 let api;
 function Harness(){
  const pages=React.useRef(null),toolbar=React.useRef(null);
  api=useFocusView(pages,toolbar,true,'page1|150%');
  React.useLayoutEffect(()=>{api.restoreLayout(true);});
  return React.createElement('section',null,React.createElement('div',{ref:toolbar}),React.createElement('div',{ref:pages,tabIndex:0},React.createElement('div',{'data-reader-page':'1'})));
 }
 const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 try{
  await act(async()=>{root.render(React.createElement(Harness));});
  const viewport=container.querySelector('[tabindex]'),page=viewport.firstElementChild;
  let left=200,top=900;
  Object.defineProperty(viewport,'clientWidth',{get:()=>api.active?1200:600});
  Object.defineProperty(viewport,'clientHeight',{get:()=>api.active?1000:500});
  Object.defineProperty(viewport,'scrollLeft',{get:()=>left=Math.max(0,Math.min(left,1048-viewport.clientWidth)),set:value=>{left=Math.max(0,Math.min(value,1048-viewport.clientWidth));}});
  Object.defineProperty(viewport,'scrollTop',{get:()=>top=Math.max(0,Math.min(top,1648-viewport.clientHeight)),set:value=>{top=Math.max(0,Math.min(value,1648-viewport.clientHeight));}});
  viewport.getBoundingClientRect=()=>({left:api.active?0:225,top:api.active?0:300,width:viewport.clientWidth,height:viewport.clientHeight});
  page.getBoundingClientRect=()=>{const box=viewport.getBoundingClientRect(),x=box.left+Math.max(24,(viewport.clientWidth-1000)/2)-viewport.scrollLeft,y=box.top+24-viewport.scrollTop;return {left:x,top:y,right:x+1000,bottom:y+1600,width:1000,height:1600};};
  await act(async()=>{api.change(true);});
  assert.equal(viewport.scrollLeft,0);assert.equal(viewport.scrollTop,648);
  await act(async()=>{api.change(false);});
  assert.ok(Math.abs(viewport.scrollLeft-200)<.00001);
  assert.ok(Math.abs(viewport.scrollTop-900)<.00001);
  await act(async()=>{api.change(true);});
  viewport.scrollTop=400;
  await act(async()=>{api.change(false);});
  assert.ok(Math.abs(viewport.scrollTop-400)<.00001,'Retain the new reading position after panning in Focus');
 }finally{await act(async()=>{root.unmount();});container.remove();}
});

test('Focus view preserves the live reader, reveals controls, supports keyboard and exits safely', async () => {
 const originalContext=window.HTMLCanvasElement.prototype.getContext;
 const originalSetTimeout=window.setTimeout,originalClearTimeout=window.clearTimeout;
 const originalFullscreen=window.HTMLElement.prototype.requestFullscreen;
 const originalObserver=globalThis.ResizeObserver;
 const timers=new Map();let timerId=0,fullscreenCalls=0;
 window.setTimeout=(callback,delay)=>{timers.set(++timerId,{callback,delay});return timerId;};
 window.clearTimeout=id=>timers.delete(id);
 window.HTMLCanvasElement.prototype.getContext=()=>({drawImage(){}});
 window.HTMLElement.prototype.requestFullscreen=()=>{fullscreenCalls++;return Promise.resolve();};
 globalThis.ResizeObserver=class {observe(){}disconnect(){}};
 globalThis.localStorage=window.localStorage;globalThis.devicePixelRatio=1;
 globalThis.readerLoads=0;globalThis.readerDestroys=0;
 const pdfPage={rotate:0,getViewport({scale,rotation}){return {width:600*scale,height:800*scale,scale,rotation};},render(){return {promise:Promise.resolve(),cancel(){}};},async getTextContent(){return {items:[]};}};
 globalThis.readerPdf={numPages:2,async getPage(){return pdfPage;}};
 const doc={id:'focus-qa',fingerprint:'focus-qa',name:'Synthetic.pdf',size:100,pages:[1,2].map(number=>({number,width:600,height:800,rotation:0}))};
 localStorage.setItem('pdfstudio.read.focus-qa',JSON.stringify({page:2,zoom:'150%',layout:'Single page',rotation:0,quality:'Auto',tool:'text'}));
 const container=document.createElement('div');document.body.append(container);const root=createRoot(container),changes=[];
 const tick=delay=>act(async()=>{for(const [id,item] of [...timers])if(item.delay===delay){timers.delete(id);item.callback();}});
 const key=(key,extra={})=>{
  const event=new dom.window.KeyboardEvent('keydown',{key,bubbles:true,cancelable:true,...extra});
  (document.activeElement??document.body).dispatchEvent(event);return event;
 };
 try{
  await act(async()=>{root.render(React.createElement(Reader,{doc,focusAvailable:true,onFocusChange:value=>changes.push(value)}));});
  const entry=container.querySelector('[aria-label="Enter focus view"]'),pages=container.querySelector('.reader-pages'),canvas=container.querySelector('canvas'),search=container.querySelector('[data-reader-search]');
  pages.scrollTop=420;pages.scrollLeft=125;
  await act(async()=>{entry.focus();entry.click();});
  assert.ok(container.querySelector('.reader-focus'));
  assert.equal(changes.at(-1),true);
  assert.equal(document.activeElement,pages);
  assert.equal(fullscreenCalls,0,'Focus view must stay inside the browser content area');
  assert.equal(container.querySelector('canvas'),canvas,'Keep the existing PDF mounted');
  assert.equal(readerLoads,1);
  assert.equal(pages.scrollTop,420);assert.equal(pages.scrollLeft,125);
  await tick(1500);
  assert.ok(!container.querySelector('.reader-toolbar').classList.contains('is-visible'));
  await act(async()=>{key('Tab');});
  assert.ok(container.querySelector('.reader-toolbar').classList.contains('is-visible'));
  const hand=container.querySelector('.reader-tools button');
  assert.equal(document.activeElement,hand,'Tab from the page should enter the document controls');
  await act(async()=>{hand.focus();});
  await tick(1500);
  assert.ok(container.querySelector('.reader-toolbar').classList.contains('is-visible'),'Focused controls must stay visible');
  await act(async()=>{hand.dispatchEvent(new dom.window.MouseEvent('click',{bubbles:true,detail:1}));});
  assert.equal(document.activeElement,pages,'Mouse toolbar actions should return focus to the PDF');
  await act(async()=>{pages.focus();});await tick(1500);
  const reveal=container.querySelector('.focus-reveal');
  await act(async()=>{pointer(reveal,'pointerover');});
  assert.ok(container.querySelector('.reader-toolbar').classList.contains('is-visible'));
  await act(async()=>{pointer(reveal,'pointerout',{relatedTarget:pages});});await tick(1500);
  await act(async()=>{assert.equal(key('f',{ctrlKey:true}).defaultPrevented,true);});
  assert.equal(document.activeElement,search);
  await tick(1500);
  assert.ok(container.querySelector('.reader-toolbar').classList.contains('is-visible'),'Search input must remain usable');
  const dialog=document.createElement('dialog');dialog.setAttribute('open','');document.body.append(dialog);
  await act(async()=>{assert.equal(key('Escape').defaultPrevented,false);});
  assert.ok(container.querySelector('.reader-focus'),'A modal above the reader owns Escape first');
  dialog.remove();
  await act(async()=>{assert.equal(key('Escape').defaultPrevented,true);});
  assert.equal(container.querySelector('.reader-focus'),null);
  assert.equal(document.activeElement,entry);
  assert.equal(changes.at(-1),false);
  assert.equal(container.querySelector('[aria-label="Zoom"]').value,'150%');
  assert.equal(container.querySelector('.inline-label input').value,'2');
  assert.equal(container.querySelector('canvas'),canvas);
  assert.equal(readerDestroys,0);
  await act(async()=>{entry.click();});
  await act(async()=>{container.querySelector('[aria-label="Exit focus view"]').click();});
  assert.equal(container.querySelector('.reader-focus'),null);
  await act(async()=>{entry.click();});
  await act(async()=>{root.unmount();});
  assert.equal(changes.at(-1),false);
  assert.equal(readerDestroys,1);
  assert.equal(timers.size,0);
 }finally{
  await act(async()=>{root.unmount();});container.remove();
  window.HTMLCanvasElement.prototype.getContext=originalContext;
  window.setTimeout=originalSetTimeout;window.clearTimeout=originalClearTimeout;
  window.HTMLElement.prototype.requestFullscreen=originalFullscreen;
  globalThis.ResizeObserver=originalObserver;
  localStorage.removeItem('pdfstudio.read.focus-qa');
 }
});

test('warning shows 10 through 1, expires, restarts for a new drop, and dismisses', async () => {
  const timers = new Map();
  let timerId = 0, closed = 0;
  const setInterval = window.setInterval, clearInterval = window.clearInterval;
  window.setInterval = callback => {timers.set(++timerId, callback); return timerId;};
  window.clearInterval = id => timers.delete(id);
  const container = document.getElementById('root'), root = createRoot(container);
  const onClose = () => {closed++; root.render(null);};
  const render = key => act(() => root.render(React.createElement(DropWarning, {key, names: ['slides.pptx'], onClose})));
  const tick = () => act(() => {for (const callback of [...timers.values()]) callback();});
  try {
    await render('first');
    assert.match(container.textContent, /Ignored 1 non-PDF file/);
    assert.equal(container.querySelector('[role="status"] .warning-countdown'), null);
    const seen = [];
    for (let n = 10; n >= 1; n--) {
      seen.push(Number(container.querySelector('.warning-countdown').textContent));
      await tick();
    }
    assert.deepEqual(seen, [10,9,8,7,6,5,4,3,2,1]);
    assert.equal(closed, 1);
    assert.equal(container.querySelector('.warning-toast'), null);
    assert.equal(timers.size, 0);
    await render('second');
    await tick();
    await tick();
    assert.equal(container.querySelector('.warning-countdown').textContent, '8');
    await render('third');
    assert.equal(container.querySelector('.warning-countdown').textContent, '10');
    assert.equal(timers.size, 1);
    await act(() => container.querySelector('button').click());
    assert.equal(closed, 2);
    assert.equal(timers.size, 0);
  } finally {
    await act(() => root.unmount());
    window.setInterval = setInterval;
    window.clearInterval = clearInterval;
  }
});


test('paragraph groups preserve TextLayer indices, line wrapping, gaps and chunk text',()=>{
 const item=(str,x,y,eol=false)=>({str,transform:[12,0,0,12,x,y],height:12,width:str.length*5,hasEOL:eol});
 const groups=paragraphGroups([item('',0,0),item('First',40,700),item('line',70,700,true),{type:'beginMarkedContent'},item('continued.',40,685,true),item('Second paragraph.',40,650,true)],2);
 assert.equal(groups.length,2);assert.equal(groups[0].text,'First line continued.');
 assert.deepEqual(groups[0].items,[1,2,3]);assert.deepEqual(groups[1].items,[4]);assert.equal(groups[0].page,2);
 const long='paragraph '.repeat(200).trim(),chunks=speechChunks(long);
 assert.ok(chunks.every(chunk=>chunk.length<=650));assert.equal(chunks.join(' '),long);
});

test('paragraph speaker highlights on voice start, keeps groups across chunks, pauses and ignores stale events',async()=>{
 const spoken=[],seen=[],states=[],errors=[];let canceled=0,paused=0,resumed=0;
 const synth={speak:u=>spoken.push(u),cancel:()=>canceled++,pause:()=>paused++,resume:()=>resumed++};
 const speaker=new ParagraphSpeaker(synth,text=>({text}));
 const paragraphs=[{page:1,index:0,text:'long paragraph '.repeat(100),items:[0,1]},{page:2,index:0,text:'Next paragraph',items:[2]}];
 async function* groups(){yield* paragraphs;}
 speaker.start(groups(),{localService:true,lang:'en',voiceURI:'local'},1,{group:g=>seen.push(g),state:s=>states.push(s),error:e=>errors.push(e)});
 await Promise.resolve();await Promise.resolve();await Promise.resolve();
 assert.equal(spoken.length,1);assert.equal(seen.length,0,'Highlight starts with actual speech');
 const stale=spoken[0];spoken[0].onstart();assert.equal(seen[0],paragraphs[0]);
 speaker.pause();assert.equal(states.at(-1),'paused');speaker.resume();assert.equal(states.at(-1),'speaking');
 let index=0;while(index<spoken.length&&index<20){const current=spoken[index++];current.onstart();current.onend();await Promise.resolve();await Promise.resolve();await Promise.resolve();}
 assert.equal(seen.filter(x=>x===paragraphs[0]).length,1);assert.ok(seen.includes(paragraphs[1]));assert.equal(states.at(-1),'idle');assert.equal(seen.at(-1),null);
 const count=spoken.length;stale.onend();stale.onstart();await Promise.resolve();assert.equal(spoken.length,count);
 assert.ok(canceled>=2&&paused===1&&resumed>=2);assert.deepEqual(errors,[]);
 speaker.start(groups(),{localService:false},1,{group(){},state(){},error:e=>errors.push(e)});assert.match(errors[0],/local voice/);assert.equal(spoken.length,count);
});

test('single PDF radio selection drives tables and clears stale previews on every input change',async()=>{
 const docs=['Alpha','Beta'].map((name,i)=>({id:String(i),name:name+'.pdf',pages:[{number:1}],kind:'pdf',size:100}));
 const calls=[];globalThis.studioApi=async(path,body)=>{calls.push({path,body});return {tables:[{page:1,table:1,cells:[['Found']]}]};};
 const run=async(_message,action)=>action();const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 const render=doc=>root.render(React.createElement(Tools,{doc,docs,onImport:async()=>[],onSave(){},run}));
 try{
  await act(async()=>render(docs[0]));
  let radios=[...container.querySelectorAll('input[type=radio]')];assert.equal(radios.length,2);
  await act(async()=>radios[1].click());assert.deepEqual(radios.map(r=>r.checked),[false,true]);
  const preview=()=>[...container.querySelectorAll('button')].find(b=>b.textContent==='Preview tables');
  await act(async()=>preview().click());assert.equal(calls.at(-1).body.id,'1');assert.match(container.textContent,/1 detected tables/);
  const strategy=container.querySelector('select');await act(async()=>{strategy.value='text';strategy.dispatchEvent(new window.Event('change',{bubbles:true}));});assert.equal(container.querySelector('.table-preview'),null);
  await act(async()=>preview().click());assert.equal(calls.at(-1).body.strategy,'text');
  const output=container.querySelectorAll('select')[1];await act(async()=>{output.value='csv';output.dispatchEvent(new window.Event('change',{bubbles:true}));});assert.equal(container.querySelector('.table-preview'),null);
  await act(async()=>render(docs[1]));assert.equal(container.querySelector('input[type=radio]:checked').value,'1','Sidebar changes must not silently replace the chosen tool source');
  assert.doesNotMatch(container.textContent,/OCR \/ searchable PDF|Read aloud|Payment PDF rename/);
  assert.equal(container.querySelectorAll('.tool-tile').length,3);
  assert.equal(container.querySelector('.document-option'),null);
  assert.deepEqual([...container.querySelectorAll('.tool-document-choice span')].map(n=>n.textContent),['Alpha.pdf','Beta.pdf']);
  await act(async()=>[...container.querySelectorAll('.tool-tile')].find(b=>b.textContent.startsWith('PDF to Markdown')).click());
  radios=[...container.querySelectorAll('input[type=radio]')];assert.deepEqual(radios.map(r=>r.checked),[false,true]);
  await act(async()=>radios[0].click());assert.deepEqual(radios.map(r=>r.checked),[true,false]);
  globalThis.studioApi=async(path,body)=>{calls.push({path,body});return {text:'Synthetic Markdown',artifact:{id:'md',name:'test.md',url:'/test',size:10}};};
  await act(async()=>[...container.querySelectorAll('button')].find(b=>b.textContent==='Convert & preview').click());
  assert.equal(calls.at(-1).path,'/tools/markdown');assert.equal(calls.at(-1).body.id,'0');
 }finally{await act(async()=>root.unmount());container.remove();}
});

test('imports reject oversized batches before upload and preserve the current workflow',async()=>{
 globalThis.localStorage=window.localStorage;globalThis.ResizeObserver=class{observe(){}disconnect(){}};
 const originalContext=window.HTMLCanvasElement.prototype.getContext;
 window.HTMLCanvasElement.prototype.getContext=()=>({drawImage(){}});
 globalThis.devicePixelRatio=1;globalThis.readerLoads=0;globalThis.readerDestroys=0;
 globalThis.readerPdf={numPages:1,getPage:async()=>({rotate:0,getViewport:({scale})=>({width:600*scale,height:800*scale,scale}),render:()=>({promise:Promise.resolve(),cancel(){}}),getTextContent:async()=>({items:[]})})};
 const doc=(id)=>({id,name:id+'.pdf',pages:[{number:1,width:600,height:800,rotation:0}],size:100,kind:'pdf'});
 const initial=Array.from({length:99},(_,i)=>doc('existing-'+i));let uploads=0;
 globalThis.studioApi=async path=>path==='/config'?{token:'test',version:'0.1.006',profiles:[],documents:initial,maxOpenDocuments:100}:path.startsWith('/import-jobs/')?{phase:'complete',index:1,total:1,completed:1,done:true,documents:[doc('new')],errors:[]}:{};
 globalThis.studioUpload=async()=>{uploads++;return {id:'job'};};
 const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 const drop=files=>{const event=new window.Event('drop',{bubbles:true,cancelable:true});Object.defineProperty(event,'dataTransfer',{value:{files,types:['Files']}});container.querySelector('.studio').dispatchEvent(event);};
 try{
  await act(async()=>root.render(React.createElement(App)));
  assert.equal(container.querySelectorAll('.source').length,99);assert.equal(container.querySelectorAll('.header-actions .primary').length,1);
  assert.equal(container.querySelector('.source-drop button'),null);assert.equal(container.querySelector('[aria-label="Add more files"]'),null);assert.deepEqual([...container.querySelectorAll('nav button')].map(b=>b.textContent),['Read','Organize','Edit / Fill','Tools']);
  await act(async()=>drop([new File(['pdf'],'a.pdf'),new File(['pdf'],'b.pdf')]));assert.equal(uploads,0);assert.match(container.querySelector('[role=alert]').textContent,/No files in this batch were uploaded/);
  await act(async()=>[...container.querySelectorAll('nav button')].find(b=>b.textContent==='Organize').click());
  await act(async()=>drop([new File(['pdf'],'a.pdf')]));assert.equal(uploads,1);assert.equal(container.querySelector('nav [aria-current=page]').textContent,'Organize');assert.equal(container.querySelectorAll('.source').length,100);
  await act(async()=>drop([new File(['pdf'],'extra.pdf')]));assert.equal(uploads,1);
  assert.equal(importProblem(0,100,100,false),'');assert.match(importProblem(1,100,100,false),/100/);assert.match(importProblem(1,1,100,true),/already running/);
 }finally{await act(async()=>root.unmount());container.remove();window.HTMLCanvasElement.prototype.getContext=originalContext;}
});


test('spoken paragraph styling follows the group without rerendering the PDF bitmap or text layer',async()=>{
 const originalContext=window.HTMLCanvasElement.prototype.getContext;window.HTMLCanvasElement.prototype.getContext=()=>({drawImage(){}});
 globalThis.devicePixelRatio=1;globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.cancelAnimationFrame=window.cancelAnimationFrame.bind(window);
 let renders=0,textLoads=0;
 const page={rotate:0,getViewport:({scale})=>({width:400*scale,height:600*scale,scale}),render:()=>{renders++;return {promise:Promise.resolve(),cancel(){}};},getTextContent:async()=>{textLoads++;return {items:[{str:'One paragraph'},{str:'Still the first'},{str:'Next paragraph'}]};}};
 const pdf={getPage:async()=>page};const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 const render=highlight=>root.render(React.createElement('div',{className:'reader-pages'},React.createElement(PdfPage,{pdf,number:1,width:400,highlight})));
 try{
  await act(async()=>render(null));const spans=[...container.querySelectorAll('.textLayer span')];assert.equal(spans.length,3);
  await act(async()=>render({page:1,index:0,text:'First',items:[0,1]}));assert.deepEqual(spans.map(s=>s.classList.contains('spoken-paragraph')),[true,true,false]);
  await act(async()=>render({page:1,index:1,text:'Next',items:[2]}));assert.deepEqual(spans.map(s=>s.classList.contains('spoken-paragraph')),[false,false,true]);
  await act(async()=>render(null));assert.equal(container.querySelector('.spoken-paragraph'),null);assert.equal(renders,1);assert.equal(textLoads,1);assert.equal(container.querySelector('.textLayer span'),spans[0]);
 }finally{await act(async()=>root.unmount());container.remove();window.HTMLCanvasElement.prototype.getContext=originalContext;}
});

test('Read Aloud offers local voices only, highlights paragraphs and cancels on closing controls',async()=>{
 const originalContext=window.HTMLCanvasElement.prototype.getContext;window.HTMLCanvasElement.prototype.getContext=()=>({drawImage(){}});
 globalThis.localStorage=window.localStorage;globalThis.ResizeObserver=class{observe(){}disconnect(){}};globalThis.devicePixelRatio=1;
 globalThis.readerLoads=0;globalThis.readerDestroys=0;let cancels=0;const spoken=[];
 window.speechSynthesis={getVoices:()=>[{voiceURI:'remote',name:'Remote',localService:false,lang:'en'},{voiceURI:'local',name:'Local device',localService:true,lang:'en'}],speak:u=>spoken.push(u),cancel:()=>cancels++,resume(){},pause(){},addEventListener(){},removeEventListener(){}};
 globalThis.SpeechSynthesisUtterance=class{constructor(text){this.text=text;}};
 const items=[{str:'First paragraph.',transform:[12,0,0,12,40,700],height:12,width:90,hasEOL:true},{str:'Second paragraph.',transform:[12,0,0,12,40,650],height:12,width:90,hasEOL:true}];
 globalThis.readerPdf={numPages:1,getPage:async()=>({rotate:0,getViewport:({scale})=>({width:600*scale,height:800*scale,scale}),render:()=>({promise:Promise.resolve(),cancel(){}}),getTextContent:async()=>({items})})};
 const doc={id:'speech-integration',name:'Speech.pdf',size:100,pages:[{number:1,width:600,height:800,rotation:0}]};
 const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 try{
  await act(async()=>root.render(React.createElement(Reader,{doc})));
  const toggle=[...container.querySelectorAll('button')].find(b=>b.textContent==='Read Aloud');await act(async()=>toggle.click());
  const select=container.querySelector('[aria-label="Local voice"]');assert.equal(select.options.length,1);assert.equal(select.value,'local');
  await act(async()=>[...container.querySelectorAll('.read-aloud button')].find(b=>b.textContent==='Read').click());assert.equal(spoken.length,1);
  await act(async()=>spoken[0].onstart());assert.match(container.querySelector('.spoken-paragraph').textContent,/First paragraph/);
  await act(async()=>{spoken[0].onend();});await act(async()=>spoken[1].onstart());assert.match(container.querySelector('.spoken-paragraph').textContent,/Second paragraph/);
  const count=cancels;await act(async()=>toggle.click());assert.ok(cancels>count);assert.equal(container.querySelector('.spoken-paragraph'),null);
 }finally{await act(async()=>root.unmount());container.remove();window.HTMLCanvasElement.prototype.getContext=originalContext;delete window.speechSynthesis;delete globalThis.SpeechSynthesisUtterance;}
});


test('password retries preserve duplicate-name files and do not misclassify Office conversion errors',()=>{
 const files=[{name:'same.pdf',index:0},{name:'slides.pptx'},{name:'same.pdf',index:2}];
 const errors=[{index:0,name:'same.pdf',error:'PDF needs a password'},{index:1,name:'slides.pptx',error:'Check its format or password protection'},{index:2,name:'same.pdf',error:'PDF needs a password'}];
 const result=partitionImportErrors(files,errors);assert.deepEqual(result.passwordFiles,[files[0],files[2]]);assert.deepEqual(result.errors,[errors[1]]);
});


test('plain document-list radios are excluded from full-width text-field rules in both themes',async()=>{
 const style=document.createElement('style');style.textContent=await readFile('web/src/styles.css','utf8');document.head.append(style);
 const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 const docs=[{id:'one',name:'A readable synthetic filename.pdf',pages:[{number:1}],kind:'pdf',size:100}];
 try{
  await act(async()=>root.render(React.createElement(Tools,{doc:docs[0],docs,onImport:async()=>[],onSave(){},run:async(_m,action)=>action()})));
  const radio=container.querySelector('input[type=radio]');
  assert.equal(radio.closest('label').textContent,docs[0].name);
  for(const theme of ['light','dark']){
   document.documentElement.classList.toggle('dark',theme==='dark');
   // Match every full-width rule: jsdom's cascade omits specificity in some cases,
   // so checking computed width alone failed to catch the original browser defect.
   const inspect=rules=>{for(const rule of rules){if(rule.style?.width==='100%'&&radio.matches(rule.selectorText))assert.fail('Radio matched a full-width field rule: '+rule.selectorText);if(rule.cssRules)inspect(rule.cssRules);}};
   inspect(style.sheet.cssRules);
   const computed=window.getComputedStyle(radio);assert.equal(computed.width,'16px');assert.equal(computed.height,'16px');
   const label=window.getComputedStyle(radio.closest('label'));assert.equal(label.display,'flex');assert.equal(label.minHeight,'28px');
  }
 }finally{await act(async()=>root.unmount());container.remove();style.remove();document.documentElement.classList.remove('dark');}
});


test('one editor toolbar exposes every editing action and one visual-box tool',async()=>{
 const container=document.createElement('div');document.body.append(container);const root=createRoot(container);let text=0,image=0;
 function Harness(){const [tool,setTool]=React.useState('select');return React.createElement(EditorToolbar,{tool,onTool:setTool,onText:()=>text++,onImage:()=>image++});}
 try{
  await act(async()=>root.render(React.createElement(Harness)));
  const buttons=[...container.querySelectorAll('button')];
  assert.deepEqual(buttons.map(b=>b.textContent),['Hand','Select','Text','Image / signature','Pencil','Box / cover','Redact content','Sample color']);
  await act(async()=>buttons.find(b=>b.textContent==='Redact content').click());
  assert.equal(container.querySelector('button[aria-pressed=true]').textContent,'Redact content');
  await act(async()=>buttons.find(b=>b.textContent==='Box / cover').click());assert.equal(container.querySelectorAll('button[aria-pressed=true]').length,1);
  assert.equal(container.querySelector('button[aria-pressed=true]').textContent,'Box / cover');
  await act(async()=>{buttons.find(b=>b.textContent==='Text').click();buttons.find(b=>b.textContent==='Image / signature').click();});assert.equal(text,1);assert.equal(image,1);
  await act(async()=>root.render(React.createElement(EditorToolbar,{tool:'cover',onTool(){},onText(){},onImage(){}})));assert.equal(container.querySelector('button[aria-pressed=true]').textContent,'Box / cover','Legacy cover objects still map to the single box tool');
 }finally{await act(async()=>root.unmount());container.remove();}
});

test('Edit / Fill retains page ranges, mixed redaction/cover exports and common undo/redo',async()=>{
 globalThis.localStorage=window.localStorage;globalThis.ResizeObserver=class{observe(){}disconnect(){}};globalThis.devicePixelRatio=1;
 const originalContext=window.HTMLCanvasElement.prototype.getContext;window.HTMLCanvasElement.prototype.getContext=()=>({drawImage(){}});
 const originalShow=window.HTMLDialogElement.prototype.showModal,originalClose=window.HTMLDialogElement.prototype.close;
 window.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};window.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
 const doc={id:'unified-editor',name:'Synthetic.pdf',kind:'pdf',size:100,pages:[1,2,3].map(number=>({number,width:600,height:800,rotation:0}))};
 globalThis.readerPdf={numPages:3,getPage:async()=>({rotate:0,getViewport:({scale})=>({width:600*scale,height:800*scale,scale}),render:()=>({promise:Promise.resolve(),cancel(){}}),getTextContent:async()=>({items:[]})})};
 const requests=[];globalThis.studioApi=async(path,body)=>{requests.push({path,body});return path==='/config'?{token:'test',version:'0.1.008',profiles:[],documents:[doc],maxOpenDocuments:100}:{id:'edited',name:'edited.pdf',size:100,url:'/edited.pdf'};};
 const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 try{
  await act(async()=>root.render(React.createElement(App)));
  assert.deepEqual([...container.querySelectorAll('nav button')].map(b=>b.textContent),['Read','Organize','Edit / Fill','Tools']);
  await act(async()=>[...container.querySelectorAll('nav button')].find(b=>b.textContent==='Edit / Fill').click());
  assert.ok(container.querySelector('.canvas-toolbar'));
  await act(async()=>[...container.querySelectorAll('.canvas-toolbar button')].find(b=>b.textContent==='Redact content').click());
  assert.equal(editorProps.tool,'redact');assert.equal(editorProps.defaults.color,'#000000');assert.equal(editorProps.defaults.opacity,1);
  assert.match(container.querySelector('.inspector').textContent,/New redaction settings|permanently removed/);assert.doesNotMatch(container.querySelector('.inspector').textContent,/Pencil thickness/);
  const scope=[...container.querySelectorAll('.inspector .field')].find(l=>l.firstElementChild.textContent==='Scope').querySelector('select');
  await act(async()=>{scope.value='range';scope.dispatchEvent(new window.Event('change',{bubbles:true}));});assert.equal(editorProps.defaults.scope,'range');
  const field=[...container.querySelectorAll('.inspector .field')].find(l=>l.firstElementChild.textContent==='Page range').querySelector('input');
  await act(async()=>{Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set.call(field,'2-3');field.dispatchEvent(new window.Event('input',{bubbles:true}));});assert.equal(editorProps.defaults.range,'2-3');
  const cover={...newObject('rect',1),name:'Visual cover'},redact={...newObject('redact',1),...editorProps.defaults,id:'permanent',name:'Permanent removal'};
  await act(async()=>{editorProps.onChange([cover,redact],[]);editorProps.onSelect(redact);});
  assert.match(container.querySelector('.inspector').textContent,/True redaction/);assert.equal(editorProps.objects.length,2);
  await act(async()=>container.querySelector('[aria-label="Undo edit"]').click());assert.equal(editorProps.objects.length,0);
  await act(async()=>container.querySelector('[aria-label="Redo edit"]').click());assert.equal(editorProps.objects.length,2);
  await act(async()=>[...container.querySelectorAll('.editing-toolbar button')].find(b=>b.textContent==='Save a copy').click());
  const exported=requests.find(r=>r.path==='/export/edit');assert.equal(exported.body.id,doc.id);assert.deepEqual(exported.body.objects.map(o=>o.type),['rect','redact']);assert.equal(exported.body.objects[1].scope,'range');assert.equal(exported.body.objects[1].range,'2-3');
  assert.equal(container.querySelector('dialog[open]'),null);assert.match(container.querySelector('.toast-info').textContent,/Save canceled/);
 }finally{await act(async()=>root.unmount());container.remove();window.HTMLCanvasElement.prototype.getContext=originalContext;window.HTMLDialogElement.prototype.showModal=originalShow;window.HTMLDialogElement.prototype.close=originalClose;delete globalThis.editorProps;}
});


async function notificationAppFixture(documents,handle,preferences){
 globalThis.localStorage=window.localStorage;localStorage.clear();globalThis.ResizeObserver=class{observe(){}disconnect(){}};globalThis.devicePixelRatio=1;
 window.getSelection().removeAllRanges();globalThis.readerLoads=0;globalThis.readerDestroys=0;
 const context=window.HTMLCanvasElement.prototype.getContext,show=window.HTMLDialogElement.prototype.showModal,close=window.HTMLDialogElement.prototype.close;
 window.HTMLCanvasElement.prototype.getContext=()=>({drawImage(){}});
 window.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};window.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
 globalThis.readerPdf={numPages:3,getPage:async()=>({rotate:0,getViewport:({scale})=>({width:600*scale,height:800*scale,scale}),render:()=>({promise:Promise.resolve(),cancel(){}}),getTextContent:async()=>({items:[]})})};
 globalThis.studioApi=(path,body,method)=>path==='/config'?Promise.resolve({token:'test',version:'0.1.013',profiles:[],documents,maxOpenDocuments:100,preferences}):handle(path,body,method);
 const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 await act(async()=>root.render(React.createElement(App)));
 return {container,root,button:text=>[...container.querySelectorAll('button')].find(button=>button.textContent===text),
  drop(files){const event=new window.Event('drop',{bubbles:true,cancelable:true});Object.defineProperty(event,'dataTransfer',{value:{files,types:['Files']}});container.querySelector('.studio').dispatchEvent(event);},
  async dispose(){await act(async()=>root.unmount());container.remove();window.HTMLCanvasElement.prototype.getContext=context;window.HTMLDialogElement.prototype.showModal=show;window.HTMLDialogElement.prototype.close=close;delete globalThis.studioNativeSave;}
 };
}
const notificationDoc=id=>({id,name:id+'.pdf',pages:[1,2,3].map(number=>({number,width:600,height:800,rotation:0})),size:100,kind:'pdf'});

test('quit reminder is remembered only when quitting and is loaded on the next launch',async()=>{
 const preferences={confirmQuit:true,confirmCloseDocument:true,confirmRefreshPdf:true},requests=[];
 const handle=async(path,body)=>{requests.push({path,body});if(path==='/preferences'){Object.assign(preferences,body);return {...preferences};}return {};};
 const f=await notificationAppFixture([notificationDoc('remember-quit')],handle,preferences);
 try{
  await act(async()=>window.dispatchEvent(new window.Event('pdfstudio:close-request')));
  let check=f.container.querySelector('dialog input[type=checkbox]');assert.equal(check.checked,false);
  await act(async()=>check.click());await act(async()=>f.button('Keep working').click());
  assert.equal(requests.length,0);assert.equal(preferences.confirmQuit,true);
  await act(async()=>window.dispatchEvent(new window.Event('pdfstudio:close-request')));
  check=f.container.querySelector('dialog input[type=checkbox]');assert.equal(check.checked,false);
  await act(async()=>check.click());await act(async()=>f.button('Quit PDF Studio').click());
  assert.deepEqual(requests.map(request=>request.path),['/preferences','/quit']);assert.equal(preferences.confirmQuit,false);
  assert.equal(preferences.confirmCloseDocument,true);assert.ok(f.container.querySelector('.stopped-overlay'));
 }finally{await f.dispose();}
 const next=await notificationAppFixture([notificationDoc('next-launch')],handle,preferences);
 try{
  const warning=new window.Event('beforeunload',{cancelable:true});window.dispatchEvent(warning);assert.equal(warning.defaultPrevented,false);
  await act(async()=>window.dispatchEvent(new window.Event('pdfstudio:close-request')));
  assert.equal(next.container.querySelector('dialog[open]'),null);assert.ok(next.container.querySelector('.stopped-overlay'));
  assert.equal(requests.filter(request=>request.path==='/quit').length,2);
 }finally{await next.dispose();}
});

test('Settings restores reminders separately and restores the browser close warning',async()=>{
 const preferences={confirmQuit:false,confirmCloseDocument:false,confirmRefreshPdf:false};
 const f=await notificationAppFixture([notificationDoc('settings')],async(path,body)=>{if(path==='/preferences'){Object.assign(preferences,body);return {...preferences};}return {};},preferences);
 try{
  await act(async()=>f.container.querySelector('[aria-label="Settings"]').click());
  const checks=[...f.container.querySelectorAll('.confirmation-settings input')];assert.deepEqual(checks.map(check=>check.checked),[false,false,false]);
  await act(async()=>checks[0].click());assert.deepEqual(preferences,{confirmQuit:true,confirmCloseDocument:false,confirmRefreshPdf:false});
  await act(async()=>f.button('Restore all reminders').click());assert.ok(Object.values(preferences).every(Boolean));
  await act(async()=>f.button('Done').click());
  const warning=new window.Event('beforeunload',{cancelable:true});window.dispatchEvent(warning);assert.equal(warning.defaultPrevented,true);
  await act(async()=>window.dispatchEvent(new window.Event('pdfstudio:close-request')));assert.ok(f.container.querySelector('dialog[open]'));
 }finally{await f.dispose();}
});

test('discarding document edits has a separate opt-in remembered choice',async()=>{
 const first=notificationDoc('first-dirty'),second=notificationDoc('second-dirty'),preferences={confirmQuit:true,confirmCloseDocument:true,confirmRefreshPdf:true},requests=[];
 const f=await notificationAppFixture([first,second],async(path,body,method)=>{requests.push({path,body,method});if(path==='/preferences'){Object.assign(preferences,body);return {...preferences};}return {};},preferences);
 try{
  await act(async()=>f.button('Edit / Fill').click());await act(async()=>editorProps.onChange([newObject('text',1)],[]));
  await act(async()=>f.container.querySelector('[aria-label="Close first-dirty.pdf"]').click());
  assert.ok(f.container.querySelector('dialog[open]'));await act(async()=>f.container.querySelector('dialog input[type=checkbox]').click());
  await act(async()=>f.button('Discard edits & close').click());assert.equal(preferences.confirmCloseDocument,false);assert.equal(preferences.confirmQuit,true);
  await act(async()=>editorProps.onChange([newObject('text',1)],[]));
  await act(async()=>f.container.querySelector('[aria-label="Close second-dirty.pdf"]').click());
  assert.equal(f.container.querySelector('dialog[open]'),null);assert.equal(requests.filter(request=>request.method==='DELETE').length,2);
 }finally{await f.dispose();}
});

test('PDF refresh can remember its reset decision without changing other reminders',async()=>{
 const doc={...notificationDoc('refresh-choice'),kind:'text',sourceKind:'text',revision:0},preferences={confirmQuit:true,confirmCloseDocument:true,confirmRefreshPdf:true};let revision=0;
 const f=await notificationAppFixture([doc],async(path,body)=>{
  if(path==='/preferences'){Object.assign(preferences,body);return {...preferences};}
  if(path.endsWith('/source'))return {text:'Original text',kind:'text',encoding:'utf-8',warnings:[],layout:{paper:'A4',orientation:'portrait',fontSize:11,wrap:true}};
  if(path.endsWith('/prepare'))return {id:'refresh-choice'};
  if(path==='/source-jobs/refresh-choice')return {done:true,error:''};
  if(path.endsWith('/commit'))return {...doc,revision:++revision};return {};
 },preferences);
 try{
  for(let round=0;round<2;round++){
   await act(async()=>f.button('Edit / Fill').click());await act(async()=>editorProps.onChange([newObject('text',1)],[]));
   await act(async()=>f.button('Read').click());await act(async()=>f.button('PDF layout').click());
   await act(async()=>f.container.querySelector('.source-layout button.primary').click());
   if(round===0){assert.ok(f.container.querySelector('dialog[open]'));await act(async()=>f.container.querySelector('dialog input[type=checkbox]').click());await act(async()=>f.button('Refresh preview').click());}
   assert.equal(f.container.querySelector('dialog[open]'),null);assert.equal(revision,round+1);
   // The settings panel stays open while its PDF is refreshed.
   await act(async()=>f.button('PDF layout').click());
  }
  assert.deepEqual(preferences,{confirmQuit:true,confirmCloseDocument:true,confirmRefreshPdf:false});
 }finally{await f.dispose();}
});

test('cancelling a batch keeps ready files and the current reader without a dialog',async()=>{
 const existing=notificationDoc('kept-reading'),ready=notificationDoc('ready-before-cancel');let cancelled=false,polls=0;
 globalThis.studioUpload=async()=>({id:'cancel-batch'});
 const f=await notificationAppFixture([existing],async path=>{
  if(path.endsWith('/cancel')){cancelled=true;return {};}
  if(path.startsWith('/import-jobs/'))return {phase:cancelled?'cancelled':'converting',done:cancelled,cancelled,current:'slow.docx',total:3,completed:1,ready:1,index:2,documents:polls++===0?[ready]:[],errors:[],files:[{index:0,phase:'ready'},{index:1,phase:cancelled?'cancelled':'converting'},{index:2,phase:cancelled?'cancelled':'queued'}]};return {};
 });
 try{
  const viewport=f.container.querySelector('.reader-pages');viewport.scrollTop=123;
  await act(async()=>f.drop([new File(['pdf'],'ready.pdf'),new File(['office'],'slow.docx'),new File(['pdf'],'queued.pdf')]));
  await act(async()=>new Promise(resolve=>setTimeout(resolve,280)));
  await act(async()=>f.button('Cancel remaining').click());assert.equal(cancelled,true);assert.equal(f.container.querySelector('.toast-progress button').disabled,true);
  await act(async()=>new Promise(resolve=>setTimeout(resolve,450)));
  assert.match(f.container.querySelector('.notification-stack').textContent,/Import cancelled/);assert.equal(f.container.querySelector('.reader-pages'),viewport);assert.equal(viewport.scrollTop,123);
  assert.equal(f.container.querySelectorAll('.pending-source').length,0);assert.equal(f.container.querySelectorAll('.source').length,2);assert.equal(f.container.querySelector('dialog[open]'),null);
 }finally{await f.dispose();}
});

test('cancelling PDF preparation keeps the working text draft and avoids committing',async()=>{
 const doc={...notificationDoc('cancel-preview'),sourceKind:'text',kind:'text'};let cancelled=false,commits=0;
 const f=await notificationAppFixture([doc],async path=>{
  if(path.endsWith('/source'))return {text:'Original',kind:'text',encoding:'utf-8',warnings:[],layout:{paper:'A4',orientation:'portrait',fontSize:11,wrap:true}};
  if(path.endsWith('/prepare'))return {id:'cancel-preview'};
  if(path.endsWith('/cancel')){cancelled=true;return {};}
  if(path.endsWith('/commit')){commits++;return doc;}
  if(path==='/source-jobs/cancel-preview')return {done:cancelled,cancelled,error:''};return {};
 });
 try{
  await act(async()=>f.button('Edit text').click());const input=f.container.querySelector('.source-text-editor');
  await act(async()=>{Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set.call(input,'Keep my draft');input.dispatchEvent(new window.Event('input',{bubbles:true}));});
  await act(async()=>f.button('Update PDF preview').click());await act(async()=>new Promise(resolve=>setTimeout(resolve,280)));
  await act(async()=>f.button('Cancel preparation').click());await act(async()=>new Promise(resolve=>setTimeout(resolve,450)));
  assert.equal(commits,0);assert.ok(f.container.querySelector('.source-draft-notice'));assert.equal(f.container.querySelector('.source-text-editor').value,'Keep my draft');assert.match(f.container.querySelector('.notification-stack').textContent,/PDF preparation cancelled/);
 }finally{await f.dispose();}
});

test('background imports preserve reading position and focus, expose ready files early and defer passwords',async()=>{
 const existing=notificationDoc('reading'),added=notificationDoc('added');let polls=0;
 const error={index:1,name:'locked.pdf',error:'This PDF needs a password. Enter its password and add it again.'};
 const f=await notificationAppFixture([existing],async path=>{
  if(path.startsWith('/import-jobs/'))return ++polls===1?
   {phase:'opening',current:'locked.pdf',index:2,total:2,completed:1,ready:1,done:false,documents:[added],errors:[],files:[{index:0,phase:'ready'},{index:1,phase:'opening'}]}:
   {phase:'complete',current:'locked.pdf',index:2,total:2,completed:2,ready:1,done:true,documents:[],errors:[error],files:[{index:0,phase:'ready'},{index:1,phase:'error'}]};
  return {};
 });
 globalThis.studioUpload=async()=>({id:'background'});
 try{
  await act(async()=>f.container.querySelector('[aria-label="Next page"]').click());
  const viewport=f.container.querySelector('.reader-pages'),canvas=f.container.querySelector('canvas'),search=f.container.querySelector('[data-reader-search]');
  viewport.scrollTop=120;viewport.scrollLeft=60;search.focus();
  await act(async()=>f.drop([new File(['pdf'],'added.pdf'),new File(['locked'],'locked.pdf')]));
  assert.equal(f.container.querySelector('.source.active').textContent.includes(existing.name),true);
  assert.equal(f.container.querySelector('.reader-controls input').value,'2');assert.equal(f.container.querySelector('.reader-pages'),viewport);
  assert.equal(f.container.querySelector('canvas'),canvas);assert.equal(document.activeElement,search);assert.equal(viewport.scrollTop,120);assert.equal(viewport.scrollLeft,60);
  assert.equal(f.container.querySelectorAll('.source:not(.pending-source)').length,2);assert.equal(f.container.querySelectorAll('.pending-source').length,1);
  assert.equal(f.container.querySelector('.busy-overlay'),null);assert.equal(f.container.querySelector('dialog[open]'),null);
  await act(async()=>new Promise(resolve=>setTimeout(resolve,460)));
  assert.match(f.container.querySelector('.pending-source').textContent,/Password required/);assert.equal(f.container.querySelector('dialog[open]'),null);
  assert.equal(document.activeElement,search);assert.match(f.container.querySelector('.toast-warning').textContent,/1 file ready · 1 need attention/);
  await act(async()=>f.button('View details').click());assert.match(f.container.querySelector('.toast-details').textContent,/locked.pdf/);
  await act(async()=>f.button('Enter password').click());assert.match(f.container.querySelector('dialog[open]').textContent,/locked.pdf/);
  await act(async()=>f.button('Cancel').click());assert.equal(f.container.querySelector('dialog[open]'),null);assert.ok(f.button('Enter password'));
 }finally{await f.dispose();}
});

test('choosing a workflow during the first import is preserved when the file becomes ready',async()=>{
 let polls=0;const doc=notificationDoc('first-ready');
 const f=await notificationAppFixture([],async()=>++polls===1?
  {phase:'converting',current:'first.docx',index:1,total:1,completed:0,ready:0,done:false,documents:[],errors:[],files:[{index:0,phase:'converting'}]}:
  {phase:'complete',current:'first.docx',index:1,total:1,completed:1,ready:1,done:true,documents:[doc],errors:[],files:[{index:0,phase:'ready'}]});
 globalThis.studioUpload=async()=>({id:'first-import'});
 try{
  await act(async()=>f.drop([new File(['pdf'],'first.pdf')]));
  await act(async()=>f.button('Tools').click());
  await act(async()=>new Promise(resolve=>setTimeout(resolve,460)));
  assert.equal(f.container.querySelector('nav [aria-current=page]').textContent,'Tools');
  assert.equal(f.container.querySelectorAll('.source:not(.pending-source)').length,1);
  assert.equal(f.container.querySelector('dialog[open]'),null);
 }finally{await f.dispose();}
});

test('Save a copy goes straight to native Save As and keeps canceled or failed results available',async()=>{
 const saved=[];let outcome={cancelled:true};
 globalThis.studioNativeSave=async artifact=>{saved.push(artifact);if(outcome instanceof Error)throw outcome;return outcome;};
 const f=await notificationAppFixture([notificationDoc('save-source')],async()=>({id:'output',name:'edited.pdf',size:100,url:'/api/artifacts/output'}));
 try{
  await act(async()=>f.button('Edit / Fill').click());await act(async()=>f.button('Save a copy').click());
  assert.equal(saved.length,1);assert.equal(f.container.querySelector('dialog[open]'),null);assert.match(f.container.querySelector('.toast-info').textContent,/Save canceled/);
  assert.equal(f.container.querySelector('.toast-actions a').getAttribute('download'),'edited.pdf');
  outcome=new Error('The destination is not writable.');await act(async()=>f.button('Save As…').click());
  assert.equal(saved.length,2);assert.match(f.container.querySelector('.toast-error').textContent,/not writable/);assert.equal(f.container.querySelectorAll('.toast').length,1);
  outcome={cancelled:false,name:'chosen.pdf'};await act(async()=>f.button('Retry Save As…').click());
  assert.equal(saved.length,3);assert.match(f.container.querySelector('.toast-success').textContent,/chosen.pdf/);assert.ok(f.button('Save last result…'));
 }finally{await f.dispose();}
});

test('clean files close immediately while unsaved edits require a decision',async()=>{
 const f=await notificationAppFixture([notificationDoc('clean'),notificationDoc('edited')],async()=>({ok:true}));
 try{
  await act(async()=>f.container.querySelector('[aria-label="Close clean.pdf"]').click());
  assert.equal(f.container.querySelector('dialog[open]'),null);assert.equal(f.container.querySelectorAll('.source').length,1);
  await act(async()=>f.button('Edit / Fill').click());
  await act(async()=>editorProps.onChange([newObject('text',1)],[]));
  await act(async()=>f.container.querySelector('[aria-label="Close edited.pdf"]').click());
  assert.match(f.container.querySelector('dialog[open]').textContent,/Unsaved edits/);assert.equal(editorProps.objects.length,1);
  await act(async()=>f.button('Keep open').click());assert.equal(editorProps.objects.length,1);
 }finally{await f.dispose();}
});

test('toast timers pause for keyboard interaction and messages never take focus',async()=>{
 const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 const notice={id:'brief',tone:'success',title:'Files ready',duration:70};
 function Harness(){const [notices,setNotices]=React.useState([notice]);return React.createElement(React.Fragment,null,React.createElement('input',{'aria-label':'Continue typing'}),React.createElement(Notifications,{notices,onDismiss:id=>setNotices(items=>items.filter(item=>item.id!==id))}));}
 try{
  await act(async()=>root.render(React.createElement(Harness)));
  const input=container.querySelector('input');input.focus();assert.equal(document.activeElement,input);
  await act(async()=>container.querySelector('[aria-label="Dismiss Files ready"]').focus());
  await act(async()=>new Promise(resolve=>setTimeout(resolve,110)));assert.ok(container.querySelector('.toast-success'));
  await act(async()=>input.focus());await act(async()=>new Promise(resolve=>setTimeout(resolve,110)));
  assert.equal(container.querySelector('.toast'),null);assert.equal(document.activeElement,input);
 }finally{await act(async()=>root.unmount());container.remove();}
});

test('Left and Right turn pages from the document and sidebar while controls and dialogs keep their keys',async()=>{
 const f=await notificationAppFixture([notificationDoc('keyboard')],async()=>({}));
 const key=(target,name,options={})=>{const event=new window.KeyboardEvent('keydown',{key:name,bubbles:true,cancelable:true,...options});target.dispatchEvent(event);return event.defaultPrevented;};
 const page=()=>f.container.querySelector('.reader-controls input').value;
 try{
  const viewport=f.container.querySelector('.reader-pages');viewport.focus();
  await act(async()=>assert.equal(key(viewport,'ArrowRight'),true));assert.equal(page(),'2');
  await act(async()=>assert.equal(key(f.container.querySelector('.source-select'),'ArrowRight'),true));assert.equal(page(),'3');
  await act(async()=>assert.equal(key(viewport,'ArrowLeft'),true));assert.equal(page(),'2');
  for(const target of [f.container.querySelector('[data-reader-search]'),f.container.querySelector('[aria-label="Zoom"]')]){
   await act(async()=>assert.equal(key(target,'ArrowRight'),false));assert.equal(page(),'2');
  }
  await act(async()=>{assert.equal(key(viewport,'ArrowRight',{ctrlKey:true}),false);assert.equal(key(viewport,'ArrowRight',{shiftKey:true}),false);assert.equal(key(viewport,'ArrowDown'),false);});assert.equal(page(),'2');
  const editable=document.createElement('div'),child=document.createElement('span');editable.contentEditable='true';editable.setAttribute('contenteditable','true');editable.append(child);viewport.append(editable);
  await act(async()=>assert.equal(key(child,'ArrowRight'),false));assert.equal(page(),'2');editable.remove();
  await act(async()=>f.container.querySelector('[aria-label="Quit PDF Studio"]').click());
  await act(async()=>assert.equal(key(f.button('Keep working'),'ArrowRight'),false));assert.equal(page(),'2');
 }finally{await f.dispose();}
});

test('HTML opens in its original sandboxed reader and prepares PDF only after a user action',async()=>{
 const original={...notificationDoc('html-source'),kind:'html',sourceKind:'html',revision:0,pages:[],pdfReady:false};
 const prepared={...original,pages:notificationDoc('pages').pages,pdfReady:true,revision:1,url:'/prepared.pdf'};
 const calls=[];let committed=false;
 const f=await notificationAppFixture([original],async(path,body)=>{
  calls.push({path,body});
  if(path.endsWith('/source'))return {text:'<h1>Report</h1>',html:'<!doctype html><h1>Report</h1>',kind:'html',encoding:'utf-8',warnings:[],layout:{paper:'A4',orientation:'portrait',fontSize:11,wrap:true}};
  if(path.endsWith('/prepare'))return {id:'prepare-html'};
  if(path==='/source-jobs/prepare-html')return {done:true,error:''};
  if(path.endsWith('/commit')){committed=true;return prepared;}
  return {};
 });
 try{
  const iframe=f.container.querySelector('iframe');assert.ok(iframe);assert.equal(iframe.getAttribute('sandbox'),'');assert.match(iframe.srcdoc,/Report/);
  assert.equal(f.container.querySelector('.reader-pages'),null);assert.equal(calls.some(call=>call.path.endsWith('/prepare')),false);
  assert.equal(f.button('Edit / Fill').disabled,true);assert.equal(f.container.querySelector('dialog[open]'),null);
  await act(async()=>f.button('Prepare PDF').click());
  assert.equal(committed,true);assert.ok(f.container.querySelector('.reader-pages'));assert.equal(f.button('Edit / Fill').disabled,false);
  assert.ok(f.button('Save as PDF…'));assert.equal(f.container.querySelector('dialog[open]'),null);
  await act(async()=>f.button('Read original').click());assert.ok(f.container.querySelector('iframe'));
 }finally{await f.dispose();}
});

test('text drafts and layout changes persist across views and require a fresh PDF before saving',async()=>{
 const doc={...notificationDoc('draft-text'),kind:'text',sourceKind:'text',revision:0};let text='Original log text';const requests=[];
 globalThis.studioUpload=async()=>({id:'draft-import'});
 const f=await notificationAppFixture([],async(path,body)=>{
  requests.push({path,body});
  if(path.startsWith('/import-jobs/'))return {done:true,completed:1,total:1,documents:[doc],errors:[],files:[]};
  if(path.endsWith('/source'))return {text,html:'',kind:'text',encoding:'utf-8',warnings:[],layout:{paper:'A4',orientation:'portrait',fontSize:11,wrap:true}};
  if(path.endsWith('/prepare')){text=body.content;return {id:'text-job'};}
  if(path==='/source-jobs/text-job')return {done:true,error:''};
  if(path.endsWith('/commit'))return {...doc,revision:1};
  return {};
 });
 try{
  await act(async()=>f.drop([new File(['Original log text'],'draft-text.txt')]));
  assert.match(f.container.querySelector('.source-text').textContent,/Original log text/);
  await act(async()=>f.button('Edit text').click());
  const input=f.container.querySelector('[aria-label="Working text copy"]');
  await act(async()=>{Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set.call(input,'Edited working copy');input.dispatchEvent(new window.Event('input',{bubbles:true}));});
  assert.ok(f.container.querySelector('.source-draft-notice'));assert.equal(f.button('Save as PDF…').disabled,true);assert.equal(f.button('Edit / Fill').disabled,true);
  await act(async()=>[...f.container.querySelectorAll('.toast button')].find(button=>button.textContent==='Save as PDF…').click());
  assert.equal(requests.some(request=>request.path==='/export/original'),false,'A retained toast action also checks the current draft');
  await act(async()=>f.button('Tools').click());await act(async()=>f.button('Read').click());
  assert.match(f.container.querySelector('.source-text').textContent,/Edited working copy/);
  await act(async()=>f.container.querySelector('[aria-label="Close draft-text.pdf"]').click());assert.match(f.container.querySelector('dialog[open]').textContent,/Unsaved edits/);
  await act(async()=>f.button('Keep open').click());
  await act(async()=>f.button('PDF layout').click());
  const orientation=[...f.container.querySelectorAll('.source-layout .field')].find(label=>label.textContent.startsWith('Orientation')).querySelector('select');
  await act(async()=>{orientation.value='landscape';orientation.dispatchEvent(new window.Event('change',{bubbles:true}));});
  await act(async()=>f.container.querySelector('.source-layout button.primary').click());
  const request=requests.find(call=>call.path.endsWith('/prepare'));assert.equal(request.body.content,'Edited working copy');assert.equal(request.body.options.orientation,'landscape');
  assert.equal(f.container.querySelector('.source-draft-notice'),null);assert.equal(f.button('Save as PDF…').disabled,false);assert.ok(f.container.querySelector('.reader-pages'));
 }finally{await f.dispose();}
});

test('uncertain text gets an optional per-file action and remembered encoding without a modal',async()=>{
 let uploaded=0;const options=[];const good={...notificationDoc('image'),kind:'image'};
 const legacy={...notificationDoc('legacy'),sourceKind:'text',kind:'text'};
 globalThis.studioUpload=async(files,password,progress,extra)=>{options.push({files,extra});return {id:'text-'+(++uploaded)};};
 const f=await notificationAppFixture([notificationDoc('continue-reading')],async path=>{
  if(path.startsWith('/import-jobs/text-1'))return {phase:'complete',done:true,ready:1,total:2,completed:2,index:2,current:'legacy.blob',documents:[good],errors:[{index:1,name:'legacy.blob',code:'open-as-text',error:'This may be text in another encoding.'}],files:[{index:0,phase:'ready'},{index:1,phase:'error'}]};
  if(path.startsWith('/import-jobs/'))return {phase:'complete',done:true,ready:1,total:1,completed:1,index:1,current:'legacy.blob',documents:[legacy],errors:[],files:[{index:0,phase:'ready'}]};
  return {};
 });
 try{
  const files=[new File(['image'],'image.png'),new File(['legacy'],'legacy.blob')];await act(async()=>f.drop(files));
  assert.deepEqual(options[0].files,files);assert.equal(f.container.querySelector('dialog[open]'),null);assert.ok(f.button('Open as text'));
  const encoding=f.container.querySelector('[aria-label="Text encoding for legacy.blob"]');
  await act(async()=>{encoding.value='cp874';encoding.dispatchEvent(new window.Event('change',{bubbles:true}));});
  await act(async()=>f.container.querySelector('.text-fallback-options input[type=checkbox]').click());
  await act(async()=>f.button('Open as text').click());
  assert.equal(options[1].extra.forceText,true);assert.equal(options[1].extra.encoding,'cp874');assert.equal(JSON.parse(localStorage.getItem('pdfstudio.textDefaults'))['.blob'],'cp874');
  assert.equal(f.container.querySelector('dialog[open]'),null);assert.match(f.container.querySelector('.source.active').textContent,/continue-reading/);
  assert.ok([...f.container.querySelectorAll('.toast')].some(toast=>toast.textContent.includes('Opened as text')));
  await act(async()=>f.drop([new File(['more'],'another.blob')]));assert.equal(options[2].extra.textDefaults['.blob'],'cp874');
 }finally{await f.dispose();}
});

test('conversion tools keep HTML optional and export chosen PDFs separately',async()=>{
 const html={...notificationDoc('original-html'),sourceKind:'html',pages:[]},pdf=notificationDoc('ready');const saves=[],prepares=[],calls=[];
 const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 globalThis.studioApi=async(path,body)=>{calls.push({path,body});return {id:'separate',name:'converted.zip',size:100,url:'/converted.zip'};};
 try{
  await act(async()=>root.render(React.createElement(Tools,{doc:html,docs:[html,pdf],onImport:async()=>[],onSave:artifact=>saves.push(artifact),onPrepare:doc=>prepares.push(doc.id),run:async(_message,operation)=>operation()})));
  assert.equal(container.querySelectorAll('input[type=radio]').length,1);
  await act(async()=>[...container.querySelectorAll('.tool-tile')].find(button=>button.textContent.includes('Convert to PDF')).click());
  const boxes=[...container.querySelectorAll('.converted-files input[type=checkbox]')];assert.equal(boxes[0].disabled,true);assert.equal(boxes[1].disabled,false);assert.equal(prepares.length,0);
  await act(async()=>boxes[1].click());
  await act(async()=>[...container.querySelectorAll('button')].find(button=>button.textContent==='Save selected PDFs separately (ZIP)').click());
  assert.deepEqual(calls.at(-1),{path:'/export/separate',body:{ids:[pdf.id]}});assert.equal(saves[0].name,'converted.zip');
  await act(async()=>[...container.querySelectorAll('button')].find(button=>button.textContent==='Prepare PDF').click());assert.deepEqual(prepares,[html.id]);
 }finally{await act(async()=>root.unmount());container.remove();}
});

test('brand logos use small prepared assets with explicit dimensions and retina choices',async()=>{
 const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 try{
  for(const size of [24,40,72]){
   await act(async()=>root.render(React.createElement(BrandLogo,{size})));
   const img=container.querySelector('img');assert.equal(img.getAttribute('src'),`/branding/pdfstudio-${size}.png`);assert.equal(img.getAttribute('srcset'),`/branding/pdfstudio-${size*2}.png 2x`);
   assert.equal(img.width,size);assert.equal(img.height,size);assert.equal(img.alt,'');assert.equal(img.getAttribute('aria-hidden'),'true');
   assert.doesNotMatch(img.src,/master|docs|1254/);
  }
 }finally{await act(async()=>root.unmount());container.remove();}
});

test('feedback opens beside the document without remounting or changing its page',async()=>{
 const f=await notificationAppFixture([notificationDoc('feedback-reader')],async()=>({}));
 try{
  const reader=f.container.querySelector('.reader'),loads=globalThis.readerLoads;
  const next=f.container.querySelector('[aria-label="Next page"]');
  if(next)await act(async()=>next.click());
  const page=f.container.querySelector('.reader-controls input').value;
  const button=f.container.querySelector('[aria-label="Feedback"]');
  await act(async()=>button.click());
  const panel=f.container.querySelector('#pdfstudio-feedback');
  assert.equal(panel.hidden,false);assert.equal(button.getAttribute('aria-expanded'),'true');
  assert.match(panel.textContent,/Connect your Microsoft Form/);
  assert.equal(panel.querySelector('iframe'),null);
  assert.equal(panel.querySelector('.forms-preview-submit').disabled,true);
  assert.equal(f.container.querySelector('.reader'),reader);assert.equal(globalThis.readerLoads,loads);
  const close=panel.querySelector('[aria-label="Close feedback"]');
  await act(async()=>close.dispatchEvent(new window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true})));
  assert.equal(f.container.querySelector('.reader-controls input').value,page);
  await act(async()=>close.click());
  assert.equal(panel.hidden,true);assert.equal(document.activeElement,button);
  assert.equal(f.container.querySelector('.reader'),reader);
  assert.equal(f.container.querySelector('.reader-controls input').value,page);
 }finally{await f.dispose();}
});

test('embedded feedback loads on first opening and keeps its iframe when hidden',async()=>{
 const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
 let closed=0;const props={config:{url:'https://forms.office.com/Pages/ResponsePage.aspx?id=synthetic&embed=true'},onClose:()=>closed++,onConfigure(){}};
 try{
  await act(async()=>root.render(React.createElement(FeedbackPanel,{...props,open:false})));
  assert.equal(container.querySelector('iframe'),null);
  await act(async()=>root.render(React.createElement(FeedbackPanel,{...props,open:true})));
  const frame=container.querySelector('iframe');assert.ok(frame);
  assert.equal(frame.title,'PDF Studio feedback — Microsoft Forms');
  assert.ok(!frame.getAttribute('sandbox').includes('allow-top-navigation'));
  await act(async()=>root.render(React.createElement(FeedbackPanel,{...props,open:false})));
  assert.equal(container.querySelector('iframe'),frame);assert.equal(container.querySelector('aside').hidden,true);
  await act(async()=>root.render(React.createElement(FeedbackPanel,{...props,open:true})));
  assert.equal(container.querySelector('iframe'),frame);
  await act(async()=>container.querySelector('[aria-label="Close feedback"]').dispatchEvent(new window.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true})));
  assert.equal(closed,1);
 }finally{await act(async()=>root.unmount());container.remove();}
});

test('feedback stays off the landing page and is discoverable through Settings',async()=>{
 const f=await notificationAppFixture([],async()=>({}));
 try{
  assert.equal(f.container.querySelector('.app-header [aria-label="Feedback"]'),null);
  assert.equal(f.container.querySelector('#pdfstudio-feedback').hidden,true);
  const settings=f.container.querySelector('[aria-label="Settings"]');
  await act(async()=>settings.click());
  const share=[...f.container.querySelectorAll('button')].find(button=>button.textContent==='Share feedback');
  assert.ok(share);await act(async()=>share.click());
  assert.equal(f.container.querySelector('#pdfstudio-feedback').hidden,false);
  assert.equal(f.container.querySelector('dialog[open]'),null);
  await act(async()=>f.container.querySelector('[aria-label="Close feedback"]').click());
  assert.equal(document.activeElement,settings);
 }finally{await f.dispose();}
});
