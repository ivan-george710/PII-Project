import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
afterEach(()=>{cleanup();vi.restoreAllMocks();});
Object.defineProperty(window,'matchMedia',{writable:true,value:(query:string)=>({matches:query.includes('reduced-motion'),media:query,onchange:null,addListener:()=>{},removeListener:()=>{},addEventListener:()=>{},removeEventListener:()=>{},dispatchEvent:()=>true})});
class ResizeObserverStub { observe(element:HTMLElement){this.callback([{contentRect:{width:600,height:220},target:element}] as unknown as ResizeObserverEntry[],this as unknown as ResizeObserver);} unobserve(){} disconnect(){} constructor(private callback:ResizeObserverCallback){} }
vi.stubGlobal('ResizeObserver',ResizeObserverStub);
Element.prototype.getBoundingClientRect=()=>({width:600,height:220,top:0,bottom:220,left:0,right:600,x:0,y:0,toJSON:()=>({})});
HTMLElement.prototype.scrollIntoView=()=>{};
