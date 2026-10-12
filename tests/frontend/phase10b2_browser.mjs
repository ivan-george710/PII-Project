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
 assert.equal(await evaluate("!!document.querySelector('.document-hero') && document.querySelector('.document-hero').textContent.includes('candidates analyzed')"),true);
 assert.equal(await evaluate("document.querySelector('.ai-access-card')?.textContent.includes('BLOCKED') && document.querySelector('.ai-access-card')?.textContent.includes('NOT ESTABLISHED')"),true);
 assert.equal(await evaluate("document.querySelector('.document-actions button')?.textContent.trim() === 'Review '+document.querySelector('.decision-stat.review strong').textContent+' Findings'"),true);
 for(const [selector,name] of [['.ai-boundary','ai-boundary.png'],['.pipeline','purpose-pipeline.png'],['.artifact-outcome','artifact-outcome.png'],['.privacy-map','sensitive-distribution.png']]){
  await evaluate(`document.querySelector('${selector}').scrollIntoView({block:'center'})`);await screenshot(name);
 }
 await evaluate('window.scrollTo(0,0)');


 if(process.env.CADENCE_UI_REPRO==='1'){
  await evaluate("document.querySelector('[aria-label=\"Filter Review\"]').click()");
  await waitFor(()=>evaluate("Boolean(document.querySelector('.review-workspace'))"));
  await sleep(700);
  const result=await evaluate("({workspaceVisible:!!document.querySelector('.review-workspace'),reviewFilterActive:document.querySelector('.segmented button[aria-pressed=true]')?.textContent,selectedRows:document.querySelectorAll('.selected-row').length,contextVisible:!!document.querySelector('.comparison mark'),topDownload:!!document.querySelector('.document-header a[download]')})");
  assert.equal(result.workspaceVisible,true);assert.equal(result.selectedRows,0);
  assert.equal(result.contextVisible,false);assert.equal(result.topDownload,false);
  await screenshot('review-bug-before.png');
  await writeFile(path.join(work,'reproduction.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify({reproduced:true,...result}));
 }else{
  const topDownload=()=>evaluate("document.querySelector('.document-header a[download]')?.getAttribute('href')");
  assert.match(await topDownload(),/^\/api\/documents\/[a-f0-9]+\/artifact\?/);
  assert.equal(await evaluate("document.querySelector('.document-actions')?.textContent.includes('Private review artifact — complete PII coverage has not been verified.')"),true);
  await click('Review Findings');
  await waitFor(()=>evaluate("!!document.querySelector('.comparison mark')"));
  assert.equal(await evaluate("document.querySelector('.segmented button[aria-pressed=true]')?.textContent"),'Review');
  assert.equal(await evaluate("document.querySelectorAll('.selected-row').length"),1);
  const first=await evaluate("document.querySelector('.selected-row code').textContent");
  assert.equal(first,await evaluate("document.querySelector('.finding-select code').textContent"));
  assert.equal(await evaluate("[...document.querySelectorAll('.detail-panel button')].some(x=>x.textContent.trim()==='Mark False Positive')"),true);
  await screenshot('review-auto-selected.png');
  await click('Confirm as PII');await waitFor(()=>evaluate("!!document.querySelector('[role=dialog]')"));
  assert.equal(await evaluate("document.querySelector('[role=dialog]').textContent.includes('Automated:') && document.querySelector('[role=dialog]').textContent.includes('Effective:')"),true);
  await evaluate("(()=>{const input=[...document.querySelectorAll('[role=dialog] input')][0];Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,'phase10b1-acceptance');input.dispatchEvent(new Event('input',{bubbles:true}));})()");
  await screenshot('review-dialog.png');
  await click('Confirm & Regenerate');
  await waitFor(()=>evaluate("[...document.querySelectorAll('.document-header button')].some(x=>x.textContent.includes('Regenerating redacted copy')&&x.disabled)"));
  assert.equal(await evaluate("[...document.querySelectorAll('[role=dialog] button')].filter(x=>x.textContent.includes('Regenerate')).every(x=>x.disabled)"),true);
  await waitFor(()=>evaluate("!!document.querySelector('.revision-feedback')&&!document.querySelector('[role=dialog]')&&!document.querySelector('.loading-line')"));
  await waitFor(()=>evaluate("!!document.querySelector('.comparison mark')"));
  const next=await evaluate("document.querySelector('.selected-row code').textContent");assert.notEqual(next,first);
 await click('All');await evaluate(`[...document.querySelectorAll('.finding-select')].find(x=>x.textContent.includes('${first}')).click()`);
 await waitFor(()=>evaluate("document.querySelector('.human-decision-story')?.textContent.includes('HUMAN DECISION') && !!document.querySelector('.replacement-tag')"));
 assert.equal(await evaluate("document.querySelector('.human-decision-story').textContent.includes('Redacted')"),true);
 await evaluate("document.querySelector('.detail-panel').scrollIntoView({block:'start'})");await screenshot('human-transformation.png');await evaluate('window.scrollTo(0,0)');

  assert.equal(await evaluate("document.querySelector('.revision-feedback').textContent.includes('Artifact verification passed')"),true);
  assert.equal(await evaluate("document.querySelector('.revision-feedback').textContent.includes('Audit revision 0 → 1')"),true);
  assert.match(await topDownload(),/revision=1/);
 await click('Audit');await waitFor(()=>evaluate("!!document.querySelector('.timeline .human')"));await screenshot('governance.png');
 assert.equal(await evaluate("document.querySelector('.timeline').closest('.panel').textContent.includes('Review & Governance Trail')"),true);
 await click('Detector Quality');await waitFor(()=>evaluate("!!document.querySelector('.quality-story')"));await screenshot('detector-quality.png');
 assert.equal(await evaluate("document.querySelector('.quality-story').textContent.includes('+17.74 pp precision')"),true);
 assert.equal(await evaluate("document.querySelector('.metrics-disclaimer').textContent.includes('Not a claim of Cadence-document accuracy')"),true);
 await evaluate("[...document.querySelectorAll('nav button')].find(x=>x.textContent.startsWith('Review Queue')).click()");await waitFor(()=>evaluate("!!document.querySelector('.comparison mark')"));

  await screenshot('review-next.png');
  await click('Overview');await waitFor(()=>evaluate("!!document.querySelector('[aria-label^=\"Privacy decision funnel:\"]')"));
  const after=await evaluate("({counts:[...document.querySelectorAll('.funnel-hit-zones button span')].map(x=>Number(x.textContent.replaceAll(',',''))),coverage:document.querySelector('.coverage-status strong').textContent})");
  assert.equal(after.counts[1],before.counts[1]+1);assert.equal(after.counts[2],before.counts[2]-1);assert.equal(after.coverage,'NOT ESTABLISHED');
  // Exercise every shortcut through the actual production DOM.
  await evaluate("[...document.querySelectorAll('nav button')].find(x=>x.textContent.startsWith('Review Queue')).click()");await waitFor(()=>evaluate("!!document.querySelector('.comparison mark')"));
  await click('Overview');await evaluate("document.querySelector('[aria-label=\"Filter Review\"]').click()");await waitFor(()=>evaluate("!!document.querySelector('.comparison mark')"));
  await click('Overview');await click('Open review workspace');await waitFor(()=>evaluate("!!document.querySelector('.comparison mark')"));
  await click('Overview');await evaluate("document.querySelector('[aria-label=\"Review required findings\"]').click()");await waitFor(()=>evaluate("!!document.querySelector('.comparison mark')"));
  await click('Overview');await evaluate("document.querySelector('.map-tile.needs-review').click()");await waitFor(()=>evaluate("!!document.querySelector('.comparison mark')"));
  assert.equal(await evaluate("document.querySelector('.segmented button[aria-pressed=true]').textContent"),'Review');
  assert.ok(await evaluate("document.querySelector('#location-filter').value"));
  let finalRevision=1,queueComplete=false;
  if(process.env.CADENCE_UI_COMPLETE==='1'){
   // Only use this on fictional fixtures: the second bank-like interpretation
   // is a driver-license false positive, not a second genuine identifier.
   await click('Review Findings');await waitFor(()=>evaluate("!!document.querySelector('.comparison mark')"));
   await click('Mark False Positive');await waitFor(()=>evaluate("!!document.querySelector('[role=dialog]')"));
   await click('Mark False Positive & Regenerate');
   await waitFor(()=>evaluate("document.querySelector('.revision-feedback')?.textContent.includes('Audit revision 1 → 2')&&!document.querySelector('.loading-line')"));
   assert.equal(await evaluate("document.body.textContent.includes('Known review queue complete')"),true);
   assert.equal(await evaluate("document.body.textContent.includes('No findings currently require human review.')"),true);
   assert.equal(await evaluate("document.body.textContent.includes('Coverage verification remains NOT ESTABLISHED.')"),true);
   assert.equal(await evaluate("[...document.querySelectorAll('a[download]')].some(x=>x.textContent.trim()==='Download Latest Redacted Review Copy')"),true);
   await screenshot('queue-complete.png');finalRevision=2;queueComplete=true;
  }
  await evaluate("document.querySelector('.document-header a[download]').click()");await waitFor(()=>downloaded);
  const files=await readdir(path.join(work,'downloads'));const file=files.find(x=>/\.(pdf|docx|pptx)$/.test(x));assert.ok(file);
  const downloadPath=path.join(work,'downloads',file),bytes=(await stat(downloadPath)).size;assert.ok(bytes>1000);
  // Reopen the downloaded artifact with the corresponding document library.
  const {execFileSync}=await import('node:child_process');
  execFileSync(path.join(root,'.venv','Scripts','python.exe'),['-c',"import sys; from pathlib import Path; p=Path(sys.argv[1]); suffix=p.suffix;\nif suffix=='.pptx':\n from pptx import Presentation; assert len(Presentation(p).slides)>0\nelif suffix=='.docx':\n from docx import Document; assert len(Document(p).paragraphs)>0\nelse:\n import pymupdf; d=pymupdf.open(p); assert len(d)>0\n",downloadPath],{windowsHide:true,stdio:'pipe'});
  await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true},sid);await screenshot('mobile-review.png');
  await click('Overview');await waitFor(()=>evaluate("!!document.querySelector('.document-hero')"));await screenshot('mobile-overview.png');
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'),true);
  await command('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false},sid);await screenshot('laptop-overview.png');
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'),true);
  await command('Emulation.setDeviceMetricsOverride',{width:820,height:1100,deviceScaleFactor:1,mobile:false},sid);await screenshot('tablet-overview.png');
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'),true);

  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'),true);
  assert.equal(failedRequests.length,0);assert.equal(errors.length,0);assert.equal(securityErrors.length,0);
  const summary={passed:true,format:path.extname(inputFile).slice(1),before_counts:before.counts,after_counts:after.counts,auto_selected:true,next_selected:true,dialog:true,regeneration_disabled:true,top_download:true,download_bytes:bytes,download_reopened:true,revision:finalRevision,queue_complete:queueComplete,coverage:'NOT ESTABLISHED',runtime_errors:errors.length,security_errors:securityErrors.length};
  await writeFile(path.join(work,'summary.json'),JSON.stringify(summary,null,2));await writeFile(path.join(root,'.private_review_app','phase10b-ui','latest-10b2.json'),JSON.stringify({work,summary},null,2));console.log(JSON.stringify(summary));
 }
 await command('Browser.close');
}catch(error){await writeFile(path.join(work,'failure.json'),JSON.stringify({message:error.message}));console.error('Focused UI acceptance failed; private diagnostics retained.');process.exitCode=1;}
finally{socket?.close();browser.kill();}
