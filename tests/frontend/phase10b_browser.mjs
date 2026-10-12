// Real Chromium + FastAPI acceptance. Screenshots/profiles/downloads stay private.
import {spawn} from 'node:child_process';
import {mkdir,readFile,writeFile,readdir,stat} from 'node:fs/promises';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import assert from 'node:assert/strict';
const root=process.cwd(),url=process.env.CADENCE_UI_URL||'http://127.0.0.1:8766';
const inputFile=process.env.CADENCE_UI_FIXTURE||path.join(root,'Cadence_Financial_Group_Organizational_Pack.pptx');
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
 await evaluate("document.querySelector('[aria-label=\"Filter Review\"]').click()");await waitFor(()=>evaluate("Boolean(document.querySelector('.finding-select'))"));await evaluate("document.querySelector('.finding-select').click()");await waitFor(()=>evaluate("[...document.querySelectorAll('button')].some(x=>x.textContent.trim()==='Confirm as PII')"));await screenshot('review.png');await click('Confirm as PII');await waitFor(()=>evaluate("Boolean(document.querySelector('[role=dialog]'))"));await screenshot('review-dialog.png');await click('Confirm & Regenerate');await waitFor(()=>evaluate("Boolean(document.querySelector('.revision-feedback'))&&!document.querySelector('[role=dialog]')&&!document.querySelector('.loading-line')"));
 await click('Overview');await waitFor(()=>evaluate("Boolean(document.querySelector('[aria-label^=\"Privacy decision funnel:\"]'))"));
 const after=await evaluate("({counts:[...document.querySelectorAll('.funnel-hit-zones button span')].map(x=>Number(x.textContent.replaceAll(',',''))),message:document.querySelector('.revision-feedback').textContent,coverage:document.querySelector('.coverage-status strong').textContent})");assert.equal(after.counts[1],before.counts[1]+1);assert.equal(after.counts[2],before.counts[2]-1);assert.match(after.message,/Audit revision 0 → 1/);assert.equal(after.coverage,'NOT ESTABLISHED');await screenshot('reviewed.png');
 await click('Artifact verification');await waitFor(()=>evaluate("Boolean(document.querySelector('.artifact-actions a'))"));await screenshot('verification.png');await evaluate("document.querySelector('.artifact-actions a').click()");await waitFor(()=>downloaded);const downloadedFiles=await readdir(path.join(work,'downloads'));const file=downloadedFiles.find(x=>/\.(pdf|docx|pptx)$/.test(x));assert.ok(file);const bytes=(await stat(path.join(work,'downloads',file))).size;assert.ok(bytes>1000);
 if(inputFile.toLowerCase().endsWith('.pdf')){await click('Preview PDF');await waitFor(()=>evaluate("document.querySelector('.pdf-preview')?.contentDocument?.contentType === 'application/pdf'"));await sleep(1000);await screenshot('pdf-preview.png');}
 await command('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false},sid);
 await screenshot('laptop.png');assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'),true);
 await command('Emulation.setDeviceMetricsOverride',{width:820,height:1100,deviceScaleFactor:1,mobile:false},sid);
 await screenshot('tablet.png');assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'),true);
 await command('Emulation.clearDeviceMetricsOverride',{},sid);
 let expectedRevision=1;
 if(synthetic){
  await evaluate("[...document.querySelectorAll('nav button')].find(x=>x.textContent.startsWith('Review Queue')).click()");await click('Find missed PII');
  await waitFor(()=>evaluate("Boolean(document.querySelector('#source-text')?.textContent)"));
  if(inputFile.toLowerCase().endsWith('.docx'))await evaluate("(()=>{const s=document.querySelector('#source-location');s.value=s.options[s.options.length-1].value;s.dispatchEvent(new Event('change',{bubbles:true}));})()");
  await waitFor(()=>evaluate("document.querySelector('#source-text')?.textContent.includes('SecretToken')"));
  await evaluate("(()=>{const box=document.querySelector('#source-text');const walker=document.createTreeWalker(box,NodeFilter.SHOW_TEXT);let node;while(node=walker.nextNode()){const i=node.textContent.indexOf('SecretToken');if(i>=0){const range=document.createRange();range.setStart(node,i);range.setEnd(node,i+11);const s=window.getSelection();s.removeAllRanges();s.addRange(range);box.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));break;}}})()");
  await waitFor(()=>evaluate("[...document.querySelectorAll('button')].some(x=>x.textContent.trim()==='Add missed PII'&&!x.disabled)"));await click('Add missed PII');await click('Submit MISSED_PII');
  await waitFor(()=>evaluate("document.querySelector('.revision-feedback')?.textContent.includes('Audit revision 1 → 2')&&!document.querySelector('.loading-line')"));
  await click('All');await waitFor(()=>evaluate("[...document.querySelectorAll('.finding-select')].some(x=>x.textContent.includes('H000001'))"));await evaluate("[...document.querySelectorAll('.finding-select')].find(x=>x.textContent.includes('H000001')).click()");await waitFor(()=>evaluate("[...document.querySelectorAll('button')].some(x=>x.textContent.trim()==='Mark False Positive')"));await click('Mark False Positive');await click('Mark False Positive & Regenerate');
  await waitFor(()=>evaluate("document.querySelector('.revision-feedback')?.textContent.includes('Audit revision 2 → 3')&&!document.querySelector('.loading-line')"));expectedRevision=3;
 }
 await click('Audit');await waitFor(()=>evaluate("Boolean(document.querySelector('.timeline .human'))"));await screenshot('audit.png');await click('Save audit');await waitFor(()=>evaluate(`document.querySelector('.audit-heading')?.textContent.includes('Saved revision ${expectedRevision}') && !document.querySelector('.processing-banner')`));
 await click('Documents');await waitFor(()=>evaluate("[...document.querySelectorAll('.saved-list button')].length>0"));await evaluate("document.querySelector('.saved-list button:last-child').click()");await waitFor(()=>evaluate("Boolean(document.querySelector('[aria-label^=\"Privacy decision funnel:\"]'))&&!document.querySelector('.loading-line')"));
 await click('Detector Quality');await waitFor(()=>evaluate("Boolean(document.querySelector('.metrics-disclaimer'))"));assert.equal(await evaluate("document.querySelector('.metrics-disclaimer').textContent.includes('Measured on synthetic labeled evaluation dataset')"),true);await screenshot('quality.png');
 await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true},sid);await screenshot('mobile.png');assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'),true);
 await evaluate("[...document.querySelectorAll('nav button')].find(x=>x.textContent.startsWith('Review Queue')).click()");await waitFor(()=>evaluate("Boolean(document.querySelector('.review-workspace'))"));await screenshot('mobile-review.png');assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'),true);
 await writeFile(path.join(work,'browser-errors.json'),JSON.stringify({runtime:errors,security:securityErrors,failedRequests},null,2));
 assert.equal(await evaluate("Boolean(document.querySelector('[role=alert]'))"),false);
 assert.equal(failedRequests.length,0);
 assert.equal(errors.length,0);assert.equal(securityErrors.length,0);
 const summary={passed:true,format:path.extname(inputFile).slice(1),before_counts:before.counts,after_counts:after.counts,download_bytes:bytes,save_reload:true,synthetic_feedback:synthetic?['CONFIRM_PII','MISSED_PII','FALSE_POSITIVE']:['CONFIRM_PII'],saved_revision:expectedRevision,synthetic_metrics_disclaimer:true,mobile_no_horizontal_overflow:true,runtime_errors:errors.length,security_errors:securityErrors.length};
 await writeFile(path.join(work,'summary.json'),JSON.stringify(summary,null,2));await writeFile(path.join(root,'.private_review_app','phase10b-ui','latest.json'),JSON.stringify({work,summary},null,2));console.log(JSON.stringify(summary));
 await command('Browser.close');
}catch(error){await writeFile(path.join(work,'failure.json'),JSON.stringify({message:error.message}));console.error('UI acceptance failed; private diagnostics retained.');process.exitCode=1;}
finally{socket?.close();browser.kill();}
