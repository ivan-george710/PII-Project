import { useEffect, useRef, useState } from 'react';
import { Plus, ArrowUp, Menu, X, FileText, MessageSquare, Moon, Sun, ExternalLink } from 'lucide-react';
import { api, documentUrl } from '@/lib/api';
import { useWorkspace } from './hooks/useWorkspace';
import { BrandMark } from './components/brand-mark';
import { LoadingIndicator } from './components/loading-indicator';
import { ManagerPage } from './components/manager-page';
import { InspectionPage } from './components/inspection-page';
import { ChatDocument } from './components/chat-document';
import { DocumentPreview } from './components/document-preview';
import { Pipeline, DetectionFunnel, Entities, ReviewBurden, PrivacyMap } from './components/analytics';
import { ReviewWorkspace, type Filters } from './components/review-workspace';
import { DetectorQuality, Timeline, Verification } from './components/evidence';
import { ArtifactDownload } from './components/artifact-download';
import { VisualPrivacy } from './components/visual-privacy';
import { AIBoundary, AIAccess } from './components/product-story';
import type { Config, DocumentState, ManagerReport, Screen } from './lib/types';

export default function App(){
  if(import.meta.env.MODE==='manager'||window.location.pathname.startsWith('/manager')||window.location.port==='8766')return <ManagerPage/>;
  const inspectId=typeof window!=='undefined'?new URLSearchParams(window.location.search).get('inspect'):null;
  if(inspectId)return <InspectionPage documentId={inspectId}/>;
  return <EmployeeChat/>;
}
function EmployeeChat(){
 const w=useWorkspace();const [screen,setScreen]=useState<Screen>('Overview'),[details,setDetails]=useState(false),[drawer,setDrawer]=useState(false),[addon,setAddon]=useState(false),[empty,setEmpty]=useState(true),[draft,setDraft]=useState(''),[pendingFile,setPendingFile]=useState<File|null>(null),[samples,setSamples]=useState<{filename:string;label:string}[]>([]);
 const [filters,setFilters]=useState<Filters>({decision:'ALL',entity:'',location:''}),[config,setConfig]=useState<Config|null>(null),[decision,setDecision]=useState<ManagerReport|null>(null),[preview,setPreview]=useState<'original'|'redacted'|null>(null),[theme,setTheme]=useState(()=>window.localStorage?.getItem('pii-theme')??'system');
 const fileRef=useRef<HTMLInputElement>(null);const lastActiveRef=useRef<HTMLElement|null>(null);const detailsPanelRef=useRef<HTMLElement|null>(null);const previewPanelRef=useRef<HTMLElement|null>(null);
 const state=empty||!w.state?null:{...w.state,manager_approval:decision?.status};
 useEffect(()=>{void api<{items:{filename:string;label:string}[]}>('/api/samples').then(value=>setSamples(value.items)).catch(()=>{});api<Config>('/api/config').then(setConfig).catch(()=>w.setError('The local processor is unavailable.'));},[]);
 useEffect(()=>{const query=window.matchMedia('(prefers-color-scheme: dark)');const apply=()=>{document.documentElement.dataset.theme=theme==='system'?(query.matches?'dark':'light'):theme;};apply();window.localStorage?.setItem('pii-theme',theme);query.addEventListener('change',apply);return()=>query.removeEventListener('change',apply);},[theme]);
 useEffect(()=>{setDecision(null);if(!state||state.revision===null)return;let live=true;const refresh=()=>api<ManagerReport>(`${documentUrl(state.document_session_id)}/manager`).then(value=>{if(live)setDecision(value);}).catch(()=>{if(live)setDecision(null);});void refresh();const timer=setInterval(()=>{if(document.visibilityState==='visible')void refresh();},5000);return()=>{live=false;clearInterval(timer);};},[state?.document_session_id,state?.revision]);
 useEffect(()=>{
  if(details||preview){
   lastActiveRef.current=document.activeElement as HTMLElement;
   const timer=setTimeout(()=>{
    const target=details?detailsPanelRef.current:previewPanelRef.current;
    const focusable=target?.querySelectorAll<HTMLElement>('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])');
    if(focusable&&focusable.length>0)focusable[0].focus();
   },30);
   return()=>clearTimeout(timer);
  }else if(lastActiveRef.current){
   lastActiveRef.current.focus();
   lastActiveRef.current=null;
  }
 },[details,preview]);
 useEffect(()=>{
  const handleKeyDown=(event:KeyboardEvent)=>{
   if(event.key==='Escape'){setDetails(false);setPreview(null);setAddon(false);setDrawer(false);return;}
   if(event.key==='Tab'&&(details||preview)){
    const target=details?detailsPanelRef.current:previewPanelRef.current;
    if(!target)return;
    const focusables=Array.from(target.querySelectorAll<HTMLElement>('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'));
    if(!focusables.length)return;
    const first=focusables[0],last=focusables[focusables.length-1];
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
   }
  };
  window.addEventListener('keydown',handleKeyDown);
  return()=>window.removeEventListener('keydown',handleKeyDown);
 },[details,preview]);
 useEffect(()=>{
  if(!addon)return;
  const clickAway=(e:MouseEvent)=>{
   const target=e.target as HTMLElement;
   if(!target.closest('.attachment-popover')&&!target.closest('button[aria-label="Add attachment"]')){setAddon(false);}
  };
  document.addEventListener('mousedown',clickAway);
  return()=>document.removeEventListener('mousedown',clickAway);
 },[addon]);
 function filter(next:Partial<Filters>){setFilters({decision:'ALL',entity:'',location:'',...next});setScreen('Review Queue');setDetails(true);}
 async function upload(file?:File){setAddon(false);if(!file||w.busy)return;if(!config||!file.size||file.size>config.max_upload_bytes){w.setError('Choose a supported file within the upload limit.');return;}const form=new FormData();form.append('file',file);setEmpty(true);try{await w.operation('Redacting…',()=>api<DocumentState>('/api/documents',{method:'POST',body:form}));setEmpty(false);return true;}catch{return false;}finally{if(fileRef.current)fileRef.current.value='';}}
 async function feedback(path:string,payload:unknown){if(!state)return;const p=payload as {finding_id?:string;action?:string}|null;const msg=path==='feedback'&&p?.finding_id?`Finding ${p.finding_id} ${p.action==='CONFIRM_PII'?'confirmed as PII':'marked false positive'}`:'Missed PII recorded';await w.operation('Updating redaction…',()=>api<DocumentState>(`${documentUrl(state.document_session_id)}/${path}`,{method:'POST',body:JSON.stringify(payload)}),true,msg);setFilters({decision:'REVIEW',entity:'',location:''});}
 function select(id:string){setEmpty(false);setDrawer(false);setDetails(false);void w.select(id);}
 async function send(){if(w.busy)return;if(pendingFile){if(await upload(pendingFile))setPendingFile(null);}else if(draft.trim()){const text=draft;setDraft('');setEmpty(true);try{await w.operation('Redacting…',()=>api<DocumentState>('/api/messages',{method:'POST',body:JSON.stringify({text})}));setEmpty(false);}catch{setDraft(text);}}}
 async function sample(filename:string){setAddon(false);try{const response=await fetch(`/api/samples/${encodeURIComponent(filename)}`);if(!response.ok)throw Error();const blob=await response.blob();setPendingFile(new File([blob],filename,{type:blob.type}));}catch{w.setError('Could not attach this sample.');}}
 const tabs:Screen[]=['Overview','Review Queue','Audit','Artifact Verification','Detector Quality'];
 return <div className="app-shell"><aside className={`sidebar ${drawer?'sidebar-open':''}`}><a className="brand" href="#" onClick={e=>{e.preventDefault();setEmpty(true);}}><BrandMark/><span>PII Guard</span></a><button className="new-chat" onClick={()=>{setEmpty(true);setDetails(false);setDrawer(false);}}><MessageSquare size={18}/>New chat</button><nav className="sidebar-documents" aria-label="Chat history">{w.documents.map((document,i)=><button key={document.document_session_id} className={state?.document_session_id===document.document_session_id?'selected-document':''} onClick={()=>select(document.document_session_id)}><FileText size={16}/><span>Document {i+1}<small>{document.format.toUpperCase()}</small></span></button>)}</nav><div className="sidebar-footer"><button onClick={()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark')}>{theme==='dark'?<Sun size={17}/>:<Moon size={17}/>}Appearance</button><a href={config?.manager_url?`${config.manager_url}/manager`:'/manager'} target="_blank" rel="noreferrer">Manager page</a></div></aside>{drawer&&<button className="drawer-backdrop" aria-label="Close navigation" onClick={()=>setDrawer(false)}/>}
 <div className="main-shell"><header className="topbar"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={()=>setDrawer(true)}><Menu size={21}/></button><span>Chat</span>{state&&<div className="topbar-actions"><button className="details-button" onClick={()=>setDetails(true)}>Details</button><a href={`?inspect=${state.document_session_id}`} target="_blank" rel="noopener noreferrer" className="topbar-inspect-link" title="Open complete inspection in a dedicated page"><span>Inspect (New Page)</span><ExternalLink size={13}/></a></div>}</header><main className={`chat-surface ${!state?'chat-empty':''}`}>
 {!state&&!w.busy&&<h1>What would you like to redact?</h1>}
 {state&&<div className="chat-messages"><article className="sent-message">{state.input_text?<p className="sent-text">{state.input_text}</p>:<ChatDocument state={state} mode="original" name={w.identity?.display_name??'Your document'} label={`Original · ${state.format.toUpperCase()}`} onOpen={()=>setPreview('original')}/>}</article><article className="reply-message">{w.busy?<LoadingIndicator label="Redacting…"/>:<>{state.output_text?<p className="reply-text">{state.output_text}</p>:<ChatDocument state={state} mode="redacted" name={w.identity?.display_name??'Redacted document'} disabled={!state.artifact_available||decision?.status==='denied'} label={state.summary.failure?'Could not redact':decision?.status==='denied'?'Denied by manager':decision?.status==='approved'?'Redacted · Approved':'Redacted · Review copy'} onOpen={()=>setPreview('redacted')}/>}<ArtifactDownload state={state} approval={decision?.status}/><div className="inspection-action-row"><button className="inspection-link" onClick={()=>setDetails(true)}>View inspection</button><span className="dot-sep">·</span><a href={`?inspect=${state.document_session_id}`} target="_blank" rel="noopener noreferrer" className="inspection-link external" title="Open full inspection in a new page"><span>Open in new page</span><ExternalLink size={13}/></a></div></>}</article></div>}
 {w.notice&&<div className="revision-feedback chat-notice">{w.notice}</div>}
 {w.error&&<p role="alert" className="error-banner">{w.error}</p>}{!state&&w.busy&&<LoadingIndicator label="Redacting…"/>}
 <div className="composer-dock">{pendingFile&&<div className="draft-attachment"><span>{pendingFile.name}</span><button aria-label="Remove attachment" onClick={()=>setPendingFile(null)}><X size={16}/></button></div>}<div className="chat-composer"><button className="icon-button" aria-label="Add attachment" aria-expanded={addon} onClick={()=>setAddon(!addon)}><Plus size={22}/></button><textarea aria-label="Message" placeholder={pendingFile?pendingFile.name:"Write a message"} value={draft} disabled={!!pendingFile||!!w.busy} onChange={event=>setDraft(event.target.value)} onKeyDown={event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();void send();}}}/><button className="send-button" aria-label="Send message" disabled={!!w.busy||!config||(!draft.trim()&&!pendingFile)} onClick={()=>void send()}><ArrowUp size={22}/></button>{addon&&<div className="attachment-popover"><button onClick={()=>fileRef.current?.click()}>Upload file</button><small>PDF, Word, PowerPoint or image</small>{samples.map(item=><button key={item.filename} onClick={()=>void sample(item.filename)}>{item.label}</button>)}</div>}</div><input ref={fileRef} aria-label="Upload document" type="file" accept=".pdf,.docx,.pptx,.png,.jpg,.jpeg" className="sr-only" onChange={e=>{setPendingFile(e.target.files?.[0]??null);setAddon(false);}}/><p className="composer-note">Processed locally. Your files stay on this device.</p></div>
 </main></div>
 {details&&<div className="details-overlay" role="dialog" aria-modal="true" aria-label="Document inspection" onClick={e=>{if(e.target===e.currentTarget)setDetails(false);}}><section ref={detailsPanelRef} className="details-panel" aria-label="Document inspection"><header><div style={{display:"flex",alignItems:"center",gap:12}}><h2>Inspection</h2><a href={`?inspect=${state?.document_session_id}`} target="_blank" rel="noopener noreferrer" className="drawer-new-tab-btn" title="Open full inspection in dedicated page"><span>Open full page</span><ExternalLink size={13}/></a></div><button className="icon-button" aria-label="Close inspection" onClick={()=>setDetails(false)}><X size={22}/></button></header>{w.notice&&<div className="revision-feedback">{w.notice}</div>}<nav className="detail-tabs">{tabs.map(tab=><button key={tab} className={screen===tab?'active':''} onClick={()=>{if(tab==='Review Queue')setFilters(f=>({...f,decision:'REVIEW'}));setScreen(tab);}}>{({'Overview':'Overview','Review Queue':'Review','Audit':'History','Artifact Verification':'Verification','Detector Quality':'Quality'})[tab as Exclude<Screen,'Documents'>]}</button>)}</nav>
 {screen==='Detector Quality'?<DetectorQuality/>:state&&<>{screen==='Overview'&&<><Pipeline state={state}/><AIBoundary state={state}/><AIAccess state={state}/><VisualPrivacy state={state} inspect={()=>filter({entity:'FACE'})}/><div className="analytics-grid"><DetectionFunnel state={state} onFilter={decision=>filter({decision})}/><ReviewBurden state={state} findings={w.findings} onReview={()=>filter({decision:'REVIEW'})}/><Entities findings={w.findings} onFilter={entity=>filter({entity})}/></div>{w.identity&&<PrivacyMap findings={w.findings} identity={w.identity} onLocation={location=>filter({location:String(location),decision:w.findings.some(f=>(f.locations??[f.location]).includes(location)&&f.effective_decision==='REVIEW')?'REVIEW':'ALL'})}/>}</>}{screen==='Review Queue'&&w.identity&&<ReviewWorkspace key={`${state.document_session_id}-${state.revision}`} state={state} identity={w.identity} findings={w.findings} filters={filters} setFilters={setFilters} submit={feedback} busy={!!w.busy}/>} {screen==='Audit'&&<Timeline state={state} audit={w.audit} busy={!!w.busy} save={()=>void w.operation('Saving…',()=>api<DocumentState>(`${documentUrl(state.document_session_id)}/save`,{method:'POST',body:JSON.stringify({expected_revision:state.revision})})).catch(()=>{})}/>} {screen==='Artifact Verification'&&<Verification state={state}/>}</>}
 </section></div>}
 {preview&&state&&<section ref={previewPanelRef}><DocumentPreview mode={preview} state={state} identity={w.identity} onClose={()=>setPreview(null)}/></section>}
 </div>;
}
