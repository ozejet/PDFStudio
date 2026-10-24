import type {Artifact} from './types';
let csrf='';
export function setToken(token:string){csrf=token;}
export async function api<T=any>(path:string,body?:unknown,method?:string):Promise<T>{
 const form=body instanceof FormData;
 const response=await fetch('/api'+path,{method:method||(body!==undefined?'POST':'GET'),headers:{...(body!==undefined&&!form?{'Content-Type':'application/json'}:{}),...(csrf?{'X-Studio-Token':csrf}:{})},body:body===undefined?undefined:form?body as FormData:JSON.stringify(body)});
 const result=await response.json();if(!response.ok)throw Error(result.error||`Operation failed (${response.status}).`);return result;
}
export async function nativeSave(artifact:Artifact,name=artifact.name){return api('/save',{id:artifact.id,name});}

export function uploadFiles(files:File[],password:string,onProgress:(percent:number)=>void,options:{forceText?:boolean;encoding?:string;textDefaults?:Record<string,string>}={}):Promise<{id:string}>{
 return new Promise((resolve,reject)=>{
  const form=new FormData();files.forEach(file=>form.append('files',file));if(password)form.append('password',password);
  if(options.forceText)form.append('forceText','1');if(options.encoding)form.append('encoding',options.encoding);if(options.textDefaults)form.append('textDefaults',JSON.stringify(options.textDefaults));
  const xhr=new XMLHttpRequest();xhr.open('POST','/api/import-jobs');if(csrf)xhr.setRequestHeader('X-Studio-Token',csrf);
  xhr.upload.onprogress=e=>{if(e.lengthComputable)onProgress(Math.round(e.loaded/e.total*100));};
  xhr.onload=()=>{let result;try{result=JSON.parse(xhr.responseText);}catch{reject(Error('Upload could not finish. Try a smaller batch.'));return;}if(xhr.status>=200&&xhr.status<300)resolve(result);else reject(Error(result.error||'Upload could not finish.'));};
  xhr.onerror=()=>reject(Error('The local app connection was interrupted.'));xhr.send(form);
 });
}
