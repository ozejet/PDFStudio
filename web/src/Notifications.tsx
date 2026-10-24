import {useEffect,useRef,useState} from 'react';
import {AlertCircle,AlertTriangle,CheckCircle2,Info,Loader2,X} from 'lucide-react';
import type {Artifact} from './types';

export type Notice = {
 id:string;tone:'success'|'info'|'warning'|'error';title:string;message?:string;details?:string;
 action?:{label:string;onClick:()=>void};download?:Artifact;duration?:number;
};

function Toast({notice,onDismiss}:{notice:Notice;onDismiss:(id:string)=>void}){
 const [hovered,setHovered]=useState(false),[focused,setFocused]=useState(false),[expanded,setExpanded]=useState(false);
 const dismiss=useRef(onDismiss);dismiss.current=onDismiss;
 const remaining=useRef(notice.duration??(notice.tone==='success'?6000:0));
 useEffect(()=>{remaining.current=notice.duration??(notice.tone==='success'?6000:0);setExpanded(false);},[notice]);
 useEffect(()=>{
  if(hovered||focused||expanded||remaining.current<=0)return;
  const start=Date.now(),timer=window.setTimeout(()=>dismiss.current(notice.id),remaining.current);
  return()=>{window.clearTimeout(timer);remaining.current=Math.max(0,remaining.current-(Date.now()-start));};
 },[notice,hovered,focused,expanded]);
 const Icon=notice.tone==='success'?CheckCircle2:notice.tone==='error'?AlertCircle:notice.tone==='warning'?AlertTriangle:Info;
 return <article className={'toast toast-'+notice.tone} onPointerEnter={()=>setHovered(true)} onPointerLeave={()=>setHovered(false)} onFocusCapture={()=>setFocused(true)} onBlurCapture={e=>{if(!e.currentTarget.contains(e.relatedTarget as Node|null))setFocused(false);}}>
  <Icon size={21} aria-hidden="true"/>
  <div className="toast-content">
   <div role={notice.tone==='error'?'alert':'status'} aria-live={notice.tone==='error'?'assertive':'polite'} aria-atomic="true"><strong>{notice.title}</strong>{notice.message&&<p>{notice.message}</p>}</div>
   {(notice.action||notice.download||notice.details)&&<div className="toast-actions">
    {notice.action&&<button className="link" onClick={notice.action.onClick}>{notice.action.label}</button>}
    {notice.download&&<a href={notice.download.url} download={notice.download.name}>Download</a>}
    {notice.details&&<button className="link" aria-expanded={expanded} onClick={()=>setExpanded(value=>!value)}>{expanded?'Hide details':'View details'}</button>}
   </div>}
   {expanded&&<pre className="toast-details">{notice.details}</pre>}
  </div>
  <button className="icon ghost toast-dismiss" aria-label={'Dismiss '+notice.title} onClick={()=>onDismiss(notice.id)}><X size={16} aria-hidden="true"/></button>
 </article>;
}

export function Notifications({notices,onDismiss,progress,cancel}:{notices:Notice[];onDismiss:(id:string)=>void;progress?:{title:string;detail?:string;value?:number|null;max?:number;elapsed?:number}|null;cancel?:{label:string;disabled:boolean;onClick:()=>void}}){
 const [showProgress,setShowProgress]=useState(false),working=!!progress;
 useEffect(()=>{if(!working){setShowProgress(false);return;}const timer=window.setTimeout(()=>setShowProgress(true),250);return()=>window.clearTimeout(timer);},[working]);
 return <section className="notification-stack" aria-label="Notifications">
  {progress&&showProgress&&<article className="toast toast-progress"><Loader2 className="spin" size={21} aria-hidden="true"/><div className="toast-content"><strong role="status" aria-live="polite">{progress.title}</strong>{progress.detail&&<p>{progress.detail}</p>}{progress.max!==undefined&&<progress aria-label="Import progress" max={progress.max} value={progress.value??undefined}/>} {progress.elapsed!==undefined&&<small aria-hidden="true">{progress.elapsed}s elapsed</small>}{cancel&&<div className="toast-actions"><button disabled={cancel.disabled} onClick={cancel.onClick}>{cancel.label}</button></div>}</div></article>}
  {notices.map(notice=><Toast key={notice.id} notice={notice} onDismiss={onDismiss}/>)}
 </section>;
}
