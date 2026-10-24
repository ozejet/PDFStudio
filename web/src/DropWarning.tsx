import {useEffect,useRef,useState} from 'react';
import {AlertTriangle,X} from 'lucide-react';

export function DropWarning({names,onClose}:{names:string[];onClose:()=>void}) {
 const [seconds,setSeconds]=useState(10),close=useRef(onClose);
 close.current=onClose;
 useEffect(()=>{
  let remaining=10;
  const timer=window.setInterval(()=>{
   remaining--;
   if(remaining>0)setSeconds(remaining);
   else {window.clearInterval(timer);close.current();}
  },1000);
  return()=>window.clearInterval(timer);
 },[]);
 const summary=names.slice(0,3).join(', ')+(names.length>3?` and ${names.length-3} more`:'');
 return <div className="warning-toast"><AlertTriangle size={20} aria-hidden="true"/><div role="status" aria-live="polite"><strong>Ignored {names.length} non-PDF {names.length===1?'file':'files'}</strong><p>{summary}</p><p>Drop PDF files here. Use Add files for images, Word or PowerPoint.</p></div><span className="warning-countdown" aria-hidden="true">{seconds}</span><button className="icon ghost" aria-label="Dismiss file warning" onClick={onClose}><X size={16}/></button></div>;
}
