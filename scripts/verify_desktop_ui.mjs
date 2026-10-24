// Real WebView2 check against a packaged EXE, using synthetic files only.
// Prepare with: npm.cmd install --prefix build/desktop-qa --ignore-scripts playwright-core
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {createServer} from 'node:net';
import {resolve} from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
import {chromium} from '../build/desktop-qa/node_modules/playwright-core/index.mjs';

const executable=resolve(process.argv[2]||'dist/update-0.1.012/PDFStudio/PDFStudio.exe');
const directory=resolve('tmp/desktop-webview2-qa');
await mkdir(directory,{recursive:true});
const fixture=resolve(directory,'synthetic-desktop.pdf');
execFileSync('python',['-c',"import fitz,sys;d=fitz.open();p=d.new_page(width=420,height=550);p.insert_text((40,60),'PDF Studio desktop check',fontsize=18);p.insert_text((40,100),'Synthetic local document. Export and save a copy.');d.save(sys.argv[1]);d.close()",fixture]);
const fingerprint=async()=>createHash('sha256').update(await readFile(fixture)).digest('hex');
const original=await fingerprint();
const freePort=()=>new Promise(resolve=>{const listener=createServer();listener.listen(0,'127.0.0.1',()=>{const port=listener.address().port;listener.close(()=>resolve(port));});});
const apiPort=await freePort(),cdpPort=await freePort();
const base=`http://127.0.0.1:${apiPort}`;
const child=spawn(executable,[fixture,'--port',String(apiPort),'--data-dir',resolve(directory,'settings')],{
 cwd:process.cwd(),stdio:'ignore',windowsHide:false,
 env:{...process.env,WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:`--remote-debugging-port=${cdpPort} --remote-debugging-address=127.0.0.1`},
});
let browser,page;
try{
 let ready=false;
 for(let n=0;n<180;n++){
  if(child.exitCode!==null)throw Error('Desktop app exited before creating its window');
  try{const response=await fetch(`http://127.0.0.1:${cdpPort}/json/version`);if(response.ok){ready=true;break;}}catch{}
  await delay(500);
 }
 assert.ok(ready,'WebView2 did not start');
 browser=await chromium.connectOverCDP(`http://127.0.0.1:${cdpPort}`);
 for(let n=0;n<120;n++){
  page=browser.contexts().flatMap(context=>context.pages()).find(candidate=>candidate.url().startsWith(base));
  if(page)break;await delay(250);
 }
 assert.ok(page,'The desktop window did not load the local interface');
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.locator('.app-version').filter({hasText:'0.1.012'}).waitFor();
 await page.getByRole('button',{name:/^synthetic-desktop\.pdf/}).waitFor();
 await page.locator('.pdf-page canvas').first().waitFor();
 await page.waitForFunction(()=>[...document.querySelectorAll('.textLayer span')].some(span=>span.textContent.includes('PDF Studio desktop check')));
 await page.screenshot({path:resolve(directory,'reader-light.png')});
 console.log('PASS: packaged desktop window, backend version, Open With PDF import and PDF.js text/canvas rendering');
 await page.getByRole('button',{name:'Use dark appearance'}).click();
 await page.waitForFunction(()=>document.documentElement.classList.contains('dark'));
 await page.waitForTimeout(500);
 await page.screenshot({path:resolve(directory,'reader-dark.png')});
 await page.getByRole('button',{name:'Use light appearance'}).click();
 const voices=await page.evaluate(async()=>{for(let n=0;n<20;n++){const local=speechSynthesis.getVoices().filter(voice=>voice.localService);if(local.length)return local.map(voice=>({name:voice.name,lang:voice.lang}));await new Promise(resolve=>setTimeout(resolve,250));}return [];});
 console.log('Local WebView2 voices:',JSON.stringify(voices));
 assert.ok(voices.length,'No local Read Aloud voice is available in WebView2');
 await page.getByRole('button',{name:'Edit / Fill',exact:true}).click();
 await page.getByRole('button',{name:'Save a copy',exact:true}).click();
 const saveDialog=page.getByRole('dialog',{name:'Save your result'});
 await saveDialog.waitFor();
 const artifactUrl=await saveDialog.getByRole('link',{name:'Download',exact:true}).getAttribute('href');
 const result=await page.evaluate(async url=>{const response=await fetch(url);if(!response.ok)throw Error('Export download failed: '+response.status);return Array.from(new Uint8Array(await response.arrayBuffer()));},artifactUrl);
 await writeFile(resolve(directory,'exported-copy.pdf'),Buffer.from(result));
 execFileSync('python',['-c',"import fitz,sys;d=fitz.open(sys.argv[1]);assert 'PDF Studio desktop check' in d[0].get_text();d.close()",resolve(directory,'exported-copy.pdf')]);
 await saveDialog.getByRole('button',{name:'Later',exact:true}).click();
 assert.equal(await fingerprint(),original);
 console.log('PASS: light/dark appearance, installed local voices, real PDF export and unchanged source file');
 await page.evaluate(()=>window.dispatchEvent(new Event('pdfstudio:close-request')));
 const quitDialog=page.getByRole('dialog',{name:'Quit PDF Studio'});
 await quitDialog.waitFor();
 await page.screenshot({path:resolve(directory,'close-reminder.png')});
 await quitDialog.getByRole('button',{name:'Keep working',exact:true}).click();
 await page.getByRole('button',{name:/^synthetic-desktop\.pdf/}).waitFor();
 await page.getByRole('button',{name:'Quit PDF Studio',exact:true}).click();
 await page.getByRole('dialog',{name:'Quit PDF Studio'}).getByRole('button',{name:'Quit PDF Studio',exact:true}).click();
 for(let n=0;n<120&&child.exitCode===null;n++)await delay(250);
 assert.equal(child.exitCode,0,'Confirmed Quit did not stop the desktop process');
 assert.deepEqual(errors,[]);
 console.log('PASS: Keep working retains the document; confirmed Quit closes the desktop process');
}catch(error){
 if(page&&!page.isClosed())await page.screenshot({path:resolve(directory,'failure.png')}).catch(()=>{});
 throw error;
}finally{
 if(child.exitCode===null&&page&&!page.isClosed()){
  await page.evaluate(async()=>{const config=await(await fetch('/api/config')).json();await fetch('/api/quit',{method:'POST',headers:{'Content-Type':'application/json','X-Studio-Token':config.token},body:'{}'});}).catch(()=>{});
  for(let n=0;n<40&&child.exitCode===null;n++)await delay(250);
 }
 await browser?.close().catch(()=>{});
 if(child.exitCode===null)child.kill(); // This script owns only this synthetic test process.
}
