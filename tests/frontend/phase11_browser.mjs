// Real Chromium + FastAPI acceptance. Screenshots/profiles/downloads stay private.
import {spawn} from 'node:child_process';
import {mkdir,readFile,writeFile,readdir,stat} from 'node:fs/promises';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import assert from 'node:assert/strict';
const root=process.cwd(),url=process.env.CADENCE_UI_URL||'http://127.0.0.1:8767';
const inputFile=process.env.CADENCE_UI_FIXTURE||path.join(root,'.private_phase11','fixtures','synthetic-face.pptx');
const synthetic=process.env.CADENCE_UI_SYNTHETIC==='1';
const work=path.join(root,'.private_review_app','phase10b-ui',randomUUID());await mkdir(path.join(work,'downloads'),{recursive:true});
const browser=spawn(process.env.CADENCE_TEST_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe',
 ['--headless=new','--no-first-run','--disable-background-networking',`--user-data-dir=${path.join(work,'profile')}`,'--remote-debugging-port=0','--window-size=1540,1150','about:blank'],{windowsHide:true,stdio:'ignore'});
let socket;const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function waitFor(operation,timeout=120000){const start=Date.now();while(Date.now()-start<timeout){if(await operation())return;await sleep(200);}throw new Error('Acceptance condition timed out');}
try{
 let port;await waitFor(async()=>{try{port=(await readFile(path.join(work,'profile','DevToolsActivePort'),'utf8')).split('\n');return true;}catch{return false;}},15000);
 socket=new WebSocket(`ws://127.0.0.1:${port[0]}${port[1]}`);await new Promise((r,j)=>{socket.addEventListener('open',r,{once:true});socket.addEventListener('error',j,{once:true});});
 let counter=0;const pending=new Map(),errors=[],securityErrors=[],failedRequests=[];let downloaded=false;
 socket.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(new Error('Browser command failed')):p.resolve(m.result);}}
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text);
  if(m.method==='Log.entryAdded'&&m.params.entry.source==='security'&&m.params.entry.level==='error')securityErrors.push(m.params.entry.text);
  if(m.method==='Browser.downloadProgress'&&m.params.state==='completed')downloaded=true;
  if(m.method==='Network.responseReceived'&&m.params.response.status>=400&&m.params.response.url.includes('/api/'))failedRequests.push({path:new URL(m.params.response.url).pathname,status:m.params.response.status});
 });
 function command(method,params={},sessionId){return new Promise((resolve,reject)=>{const id=++counter;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));});}
 await command('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:path.join(work,'downloads'),eventsEnabled:true});
 const target=await command('Target.createTarget',{url});const attach=await command('Target.attachToTarget',{targetId:target.targetId,flatten:true});const sid=attach.sessionId;
 const evaluate=async expression=>{const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true},sid);if(r.exceptionDetails)throw new Error('Browser expression failed');return r.result.value;};
 await command('Runtime.enable',{},sid);await command('Page.enable',{},sid);await command('Log.enable',{},sid);await command('Network.enable',{},sid);
 const screenshot=async name=>{await sleep(350);const r=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:false},sid);await writeFile(path.join(work,name),Buffer.from(r.data,'base64'));};
 const click=async text=>evaluate(`(()=>{const e=[...document.querySelectorAll('button')].find(x=>(x.textContent.trim()===${JSON.stringify(text)}||x.getAttribute('aria-label')===${JSON.stringify(text)}));if(!e)throw new Error('Button unavailable');e.click();})()`);
 await waitFor(()=>evaluate("Boolean(document.getElementById('file-input')) && [...document.querySelectorAll('button')].some(x=>x.textContent.includes('Upload Business Artifact')&&!x.disabled)"));await screenshot('empty.png');
 const dom=await command('DOM.getDocument',{},sid);const input=await command('DOM.querySelector',{nodeId:dom.root.nodeId,selector:'#file-input'},sid);await command('DOM.setFileInputFiles',{nodeId:input.nodeId,files:[inputFile]},sid);
 await waitFor(()=>evaluate("Boolean(document.querySelector('[aria-label^=\"Privacy decision funnel:\"]')) && !document.querySelector('.loading-line')"));
 const before=await evaluate("({counts:[...document.querySelectorAll('.funnel-hit-zones button span')].map(x=>Number(x.textContent.replaceAll(',',''))),coverage:document.querySelector('.coverage-status strong').textContent,blocked:document.querySelector('.safety-grid .blocked-status strong').textContent})");
 assert.ok(before.counts[0]>0);assert.equal(before.counts[0],before.counts.slice(1).reduce((a,b)=>a+b,0));assert.equal(before.coverage,'NOT ESTABLISHED');assert.equal(before.blocked,'BLOCKED');await screenshot('overview.png');

 assert.equal(await evaluate("document.querySelector('.visual-counts div:nth-child(1) strong').textContent"),'1');
 assert.equal(await evaluate("document.querySelector('.visual-counts div:nth-child(2) strong').textContent"),'1');
 await click('Inspect face findings');
 await waitFor(()=>evaluate("document.querySelectorAll('.face-comparison img').length===2 && [...document.querySelectorAll('.face-comparison img')].every(x=>x.complete&&x.naturalWidth>0)"));
 assert.equal(await evaluate("document.querySelector('.selected-row code').textContent.startsWith('V')"),true);
 assert.equal(await evaluate("document.querySelector('.finding-facts').textContent.includes('YuNet')"),true);
 assert.equal(await evaluate("document.querySelector('.human-decision-story').textContent.includes('No correction recorded')"),true);
 assert.equal(await evaluate("document.querySelector('.face-comparison').textContent.includes('Requested blur verified in artifact')"),true);
 await evaluate("document.querySelector('.face-comparison').scrollIntoView({block:'center'})");await screenshot('synthetic-face-before-after.png');
 const cropUrls=await evaluate("[...document.querySelectorAll('.face-comparison img')].map(x=>x.src)");
 for(let i=0;i<cropUrls.length;i++)await writeFile(path.join(work,i?'after.png':'before.png'),Buffer.from(await (await fetch(cropUrls[i])).arrayBuffer()));
 await evaluate("document.querySelector('.document-header a[download]').click()");await waitFor(()=>downloaded);
 const files=await readdir(path.join(work,'downloads'));const file=files.find(x=>x.endsWith('.pptx'));assert.ok(file);
 const downloadedPath=path.join(work,'downloads',file);
 const {execFileSync}=await import('node:child_process');
 const validation=JSON.parse(execFileSync(path.join(root,'.venv','Scripts','python.exe'),['-c',
  "import sys,json; from pathlib import Path; from zipfile import ZipFile; from io import BytesIO; from PIL import Image; import numpy as np; from pptx import Presentation;\np=Path(sys.argv[1]); assert len(Presentation(p).slides)==2\nwith ZipFile(p) as z:\n part=next(n for n in z.namelist() if n.startswith('ppt/media/') and n.endswith('.png')); data=z.read(part); im=Image.open(BytesIO(data)); im.save(sys.argv[4]); assert im.size==(512,512)\nb=np.asarray(Image.open(sys.argv[2]),dtype=float); a=np.asarray(Image.open(sys.argv[3]),dtype=float); assert b.shape==a.shape and not np.array_equal(b,a)\ngrad=lambda im:abs(np.diff(im,axis=0)).mean()+abs(np.diff(im,axis=1)).mean(); ratio=float(grad(a)/grad(b)); assert ratio<.25\nprint(json.dumps({'opened':True,'blur_gradient_ratio':ratio,'media_dimensions_preserved':True}))",
  downloadedPath,path.join(work,'before.png'),path.join(work,'after.png'),path.join(work,'downloaded-blurred-media.png')],{windowsHide:true,encoding:'utf8'}));
 await click('Overview');await waitFor(()=>evaluate("!!document.querySelector('.document-hero')"));
 assert.equal(await evaluate("document.querySelector('.ai-access-card').textContent.includes('BLOCKED')"),true);
 assert.equal(await evaluate("document.querySelectorAll('.face-map-count').length"),2);
 await click('Artifact verification');await waitFor(()=>evaluate("!!document.querySelector('.face-verification')"));
 assert.equal(await evaluate("document.querySelector('.face-verification').textContent.includes('Verified requested transformations')"),true);await screenshot('face-verification.png');
 await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true},sid);
 assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'),true);
 assert.equal(errors.length,0);assert.equal(securityErrors.length,0);assert.equal(failedRequests.length,0);
 const summary={passed:true,synthetic_fixture:true,detected_faces:1,protected_faces:1,face_placements:2,blur_in_download_verified:true,...validation,runtime_errors:0,security_errors:0,coverage:'NOT ESTABLISHED',downstream:'BLOCKED'};
 await writeFile(path.join(work,'summary.json'),JSON.stringify(summary,null,2));await writeFile(path.join(root,'.private_phase11','browser-summary.json'),JSON.stringify({work,summary},null,2));console.log(JSON.stringify(summary));
 await command('Browser.close');
}catch(error){await writeFile(path.join(work,'failure.json'),JSON.stringify({message:error.message}));console.error('Face UI acceptance failed; private diagnostics retained.');process.exitCode=1;}
finally{socket?.close();browser.kill();}
