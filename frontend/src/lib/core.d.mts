export function codePointLength(text:string):number;
export function codePointSlice(text:string,start:number,end?:number):string;
export function sourceSelection(prefix:string,selected:string,windowStart:number):{start:number;end:number};
export function feedbackPayload(revision:number|null,findingId:string,action:string,reviewer:string,reason:string):{expected_revision:number|null;finding_id:string;action:string;reviewer_id:string;reason:string|null};
export function missedPayload(revision:number|null,location:number,range:{start:number;end:number},entity:string,reviewer:string,reason:string):{expected_revision:number|null;location:number;start:number;end:number;entity_type:string;reviewer_id:string;reason:string|null};
export function stageLabel(name:string):string;
