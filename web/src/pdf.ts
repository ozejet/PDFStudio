import {getDocument,GlobalWorkerOptions,type PDFDocumentProxy} from 'pdfjs-dist';
import type {Doc} from './types';
GlobalWorkerOptions.workerSrc='/vendor/pdfjs/pdf.worker.min.mjs';
export function docUrl(doc:Doc){return doc.url||`/api/documents/${doc.id}/file`;}
export function loadPdf(doc:Doc){return getDocument({url:docUrl(doc),cMapUrl:'/vendor/pdfjs/cmaps/',cMapPacked:true,standardFontDataUrl:'/vendor/pdfjs/standard_fonts/',wasmUrl:'/vendor/pdfjs/wasm/',iccUrl:'/vendor/pdfjs/iccs/'});}
export type {PDFDocumentProxy};
