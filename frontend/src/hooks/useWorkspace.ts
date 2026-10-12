import { useEffect, useRef, useState } from 'react';
import { api, allFindings, documentUrl, ApiError } from '@/lib/api';
import type { AuditView, DocumentState, Finding, Identity, SavedAudit } from '@/lib/types';

export function useWorkspace(){
  const [documents,setDocuments]=useState<DocumentState[]>([]),[state,setState]=useState<DocumentState|null>(null);
  const [identity,setIdentity]=useState<Identity|null>(null),[findings,setFindings]=useState<Finding[]>([]),[audit,setAudit]=useState<AuditView|null>(null);
  const [saved,setSaved]=useState<SavedAudit[]>([]),[busy,setBusy]=useState(''),[loading,setLoading]=useState(false),[error,setError]=useState('');
  const [notice,setNotice]=useState('');const epoch=useRef(0),active=useRef<string|null>(null),locked=useRef(false);
  async function lists(){const [docs,refs]=await Promise.all([api<DocumentState[]>('/api/documents'),api<SavedAudit[]>('/api/saved-audits')]);setDocuments(docs);setSaved(refs);}
  useEffect(()=>{let live=true;Promise.all([api<DocumentState[]>('/api/documents'),api<SavedAudit[]>('/api/saved-audits')]).then(([d,s])=>{if(live){setDocuments(d);setSaved(s);}}).catch(()=>{if(live)setError('The local backend is unavailable. Start the review application and retry.');});return()=>{live=false;epoch.current++;};},[]);
  async function select(id:string,known?:DocumentState){
    const token=++epoch.current;active.current=id;setLoading(true);setError('');setFindings([]);setIdentity(null);setAudit(null);setState(known??null);
    try{const current=known??await api<DocumentState>(documentUrl(id));if(token!==epoch.current)return;setState(current);
      const who=await api<Identity>(`${documentUrl(id)}/review`);if(token!==epoch.current)return;setIdentity(who);
      if(current.revision!==null){const values=await allFindings(id);if(token!==epoch.current)return;setFindings(values);const history=await api<AuditView>(`${documentUrl(id)}/audit`);if(token!==epoch.current)return;setAudit(history);}
    }catch(e){if(token===epoch.current)setError(e instanceof Error?e.message:'The review could not be loaded.');}
    finally{if(token===epoch.current)setLoading(false);}
  }
  async function operation(label:string,work:()=>Promise<DocumentState>,feedback=false,feedbackMessage='Human review recorded'){
    if(locked.current)return;locked.current=true;setBusy(label);setError('');setNotice('');const previous=state?.revision;
    try{const next=await work();await select(next.document_session_id,next);await lists();
      if(feedback){setNotice(`${feedbackMessage} · ${!next.summary.failure&&next.artifact_available&&next.summary.artifact?.redaction_completed?'Redacted artifact regenerated':'Redacted artifact regeneration needs attention'} · ${next.summary.artifact?.verification_completed&&next.summary.artifact.supported_content_verified?'Artifact verification passed (supported mappings only)':'Artifact verification needs attention'} · Audit revision ${previous??0} → ${next.revision??'—'}`);}
      return next;
    }catch(e){setError(e instanceof Error?e.message:'The local operation failed.');if(e instanceof ApiError&&e.status===409&&active.current){await select(active.current);setError('This review changed. The latest revision is loaded; open the finding again before deciding.');}throw e;}
    finally{locked.current=false;setBusy('');}
  }
  return {documents,state,identity,findings,audit,saved,busy,loading,error,notice,setError,select,operation,lists};
}
