import { Download } from 'lucide-react';
import { artifactUrl } from '@/lib/api';
import type { DocumentState } from '@/lib/types';
import { Button } from './ui/button';

export function ArtifactDownload({state,regenerating=false,latest=false}:{state:DocumentState;regenerating?:boolean;latest?:boolean}){
 const available=state.artifact_available&&!state.summary.failure;
 return <div className="artifact-download">
  {regenerating?<Button disabled>Regenerating redacted copy...</Button>:available?
   <Button asChild><a href={artifactUrl(state.document_session_id,state.revision)} download><Download size={16}/>{latest?'Download Latest Redacted Review Copy':'Download Redacted Review Copy'}</a></Button>:
   <><Button disabled>Redacted copy unavailable</Button><p role="status">{state.issue_message??'No redacted artifact is available for this revision.'}</p></>}
  <p className="chart-note">Private review artifact — complete PII coverage has not been verified.</p>
 </div>;
}
