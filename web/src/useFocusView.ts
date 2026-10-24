import {useEffect,useLayoutEffect,useRef,useState,type RefObject,type MouseEvent as ReactMouseEvent} from 'react';
import {flushSync} from 'react-dom';
import {captureReadingPosition,restoreReadingPosition,type ReadingPosition} from './readingPosition';

export function useFocusView(pages:RefObject<HTMLDivElement|null>,toolbar:RefObject<HTMLDivElement|null>,available:boolean,readingKey:string,onChange?:(active:boolean)=>void) {
 const [active,setActive]=useState(false),[visible,setVisible]=useState(true);
 const live=useRef({active,readingKey,onChange});live.current={active,readingKey,onChange};
 const timer=useRef<number|undefined>(undefined),hover=useRef({top:false,toolbar:false});
 const returnFocus=useRef<HTMLElement|null>(null),position=useRef<ReadingPosition|null>(null),wasActive=useRef(false);
 const entry=useRef<{position:ReadingPosition|null;key:string}|null>(null),focusStart=useRef<ReadingPosition|null>(null);
 const clear=()=>{window.clearTimeout(timer.current);timer.current=undefined;};
 const show=()=>{clear();setVisible(true);};
 const schedule=()=>{
  clear();if(!live.current.active)return;
  timer.current=window.setTimeout(()=>{
   if(!hover.current.top&&!hover.current.toolbar&&!toolbar.current?.contains(document.activeElement))setVisible(false);
  },1500);
 };
 const change=(next:boolean)=>{
  if(!available)return;
  const current=pages.current?captureReadingPosition(pages.current):null;
  position.current=current;
  if(next){returnFocus.current=document.activeElement as HTMLElement|null;entry.current={position:current,key:live.current.readingKey};focusStart.current=null;}
  else if(entry.current?.key===live.current.readingKey&&current&&focusStart.current){
   const start=focusStart.current;
   // A larger viewport may show the entire page and clamp its scroll offset.
   // Returning immediately should recover the original offset in the small pane.
   if(current.page===start.page&&Math.abs(current.x-start.x)<.0001&&Math.abs(current.y-start.y)<.0001)position.current=entry.current.position;
  }
  hover.current={top:false,toolbar:false};
  setVisible(true);setActive(next);
 };
 useLayoutEffect(()=>{
  live.current.onChange?.(active);
  if(active){pages.current?.focus({preventScroll:true});schedule();}
  else if(wasActive.current&&returnFocus.current?.isConnected)returnFocus.current.focus({preventScroll:true});
  wasActive.current=active;
  return clear;
 },[active]);
 useLayoutEffect(()=>()=>{clear();live.current.onChange?.(false);},[]);
 useEffect(()=>{
  if(!active)return;
  const keyboard=(event:KeyboardEvent)=>{
   // A real modal above the reader owns Escape and keyboard focus first.
   const modal=document.querySelector('dialog[open]');
   if(modal&&!modal.contains(pages.current))return;
   if(event.key==='Escape'){
    event.preventDefault();event.stopImmediatePropagation();change(false);
   }else if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='f'){
    event.preventDefault();flushSync(show);toolbar.current?.querySelector<HTMLInputElement>('[data-reader-search]')?.focus();
   }else if(event.key==='Tab'){
    // Make controls available before the browser calculates the next Tab stop.
    flushSync(show);
    if(event.target===pages.current){
     event.preventDefault();
     const controls=toolbar.current?.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled),select:not(:disabled),a[href]');
     const next=controls?.[event.shiftKey?controls.length-1:0];next?.focus();
    }
    schedule();
   }
  };
  window.addEventListener('keydown',keyboard,true);
  return()=>window.removeEventListener('keydown',keyboard,true);
 },[active]);
 return {active,visible,change,
  restoreLayout(settled:boolean){if(position.current&&pages.current){restoreReadingPosition(pages.current,position.current);if(settled){position.current=null;if(active)focusStart.current=captureReadingPosition(pages.current);else{entry.current=null;focusStart.current=null;}}}},
  topEnter(){hover.current.top=true;show();},topLeave(){hover.current.top=false;schedule();},
  toolbarEnter(){hover.current.toolbar=true;show();},toolbarLeave(){hover.current.toolbar=false;schedule();},
  toolbarFocus:show,toolbarBlur:schedule,show,
  toolbarClick(event:ReactMouseEvent<HTMLDivElement>){
   // Mouse buttons return control to the document. Keyboard navigation and
   // active fields keep their focus, so controls never disappear while typing.
   if(active&&event.detail>0&&(event.target as HTMLElement).closest('button'))pages.current?.focus({preventScroll:true});
  },
 };
}
