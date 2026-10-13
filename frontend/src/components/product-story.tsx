import { ArrowRight, FileText, ShieldCheck, ShieldAlert } from 'lucide-react';
import type { DocumentState, Identity } from '@/lib/types';
import { count } from '@/lib/review';
import { Panel } from './analytics';
import { ArtifactDownload } from './artifact-download';
import { Button } from './ui/button';

export function DocumentHero({state,identity,children}:{state:DocumentState;identity:Identity|null;children:React.ReactNode}){
 const c=state.summary.audit?.counts;
 const allowed=!!(state.summary.safe_for_llm&&state.summary.coverage_verified&&state.summary.downstream_export_permitted);
 return <section className="document-header document-hero" aria-label="Current document privacy story">
  <div className="hero-purpose"><span className="eyebrow">CADENCE PII GUARD · PRIVACY GATEWAY</span><span className={`hero-ai-status ${allowed?'technical-pass':'blocked-status'}`}>AI ACCESS · {allowed?'PERMITTED':'BLOCKED'}</span><h1>Protect sensitive business artifacts<br/>before they reach enterprise AI.</h1><p>Cadence’s document-analysis agents must not receive PII.</p></div>
  <div className="hero-document"><FileText size={28}/><div><span className="format-pill">{state.format.toUpperCase()}</span><h2>{identity?.display_name.replaceAll('_',' ')??'Loading document identity…'}</h2><p>{identity?`${count(identity.location_count)} ${identity.location_kind}${identity.location_count===1?'':'s'}`:'Source locations loading'} · Revision {state.revision??'—'}</p></div></div>
  <div className="inspection-status"><ShieldCheck size={18}/><strong>{state.summary.detection_completed?'Privacy inspection complete':'Privacy inspection incomplete'}</strong><span>{c?`${count(c.raw_detection_count)} candidates analyzed`:'Detection results unavailable'}</span><small>Inspection completion does not establish PII coverage.</small></div>
  <p className="eyebrow textual-scope">TEXTUAL PII DECISIONS</p><div className="decision-summary" aria-label="PII decision summary">{[
   ['confirmed',c?.confirmed,'Confirmed sensitive findings'],['review',c?.review,'Need human judgement'],['rejected',c?.rejected,'Rejected as non-PII']
  ].map(([kind,n,label])=><div key={kind} className={`decision-stat ${kind}`}><strong>{typeof n==='number'?count(n):'—'}</strong><span>{label}</span></div>)}</div>
  {c?.human_added? <p className="chart-note">Effective counts include {count(c.human_added)} human-added findings.</p>:null}
  {children}
 </section>;
}

export function LandingStory({children}:{children:React.ReactNode}){
 return <section className="landing-story"><div><span className="eyebrow">CADENCE PII GUARD · ENTERPRISE AI PRIVACY</span><h1>Privacy enforcement for<br/>enterprise AI workflows.</h1><p>Inspect business artifacts for PII, resolve uncertain findings, and generate redacted review copies before content reaches document-analysis agents.</p><span className="landing-formats">Scanned policy PDFs · Organizational PPTX · Process DOCX</span><div className="opening-steps">{[
 ['01','Inspect','Extract content and identify sensitive information.'],['02','Resolve','Human validation for ambiguous findings.'],['03','Protect','Produce a checked review copy. Block unverified AI use.']
 ].map(([n,title,copy])=><div key={n}><span>{n}</span><strong>{title}</strong><p>{copy}</p></div>)}</div></div>{children}</section>;
}

export function WhyInspection(){return <details className="why-inspection" open><summary>Why this document is being inspected</summary><p>Cadence is a global financial-services firm using document-analysis agents for business operations. Organizational policy restricts PII from AI processing. This gateway identifies known sensitive information, routes ambiguity to human review, and creates a redacted review copy. Unverified coverage keeps downstream use blocked.</p></details>;}

export function AIBoundary({state}:{state:DocumentState|null}){
 const generated=!!(state?.artifact_available&&!state.summary.failure);
 return <section className="ai-boundary" aria-label="Local document redaction flow"><div className="boundary-heading"><h2>Document flow</h2></div><div className="boundary-flow"><div className="boundary-node"><FileText/><strong>Original document</strong><span>{state?state.format.toUpperCase():'PDF · Word · PowerPoint · Image'}</span></div><ArrowRight className="boundary-arrow"/><div className="boundary-node guard-node"><ShieldCheck/><strong>PII Guard</strong><span>Text and face redaction</span></div><ArrowRight className="boundary-arrow"/><div className="boundary-node"><FileText/><strong>Redacted review copy</strong><span>{generated?'Private artifact generated':'Awaiting artifact'}</span></div><div className="boundary-gate"><ShieldCheck/><strong>{generated?'GENERATED':'WAITING'}</strong><span>Returned to chat</span></div><div className="boundary-node agent-node"><FileText/><strong>On your device</strong><span>Full files stay local</span></div></div></section>;
}

export function AIAccess({state}:{state:DocumentState|null}){
 const s=state?.summary,a=s?.artifact;
 return <Panel title="Review status" className="ai-access-card"><dl><div><dt>Artifact redaction</dt><dd>{a?.supported_content_verified?'Supported mappings verified':a?'Verification needs attention':'Awaiting result'}</dd></div><div><dt>Known review findings</dt><dd>{s?.audit?`${count(s.audit.counts.review)} textual unresolved`:'Awaiting inspection'}</dd></div><div><dt>Visual privacy</dt><dd>{s?.visual_privacy?`${s.visual_privacy.review_faces} faces require review`:'Not inspected'}</dd></div></dl><p className="access-reason">Review uncertain findings. Model detection can miss sensitive information.</p></Panel>;
}

export function ArtifactOutcome({state,regenerating,inspect}:{state:DocumentState;regenerating:boolean;inspect:()=>void}){
 const a=state.summary.artifact;
 return <Panel eyebrow="REDACTED REVIEW COPY" title="The result of this privacy inspection" className="artifact-outcome" subtitle={`${state.format.toUpperCase()} · Current revision ${state.revision??'—'} · Internal review only`}><div className="outcome-metrics">{[['Redactions applied',a?.applied_redactions],['Mapping failures',a?.mapping_failures],['Verification failures',a?.verification_failures]].map(([label,n])=><div key={label}><strong>{n??'—'}</strong><span>{label}</span></div>)}</div><p className={a?.supported_content_verified?'technical-pass':'amber'}><ShieldAlert size={18}/>{a?.supported_content_verified?'Supported redactions verified':'Artifact checks need attention'}</p><div className="artifact-actions"><ArtifactDownload state={state} regenerating={regenerating}/><Button variant="outline" onClick={inspect}>Artifact verification <ArrowRight size={15}/></Button></div></Panel>;
}
