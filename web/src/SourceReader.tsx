import {useEffect,useRef,useState} from 'react';
import {FileText,Layers,Pencil,Settings2} from 'lucide-react';
import {api} from './api';
import {Reader} from './Reader';
import {Field} from './ui';
import type {Doc} from './types';

export type PageLayout={paper:string;orientation:string;fontSize:number;wrap:boolean};
export type SourceDraft={content:string;options:PageLayout};
type SourceContent={text:string;html:string;encoding:string;kind:string;layout:PageLayout;warnings:string[];revision?:number};
type Props={doc:Doc;draft?:SourceDraft;onDraft:(draft:SourceDraft|undefined)=>void;onPrepare:(draft?:SourceDraft)=>void;preparing:boolean;onError:(message:string)=>void;onFocusChange:(active:boolean)=>void;requestedView?:{id:string;token:number}};

export function SourceReader({doc,draft,onDraft,onPrepare,preparing,onError,onFocusChange,requestedView}:Props){
 const [source,setSource]=useState<SourceContent|null>(null),[view,setView]=useState(doc.sourceKind==='markdown'&&doc.pages.length?'pdf':'original'),[settings,setSettings]=useState(false),[editing,setEditing]=useState(false);
 const revision=useRef(doc.revision||0);
 const [visibleChars,setVisibleChars]=useState(200000);
 useEffect(()=>{
  let active=true;
  api<SourceContent>('/documents/'+doc.id+'/source').then(value=>{if(active)setSource({...value,revision:doc.revision||0});}).catch(error=>{if(active)onError(error.message);});
  if((doc.revision||0)!==revision.current){revision.current=doc.revision||0;setView('pdf');setEditing(false);}
  return()=>{active=false;};
 },[doc.id,doc.revision]);
 useEffect(()=>{if(requestedView?.id===doc.id){if(doc.pages.length)setView('pdf');else onPrepare(draft);}},[requestedView?.token]);
 const ready=source?.revision===(doc.revision||0);
 const current=draft||(source&&ready?{content:source.text,options:source.layout}:null);
 function change(patch:Partial<SourceDraft>){if(!source||!current)return;const next={...current,...patch};onDraft(next.content===source.text&&JSON.stringify(next.options)===JSON.stringify(source.layout)?undefined:next);}
 function pdfPreview(){if(!doc.pages.length||draft){onPrepare(draft);return;}setEditing(false);setView('pdf');}
 return <section className="source-reader" aria-label={doc.name+' reader'}>
  <div className="source-controls">
   <div className="source-view-tabs" role="group" aria-label="Document view"><button aria-pressed={view==='original'&&!editing} onClick={()=>{setView('original');setEditing(false);}}><FileText size={16} aria-hidden="true"/>{source?.kind==='html'?'Read original':source?.kind==='markdown'?'Read Markdown':'Read text'}</button><button aria-pressed={view==='pdf'&&!editing} disabled={preparing} onClick={pdfPreview}><Layers size={16} aria-hidden="true"/>{doc.pages.length?'PDF preview':'Prepare PDF'}</button></div>
   <div className="actions"><button aria-expanded={settings} onClick={()=>setSettings(value=>!value)}><Settings2 size={16} aria-hidden="true"/>PDF layout</button>{source&&source.kind!=='html'&&<button disabled={preparing||!ready} aria-pressed={editing} onClick={()=>{setEditing(value=>!value);setView('original');}}><Pencil size={16} aria-hidden="true"/>Edit text</button>}</div>
  </div>
  {source?.kind==='html'&&<p className="source-caption">Original HTML · PDF preparation is optional. Include local images/styles with the HTML when adding files. Review the PDF layout before saving.</p>}
  {source?.warnings.length? <details className="source-notes"><summary>Preview notes · {source.warnings.length}</summary>{source.warnings.map(note=><p key={note}>{note}</p>)}</details>:null}
  {settings&&current&&<fieldset className="source-layout" disabled={preparing}><legend>PDF layout</legend><Field label="Paper"><select value={current.options.paper} onChange={e=>change({options:{...current.options,paper:e.target.value}})}><option>A4</option><option>Letter</option><option>Legal</option></select></Field><Field label="Orientation"><select value={current.options.orientation} onChange={e=>change({options:{...current.options,orientation:e.target.value}})}><option value="portrait">Portrait</option><option value="landscape">Landscape</option></select></Field>{source?.kind!=='html'&&<><Field label="Font size"><input type="number" min={8} max={24} value={current.options.fontSize} onChange={e=>change({options:{...current.options,fontSize:Number(e.target.value)}})}/></Field><label className="check"><input type="checkbox" checked={current.options.wrap} onChange={e=>change({options:{...current.options,wrap:e.target.checked}})}/>Wrap long lines</label></>}<button className="primary" onClick={()=>onPrepare(draft)}>{doc.pages.length?'Update PDF preview':'Prepare PDF'}</button></fieldset>}
  {draft&&<div className="source-draft-notice"><span>Text or layout changes are pending. Update the PDF preview to include them in exports.</span><button disabled={preparing} onClick={()=>onPrepare(draft)}>Update PDF preview</button><button className="ghost" disabled={preparing} onClick={()=>onDraft(undefined)}>Discard changes</button></div>}
  {!source?<div className="empty muted">Opening document…</div>:editing&&current?<textarea className="source-text-editor" aria-label="Working text copy" spellCheck={false} disabled={preparing} value={current.content} onChange={e=>change({content:e.target.value})}/>:view==='pdf'&&doc.pages.length?<Reader key={`${doc.id}-${doc.revision||0}`} doc={doc} focusAvailable onFocusChange={onFocusChange}/>:source.kind==='text'?<pre className="source-text" tabIndex={0} aria-label="Document text">{(current?.content||'Empty text file').slice(0,visibleChars)}</pre>:<iframe className="source-html" title={doc.name+' original content'} sandbox="" referrerPolicy="no-referrer" srcDoc={source.html}/>}
  {source&&source.kind==='text'&&view!=='pdf'&&!editing&&(current?.content.length||0)>visibleChars&&<div className="source-caption">Showing {visibleChars.toLocaleString()} of {current?.content.length.toLocaleString()} characters. PDF export uses the complete text. <button onClick={()=>setVisibleChars(value=>value+200000)}>Show more text</button></div>}
  {source&&view!=='pdf'&&<p className="source-caption">{source.kind==='html'?'Static HTML reader':source.kind==='markdown'?'Formatted Markdown':'Text reader'} · {source.encoding} · source files are preserved</p>}
 </section>;
}
