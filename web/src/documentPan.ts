type PanOptions = {isHand: () => boolean; scrollTarget?: HTMLElement};

export function attachDocumentPan(viewport: HTMLElement, options: PanOptions) {
  const win = viewport.ownerDocument.defaultView!;
  const scroll = options.scrollTarget ?? viewport;
  let hovered = false, space = false, pointerDown = false;
  let drag: {id: number; x: number; y: number; left: number; top: number} | null = null;
  const editing = (target: EventTarget | null) => target instanceof win.HTMLElement && !!target.closest('input,textarea,select,button,a,[contenteditable="true"],[role="textbox"]');
  const update = () => {
    viewport.classList.toggle('document-pan-ready', options.isHand() || space || !!drag);
    viewport.classList.toggle('document-panning', !!drag);
  };
  const finish = () => {
    const previous = drag;
    drag = null;
    if (previous) {
      try {viewport.releasePointerCapture(previous.id);} catch { /* Capture may already be released. */ }
    }
    pointerDown = false;
    update();
  };
  const enter = () => {hovered = true;};
  const leave = () => {hovered = false;};
  const keydown = (event: KeyboardEvent) => {
    if (event.code !== 'Space' || event.ctrlKey || event.metaKey || event.altKey || event.isComposing || editing(event.target)) return;
    if (!hovered && !viewport.contains(viewport.ownerDocument.activeElement)) return;
    event.preventDefault();
    // Do not turn an in-progress pencil stroke or object move into a pan.
    if (!pointerDown) {space = true; update();}
  };
  const keyup = (event: KeyboardEvent) => {if (event.code === 'Space') {space = false; update();}};
  const down = (event: PointerEvent) => {
    if (event.button !== 0 || event.isPrimary === false || editing(event.target)) return;
    pointerDown = true;
    if (!space && !options.isHand()) return;
    // Capture before PDF text selection or Fabric's drawing handlers receive it.
    event.preventDefault();
    event.stopImmediatePropagation();
    viewport.focus({preventScroll: true});
    drag = {id: event.pointerId, x: event.clientX, y: event.clientY, left: scroll.scrollLeft, top: scroll.scrollTop};
    try {viewport.setPointerCapture(event.pointerId);} catch { /* Window listeners also support older browsers. */ }
    update();
  };
  const move = (event: PointerEvent) => {
    if (!drag || event.pointerId !== drag.id) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    scroll.scrollLeft = drag.left - (event.clientX - drag.x);
    scroll.scrollTop = drag.top - (event.clientY - drag.y);
  };
  const up = (event: PointerEvent) => {
    if (drag && event.pointerId !== drag.id) return;
    if (drag) {event.preventDefault(); event.stopImmediatePropagation();}
    finish();
  };
  const mouse = (event: MouseEvent) => {
    if (drag || space || options.isHand()) {event.preventDefault(); event.stopImmediatePropagation();}
  };
  const blur = () => {space = false; hovered = false; finish();};
  const visibility = () => {if (viewport.ownerDocument.hidden) blur();};
  viewport.addEventListener('pointerenter', enter);
  viewport.addEventListener('pointerleave', leave);
  viewport.addEventListener('pointerdown', down, true);
  viewport.addEventListener('lostpointercapture', finish);
  viewport.addEventListener('mousedown', mouse, true);
  viewport.addEventListener('dragstart', mouse, true);
  win.addEventListener('pointermove', move, {capture: true, passive: false});
  win.addEventListener('pointerup', up, true);
  win.addEventListener('pointercancel', up, true);
  win.addEventListener('keydown', keydown);
  win.addEventListener('keyup', keyup);
  win.addEventListener('blur', blur);
  viewport.ownerDocument.addEventListener('visibilitychange', visibility);
  update();
  return {update, dispose() {
    blur();
    viewport.classList.remove('document-pan-ready', 'document-panning');
    viewport.removeEventListener('pointerenter', enter);
    viewport.removeEventListener('pointerleave', leave);
    viewport.removeEventListener('pointerdown', down, true);
    viewport.removeEventListener('lostpointercapture', finish);
    viewport.removeEventListener('mousedown', mouse, true);
    viewport.removeEventListener('dragstart', mouse, true);
    win.removeEventListener('pointermove', move, true);
    win.removeEventListener('pointerup', up, true);
    win.removeEventListener('pointercancel', up, true);
    win.removeEventListener('keydown', keydown);
    win.removeEventListener('keyup', keyup);
    win.removeEventListener('blur', blur);
    viewport.ownerDocument.removeEventListener('visibilitychange', visibility);
  }};
}
