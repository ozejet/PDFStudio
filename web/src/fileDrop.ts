// Content validation belongs to the local importer, shared by drops and the picker.
export function importDropFiles<T extends {name:string}>(files:T[]){return {accepted:[...files],ignored:[] as T[]};}
