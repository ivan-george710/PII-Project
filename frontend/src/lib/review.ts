import type { RangeSelection, SourceWindow } from './types';
import { codePointLength } from './core.mjs';
export const readable=(name:string)=>({PERSON:'Person',EMAIL_ADDRESS:'Email address',PHONE_NUMBER:'Phone number',EMPLOYEE_ID:'Employee ID',US_BANK_NUMBER:'US bank number',US_DRIVER_LICENSE:'US driver’s license',US_SSN:'US social security number'}[name]??name.toLowerCase().replaceAll('_',' '));
export const decisionLabel=(s:string)=>({CONFIRM:'Confirmed',REVIEW:'Review',REJECT:'Rejected'}[s]??s);
export const count=(n:number)=>n.toLocaleString();
export function sourceSelection(container:HTMLElement,source:SourceWindow):RangeSelection|null {
  const selection=window.getSelection();if(!selection?.rangeCount||selection.isCollapsed)return null;
  const range=selection.getRangeAt(0);if(!container.contains(range.startContainer)||!container.contains(range.endContainer))return null;
  const prefix=document.createRange();prefix.selectNodeContents(container);prefix.setEnd(range.startContainer,range.startOffset);
  const text=range.toString(),start=source.start+codePointLength(prefix.toString()),end=start+codePointLength(text);
  if(end<=start||end-start>1000)return null;
  return {start,end,text};
}
