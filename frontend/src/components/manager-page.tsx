import { useCallback, useEffect, useState } from 'react';
import { Moon, Sun, ShieldAlert, Plus, Trash2, FileCheck2 } from 'lucide-react';
import { BrandMark } from './brand-mark';
import { LoadingIndicator } from './loading-indicator';
import type { ManagerReport, CustomRule } from '@/lib/types';
import { api } from '@/lib/api';

export function ManagerPage(){
 const [tab,setTab]=useState<'reports'|'rules'>('reports');
 const [items,setItems]=useState<ManagerReport[]>([]),[selected,setSelected]=useState<ManagerReport|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [rules,setRules]=useState<CustomRule[]>([]);
 const [newRuleName,setNewRuleName]=useState('');
 const [newRulePattern,setNewRulePattern]=useState('');
 const [newRuleEntity,setNewRuleEntity]=useState('CUSTOM_BLOCKED');
 const [theme,setTheme]=useState(()=>window.localStorage?.getItem('pii-theme')??'system');

 useEffect(()=>{const query=window.matchMedia('(prefers-color-scheme: dark)');const apply=()=>{document.documentElement.dataset.theme=theme==='system'?(query.matches?'dark':'light'):theme;};apply();window.localStorage?.setItem('pii-theme',theme);query.addEventListener('change',apply);return()=>query.removeEventListener('change',apply);},[theme]);

 const refresh=useCallback(async()=>{
   try{
     const [result, rulesRes] = await Promise.all([
       api<{items:ManagerReport[]}>('/api/manager/reports'),
       api<{items:CustomRule[]}>('/api/manager/rules').catch(()=>({items:[]}))
     ]);
     setItems(Array.isArray(result?.items) ? result.items : []);
     setRules(Array.isArray(rulesRes?.items) ? rulesRes.items : []);
   }catch{setError('Could not load manager data. Try again.');}
 },[]);

 useEffect(()=>{void refresh();const interval=setInterval(()=>{if(document.visibilityState==='visible')void refresh();},10000);return()=>clearInterval(interval);},[refresh]);

 async function open(item:ManagerReport){setBusy(true);setError('');try{setSelected(await api<ManagerReport>(`/api/manager/reports/${item.id}`));}catch{setError('Could not open this submission.');}finally{setBusy(false);}}

 async function decide(action:'approved'|'denied'){if(!selected||busy)return;setBusy(true);setError('');try{setSelected(await api<ManagerReport>(`/api/manager/reports/${selected.id}/decision`,{method:'POST',body:JSON.stringify({revision:selected.revision,artifact_sha256:selected.artifact_sha256,action})}));await refresh();}catch{setError('The result changed or is not ready. Open the latest submission.');}finally{setBusy(false);}}

 async function handleAddRule(e:React.FormEvent){
   e.preventDefault();
   if(!newRuleName.trim()||!newRulePattern.trim())return;
   setBusy(true);setError('');
   try{
     await api('/api/manager/rules',{method:'POST',body:JSON.stringify({name:newRuleName.trim(),pattern:newRulePattern.trim(),entity_type:newRuleEntity.trim().toUpperCase()||'CUSTOM_BLOCKED',action:'redact',is_regex:false})});
     setNewRuleName('');setNewRulePattern('');
     await refresh();
   }catch{setError('Failed to add custom rule.');}finally{setBusy(false);}
 }

 async function handleDeleteRule(id:string){
   setBusy(true);setError('');
   try{
     await api(`/api/manager/rules/${id}`,{method:'DELETE'});
     await refresh();
   }catch{setError('Failed to delete custom rule.');}finally{setBusy(false);}
 }

 return <div className="manager-shell">
   <header className="manager-top">
     <div style={{display:'flex',alignItems:'center',gap:'1.5rem'}}>
       <a className="brand" href="/manager"><BrandMark/><span>PII Guard</span></a>
       <nav style={{display:'flex',gap:'0.5rem'}}>
         <button className={`tab-button ${tab==='reports'?'active':''}`} onClick={()=>{setTab('reports');setSelected(null);}} style={{padding:'0.4rem 0.8rem',borderRadius:'6px',fontSize:'0.875rem',fontWeight:500,background:tab==='reports'?'rgba(255,255,255,0.1)':'transparent',color:tab==='reports'?'var(--text)':'var(--text-muted)',border:'1px solid '+(tab==='reports'?'var(--border)':'transparent')}}>
           Submissions ({items.length})
         </button>
         <button className={`tab-button ${tab==='rules'?'active':''}`} onClick={()=>{setTab('rules');setSelected(null);}} style={{padding:'0.4rem 0.8rem',borderRadius:'6px',fontSize:'0.875rem',fontWeight:500,background:tab==='rules'?'rgba(255,255,255,0.1)':'transparent',color:tab==='rules'?'var(--text)':'var(--text-muted)',border:'1px solid '+(tab==='rules'?'var(--border)':'transparent')}}>
           Blocking Rules ({rules.length})
         </button>
       </nav>
     </div>
     <button className="icon-button" aria-label="Change appearance" onClick={()=>setTheme(theme==='dark'?'light':'dark')}>{theme==='dark'?<Sun size={20}/>:<Moon size={20}/>}</button>
   </header>
   <main className="manager-content">
   {tab==='rules'?(
     <div>
       <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:'1.5rem',flexWrap:'wrap',gap:'1rem'}}>
         <div>
           <h1 style={{fontSize:'1.5rem',fontWeight:600,margin:0}}>Custom Blocking Rules</h1>
           <p className="muted" style={{margin:'0.25rem 0 0 0'}}>Define terms, organization entities, or project phrases that must always be redacted across all employee documents.</p>
         </div>
       </div>

       <form onSubmit={handleAddRule} style={{background:'var(--card-bg, rgba(255,255,255,0.03))',border:'1px solid var(--border)',borderRadius:'8px',padding:'1.25rem',marginBottom:'2rem'}}>
         <h2 style={{fontSize:'1rem',fontWeight:600,margin:'0 0 1rem 0'}}>Add New Blocking Rule</h2>
         <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit, minmax(220px, 1fr))',gap:'1rem',marginBottom:'1rem'}}>
           <div>
             <label style={{display:'block',fontSize:'0.75rem',fontWeight:500,color:'var(--text-muted)',marginBottom:'0.25rem'}}>Rule Label / Description</label>
             <input type="text" placeholder="e.g. Confidential Vendor" value={newRuleName} onChange={e=>setNewRuleName(e.target.value)} required style={{width:'100%',padding:'0.5rem 0.75rem',borderRadius:'6px',border:'1px solid var(--border)',background:'var(--bg)',color:'var(--text)',fontSize:'0.875rem'}} />
           </div>
           <div>
             <label style={{display:'block',fontSize:'0.75rem',fontWeight:500,color:'var(--text-muted)',marginBottom:'0.25rem'}}>Pattern or Keyword to Redact</label>
             <input type="text" placeholder="e.g. Cadence TPRM" value={newRulePattern} onChange={e=>setNewRulePattern(e.target.value)} required style={{width:'100%',padding:'0.5rem 0.75rem',borderRadius:'6px',border:'1px solid var(--border)',background:'var(--bg)',color:'var(--text)',fontSize:'0.875rem'}} />
           </div>
           <div>
             <label style={{display:'block',fontSize:'0.75rem',fontWeight:500,color:'var(--text-muted)',marginBottom:'0.25rem'}}>Entity Classification</label>
             <input type="text" placeholder="CUSTOM_BLOCKED" value={newRuleEntity} onChange={e=>setNewRuleEntity(e.target.value)} style={{width:'100%',padding:'0.5rem 0.75rem',borderRadius:'6px',border:'1px solid var(--border)',background:'var(--bg)',color:'var(--text)',fontSize:'0.875rem'}} />
           </div>
         </div>
         <button type="submit" disabled={busy||!newRuleName.trim()||!newRulePattern.trim()} className="primary" style={{display:'inline-flex',alignItems:'center',gap:'0.5rem',padding:'0.5rem 1rem',borderRadius:'6px',fontSize:'0.875rem',fontWeight:500}}>
           <Plus size={16}/> Add Blocking Rule
         </button>
       </form>

       <div className="manager-list">
         {rules.map(rule=>(
           <div key={rule.id} style={{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'1rem',border:'1px solid var(--border)',borderRadius:'8px',marginBottom:'0.75rem',background:'var(--card-bg, rgba(255,255,255,0.02))'}}>
             <div>
               <div style={{display:'flex',alignItems:'center',gap:'0.75rem'}}>
                 <strong style={{fontSize:'0.95rem'}}>{rule.name}</strong>
                 <span style={{fontSize:'0.75rem',padding:'0.15rem 0.5rem',borderRadius:'4px',background:'rgba(244,63,94,0.15)',color:'#f43f5e',border:'1px solid rgba(244,63,94,0.3)',fontWeight:600}}>{rule.entity_type}</span>
               </div>
               <p style={{margin:'0.35rem 0 0 0',fontFamily:'monospace',fontSize:'0.85rem',color:'var(--text-muted)'}}>
                 Pattern: <span style={{color:'var(--text)',fontWeight:500}}>{rule.pattern}</span>
               </p>
             </div>
             <button onClick={()=>rule.id&&handleDeleteRule(rule.id)} disabled={busy} aria-label={`Delete rule ${rule.name}`} style={{background:'transparent',border:'none',color:'var(--text-muted)',cursor:'pointer',padding:'0.5rem',borderRadius:'6px'}}>
               <Trash2 size={18}/>
             </button>
           </div>
         ))}
         {!rules.length&&!busy&&<p className="muted">No custom blocking rules active. Add a rule above to enforce automatic redaction.</p>}
       </div>
     </div>
   ):(selected?<><button className="back-button" onClick={()=>setSelected(null)}>Back to uploads</button><h1>{selected.filename}</h1><p className="muted">{new Date(selected.submitted_at).toLocaleString()}</p><div className="decision-bar"><span className={`status-pill ${selected.status==='approved'?'status-approved':selected.status==='denied'?'status-denied':'status-pending'}`}>{selected.status==='pending'?'Awaiting your decision':selected.status==='approved'?'Approved':'Denied'}</span><div><button disabled={busy||!selected.ready||selected.status==='approved'} className="primary" onClick={()=>void decide('approved')}>Approve</button><button disabled={busy||selected.status==='denied'} onClick={()=>void decide('denied')}>Deny</button></div></div>{!selected.ready&&<p className="muted">Local review or verification must finish before approval.</p>}
    <div className="comparison-labels"><strong>Original part</strong><strong>Redacted part</strong></div>{selected.parts?.length?selected.parts.map(part=><div className="manager-comparison" key={part.finding_id}><div>{part.original_image?<img src={part.original_image} alt="Original affected region"/>:<p>{part.original}{part.truncated&&'…'}</p>}</div><div>{part.redacted_image?<img src={part.redacted_image} alt="Redacted affected region"/>:<p>{part.redacted??'Awaiting review'}</p>}</div></div>):<p>{selected.ready?'Nothing needed redaction.':'Affected content is unavailable until local processing finishes.'}</p>}
   </>:<><h1>Uploads</h1><p className="muted">Review your team’s redacted results.</p><div className="manager-list">{items.map(item=><button className="manager-row" key={item.id} onClick={()=>void open(item)}><span><strong>{item.filename}</strong><small>{new Date(item.submitted_at).toLocaleString()}</small></span><span className={`status-pill ${item.status==='approved'?'status-approved':item.status==='denied'?'status-denied':'status-pending'}`}>{item.status==='pending'?'Pending':item.status==='approved'?'Approved':'Denied'}</span></button>)}{!items.length&&!busy&&!error&&<p className="muted">New submissions will appear here.</p>}</div></>)}
   {busy&&<LoadingIndicator label="Updating…"/>}{error&&<div role="alert" className="error-banner">{error}<button onClick={()=>void refresh()}>Try again</button></div>}
  </main></div>;
}
