import { ScanFace, ShieldAlert } from 'lucide-react';
import type { DocumentState } from '@/lib/types';
import { Panel } from './analytics';
import { Button } from './ui/button';

export function VisualPrivacy({state,inspect}:{state:DocumentState;inspect:()=>void}){
 const v=state.summary.visual_privacy,a=state.summary.artifact;
 return <Panel eyebrow="VISUAL PRIVACY · YUNET" title="Faces are biometric privacy findings" className="visual-privacy-card">
  {!v?<p>Visual inspection is not recorded for this document. Visual coverage remains unverified.</p>:<>
   <div className="visual-counts"><div><strong>{v.detected_faces}</strong><span>Face findings detected</span></div><div><strong>{a?.protected_faces??0}</strong><span>Protected in output</span></div><div><strong>{v.review_faces}</strong><span>Require human review</span></div></div>
   <p>{v.inspected_visual_units} image/raster units inspected locally · {v.face_placements} face placements. Reused media is inspected once and protected across its mapped placements.</p>
   <p className="chart-note">Textual PII → redacted. FACE / BIOMETRIC → strong pixel blur. No identity or demographic attributes are inferred.</p>
   {!!v.unsupported_visual_units&&<p className="amber"><ShieldAlert size={16}/> {v.unsupported_visual_units} unsupported/unverified visual items remain.</p>}
   <Button variant="outline" onClick={inspect}><ScanFace size={16}/>Inspect face findings</Button>
  </>}
 </Panel>;
}
