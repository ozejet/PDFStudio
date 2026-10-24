export type Doc = {id:string;name:string;kind:string;size:number;pages:{number:number;width:number;height:number;rotation:number}[];url?:string;fingerprint?:string;pdfReady?:boolean;sourceKind?:string;revision?:number;textFallback?:boolean;warnings?:string[];draftPending?:boolean};
export type Artifact = {id:string;name:string;size:number;url:string};
export type Card = {key:string;id:string;label:string;pages:number[];rotations:Record<string,number>;memo:string};
export type Mode = 'Read'|'Organize'|'Edit / Fill'|'Templates'|'Tools';
export type StudioObject = {
 id:string;type:'text'|'image'|'rect'|'cover'|'redact'|'pencil';name:string;page:number;scope:'current'|'all'|'range';range:string;
 x:number;y:number;w:number;h:number;angle:number;corners?:number[][];color:string;opacity:number;value:string;font:string;fontSize:number;align:string;
 assetId?:string;legacyImageName?:string;digitOffsets?:number[];points?:number[][];strokeWidth?:number;sourceType:'constant'|'excel'|'computed';column:string;computed:string;format:string;digits:number;required:boolean;
};
export type Profile = {id?:string;name:string;schema?:string;coordinates?:string;objects:StudioObject[]};
export type DataSheet = {columns:string[];rows:Record<string,unknown>[];sheets:string[];name:string};
export function label(index:number):string {let s='';for(let n=index+1;n>0;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;}
export function parsePages(text:string,count:number):number[]{
 if(!text.trim()||text.trim()==='all')return Array.from({length:count},(_,i)=>i+1);
 const out:number[]=[];
 for(const part of text.trim().split(/[,\s]+/)){const m=part.match(/^(\d+)(?:-(\d+))?$/);if(!m)throw Error(`Invalid page range: ${part}`);const a=+m[1],b=+(m[2]||m[1]);if(a<1||b<1||a>count||b>count)throw Error(`Use page numbers 1–${count}.`);for(let p=a;;p+=a<=b?1:-1){out.push(p);if(p===b)break;if(out.length>50000)throw Error('The range is too large.');}}
 return out;
}
export function applies(item:StudioObject,page:number,count:number){try{return item.scope==='all'||(item.scope==='current'?item.page===page:parsePages(item.range,count).includes(page));}catch{return item.page===page;}}
export function newObject(type:StudioObject['type'],page:number):StudioObject{return {id:crypto.randomUUID(),type,name:type==='text'?'Text':type==='redact'?'Redaction':type==='rect'||type==='cover'?'Box / cover':type[0].toUpperCase()+type.slice(1),page,scope:'current',range:String(page),x:.12,y:.18,w:.4,h:.08,angle:0,color:type==='redact'?'#000000':'#20365b',opacity:1,value:'Type your text',font:'Sarabun',fontSize:14,align:'left',sourceType:'constant',column:'',computed:'',format:'text',digits:0,required:false,strokeWidth:2};}
