import { Download } from 'lucide-react';
import { artifactUrl } from '@/lib/api';
import type { DocumentState } from '@/lib/types';
import { Button } from './ui/button';

export function ArtifactDownload({state,regenerating=false,latest=false,approval}:{state:DocumentState;regenerating?:boolean;latest?:boolean;approval?:'pending'|'approved'|'denied'}){
 approval=approval??state.manager_approval;
 const available=state.artifact_available&&!state.summary.failure&&approval!=='denied';
 return <div className="artifact-download">
  {regenerating?<Button disabled>Regenerating redacted copy...</Button>:available?
   <Button asChild><a href={artifactUrl(state.document_session_id,state.revision)} download><Download size={16}/>{latest?'Download Latest Redacted Review Copy':'Download Redacted Review Copy'}</a></Button>:
   <><Button disabled>{approval==='denied'?'Download denied':'Redacted copy unavailable'}</Button><p role="status">{state.issue_message??(approval==='denied'?'This document was denied by manager.':'No redacted artifact is available.')}</p></>}
  
 </div>;
}
