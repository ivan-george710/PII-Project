"""Build focused Chromium acceptance from the existing real-browser harness."""
from pathlib import Path

root=Path(__file__).resolve().parents[1]
original=(root/'tests/frontend/phase10b_browser.mjs').read_text(encoding='utf-8')
prefix=original[:original.index(' await evaluate("document.querySelector(\'[aria-label=')]
tail=r'''
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
  assert.equal(await evaluate("document.querySelector('.revision-feedback').textContent.includes('Artifact verification passed')"),true);
  assert.equal(await evaluate("document.querySelector('.revision-feedback').textContent.includes('Audit revision 0 → 1')"),true);
  assert.match(await topDownload(),/revision=1/);
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
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'),true);
  assert.equal(failedRequests.length,0);assert.equal(errors.length,0);assert.equal(securityErrors.length,0);
  const summary={passed:true,format:path.extname(inputFile).slice(1),before_counts:before.counts,after_counts:after.counts,auto_selected:true,next_selected:true,dialog:true,regeneration_disabled:true,top_download:true,download_bytes:bytes,download_reopened:true,revision:finalRevision,queue_complete:queueComplete,coverage:'NOT ESTABLISHED',runtime_errors:errors.length,security_errors:securityErrors.length};
  await writeFile(path.join(work,'summary.json'),JSON.stringify(summary,null,2));await writeFile(path.join(root,'.private_review_app','phase10b-ui','latest-10b1.json'),JSON.stringify({work,summary},null,2));console.log(JSON.stringify(summary));
 }
 await command('Browser.close');
}catch(error){await writeFile(path.join(work,'failure.json'),JSON.stringify({message:error.message}));console.error('Focused UI acceptance failed; private diagnostics retained.');process.exitCode=1;}
finally{socket?.close();browser.kill();}
'''
(root/'tests/frontend/phase10b1_browser.mjs').write_text(prefix+tail,encoding='utf-8')
