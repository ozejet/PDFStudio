import {useEffect} from 'react';

export function useCloseWarning(hasWork:boolean) {
 useEffect(()=>{
  if(!hasWork)return;
  const warn=(event:BeforeUnloadEvent)=>{
   event.preventDefault();
   // Browsers choose the confirmation text; retain the legacy signal as well.
   event.returnValue='Save any results you want to keep before leaving PDF Studio.';
  };
  window.addEventListener('beforeunload',warn);
  return()=>window.removeEventListener('beforeunload',warn);
 },[hasWork]);
}
