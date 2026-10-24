import {useEffect,useRef,useState} from 'react';
import {TextLayer,type PDFDocumentProxy,type PDFPageProxy} from 'pdfjs-dist';
import type {Paragraph} from './speech';

type Frame = {page: PDFPageProxy; viewport: ReturnType<PDFPageProxy['getViewport']>};
type Props = {pdf:PDFDocumentProxy;number:number;width:number;rotation?:number;text?:boolean;query?:string;quality?:string;aspect?:number;deferRender?:boolean;highlight?:Paragraph|null;onReady?:(canvas:HTMLCanvasElement,cssWidth:number,cssHeight:number)=>void};

export function PdfPage({pdf,number,width,rotation=0,text=true,query='',quality='Auto',aspect,deferRender=false,highlight,onReady}:Props) {
 const canvas=useRef<HTMLCanvasElement>(null),layer=useRef<HTMLDivElement>(null);
 const [settledWidth,setSettledWidth]=useState(width),[frame,setFrame]=useState<Frame|null>(null),[error,setError]=useState('');
 const renderWidth=deferRender?settledWidth:width;
 const textDivs=useRef<HTMLElement[]>([]),scrolledGroup=useRef(''),[textRevision,setTextRevision]=useState(0);
 useEffect(()=>{
  if(!deferRender)return;
  const timer=window.setTimeout(()=>setSettledWidth(width),160);
  return()=>window.clearTimeout(timer);
 },[width,deferRender]);
 useEffect(()=>{
  let canceled=false,render:ReturnType<PDFPageProxy['render']>|undefined;
  const buffer=document.createElement('canvas');
  setError('');
  (async()=>{
   const page=await pdf.getPage(number);
   if(canceled)return;
   const base=page.getViewport({scale:1,rotation:(page.rotate+rotation)%360});
   const viewport=page.getViewport({scale:renderWidth/base.width,rotation:(page.rotate+rotation)%360});
   let ratio=quality==='Standard'?1:quality==='Sharp'?2:Math.min(devicePixelRatio||1,2);
   // Bound both the visible bitmap and its temporary render buffer.
   ratio=Math.min(ratio,Math.sqrt(8000000/(viewport.width*viewport.height)));
   buffer.width=Math.max(1,Math.floor(viewport.width*ratio));
   buffer.height=Math.max(1,Math.floor(viewport.height*ratio));
   render=page.render({canvas:buffer,viewport,transform:ratio===1?undefined:[ratio,0,0,ratio,0,0]});
   await render.promise;
   if(canceled||!canvas.current)return;
   const front=canvas.current;
   front.width=buffer.width;front.height=buffer.height;
   front.getContext('2d')!.drawImage(buffer,0,0);
   setFrame({page,viewport});
   onReady?.(front,viewport.width,viewport.height);
  })().catch(e=>{if(!canceled&&e.name!=='RenderingCancelledException')setError(e.message);}).finally(()=>{
   buffer.width=0;buffer.height=0;
  });
  return()=>{canceled=true;render?.cancel();};
 },[pdf,number,renderWidth,rotation,quality]);
 useEffect(()=>{
  if(!text||!frame||!layer.current)return;
  let canceled=false,textLayer:TextLayer|undefined;
  const container=layer.current;
  container.replaceChildren();
  container.style.setProperty('--total-scale-factor',String(frame.viewport.scale));
  container.style.setProperty('--scale-factor',String(frame.viewport.scale));
  (async()=>{
   const content=await frame.page.getTextContent();
   if(canceled)return;
   textLayer=new TextLayer({textContentSource:content,container,viewport:frame.viewport});
   await textLayer.render();
   if(!canceled){textDivs.current=textLayer.textDivs;setTextRevision(value=>value+1);}
  })().catch(e=>{if(!canceled&&e.name!=='RenderingCancelledException')setError(e.message);});
  return()=>{canceled=true;textLayer?.cancel();textDivs.current=[];};
 },[frame,text]);
 useEffect(()=>{
  const selected=new Set(highlight?.page===number?highlight.items:[]);
  textDivs.current.forEach((span,index)=>{span.classList.toggle('search-hit',!!query&&!!span.textContent?.toLocaleLowerCase().includes(query.toLocaleLowerCase()));span.classList.toggle('spoken-paragraph',selected.has(index));});
  if(!selected.size){scrolledGroup.current='';return;}
  const groupKey=`${highlight!.page}:${highlight!.index}`,first=textDivs.current[highlight!.items[0]];
  if(!first||scrolledGroup.current===groupKey)return;
  const viewport=layer.current?.closest<HTMLElement>('.reader-pages');if(!viewport)return;
  const timer=requestAnimationFrame(()=>{
   const bounds=first.getBoundingClientRect(),area=viewport.getBoundingClientRect();
   if(!bounds.width&&!bounds.height)return;
   scrolledGroup.current=groupKey;
   const reader=viewport.closest('.reader-focus'),inset=reader?.querySelector('.reader-toolbar')?.getBoundingClientRect().height||0;
   if(bounds.top<area.top+inset+16||bounds.bottom>area.bottom-16)viewport.scrollTop+=bounds.top-area.top-inset-32;
   if(bounds.left<area.left||bounds.right>area.right)viewport.scrollLeft+=bounds.left-area.left-24;
  });return()=>cancelAnimationFrame(timer);
 },[textRevision,query,highlight,number]);
 const height=width*(aspect??(frame?frame.viewport.height/frame.viewport.width:1.414));
 // Scale an outer wrapper: PDF.js owns the text layer's rotation transform.
 return <div className="pdf-page" style={{width,height}}><canvas ref={canvas}/>{text&&<div className="pdf-text-scale" style={{position:'absolute',left:0,top:0,width:frame?.viewport.width??width,height:frame?.viewport.height??height,transform:`scale(${frame?width/frame.viewport.width:1})`,transformOrigin:'top left'}}><div ref={layer} className="textLayer"/></div>}<span className="sr-only">Page {number}</span>{error&&<p role="alert" className="page-error">{error}</p>}</div>;
}
