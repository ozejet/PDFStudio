export function importProblem(open:number,incoming:number,limit:number,busy:boolean){
 if(busy)return 'An operation is already running. Wait for it to finish before adding files.';
 if(open+incoming>limit)return `PDF Studio can open up to ${limit} files. You have ${open} open and selected ${incoming}. Close files or choose a smaller batch. No files in this batch were uploaded or opened.`;
 return '';
}

export function partitionImportErrors<T extends {name:string}>(files:T[],errors:{index:number;name:string;error:string}[]){
 const needsPassword=(item:typeof errors[number])=>/\.pdf$/i.test(files[item.index]?.name||'')&&/password/i.test(item.error);
 return {passwordFiles:errors.filter(needsPassword).map(item=>files[item.index]),errors:errors.filter(item=>!needsPassword(item))};
}
