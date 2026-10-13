import { useEffect, useState } from 'react';
import { FileText } from 'lucide-react';
import { api, documentUrl } from '@/lib/api';
import type { DocumentState, PreviewPagesResponse } from '@/lib/types';

/** Local source content only; a returned preview never falls back to the original. */
export function ChatDocument({state,mode,name,label,disabled=false,onOpen}:{state:DocumentState;mode:'original'|'redacted';name:string;label:string;disabled?:boolean;onOpen:()=>void}){
 const visual=['pdf','image'].includes(state.format);
 const [content,setContent]=useState<{text:string;image?:string}|null>(null);
 const [failed,setFailed]=useState(false);
 useEffect(()=>{
  let active=true;
  setContent(null);setFailed(false);
  if(disabled||visual)return;
  const base=documentUrl(state.document_session_id);
  void Promise.allSettled([
   api<PreviewPagesResponse>(`${base}/preview-pages?revision=${state.revision??0}`),
   api<{items:{url:string}[]}>(`${base}/preview-media?variant=${mode}&revision=${state.revision??0}`)
  ]).then(([pages,media])=>{
   if(!active)return;
   const first=pages.status==='fulfilled'?pages.value.pages?.[0]:null;
   const text=(mode==='original'?first?.original_text:first?.redacted_text)??'';
   const image=media.status==='fulfilled'?media.value.items?.[0]?.url:undefined;
   setContent({text:text.slice(0,650),image});
   if(pages.status==='rejected'&&media.status==='rejected')setFailed(true);
  });
  return()=>{active=false;};
 },[state.document_session_id,state.revision,mode,visual,disabled]);
 const image=visual?`${documentUrl(state.document_session_id)}/preview-image?variant=${mode}&page=1&revision=${state.revision??0}`:content?.image;
 return <button className="file-card document-card" disabled={disabled} onClick={onOpen} aria-label={`Open ${mode} ${name}`}>
  {!disabled&&<span className={`document-thumbnail ${state.format==='pptx'?'slide-thumbnail':''}`}>
   {image&&!failed&&<img src={image} alt={`${mode} ${name} preview`} loading="lazy" onError={()=>setFailed(true)}/>}
   {!visual&&content?.text&&<span className="document-excerpt">{content.text}</span>}
   {failed&&<span className="thumbnail-note">Preview unavailable · open file</span>}
   {!visual&&!content&&<span className="thumbnail-note">Loading preview…</span>}
   {!visual&&content&&!content.text&&!image&&<span className="thumbnail-note">Open to view document</span>}
  </span>}
  <span className="document-caption"><FileText size={21}/><span><strong>{name}</strong><small>{label}</small></span></span>
 </button>;
}
