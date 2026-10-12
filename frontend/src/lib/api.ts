import type { FindingList, Finding } from './types';
export class ApiError extends Error { constructor(public status:number){ super(status===409?'This review changed. Refresh before submitting feedback.':status===413?'The document exceeds the local size limit.':status===415?'Supported uploads are PDF, DOCX and PPTX.':status===422?'Check the finding, source range and current decision.':'The local operation could not be completed. Please retry.'); } }
let pending:Promise<void>=Promise.resolve();
export function api<T>(path:string, init:RequestInit={}):Promise<T> {
  // The existing local launcher has a four-connection limit and synchronous
  // processing. Serialize JSON requests rather than burst on each React mount.
  const request=pending.then(async()=>{
    const response=await fetch(path,{...init,credentials:'same-origin',headers:{'X-Cadence-Local':'1',...(init.body instanceof FormData?{}:{'Content-Type':'application/json'}),...init.headers}});
    if(!response.ok)throw new ApiError(response.status);
    return response.json() as Promise<T>;
  });
  pending=request.then(()=>undefined,()=>undefined);
  return request;
}
export const documentUrl=(id:string)=>`/api/documents/${encodeURIComponent(id)}`;
export const artifactUrl=(id:string,revision:number|null,inline=false)=>`${documentUrl(id)}/artifact?inline=${inline}&revision=${revision??0}`;
export async function allFindings(id:string):Promise<Finding[]> {
  const first=await api<FindingList>(`${documentUrl(id)}/findings?limit=100&offset=0`);
  const items=[...first.items];
  for(let offset=100;offset<first.total;offset+=100){const page=await api<FindingList>(`${documentUrl(id)}/findings?limit=100&offset=${offset}`);items.push(...page.items);}
  return items;
}
