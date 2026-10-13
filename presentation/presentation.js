'use strict';
const $=id=>document.getElementById(id);
const shots=[
 {node:'source',rect:[-30,325,710,740],seconds:28,heading:'PII Guard.'},
 {node:'source',rect:[20,360,620,700],seconds:20},
 {node:'extract',rect:[610,315,690,760],seconds:40},
 {node:'detect',rect:[1260,315,700,760],seconds:45},
 {node:'redact',rect:[1920,315,700,760],seconds:40},
 {node:'rules',rect:[1260,-45,700,470],seconds:50},
 {node:'audit',rect:[1260,1110,700,620],seconds:60},
 {node:'integration',rect:[600,285,1990,1420],seconds:40},
 {node:'manager',rect:[2630,455,740,800],seconds:45},
 {node:'verify',rect:[1920,1100,700,630],seconds:25},
 {node:'architecture',rect:[-35,-70,3420,1920],seconds:45,heading:'The whole system.'},
 {node:'network',rect:[430,1780,910,730],seconds:35,heading:'Beyond one interface.'},
 {node:'shares',rect:[1410,1780,910,730],seconds:30,heading:'Before sharing.'},
 {node:'closing',rect:[-35,-70,3420,2610],seconds:15,heading:'From upload to oversight.'}
];
const groups=[{label:'Diljot · introduction',indices:[0,1]},{label:'Ivan · engines',indices:[2,3,4]},{label:'Adarsh · custom rules',indices:[5]},{label:'Shambavi · audit',indices:[6]},{label:'Anubhav · integration + manager',indices:[7,8,9]},{label:'Diljot · architecture + future',indices:[10,11,12,13]}];
let durations=shots.map(s=>s.seconds);
try{const saved=JSON.parse(localStorage.getItem('pii-presentation-timing'));if(Array.isArray(saved)&&saved.length===14&&saved.every(v=>Number.isFinite(v)&&v>=.25&&v<=3600))durations=saved;}catch{}
let index=-1,elapsed=0,playing=false,total=0,starts=[];
let cam={x:325,y:695,z:0},goal={...cam},velocity={x:0,y:0,z:0},last=performance.now(),demoBase=0;
let traveler={x:170,y:562,scale:1,opacity:1},travelerFrom={...traveler};
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const clamp=(v,min=0,max=1)=>Math.max(min,Math.min(max,v));
const ramp=(t,start,length=1)=>clamp((t-start)/length);
const ease=t=>1-Math.pow(1-clamp(t),4);
const clock=t=>`${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
function rebuild(){total=durations.reduce((a,b)=>a+b,0);starts=[];let sum=0;for(const d of durations){starts.push(sum);sum+=d;}}
rebuild();
function focus(rect){const box=$('viewport').getBoundingClientRect();let [x,y,w,h]=rect;const nodeElement=index>=0?$(shots[index].node+'-engine'):null;if(innerWidth<600&&nodeElement&&h<950){x=nodeElement.offsetLeft-25;y=nodeElement.offsetTop-50;w=nodeElement.offsetWidth+50;h=nodeElement.offsetHeight+100;}const scale=Math.min(box.width/w,box.height/h)*.94;goal={x:x+w/2,y:y+h/2,z:Math.log(scale)};if(reduced.matches){cam={...goal};velocity={x:0,y:0,z:0};}}
function activeNode(node){document.querySelectorAll('.engine').forEach(el=>el.classList.toggle('active',el.id===node+'-engine'||['architecture','closing','integration'].includes(node)));}
function select(next,snap=false){
 index=clamp(Math.trunc(next),0,shots.length-1);const shot=shots[index],s=story[index];
 $('world').dataset.shot=shot.node;$('world').classList.toggle('world-overview',['architecture','integration','closing'].includes(shot.node));document.body.dataset.shot=shot.node;
 $('world').classList.toggle('show-future',index>=11);activeNode(shot.node);focus(shot.rect);
 if(snap){cam={...goal};velocity={x:0,y:0,z:0};}
 travelerFrom={...traveler};demoBase=starts[index];
 $('scene-title').textContent=shot.heading??'';$('speaker').textContent=s.speaker;$('chapter').textContent=s.chapter;
 $('scene-count').textContent=`${index+1} / ${shots.length}`;
 $('notes-title').textContent=`${s.speaker} · ${s.chapter}`;$('notes-text').textContent=s.notes;
 $('demo-label').textContent=index>=11&&index<13?'Future scope · proposed demonstration':'Illustrative demonstration';
 $('context-label').textContent=index>=10?'Full files local · affected evidence remote':'No LLM · local redaction';
 console.debug('PII film scene',index,s.speaker,s.chapter);document.title=`${s.chapter} · PII Guard`;history.replaceState(null,'',`#${index}`);
 document.querySelectorAll('#chapters button').forEach((el,i)=>el.setAttribute('aria-current',i===index?'step':'false'));
}
function seek(next){elapsed=clamp(next,0,total);let nextIndex=starts.findLastIndex(s=>s<=elapsed);if(nextIndex<0)nextIndex=0;select(nextIndex);updateDemo(elapsed-starts[index]);renderTransport();setPlaying(playing);}
function setPlaying(value){playing=value&&elapsed<total;$('play-label').textContent=playing?'Pause':elapsed>=total?'Replay':elapsed>0?'Resume':'Start film';$('play').setAttribute('aria-label',playing?'Pause automatic presentation':elapsed>=total?'Replay automatic presentation':elapsed>0?'Resume automatic presentation':'Start automatic presentation');$('play').querySelector('path').setAttribute('d',playing?'M8 5h3v14H8zm6 0h3v14h-3Z':'m8 5 11 7-11 7Z');last=performance.now();}
function renderTransport(){const ratio=elapsed/total;$('scrub').value=String(Math.round(ratio*1000));$('scrub').style.setProperty('--progress',ratio*100+'%');$('clock').textContent=`${clock(elapsed)} / ${clock(total)}`;}
const worldStyle=$('world').style;
const portrait=document.querySelector('.paper-portrait img'),faceCanvas=document.querySelector('canvas.portrait-blur');
const faceContext=faceCanvas.getContext('2d'),scratch=document.createElement('canvas');
scratch.width=36;scratch.height=48;const scratchContext=scratch.getContext('2d');let previousFace=-1,lastDecision=-1,frameCount=0,frameEpoch=performance.now();
function pixelateFace(amount){
 if(!faceContext||!scratchContext||!portrait.complete||!portrait.naturalWidth||Math.abs(amount-previousFace)<.02)return;
 previousFace=amount;faceContext.clearRect(0,0,76,76);
 if(amount<=0)return;
 const cells=Math.max(2,Math.round(36/(1+amount*12)));
 scratchContext.clearRect(0,0,36,48);scratchContext.filter='grayscale(1)';
 scratchContext.drawImage(portrait,152,84,144,192,0,0,cells,Math.max(2,Math.round(cells*4/3)));
 faceContext.imageSmoothingEnabled=false;faceContext.globalAlpha=Math.min(1,amount*2);
 faceContext.drawImage(scratch,0,0,cells,Math.max(2,Math.round(cells*4/3)),13,14,36,48);
}
portrait.addEventListener('load',()=>{previousFace=-1;});
function v(name,value){worldStyle.setProperty(name,String(value));}
function updateDemo(sceneTime){
 const node=shots[index].node;const loop=(sceneTime*Math.max(1,12/durations[index]))%12;const done=reduced.matches?1:null;
 const overview=['architecture','closing','integration'].includes(node);
 v('--route',(elapsed%12)/12);
 const extract=node==='extract'?loop:overview?8:0;
 v('--unfold',done??ramp(extract,.7,2.4));v('--layer-blur',reduced.matches?0:extract>.7&&extract<3.1?Math.sin((extract-.7)/2.4*Math.PI)*2.5:0);v('--scan',done??((extract%4)/4));v('--ocr',done??ramp(extract,2.6,.8));v('--structured',done??ramp(extract,4,.8));
 const detection=node==='detect'?loop:overview?8:0;
 for(let i=1;i<=4;i++)v('--r'+i,done??ramp(detection,.5+i*.5,.7));v('--face',done??ramp(detection,3.5,.9));
 const protect=node==='redact'?loop:['architecture','closing','integration','verify','audit','manager'].includes(node)?10:0;
 v('--highlight',node==='detect'?ramp(loop,.4,1):0);
 for(let i=1;i<=3;i++)v('--mask'+i,reduced.matches?(protect>0?1:0):ramp(protect,.5+i*.45,.9));v('--masks',reduced.matches?(protect>0?1:0):ramp(protect,1.5,1));v('--face-blur',reduced.matches?(protect>0?1:0):ramp(protect,2.5,1));pixelateFace(reduced.matches?(protect>0?1:0):ramp(protect,2.5,1));
 const rule=node==='rules'?loop:overview?8:0;const chars=reduced.matches?5:Math.min(5,Math.floor(ramp(rule,.7,2.3)*5));$('rule-typing').textContent=rule?('Orion'.slice(0,chars)||' '):'Orion';v('--caret',reduced.matches?0:Math.floor(sceneTime*2)%2?0:1);v('--rule-on',done??ramp(rule,3.3,.5));v('--mask4',reduced.matches?(node==='rules'||overview?1:0):node==='rules'?ramp(rule,3.8,1):overview?1:0);
 const audit=node==='audit'?loop:overview?8:0;for(let i=1;i<=4;i++)v('--a'+i,done??ramp(audit,.3+i*.65,.7));v('--audit-link',done??ramp(audit,1.4,2));
 const verify=node==='verify'?loop:overview?8:0;v('--verify-scan',done??clamp(verify/4));v('--verified',done??ramp(verify,4,1.1));
 const managerClock=sceneTime*Math.max(1,30/durations[index]);const decision=node==='manager'?Math.floor((managerClock%30)/10):0;if(node==='manager'&&decision!==lastDecision){console.debug('PII film decision',['pending','approved','denied'][decision]);lastDecision=decision;}
 $('approve-demo').classList.toggle('selected',decision===1);$('deny-demo').classList.toggle('selected',decision===2);
 $('manager-result').textContent=decision===2?'Denied · download blocked':decision===1?'Approved · copy available':'Pending · download available';
 $('lock-shape').setAttribute('d',decision===2?'M6 11h12v10H6zm3 0V7a3 3 0 0 1 6 0':'M6 11h12v10H6zm9 0V7a3 3 0 0 0-6 0');
 v('--report-in',done??(node==='manager'?ramp(loop,0,1):1));
 v('--packet',reduced.matches?.25:(sceneTime%3)/3);v('--packet2',reduced.matches?.5:((sceneTime+1)%3)/3);v('--packet3',reduced.matches?.75:((sceneTime+2)%3)/3);v('--packet-visible',node==='network'?1:0);v('--share',done??(node==='shares'?ramp(loop,2,2):overview?1:0));
 // Rules zoom back to include the connected classifier automatically.
 if(node==='rules'&&sceneTime>7)focus([1250,-35,730,1130]);
 const positions={source:{x:170,y:552,scale:1,opacity:1},extract:{x:770,y:555,scale:.92,opacity:reduced.matches?0:1-ramp(sceneTime,.8,2.6)},detect:{x:1460,y:568,scale:.9,opacity:0},redact:{x:2115,y:524,scale:.88,opacity:1},rules:{x:2115,y:524,scale:.88,opacity:0},audit:{x:1450,y:1300,scale:.5,opacity:0},verify:{x:2115,y:1250,scale:.65,opacity:0},integration:{x:2115,y:524,scale:.88,opacity:1},architecture:{x:2115,y:524,scale:.88,opacity:1},manager:{x:2800,y:750,scale:.5,opacity:0},network:{x:2115,y:524,scale:.88,opacity:1},shares:{x:2115,y:524,scale:.88,opacity:1},closing:{x:2115,y:524,scale:.88,opacity:1}};
 const target=positions[node];const motion=reduced.matches?1:ease(sceneTime/2.7);
 for(const key of ['x','y','scale','opacity'])traveler[key]=travelerFrom[key]+(target[key]-travelerFrom[key])*motion;
 const arc=reduced.matches?0:Math.sin(clamp(sceneTime/2.7)*Math.PI)*-65;
 $('traveler').style.transform=`translate3d(${traveler.x}px,${traveler.y+arc}px,0) scale(${traveler.scale})`;$('traveler').style.opacity=String(traveler.opacity);$('traveler').style.filter=reduced.matches?'none':`blur(${(Math.sin(clamp(sceneTime/2.7)*Math.PI)*2.8).toFixed(2)}px)`;v('--tilt',node==='source'?reduced.matches?-5:-5+Math.sin(sceneTime*.45)*2:0);
}
let lastPaint=0;
function frame(now){frameCount++;if(now-frameEpoch>=1000){$('viewport').dataset.frameRate=(frameCount*1000/(now-frameEpoch)).toFixed(1);frameCount=0;frameEpoch=now;}const rawDt=Math.max(0,(now-last)/1000),dt=Math.min(.04,rawDt);last=now;
 if(playing){elapsed=Math.min(total,elapsed+rawDt);let next=starts.findLastIndex(s=>s<=elapsed);if(next!==index)select(next);if(elapsed===total)setPlaying(false);}
 if(!reduced.matches){for(let step=0;step<4;step++){for(const key of ['x','y','z']){const h=dt/4;velocity[key]+=(75*(goal[key]-cam[key])-18*velocity[key])*h;cam[key]+=velocity[key]*h;}}}
 const viewport=$('viewport');const scale=Math.exp(cam.z);const speed=Math.hypot(velocity.x,velocity.y)*scale+Math.abs(velocity.z)*Math.min(viewport.clientWidth,viewport.clientHeight)*.8;const blur=reduced.matches?0:clamp(speed/320,0,5.5);viewport.style.setProperty('--motion-blur',blur.toFixed(2)+'px');worldStyle.transform=`translate3d(${viewport.clientWidth/2-cam.x*scale}px,${viewport.clientHeight/2-cam.y*scale}px,0) scale(${scale})`;
 if(now-lastPaint>30){updateDemo(elapsed-demoBase);renderTransport();lastPaint=now;}
 requestAnimationFrame(frame);
}
$('play').addEventListener('click',()=>{if(elapsed>=total)seek(0);setPlaying(!playing);});
$('scrub').addEventListener('input',event=>seek(Number(event.target.value)/1000*total));
$('next').addEventListener('click',()=>seek(starts[Math.min(index+1,13)]));$('previous').addEventListener('click',()=>seek(starts[Math.max(index-1,0)]));$('replay').addEventListener('click',()=>{seek(starts[index]);setPlaying(true);});
$('notes-toggle').addEventListener('click',()=>{const open=$('notes').hidden;$('notes').hidden=!open;$('notes-toggle').setAttribute('aria-expanded',String(open));if(open)$('notes-close').focus();});$('notes-close').addEventListener('click',()=>{$('notes').hidden=true;$('notes-toggle').setAttribute('aria-expanded','false');$('notes-toggle').focus();});
$('chapters').innerHTML=story.map((s,i)=>`<button data-index="${i}"><span>${s.chapter}</span><small>${s.speaker}</small></button>`).join('');
$('overview-toggle').addEventListener('click',()=>{setPlaying(false);$('overview').showModal();});$('overview-close').addEventListener('click',()=>{$('overview').close();$('overview-toggle').focus();});$('chapters').addEventListener('click',event=>{const choice=event.target.closest('[data-index]');if(choice){$('overview').close();seek(starts[Number(choice.dataset.index)]);$('play').focus();}});
$('timing-toggle').addEventListener('click',()=>{setPlaying(false);$('timing-form').innerHTML=groups.map((g,i)=>`<label>${g.label}<input type="number" min="15" max="3600" step="1" value="${Math.round(g.indices.reduce((n,j)=>n+durations[j],0))}" aria-label="${g.label}, seconds" data-group="${i}"></label>`).join('');$('timing').showModal();});$('timing-close').addEventListener('click',()=>{$('timing').close();$('timing-toggle').focus();});
$('timing-save').addEventListener('click',()=>{const form=$('timing-form');if(!form.reportValidity())return;for(const input of form.querySelectorAll('input')){const group=groups[Number(input.dataset.group)],sum=group.indices.reduce((a,i)=>a+shots[i].seconds,0);for(const i of group.indices)durations[i]=shots[i].seconds/sum*Number(input.value);}try{localStorage.setItem('pii-presentation-timing',JSON.stringify(durations));}catch{}rebuild();elapsed=starts[index];select(index);$('timing').close();$('play').focus();});
$('fullscreen').addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{$('fullscreen').setAttribute('aria-label','Use browser fullscreen control');}});document.addEventListener('fullscreenchange',()=>{$('fullscreen').setAttribute('aria-label',document.fullscreenElement?'Exit fullscreen':'Enter fullscreen');focus(shots[index].rect);});
addEventListener('resize',()=>focus(shots[index].rect));reduced.addEventListener('change',()=>focus(shots[index].rect));
document.addEventListener('visibilitychange',()=>{if(document.hidden)setPlaying(false);});
document.addEventListener('keydown',event=>{if(event.target.matches('input,textarea,select')||$('overview').open||$('timing').open)return;
 if(event.key===' '&&event.target===document.body){event.preventDefault();$('play').click();}if(event.key==='ArrowRight'){event.preventDefault();$('next').click();}if(event.key==='ArrowLeft'){event.preventDefault();$('previous').click();}if(event.key==='Home'){event.preventDefault();seek(0);}if(event.key==='End'){event.preventDefault();seek(starts[13]);}if(event.key.toLowerCase()==='n')$('notes-toggle').click();if(event.key.toLowerCase()==='f')$('fullscreen').click();if(event.key==='Escape'){$('notes').hidden=true;$('notes-toggle').setAttribute('aria-expanded','false');}});
window.addEventListener('hashchange',()=>{const n=Number(location.hash.slice(1));if(Number.isInteger(n)&&n>=0&&n<14)seek(starts[n]);});
const print=document.createElement('div');print.id='print-deck';story.forEach((s,i)=>{const section=document.createElement('section');section.className='print-slide';const h=document.createElement('h1');h.textContent=s.chapter;const p=document.createElement('p');p.textContent=s.notes;const f=document.createElement('footer');f.textContent=`PII Guard · ${s.speaker} · ${i+1} / 14`;section.append(h,p,f);print.append(section);});document.body.append(print);
let initial=Number(location.hash.slice(1));if(!Number.isInteger(initial)||initial<0||initial>=14)initial=0;elapsed=starts[initial];select(initial,true);updateDemo(0);renderTransport();requestAnimationFrame(frame);
