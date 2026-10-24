import {useEffect,useRef,useState} from 'react';
import {Play,Pause,Square} from 'lucide-react';
import type {PDFDocumentProxy} from 'pdfjs-dist';
import {parsePages} from './types';
import {ParagraphSpeaker,paragraphGroups,type Paragraph} from './speech';

export function ReadAloud({pdf,page,onGroup}:{pdf:PDFDocumentProxy|null;page:number;onGroup:(group:Paragraph|null)=>void}){
 const [voices,setVoices]=useState<SpeechSynthesisVoice[]>([]),[voice,setVoice]=useState(''),[rate,setRate]=useState(1),[range,setRange]=useState('current'),[state,setState]=useState<'idle'|'loading'|'speaking'|'paused'>('idle'),[error,setError]=useState(''),[current,setCurrent]=useState<Paragraph|null>(null);
 const speaker=useRef<ParagraphSpeaker|null>(null),callback=useRef(onGroup);callback.current=onGroup;
 useEffect(()=>{
  if(!('speechSynthesis'in window)){setError('Read Aloud is unavailable in this browser.');return;}
  const synth=window.speechSynthesis;const controller=new ParagraphSpeaker(synth);speaker.current=controller;
  const update=()=>{const local=synth.getVoices().filter(v=>v.localService);setVoices(local);setVoice(old=>local.some(v=>v.voiceURI===old)?old:local[0]?.voiceURI||'');};
  update();synth.addEventListener('voiceschanged',update);
  return()=>{controller.stop();speaker.current=null;synth.removeEventListener('voiceschanged',update);};
 },[pdf]);
 const active=state!=='idle';
 function start(){
  setError('');const selected=voices.find(v=>v.voiceURI===voice&&v.localService);if(!pdf||!selected)return;
  let selectedPages:number[];try{selectedPages=parsePages(range==='current'?String(page):range,pdf.numPages);}catch(error){setError((error as Error).message);return;}
  const document=pdf;
  async function* groups(){let count=0;for(const number of selectedPages){const content=await (await document.getPage(number)).getTextContent();for(const group of paragraphGroups(content.items,number)){count++;yield group;}}if(!count)throw Error('No selectable text was found in this page range. Image-only scans cannot be read aloud.');}
  speaker.current?.start(groups(),selected,rate,{group:group=>{setCurrent(group);callback.current(group);},state:setState,error:setError});
 }
 return <div className="read-aloud" role="region" aria-label="Read Aloud controls">
  <label>Local voice<select disabled={active} value={voice} onChange={e=>setVoice(e.target.value)} aria-label="Local voice">{voices.map(v=><option key={v.voiceURI} value={v.voiceURI}>{v.name} / {v.lang}</option>)}</select></label>
  <label>Pages<input disabled={active} aria-label="Read Aloud page range" value={range} onChange={e=>setRange(e.target.value)} placeholder="current, all, 1-3"/></label>
  <label>Speed<select disabled={active} aria-label="Read Aloud speed" value={rate} onChange={e=>setRate(+e.target.value)}>{[.5,.75,1,1.25,1.5,1.75,2].map(n=><option key={n} value={n}>{n}x</option>)}</select></label>
  <div className="actions"><button disabled={!pdf||!voices.length||active} onClick={start}><Play size={15}/>Read</button><button disabled={!active||state==='loading'} onClick={()=>state==='paused'?speaker.current?.resume():speaker.current?.pause()}><Pause size={15}/>{state==='paused'?'Resume':'Pause'}</button><button disabled={!active} onClick={()=>speaker.current?.stop()}><Square size={15}/>Stop</button></div>
  <p className="speech-status" role="status">{error||(!voices.length?'No installed local voice is available in this browser.':current?`${state==='paused'?'Paused':'Reading'} page ${current.page}, paragraph ${current.index+1}`:state==='loading'?'Preparing paragraphs...':'Whole paragraphs are highlighted. Pages: current, all, or a range such as 1-3.')}</p>
 </div>;
}
