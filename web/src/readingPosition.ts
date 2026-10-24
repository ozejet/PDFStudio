export type ReadingPosition = {page: HTMLElement; x: number; y: number; offsetX: number; offsetY: number};

export function captureReadingPosition(viewport: HTMLElement): ReadingPosition | null {
 const bounds=viewport.getBoundingClientRect();
 const clientX=bounds.left+24,clientY=bounds.top+24;
 const pages=Array.from(viewport.querySelectorAll<HTMLElement>('[data-reader-page]'));
 let nearest:{page:HTMLElement;rect:DOMRect;distance:number}|undefined;
 // Layout changes are infrequent; measure only pages around the viewport top.
 let low=0,high=pages.length-1;
 if(pages.length>4){while(low<high){const mid=Math.floor((low+high)/2);if(pages[mid].getBoundingClientRect().bottom<clientY)low=mid+1;else high=mid;}}
 const candidates=pages.length>4?pages.slice(Math.max(0,low-1),low+1):pages;
 for(const page of candidates){
  const rect=page.getBoundingClientRect();if(!rect.width||!rect.height)continue;
  const dx=Math.max(rect.left-clientX,0,clientX-rect.right),dy=Math.max(rect.top-clientY,0,clientY-rect.bottom);
  const distance=dx*dx+dy*dy;if(!nearest||distance<nearest.distance)nearest={page,rect,distance};
 }
 if(!nearest)return null;
 const {page,rect}=nearest,atX=Math.max(rect.left,Math.min(rect.right,clientX)),atY=Math.max(rect.top,Math.min(rect.bottom,clientY));
 return {page,x:(atX-rect.left)/rect.width,y:(atY-rect.top)/rect.height,offsetX:atX-bounds.left,offsetY:atY-bounds.top};
}

export function restoreReadingPosition(viewport:HTMLElement,position:ReadingPosition) {
 if(!viewport.contains(position.page))return;
 const bounds=viewport.getBoundingClientRect(),page=position.page.getBoundingClientRect();
 viewport.scrollLeft+=page.left+position.x*page.width-bounds.left-position.offsetX;
 viewport.scrollTop+=page.top+position.y*page.height-bounds.top-position.offsetY;
}
