import {useEffect,useId,useRef,type ReactNode} from 'react';
import {X} from 'lucide-react';
import {BrandLogo} from './BrandLogo';
export function Field({label,children,hint}:{label:string;children:ReactNode;hint?:string}){return <label className="field"><span>{label}</span>{children}{hint&&<small>{hint}</small>}</label>;}
export function Dialog({title,children,onClose,wide=false}:{title:string;children:ReactNode;onClose:()=>void;wide?:boolean}){const ref=useRef<HTMLDialogElement>(null),id=useId();useEffect(()=>{ref.current?.showModal();return()=>ref.current?.close();},[]);return <dialog ref={ref} className={wide?'dialog wide':'dialog'} aria-labelledby={id} onCancel={e=>{e.preventDefault();onClose();}}><header><h2 id={id}>{title}</h2><button className="icon ghost" onClick={onClose} aria-label="Close dialog"><X size={18}/></button></header>{children}</dialog>;}
export function Empty({title,children}:{title:string;children?:ReactNode}){return <div className="empty"><BrandLogo size={72} className="empty-symbol"/><h2>{title}</h2>{children}</div>;}
