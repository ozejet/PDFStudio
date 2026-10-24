import {useEffect,useRef,useState} from 'react';
import {BookOpen,Layers,Pencil,Wrench,Plus,Files,X,Sun,Moon,Undo2,Redo2,Eye,Download,ChevronLeft,ChevronRight,AlertCircle,Loader2,LockKeyhole,ShieldCheck,Power,Settings,MessageSquare} from 'lucide-react';
import {api,nativeSave,setToken,uploadFiles} from './api';
import {Dialog,Empty,Field} from './ui';
import {BrandLogo} from './BrandLogo';
import {Reader} from './Reader';
import {SourceReader,type SourceDraft} from './SourceReader';
import {Notifications,type Notice} from './Notifications';
import {importDropFiles} from './fileDrop';
import {importProblem} from './importPolicy';
import {useCloseWarning} from './useCloseWarning';
import {Organize} from './Organize';
import {Editor,type EditorHandle,type EditorTool} from './Editor';
import {Inspector} from './Inspector';
import {TemplateControls} from './Templates';
import {Tools} from './Tools';
import {FeedbackPanel,FeedbackSettings,type FeedbackConfig} from './Feedback';
import {applies,label,type Artifact,type Card,type DataSheet,type Doc,type Mode,type Profile,type StudioObject} from './types';

const modes:{name:Mode;icon:typeof BookOpen}[]=[{name:'Read',icon:BookOpen},{name:'Organize',icon:Layers},{name:'Edit / Fill',icon:Pencil},{name:'Tools',icon:Wrench}];
type History={past:StudioObject[][];present:StudioObject[];future:StudioObject[][]};
const emptyHistory=():History=>({past:[],present:[],future:[]});
type ImportRow={key:string;file:File;phase:string;error?:string;code?:string;encoding?:string;remember?:boolean};
type ImportState={phase:string;current:string;index:number;total:number;completed:number;ready?:number;done:boolean;cancelled?:boolean;documents:Doc[];errors:{index:number;name:string;error:string;code?:string}[];files?:{index:number;name:string;phase:string;error?:string}[]};
type ConfirmationPreferences={confirmQuit:boolean;confirmCloseDocument:boolean;confirmRefreshPdf:boolean};
const defaultConfirmations:ConfirmationPreferences={confirmQuit:true,confirmCloseDocument:true,confirmRefreshPdf:true};
type CancelAction={url:string;label:string;cancelling?:boolean};

export default function App(){
 const [mode,setMode]=useState<Mode>('Read'),[docs,setDocs]=useState<Doc[]>([]),[cards,setCards]=useState<Card[]>([]),[activeId,setActiveId]=useState(''),[page,setPage]=useState(1),[busy,setBusy]=useState(''),[status,setStatus]=useState('Ready · add files to begin'),[connected,setConnected]=useState(false),[dragging,setDragging]=useState(false),[lastArtifact,setLastArtifact]=useState<Artifact|null>(null),[preview,setPreview]=useState<Doc|null>(null),[histories,setHistories]=useState<Record<string,History>>({}),[version,setVersion]=useState(0),[selected,setSelected]=useState<StudioObject|null>(null),[selectedId,setSelectedId]=useState(''),[tool,setTool]=useState<EditorTool>('select'),[defaults,setDefaults]=useState<Partial<StudioObject>>({color:'#20365b',scope:'current',range:'1',strokeWidth:2,fontSize:14,font:'Sarabun',opacity:1}),[profiles,setProfiles]=useState<{id:string;name:string}[]>([]),[profileMeta,setProfileMeta]=useState<Record<string,Profile>>({}),[data,setData]=useState<DataSheet|null>(null),[passwordRetry,setPasswordRetry]=useState<ImportRow|null>(null),[password,setPassword]=useState(''),[closeDoc,setCloseDoc]=useState<Doc|null>(null),[theme,setTheme]=useState(()=>localStorage.getItem('pdfstudio.theme')||'light');
 const input=useRef<HTMLInputElement>(null),imageInput=useRef<HTMLInputElement>(null),editor=useRef<EditorHandle>(null),dragCount=useRef(0);const active=docs.find(d=>d.id===activeId)||docs[0]||null,history=active?(histories[active.id]||emptyHistory()):emptyHistory(),objects=history.present;const editing=['Edit / Fill','Templates'].includes(mode);
 const [readerFocus,setReaderFocus]=useState(false);
 const [feedbackOpen,setFeedbackOpen]=useState(false),[feedbackConfig,setFeedbackConfig]=useState<FeedbackConfig>({url:''});
 const feedbackButton=useRef<HTMLButtonElement>(null),settingsButton=useRef<HTMLButtonElement>(null);
 function closeFeedback(){setFeedbackOpen(false);(feedbackButton.current||settingsButton.current)?.focus({preventScroll:true});}
 const activeRef=useRef(active?.id);activeRef.current=active?.id;
 const [sourceDrafts,setSourceDrafts]=useState<Record<string,SourceDraft>>({}),[preparingId,setPreparingId]=useState(''),[prepareDecision,setPrepareDecision]=useState<{doc:Doc;draft?:SourceDraft}|null>(null),[sourceViewRequest,setSourceViewRequest]=useState<{id:string;token:number}>();
 const prepareRef=useRef<(doc:Doc,draft?:SourceDraft)=>void>(()=>{}),sourceDraftsRef=useRef(sourceDrafts);sourceDraftsRef.current=sourceDrafts;
 const [textDefaults,setTextDefaults]=useState<Record<string,string>>(()=>{try{return JSON.parse(localStorage.getItem('pdfstudio.textDefaults')||'{}');}catch{return {};}});
 const [preferences,setPreferences]=useState(defaultConfirmations),[settingsOpen,setSettingsOpen]=useState(false),[preferenceSaving,setPreferenceSaving]=useState(false),[rememberQuit,setRememberQuit]=useState(false),[rememberClose,setRememberClose]=useState(false),[rememberRefresh,setRememberRefresh]=useState(false),[quitPending,setQuitPending]=useState(false),[exitInProgress,setExitInProgress]=useState(false);
 const preferencesRef=useRef(preferences),quitRequest=useRef<()=>void>(()=>{});preferencesRef.current=preferences;
 const [importCancel,setImportCancel]=useState<CancelAction|null>(null),[sourceCancel,setSourceCancel]=useState<CancelAction|null>(null);
 const cancelledJobs=useRef(new Set<string>());
 function dirtyDocument(id:string){return !!histories[id]?.present.length||!!sourceDrafts[id];}
 function changeSourceDraft(id:string,draft:SourceDraft|undefined){setSourceDrafts(items=>{const next={...items};if(draft)next[id]=draft;else delete next[id];return next;});}
 const [maxFiles,setMaxFiles]=useState(100),[importProgress,setImportProgress]=useState<{title:string;value:number|null;max:number;detail:string}|null>(null),[elapsed,setElapsed]=useState(0),[importRows,setImportRows]=useState<ImportRow[]>([]),[notices,setNotices]=useState<Notice[]>([]),[saving,setSaving]=useState(false);
 const docsRef=useRef(docs),busyRef=useRef(false),importing=useRef(false),savingRef=useRef(false);docsRef.current=docs;
 function notify(notice:Omit<Notice,'id'>&{id?:string}){const id=notice.id||crypto.randomUUID();setNotices(items=>{const previous=items.find(item=>item.id===id||(!notice.id&&item.title===notice.title&&item.message===notice.message));const next={...notice,id:previous?.id||id};return previous?items.map(item=>item===previous?next:item):[...items,next];});}
 function dismissNotice(id:string){setNotices(items=>items.filter(item=>item.id!==id));}
 function setError(message:string){if(message)notify({tone:'error',title:'Couldn’t finish that operation',message});}
 function dismissPassword(){setPasswordRetry(null);setPassword('');}

 const [quitting,setQuitting]=useState(false),[stopped,setStopped]=useState(false),[appVersion,setAppVersion]=useState('');
 useEffect(()=>{
  const requestClose=()=>quitRequest.current();
  Object.assign(window,{__pdfStudioReady:true});
  window.addEventListener('pdfstudio:close-request',requestClose);
  return()=>{Object.assign(window,{__pdfStudioReady:false});window.removeEventListener('pdfstudio:close-request',requestClose);};
 },[]);
 useEffect(()=>{document.documentElement.classList.toggle('dark',theme==='dark');document.documentElement.style.colorScheme=theme;localStorage.setItem('pdfstudio.theme',theme);},[theme]);
 useEffect(()=>{api('/config').then(c=>{setToken(c.token);setFeedbackConfig(c.feedback||{url:''});setPreferences({...defaultConfirmations,...c.preferences});setAppVersion(c.version.replace(/\.(\d+)$/,(_:string,n:string)=>'.'+n.padStart(3,'0')));setProfiles(c.profiles);setMaxFiles(c.maxOpenDocuments||100);addDocuments(c.documents||[]);if(c.launchedWithFiles&&c.documents?.length){setMode('Read');setStatus('Opened '+c.documents[c.documents.length-1].name);}if(c.launchErrors?.length)setError(c.launchErrors.map((item:{name:string;error:string})=>item.name+': '+item.error).join('\n'));setConnected(true);}).catch(e=>setError(e.message));},[]);
 useCloseWarning(preferences.confirmQuit&&!exitInProgress&&!stopped&&(docs.length>0||importRows.length>0||!!importProgress||saving||!!lastArtifact||!!busy||Object.keys(sourceDrafts).length>0||Object.values(histories).some(h=>h.present.length>0)));
 async function updatePreferences(patch:Partial<ConfirmationPreferences>){setPreferenceSaving(true);try{const saved=await api<ConfirmationPreferences>('/preferences',patch);preferencesRef.current={...preferencesRef.current,...patch,...saved};setPreferences(preferencesRef.current);}finally{setPreferenceSaving(false);}}
 async function changePreference(patch:Partial<ConfirmationPreferences>){try{await updatePreferences(patch);notify({tone:'success',title:'Reminder preferences saved',duration:6000});}catch(error){setError((error as Error).message);}}
 async function quitApplication(remember=false){if(quitPending)return;setQuitPending(true);try{if(remember)await updatePreferences({confirmQuit:false});setExitInProgress(true);await api('/quit',{});setQuitting(false);setStopped(true);setConnected(false);setStatus('PDF Studio stopped');}catch(error){setExitInProgress(false);setError((error as Error).message);}finally{setQuitPending(false);}}
 function requestQuit(){if(preferencesRef.current.confirmQuit){setRememberQuit(false);setQuitting(true);}else void quitApplication();}
 quitRequest.current=requestQuit;
 async function cancelCurrentOperation(){const target=busy?sourceCancel:importCancel;if(!target||target.cancelling)return;const setTarget=busy?setSourceCancel:setImportCancel;cancelledJobs.current.add(target.url);setTarget(value=>value?.url===target.url?{...value,cancelling:true}:value);try{await api(target.url+'/cancel',{});}catch(error){if(cancelledJobs.current.delete(target.url)){setTarget(value=>value?.url===target.url?{...value,cancelling:false}:value);setError((error as Error).message);}}}
 async function run<T>(message:string,operation:()=>Promise<T>,noticeId='operation-'+crypto.randomUUID()):Promise<T|undefined>{
  if(busyRef.current){notify({tone:'info',title:'An operation is already running',message:'You can keep reading while it finishes.',duration:6000});return undefined;}
  busyRef.current=true;setBusy(message);
  try{const result=await operation();dismissNotice(noticeId);return result;}catch(e){notify({id:noticeId,tone:'error',title:'Couldn’t finish that operation',message:(e as Error).message||'The operation could not finish.',action:{label:'Retry',onClick:()=>{void run(message,operation,noticeId);}}});return undefined;}finally{busyRef.current=false;setBusy('');}
 }
 function addDocuments(incoming:Doc[],activate=false){
  if(!incoming.length)return;
  const existing=new Set(docsRef.current.map(d=>d.id)),added=incoming.filter(d=>!existing.has(d.id));
  const wasEmpty=!docsRef.current.length;
  docsRef.current=[...docsRef.current,...added];setDocs(docsRef.current);if(activate||wasEmpty){setActiveId(incoming[0].id);setPage(1);}
  setCards(prev=>{const next=[...prev];for(const doc of added){let n=next.length;while(next.some(c=>c.label===label(n)))n++;next.push({key:crypto.randomUUID(),id:doc.id,label:label(n),pages:doc.pages.map(p=>p.number),rotations:{},memo:''});}return next;});
 }
 function addDocument(doc:Doc){addDocuments([doc],true);}
 async function importFiles(files:File[],pass='',textOptions:{forceText?:boolean;encoding?:string}={}):Promise<Doc[]>{
  if(!files.length)return [];
  const problem=importProblem(docsRef.current.length,files.length,maxFiles,importing.current);
  if(problem){setError(problem);return [];}
  const batch=crypto.randomUUID(),rows=files.map((file,index)=>({key:batch+'-'+index,file,phase:'uploading'}));
  setImportRows(items=>[...items,...rows]);
  importing.current=true;const started=Date.now();setElapsed(0);const timer=window.setInterval(()=>setElapsed(Math.floor((Date.now()-started)/1000)),1000);
  const opened:Doc[]=[];let jobId='',after=0;
  try{
   setImportProgress({title:'Adding files',value:0,max:100,detail:'Transferring to the local app — 0%'});
   const job=await uploadFiles(files,pass,percent=>setImportProgress({title:'Adding files',value:percent,max:100,detail:`Transferring to the local app — ${percent}%`}),{...textOptions,textDefaults});jobId=job.id;setImportCancel({url:'/import-jobs/'+job.id,label:files.length===1?'Cancel conversion':'Cancel remaining'});
   let state:ImportState;
   do{state=await api<ImportState>('/import-jobs/'+job.id+'?after='+after);
    addDocuments(state.documents);opened.push(...state.documents);after=state.ready??after+state.documents.length;
    setImportRows(items=>items.flatMap(row=>{
     const index=rows.findIndex(item=>item.key===row.key);if(index<0)return [row];
     const fileState=state.files?.find(file=>file.index===index),error=state.errors.find(error=>error.index===index);
     if(fileState?.phase==='ready'||fileState?.phase==='cancelled'||(state.done&&!error))return [];
     return [{...row,phase:error?'error':fileState?.phase||(index+1===state.index?state.phase:'queued'),error:error?.error,code:error?.code}];
    }));
    setImportProgress({title:`${state.completed} of ${state.total} files processed`,value:state.completed,max:state.total,detail:state.phase==='converting'?`Preparing preview: ${state.current}`:state.current||'Preparing previews on this device'});
    if(!state.done)await new Promise(resolve=>setTimeout(resolve,400));
   }while(!state.done);
   const notes=opened.flatMap(doc=>(doc.warnings||[]).map(note=>doc.name+': '+note));
   const title=`${state.cancelled?'Import cancelled · ':''}${opened.length} file${opened.length===1?'':'s'} ready${state.errors.length?` · ${state.errors.length} need attention`:''}`;
   setStatus(title);
   notify({id:'import-'+batch,tone:state.errors.length||notes.length?'warning':'success',title,
    message:state.errors.length?'Retry, unlock, or open affected files as text in the file list.':state.cancelled?'Unfinished files were skipped. Original files are preserved.':notes.length?'Some files have preview notes.':undefined,
    details:[...state.errors.map(item=>item.name+': '+item.error),...notes].join('\n')||undefined,
    action:opened.length===1&&opened[0].pages.length&&opened[0].kind!=='pdf'?{label:'Save as PDF…',onClick:()=>saveDocument(opened[0])}:undefined});
   const textFiles=opened.filter(doc=>doc.sourceKind==='text');
   if(textFiles.length)notify({tone:'info',duration:6000,title:textFiles.length===1?'Opened as text':`${textFiles.length} files opened as text`,message:textFiles.length===1?textFiles[0].name:undefined,details:textFiles.length>1?textFiles.map(doc=>doc.name).join('\n'):undefined,action:{label:'Change view',onClick:()=>{selectDocument(textFiles[0]);setMode('Read');setSourceViewRequest({id:textFiles[0].id,token:Date.now()});}}});
   return opened;
  }catch(e){
   // Never re-upload blindly after losing a progress response: the job may have succeeded.
   setImportRows(items=>items.map(row=>rows.some(item=>item.key===row.key)?{...row,phase:'error',error:jobId?'Status unavailable. Refresh the file list before trying again.':(e as Error).message}:row));
   notify({tone:'error',title:'Couldn’t finish adding files',message:(e as Error).message,action:{label:jobId?'Refresh file list':'Retry',onClick:()=>{
    if(jobId)void run('Refreshing files…',async()=>{const config=await api('/config');addDocuments(config.documents||[]);setImportRows(items=>items.filter(row=>!rows.some(item=>item.key===row.key)));});
    else{setImportRows(items=>items.filter(row=>!rows.some(item=>item.key===row.key)));void importFiles(files,pass,textOptions);}
   }}});return opened;
  }finally{importing.current=false;setImportProgress(null);setImportCancel(null);if(jobId)cancelledJobs.current.delete('/import-jobs/'+jobId);window.clearInterval(timer);}
 }
 function sceneChange(visible:StudioObject[],visibleIds:string[]){if(!active)return;setHistories(prev=>{const h=prev[active.id]||emptyHistory(),ids=new Set(visibleIds),updates=new Map(visible.map(o=>[o.id,o]));const next=h.present.flatMap(o=>updates.has(o.id)?[updates.get(o.id)!]:ids.has(o.id)?[]:[o]);const existing=new Set(h.present.map(o=>o.id));next.push(...visible.filter(o=>!existing.has(o.id)));if(JSON.stringify(next)===JSON.stringify(h.present))return prev;return {...prev,[active.id]:{past:[...h.past,h.present].slice(-60),present:next,future:[]}};});}
 function dropFiles(files:File[]){void importFiles(importDropFiles(files).accepted);}
 function undo(redo=false){if(!active)return;setSelected(null);setSelectedId('');setHistories(prev=>{const h=prev[active.id]||emptyHistory();if(redo){if(!h.future.length)return prev;return {...prev,[active.id]:{past:[...h.past,h.present],present:h.future[0],future:h.future.slice(1)}};}if(!h.past.length)return prev;return {...prev,[active.id]:{past:h.past.slice(0,-1),present:h.past[h.past.length-1],future:[h.present,...h.future]}};});setVersion(v=>v+1);}
 useEffect(()=>{const handler=(e:KeyboardEvent)=>{const target=e.target as HTMLElement;if(document.querySelector('dialog[open]')||target.closest?.('input,textarea,select,[contenteditable]:not([contenteditable="false"])'))return;if(editing&&(e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();undo(e.shiftKey);}if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='o'){e.preventDefault();input.current?.click();}};window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler);},[active?.id,editing]);
 function saveDocument(doc:Doc){if(sourceDraftsRef.current[doc.id]){setError('Update the PDF preview before saving pending text or layout changes.');return;}void run('Preparing PDF for saving…',async()=>saveResult(await api('/export/original',{id:doc.id})));}
 async function requestSave(a:Artifact){
  if(savingRef.current){notify({id:'save-'+a.id,tone:'info',title:'Your result is ready',message:a.name,action:{label:'Save As…',onClick:()=>{void requestSave(a);}},download:a});return;}
  savingRef.current=true;setSaving(true);setLastArtifact(a);
  const id='save-'+a.id;
  try{
   const result=await nativeSave(a);
   if(result.cancelled)notify({id,tone:'info',title:'Save canceled',message:a.name+' is still available.',action:{label:'Save As…',onClick:()=>{void requestSave(a);}},download:a});
   else{setStatus('Saved '+result.name);notify({id,tone:'success',title:'PDF Studio saved your file',message:result.name});}
  }catch(e){notify({id,tone:'error',title:'Couldn’t save your file',message:(e as Error).message,action:{label:'Retry Save As…',onClick:()=>{void requestSave(a);}},download:a});}
  finally{savingRef.current=false;setSaving(false);}
 }
 function saveResult(a:Artifact){setLastArtifact(a);setStatus('Result ready · '+a.name);void requestSave(a);}
 function refreshProfiles(){void api('/profiles').then(r=>setProfiles(r.profiles)).catch(e=>setError(e.message));}
 function loadProfile(profile:Profile,doc:Doc){if(!docs.some(d=>d.id===doc.id))addDocument(doc);else setActiveId(doc.id);setProfileMeta(p=>({...p,[doc.id]:profile}));setHistories(p=>({...p,[doc.id]:{...emptyHistory(),present:profile.objects}}));setSelected(null);setSelectedId('');setVersion(v=>v+1);setMode('Templates');setPage(1);setStatus('Profile opened · review bindings before generating');}
 async function exportEdits(previewOnly=false){if(!active)return;await run(previewOnly?'Rendering edited PDF preview…':'Applying changes to a new PDF…',async()=>{const result=await api<Artifact>('/export/edit',{id:active.id,objects});if(previewOnly)setPreview({...active,id:result.id,url:result.url,name:'Preview - '+active.name});else saveResult(result);});}
 function switchMode(next:Mode){setMode(next);setSelected(null);setSelectedId('');setTool('select');}
 function chooseEditorTool(next:EditorTool){setTool(next);if(['pencil','rect','redact','cover'].includes(next)){setSelected(null);setSelectedId('');}if(next==='redact')setDefaults(value=>({...value,color:'#000000',opacity:1}));}
 function removeImportRow(key:string){
  setImportRows(items=>items.filter(row=>row.key!==key));
  const batch=key.slice(0,key.lastIndexOf('-'));
  if(!importRows.some(row=>row.key!==key&&row.key.startsWith(batch+'-')))dismissNotice('import-'+batch);
 }
 function retryImport(row:ImportRow,pass=''){
  const problem=importProblem(docsRef.current.length,1,maxFiles,importing.current);
  if(problem){setError(problem);return;}
  if(row.remember&&row.code==='open-as-text'){const ext=row.file.name.match(/\.[^.]+$/)?.[0].toLowerCase();if(ext){const next={...textDefaults,[ext]:row.encoding||'cp1252'};setTextDefaults(next);localStorage.setItem('pdfstudio.textDefaults',JSON.stringify(next));}}
  removeImportRow(row.key);void importFiles([row.file],pass,row.code==='open-as-text'?{forceText:true,encoding:row.encoding||'cp1252'}:{});
 }
 function requestCloseDocument(doc:Doc){if(dirtyDocument(doc.id)&&preferencesRef.current.confirmCloseDocument){setRememberClose(false);setCloseDoc(doc);}else void closeDocument(doc);}
 async function closeDocument(doc:Doc,remember=false){
  await run('Closing document…',async()=>{
   if(remember)await updatePreferences({confirmCloseDocument:false});
   await api('/documents/'+doc.id,undefined,'DELETE');
   docsRef.current=docsRef.current.filter(item=>item.id!==doc.id);setDocs(docsRef.current);
   setCards(items=>items.filter(card=>card.id!==doc.id));
   setHistories(items=>{const copy={...items};delete copy[doc.id];return copy;});
   if(activeRef.current===doc.id){setActiveId(docsRef.current[0]?.id||'');setPage(1);setSelected(null);setSelectedId('');}
   changeSourceDraft(doc.id,undefined);setCloseDoc(null);setStatus('Closed '+doc.name);
  });
 }
 function prepareDocument(doc:Doc,draft?:SourceDraft,confirmed=false){
  if(preparingId||busyRef.current){notify({tone:'info',title:'A preview is already preparing',message:'You can continue reading while it finishes.',duration:6000});return;}
  const arranged=cards.some(card=>card.id===doc.id&&(card.pages.length!==doc.pages.length||card.pages.some((page,i)=>page!==i+1)||Object.keys(card.rotations).length>0));
  if(!confirmed&&preferencesRef.current.confirmRefreshPdf&&(histories[doc.id]?.present.length||arranged)){setRememberRefresh(false);setPrepareDecision({doc,draft});return;}
  setPreparingId(doc.id);
  void run('Preparing PDF preview…',async()=>{
   setPreparingId(doc.id);
   let jobUrl='';
   try{
    const job=await api('/documents/'+doc.id+'/prepare',{content:doc.sourceKind==='html'?undefined:draft?.content,options:draft?.options});
    jobUrl='/source-jobs/'+job.id;setSourceCancel({url:jobUrl,label:'Cancel preparation'});
    let state:{done:boolean;error?:string;document:Doc;cancelled?:boolean};
    do{state=await api('/source-jobs/'+job.id);if(!state.done)await new Promise(resolve=>setTimeout(resolve,400));}while(!state.done);
    if(state.cancelled||cancelledJobs.current.has(jobUrl)){notify({tone:'info',title:'PDF preparation cancelled',message:'Your text draft and previous preview are preserved.',duration:6000});return;}
    if(state.error)throw Error(state.error);
    setSourceCancel(null);
    const prepared=await api<Doc>('/source-jobs/'+job.id+'/commit',{});
    docsRef.current=docsRef.current.map(item=>item.id===doc.id?prepared:item);setDocs(docsRef.current);
    setCards(items=>items.map(card=>card.id===doc.id?{...card,key:crypto.randomUUID(),pages:prepared.pages.map(page=>page.number),rotations:{}}:card));
    setHistories(items=>{const next={...items};delete next[doc.id];return next;});changeSourceDraft(doc.id,undefined);
    if(activeRef.current===doc.id){setPage(1);setSelected(null);setSelectedId('');}
    dismissNotice('prepare-'+doc.id);notify({tone:'success',title:'PDF preview ready',message:prepared.name});
   }catch(error){notify({id:'prepare-'+doc.id,tone:'error',title:'Couldn’t prepare PDF preview',message:(error as Error).message,action:{label:'Retry',onClick:()=>{const current=docsRef.current.find(item=>item.id===doc.id);if(current)prepareRef.current(current,sourceDraftsRef.current[doc.id]);}}});}
   finally{setPreparingId('');setSourceCancel(null);if(jobUrl)cancelledJobs.current.delete(jobUrl);}
  });
 }
 prepareRef.current=prepareDocument;
 async function confirmRefresh(){if(!prepareDecision)return;try{if(rememberRefresh)await updatePreferences({confirmRefreshPdf:false});const request=prepareDecision;setPrepareDecision(null);prepareDocument(request.doc,request.draft,true);}catch(error){setError((error as Error).message);}}
 const cancelAction=saving?null:busy?sourceCancel:importProgress?importCancel:null;
 const selectDocument=(doc:Doc)=>{setActiveId(doc.id);setPage(1);setSelected(null);setSelectedId('');};
 return <div className={'studio'+(readerFocus?' reading-focus':'')+(feedbackOpen?' feedback-open':'')} onDragEnter={e=>{if(e.dataTransfer.types.includes('Files')){e.preventDefault();dragCount.current++;setDragging(true);}}} onDragLeave={e=>{if(e.dataTransfer.types.includes('Files')){dragCount.current=Math.max(0,dragCount.current-1);if(!dragCount.current)setDragging(false);}}} onDragOver={e=>{if(e.dataTransfer.types.includes('Files'))e.preventDefault();}} onDrop={e=>{if(e.dataTransfer.files.length){e.preventDefault();dragCount.current=0;setDragging(false);dropFiles(Array.from(e.dataTransfer.files));}}}>
 <header className="app-header" inert={readerFocus}><div className="brand"><BrandLogo className="brand-mark"/><div><h1>PDF Studio</h1></div></div><div className="header-actions"><button className="icon ghost" aria-label="Quit PDF Studio" disabled={!connected||quitPending} onClick={requestQuit}><Power size={18}/></button>{active?.pages.length&&mode==='Read'?<button disabled={saving||preparingId===active.id||!!sourceDrafts[active.id]} onClick={()=>saveDocument(active)}><Download size={16}/>Save as PDF…</button>:null}{lastArtifact&&<button disabled={saving} onClick={()=>void requestSave(lastArtifact)}><Download size={16}/>Save last result…</button>}{docs.length>0&&<button ref={feedbackButton} className="feedback-toggle ghost" aria-label="Feedback" aria-expanded={feedbackOpen} aria-controls="pdfstudio-feedback" disabled={!connected} onClick={()=>feedbackOpen?closeFeedback():setFeedbackOpen(true)}><MessageSquare size={17} aria-hidden="true"/><span>Feedback</span></button>}<button ref={settingsButton} className="icon ghost" aria-label="Settings" disabled={!connected} onClick={()=>setSettingsOpen(true)}><Settings size={18} aria-hidden="true"/></button><button className="icon ghost" aria-label={theme==='light'?'Use dark appearance':'Use light appearance'} onClick={()=>setTheme(t=>t==='light'?'dark':'light')}>{theme==='light'?<Moon size={19}/>:<Sun size={19}/>}</button><button className="primary" disabled={!connected} onClick={()=>input.current?.click()}><Plus size={17}/>Add files</button></div></header>
 <nav inert={readerFocus} className="main-nav" aria-label="PDF workflows">{modes.map(item=><button key={item.name} aria-current={mode===item.name?'page':undefined} disabled={item.name==='Edit / Fill'&&(!active?.pages.length||preparingId===active.id||!!sourceDrafts[active.id])} onClick={()=>switchMode(item.name)}><item.icon size={17}/>{item.name}</button>)}</nav>
 <div className="application-body"><aside className="sources" inert={readerFocus}><div className="sources-heading"><h2>Files <span>{docs.length}/{maxFiles}</span></h2></div><div className="source-list">{docs.map(doc=><div className={'source '+(active?.id===doc.id?'active':'')} key={doc.id}><button className="source-select" onClick={()=>selectDocument(doc)} aria-pressed={active?.id===doc.id}><Files size={17}/><span>{doc.name}<small>{doc.pages.length?`${doc.pages.length} PDF pages`:doc.sourceKind==='html'?'HTML · read original':'Text · read original'} · {(doc.size/1024).toLocaleString(undefined,{maximumFractionDigits:0})} KB</small></span></button><button className="icon ghost close-file" aria-label={`Close ${doc.name}`} onClick={()=>requestCloseDocument(doc)}><X size={14}/></button></div>)}{importRows.map(row=>{const locked=/password/i.test(row.error||'')&&/\.pdf$/i.test(row.file.name),asText=row.code==='open-as-text',failed=row.phase==='error';return <div className={'source pending-source '+(failed?'source-failed':'')} key={row.key}>
  <div className="pending-file-heading">{failed?(locked?<LockKeyhole size={17} aria-hidden="true"/>:<AlertCircle size={17} aria-hidden="true"/>):<Loader2 size={17} className="spin" aria-hidden="true"/>}<span>{row.file.name}<small>{asText?'Text format needs a choice':locked?'Password required':failed?'Couldn’t open':row.phase==='converting'?'Preparing preview…':row.phase==='opening'?'Opening…':row.phase==='uploading'?'Adding…':'Queued'}</small></span></div>
  {asText&&<div className="text-fallback-options"><label>Text encoding<select aria-label={'Text encoding for '+row.file.name} value={row.encoding||'cp1252'} onChange={e=>setImportRows(items=>items.map(item=>item.key===row.key?{...item,encoding:e.target.value}:item))}><option value="cp1252">Western text</option><option value="cp874">Thai (Windows)</option><option value="utf-8">UTF-8</option><option value="utf-16">UTF-16</option></select></label><label className="check"><input type="checkbox" checked={!!row.remember} onChange={e=>setImportRows(items=>items.map(item=>item.key===row.key?{...item,remember:e.target.checked}:item))}/>Remember this extension</label></div>}
  {failed&&<div className="pending-file-actions">{!row.error?.startsWith('Status unavailable')&&<button className="link" disabled={!!importProgress} onClick={()=>locked?setPasswordRetry(row):retryImport(row)}>{asText?'Open as text':locked?'Enter password':'Retry'}</button>}<button className="icon ghost" aria-label={'Dismiss '+row.file.name} onClick={()=>removeImportRow(row.key)}><X size={14} aria-hidden="true"/></button></div>}
 </div>;})}</div></aside>
 <main className="workspace" aria-label={mode+' workspace'}>{mode==='Tools'?<Tools doc={active} docs={docs.map(doc=>({...doc,draftPending:!!sourceDrafts[doc.id]}))} onPrepare={doc=>prepareDocument(doc,sourceDrafts[doc.id])} onRead={doc=>{selectDocument(doc);setMode('Read');}} onImport={files=>importFiles(files)} onSave={saveResult} run={run}/>:!active?<Empty title="Open your documents"><p>Drop PDFs, images, Office documents, HTML, Markdown or text files here.</p><p>Use <strong>Add files</strong> at the top right.</p><p className="muted">Your files are processed on this device.</p></Empty>:mode==='Read'?(active.sourceKind?<SourceReader key={active.id} doc={active} draft={sourceDrafts[active.id]} onDraft={draft=>changeSourceDraft(active.id,draft)} onPrepare={draft=>prepareDocument(active,draft)} preparing={preparingId===active.id} onError={setError} onFocusChange={setReaderFocus} requestedView={sourceViewRequest}/>:<Reader key={active.id} doc={active} focusAvailable onFocusChange={setReaderFocus}/>):mode==='Organize'?<Organize docs={docs.map(doc=>({...doc,draftPending:!!sourceDrafts[doc.id]}))} preparingId={preparingId} onPrepare={doc=>prepareDocument(doc,sourceDrafts[doc.id])} onRead={doc=>{selectDocument(doc);setMode('Read');}} cards={cards} setCards={setCards} active={active} onSave={saveResult} run={run}/>:<div className="editing-workspace"><div className="editing-toolbar"><div className="page-nav"><button className="icon" disabled={page<=1} aria-label="Previous editor page" onClick={()=>{setPage(n=>n-1);setSelected(null);setSelectedId('');}}><ChevronLeft size={17}/></button><label>Page <input type="number" min={1} max={active.pages.length} value={page} onChange={e=>{setPage(Math.min(active.pages.length,Math.max(1,+e.target.value||1)));setSelected(null);}}/> / {active.pages.length}</label><button className="icon" aria-label="Next editor page" disabled={page>=active.pages.length} onClick={()=>{setPage(n=>n+1);setSelected(null);setSelectedId('');}}><ChevronRight size={17}/></button></div><div className="actions"><button className="icon" aria-label="Undo edit" disabled={!history.past.length} onClick={()=>undo()}><Undo2 size={17}/></button><button className="icon" aria-label="Redo edit" disabled={!history.future.length} onClick={()=>undo(true)}><Redo2 size={17}/></button><button onClick={()=>exportEdits(true)}><Eye size={16}/>Preview</button>{mode!=='Templates'&&<button className="primary" onClick={()=>exportEdits(false)}><Download size={16}/>Save a copy</button>}</div></div><div className="mode-grid editor-mode"><section className="editor-panel"><Editor key={`${active.id}-${page}-${version}`} ref={editor} doc={active} page={page} objects={objects} tool={tool} defaults={defaults} selectedId={selectedId} onChange={sceneChange} onSelect={setSelected} onTool={chooseEditorTool} onColor={color=>{setDefaults(d=>({...d,color}));editor.current?.update({color});}} onError={setError} template={mode==='Templates'}/></section><aside className="inspector">{mode==='Templates'&&<><TemplateControls doc={active} objects={objects} profiles={profiles} profile={profileMeta[active.id]||{name:active.name.replace(/\.pdf$/i,'')+' profile',objects}} onProfile={profile=>setProfileMeta(p=>({...p,[active.id]:profile}))} onLoad={loadProfile} onRefresh={refreshProfiles} onData={setData} data={data} run={run} onSave={saveResult}/><hr/></>}<Inspector selected={selected} defaults={defaults} onDefaults={patch=>setDefaults(v=>({...v,...patch}))} onUpdate={patch=>editor.current?.update(patch)} template={mode==='Templates'} columns={data?.columns} tool={tool}/>{objects.length>0&&<><hr/><h3>Objects · {objects.length}</h3><div className="object-list">{objects.map(o=><button key={o.id} className={selected?.id===o.id?'selected':''} onClick={()=>{setPage(o.page);setSelectedId(o.id);}}><span>{o.name}</span><small>p{o.page} · {o.scope==='range'?o.range:o.scope}</small></button>)}</div></>}</aside></div></div>}</main><FeedbackPanel open={feedbackOpen&&!readerFocus} config={feedbackConfig} onClose={closeFeedback} onConfigure={()=>setSettingsOpen(true)}/></div>
 <footer className="app-footer" inert={readerFocus}><span>{saving?'Choose a destination in Save As…':busy||importProgress?.title||status}</span><span className="app-version" title="PDF Studio version">PDF Studio{appVersion&&` · v${appVersion}`}</span></footer>
 <input ref={input} type="file" multiple hidden onChange={e=>{void importFiles(Array.from(e.target.files||[]));e.target.value='';}}/><input id="image-input" ref={imageInput} type="file" accept=".png,.jpg,.jpeg" hidden onChange={e=>{const file=e.target.files?.[0];if(file)void run('Adding image…',async()=>{const target=editor.current;const form=new FormData();form.append('file',file);const asset=await api('/assets',form);if(editor.current!==target)throw Error('Select the destination page and add the image again.');await target?.addImage(asset,!!(selected?.type==='image'&&!selected.assetId));});e.target.value='';}}/>
 {dragging&&<div className="drop-overlay"><Files size={44}/><strong>Drop files to add them</strong><span>PDF, images, Office, HTML, Markdown and readable text</span></div>}
 {stopped&&<div className="stopped-overlay" role="status"><ShieldCheck size={32}/><h2>PDF Studio has stopped</h2><p>You can close this tab. Launch PDF Studio again when you need it.</p></div>}
 {quitting&&<Dialog title="Quit PDF Studio" onClose={()=>{if(!quitPending)setQuitting(false);}}><p>Save any results you want to keep before quitting. Temporary documents and unsaved edits will be cleared.</p><label className="check remember-choice"><input type="checkbox" checked={rememberQuit} disabled={quitPending} onChange={e=>setRememberQuit(e.target.checked)}/><span>Don’t show this quit reminder again<small>Future exits will clear temporary documents and unsaved edits without asking. You can restore this reminder in Settings.</small></span></label><div className="dialog-actions"><button disabled={quitPending} onClick={()=>setQuitting(false)}>Keep working</button><button className="primary" disabled={!connected||quitPending} onClick={()=>void quitApplication(rememberQuit)}>{quitPending?'Quitting…':'Quit PDF Studio'}</button></div></Dialog>}
 {settingsOpen&&<Dialog title="Settings" onClose={()=>{if(!preferenceSaving)setSettingsOpen(false);}}><section className="feedback-settings-entry"><h3>Feedback</h3><p>Share an idea, report a problem or tell us what works well.</p><button onClick={()=>{setSettingsOpen(false);setFeedbackOpen(true);}}><MessageSquare size={16} aria-hidden="true"/>Share feedback</button><FeedbackSettings config={feedbackConfig} onChange={setFeedbackConfig}/></section><hr/><h3>Confirmation reminders</h3><p>Choose when PDF Studio asks before clearing temporary work. These preferences stay on this device.</p><fieldset className="confirmation-settings" disabled={preferenceSaving}>{([{key:'confirmQuit',label:'Ask before quitting',hint:'When off, exiting clears temporary documents and unsaved edits immediately.'},{key:'confirmCloseDocument',label:'Ask before discarding document edits',hint:'When off, Close discards unsaved PDF edits and text drafts immediately.'},{key:'confirmRefreshPdf',label:'Ask before resetting PDF edits during refresh',hint:'When off, refreshing resets annotations, page selections and rotations immediately.'}] as const).map(item=><label className="check remember-choice" key={item.key}><input type="checkbox" checked={preferences[item.key]} onChange={e=>void changePreference({[item.key]:e.target.checked})}/><span>{item.label}<small>{item.hint}</small></span></label>)}</fieldset><div className="dialog-actions"><button disabled={preferenceSaving} onClick={()=>void changePreference(defaultConfirmations)}>Restore all reminders</button><button className="primary" disabled={preferenceSaving} onClick={()=>setSettingsOpen(false)}>Done</button></div></Dialog>}
 <Notifications notices={notices} onDismiss={dismissNotice} progress={saving?{title:'Choose a destination in Save As…'}:busy?{title:cancelAction?.cancelling?'Cancelling…':busy}:importProgress?{...importProgress,title:cancelAction?.cancelling?'Cancelling…':importProgress.title,elapsed}:null} cancel={cancelAction?{label:cancelAction.cancelling?'Cancelling…':cancelAction.label,disabled:!!cancelAction.cancelling,onClick:()=>void cancelCurrentOperation()}:undefined}/>
 {preview&&<Dialog title="Export preview" wide onClose={()=>setPreview(null)}><Reader doc={preview}/></Dialog>}
 {passwordRetry&&<Dialog title="Password-protected PDF" onClose={()=>{dismissPassword();}}><p>Enter the password for {passwordRetry.file.name}.</p><Field label="PDF password"><input type="password" autoComplete="off" value={password} onChange={e=>setPassword(e.target.value)}/></Field><div className="dialog-actions"><button onClick={()=>{dismissPassword();}}>Cancel</button><button className="primary" onClick={()=>{const row=passwordRetry,pass=password;dismissPassword();retryImport(row,pass);}}>Open PDF</button></div></Dialog>}
 {prepareDecision&&<Dialog title="Refresh PDF preview" onClose={()=>{if(!preferenceSaving)setPrepareDecision(null);}}><p>Refreshing {prepareDecision.doc.name} will reset its PDF annotations, page selections and rotations. The text draft and original file are preserved.</p><label className="check remember-choice"><input type="checkbox" disabled={preferenceSaving} checked={rememberRefresh} onChange={e=>setRememberRefresh(e.target.checked)}/><span>Don’t ask again before resetting PDF edits<small>This applies only to PDF preview refreshes. Restore the reminder in Settings.</small></span></label><div className="dialog-actions"><button disabled={preferenceSaving} onClick={()=>setPrepareDecision(null)}>Keep current preview</button><button className="primary" disabled={preferenceSaving} onClick={()=>void confirmRefresh()}>Refresh preview</button></div></Dialog>}
 {closeDoc&&<Dialog title="Close document" onClose={()=>{if(!preferenceSaving)setCloseDoc(null);}}><p>Close {closeDoc.name}? Unsaved edits in this workspace will be discarded. Saved profiles and source files are preserved.</p><label className="check remember-choice"><input type="checkbox" disabled={preferenceSaving} checked={rememberClose} onChange={e=>setRememberClose(e.target.checked)}/><span>Don’t ask again before discarding document edits<small>This applies only to closing documents. Restore the reminder in Settings.</small></span></label><div className="dialog-actions"><button disabled={preferenceSaving} onClick={()=>setCloseDoc(null)}>Keep open</button><button className="primary" disabled={preferenceSaving} onClick={()=>void closeDocument(closeDoc,rememberClose)}>Discard edits &amp; close</button></div></Dialog>}
 </div>;
}
