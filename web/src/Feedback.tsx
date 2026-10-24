import {useEffect,useId,useRef,useState} from 'react';
import {ExternalLink,Loader2,RefreshCw,Settings,Star,X} from 'lucide-react';
import {api} from './api';
import {Dialog} from './ui';

export type FeedbackConfig={url:string};

export function FeedbackSettings({config,onChange}:{config:FeedbackConfig;onChange:(config:FeedbackConfig)=>void}){
 const id=useId(),[url,setUrl]=useState(config.url),[saving,setSaving]=useState(false),[error,setError]=useState(''),[saved,setSaved]=useState(false),[expanded,setExpanded]=useState(!config.url);
 useEffect(()=>{setUrl(config.url);},[config.url]);
 async function save(){
  setSaving(true);setError('');setSaved(false);
  try{const value=await api<FeedbackConfig>('/feedback/settings',{url:url.trim()});onChange(value);setUrl(value.url);setSaved(true);}
  catch(error){setError((error as Error).message);}
  finally{setSaving(false);}
 }
 return <details open={expanded} onToggle={event=>setExpanded(event.currentTarget.open)}><summary>Form connection</summary><section className="feedback-settings" aria-labelledby={id}>
  <h3 id={id}>Feedback form</h3>
  <p>Connect your Microsoft Form to collect feedback inside PDF Studio. This response link stays on this device and can be changed later.</p>
  <label className="field" htmlFor={id+'-url'}><span>Microsoft Forms response URL</span><input id={id+'-url'} aria-label="Microsoft Forms response URL" type="url" autoComplete="off" spellCheck={false} value={url} aria-invalid={!!error} aria-describedby={id+'-hint'+(error?' '+id+'-error':'')} onChange={event=>{setUrl(event.target.value);setSaved(false);setError('');}} placeholder="https://forms.office.com/Pages/ResponsePage.aspx?id=…"/><small id={id+'-hint'}>In Microsoft Forms, choose Collect responses and copy the response link or the URL inside its Embed code.</small></label>
  {error&&<p className="error" role="alert" id={id+'-error'}>{error}</p>}
  <div className="feedback-settings-actions"><button disabled={saving||url.trim()===config.url} onClick={()=>void save()}>{saving?<><Loader2 size={16} className="spin" aria-hidden="true"/>Saving…</>:'Save form link'}</button><span role="status">{saved?'Form link saved.':config.url?'Form connected.':'No form connected yet.'}</span></div>
 </section></details>;
}

function FormPreview({onConfigure}:{onConfigure:()=>void}){
 return <div className="feedback-preview">
  <div className="feedback-setup-note"><strong>Connect your Microsoft Form</strong><p>This preview shows the approved structure. Connect a form to start collecting responses.</p><button onClick={onConfigure}><Settings size={16} aria-hidden="true"/>Set up form</button></div>
  <div className="forms-preview-title"><h3>PDF Studio feedback</h3><p>Help improve the tools you use every day.</p><small>* Required</small></div>
  <fieldset className="forms-preview-fields" disabled aria-label="Feedback form preview — not connected">
   <div className="forms-preview-question"><label>1. How would you rate PDF Studio? *</label><div className="forms-preview-stars" aria-hidden="true">{[1,2,3,4,5].map(value=><Star key={value} size={32}/>)}</div><small>1 = Poor &nbsp; · &nbsp; 5 = Excellent</small></div>
   <div className="forms-preview-question"><label htmlFor="feedback-preview-comment">2. What would you like to share? *</label><textarea id="feedback-preview-comment" placeholder="What worked well? What could improve?" rows={3}/></div>
   <div className="forms-preview-question"><label htmlFor="feedback-preview-feature">3. Which feature did you use?</label><select id="feedback-preview-feature" defaultValue=""><option value="">Select a feature</option></select></div>
   <button className="forms-preview-submit" disabled>Submit · form not connected</button>
  </fieldset>
  <small className="forms-preview-brand">Microsoft Forms · structure preview</small>
 </div>;
}

export function FeedbackPanel({open,config,onClose,onConfigure}:{open:boolean;config:FeedbackConfig;onClose:()=>void;onConfigure:()=>void}){
 const id=useId(),close=useRef<HTMLButtonElement>(null),[started,setStarted]=useState(false),[loaded,setLoaded]=useState(false),[reload,setReload]=useState(0),[confirmReload,setConfirmReload]=useState(false),[error,setError]=useState(''),[opening,setOpening]=useState(false);
 useEffect(()=>{if(open){setStarted(true);close.current?.focus({preventScroll:true});}},[open]);
 useEffect(()=>{setLoaded(false);setError('');},[config.url]);
 useEffect(()=>{if(open&&started)close.current?.focus({preventScroll:true});},[started]);
 async function openBrowser(){setOpening(true);setError('');try{await api('/feedback/open',{});}catch(error){setError((error as Error).message);}finally{setOpening(false);}}
 return <aside id="pdfstudio-feedback" className="feedback-panel" hidden={!open} aria-labelledby={id} onKeyDown={event=>{if(event.key==='Escape'&&!event.defaultPrevented){event.preventDefault();event.stopPropagation();onClose();}}}>
  <header className="feedback-panel-heading"><div><h2 id={id}>Feedback</h2><p>Your document stays open while you share feedback.</p></div><button ref={close} className="icon ghost" aria-label="Close feedback" onClick={onClose}><X size={20} aria-hidden="true"/></button></header>
  <div className="feedback-panel-content">
   {!config.url?<FormPreview onConfigure={onConfigure}/>:started&&<div className="feedback-frame-wrap">
    {!loaded&&<div className="feedback-frame-loading" role="status"><Loader2 size={20} className="spin" aria-hidden="true"/>Loading Microsoft Forms…</div>}
    <iframe key={config.url+'-'+reload} src={config.url} title="PDF Studio feedback — Microsoft Forms" referrerPolicy="no-referrer" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox" onLoad={()=>setLoaded(true)}/>
   </div>}
  </div>
  <footer className="feedback-panel-footer">
   {error&&<p className="error" role="alert">{error}</p>}
   {config.url&&<><div className="feedback-panel-actions"><button disabled={opening} onClick={()=>void openBrowser()}><ExternalLink size={15} aria-hidden="true"/>{opening?'Opening…':'Open in browser'}</button><button className="icon ghost" aria-label="Reload feedback form" onClick={()=>setConfirmReload(true)}><RefreshCw size={16} aria-hidden="true"/></button><button className="icon ghost" aria-label="Configure feedback form" onClick={onConfigure}><Settings size={16} aria-hidden="true"/></button></div><p>If the form or company sign-in does not appear, open it in your browser.</p></>}
   <small>Feedback is collected by Microsoft Forms. PDF Studio does not attach your documents.</small>
  </footer>
  {confirmReload&&<Dialog title="Reload feedback form" onClose={()=>setConfirmReload(false)}><p>Answers that have not been submitted may be cleared. Closing and reopening the panel keeps the current form instead.</p><div className="dialog-actions"><button onClick={()=>setConfirmReload(false)}>Keep current form</button><button className="primary" onClick={()=>{setLoaded(false);setReload(value=>value+1);setConfirmReload(false);}}>Reload form</button></div></Dialog>}
 </aside>;
}
