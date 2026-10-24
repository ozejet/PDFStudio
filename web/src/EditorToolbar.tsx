import {MousePointer2,Type,ImagePlus,Pencil,Square,ScanLine,Pipette,Hand} from 'lucide-react';

export type EditorTool='select'|'hand'|'pencil'|'rect'|'redact'|'cover'|'sample';
type Props={tool:EditorTool;onTool:(tool:EditorTool)=>void;onText:()=>void;onImage:()=>void;template?:boolean};

export function EditorToolbar({tool,onTool,onText,onImage,template=false}:Props){
 const choices=[
  {tool:'hand',name:'Hand',icon:Hand},
  {tool:'select',name:'Select',icon:MousePointer2},
  {tool:'pencil',name:'Pencil',icon:Pencil},
  {tool:'rect',name:'Box / cover',icon:Square},
  ...(!template?[{tool:'redact',name:'Redact content',icon:ScanLine}]:[]),
  {tool:'sample',name:'Sample color',icon:Pipette},
 ] as const;
 const choice=(item:typeof choices[number])=>{
  const selected=tool===item.tool||(item.tool==='rect'&&tool==='cover');
  return <button key={item.tool} aria-pressed={selected} className={selected?'selected':''} onClick={()=>onTool(item.tool as EditorTool)}><item.icon size={16} aria-hidden="true"/>{item.name}</button>;
 };
 return <div className="canvas-toolbar" role="group" aria-label="Edit and fill tools">
  {choices.slice(0,2).map(choice)}
  <button onClick={onText}><Type size={16} aria-hidden="true"/>Text</button>
  <button onClick={onImage}><ImagePlus size={16} aria-hidden="true"/>Image / signature</button>
  {choices.slice(2).map(choice)}
 </div>;
}
