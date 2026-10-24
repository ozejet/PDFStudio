/** Keep navigation with the visible document without taking keys from controls. */
export function documentKeyboardAvailable(event:KeyboardEvent,reader:HTMLElement|null){
 if(!reader||event.defaultPrevented||event.ctrlKey||event.metaKey||event.altKey||event.shiftKey||event.isComposing)return false;
 const target=event.target as Element|null;
 if(target?.closest?.('input,textarea,select,[contenteditable]:not([contenteditable="false"]),[role="slider"],[role="menu"],[role="menubar"],[role="listbox"],[role="tablist"],[role="tree"],[role="grid"],.notification-stack,.feedback-panel'))return false;
 const dialogs=reader.ownerDocument.querySelectorAll('dialog[open]'),top=dialogs[dialogs.length-1];
 if(top&&!top.contains(reader))return false;
 if(reader.querySelector('.document-panning'))return false;
 const selection=reader.ownerDocument.getSelection();
 if(selection&&!selection.isCollapsed)return false;
 return true;
}
