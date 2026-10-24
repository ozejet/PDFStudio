type ZoomAnchor = {page: HTMLElement; x: number; y: number; clientX: number; clientY: number};

// A native, non-passive listener is needed: React's wheel listener lets the
// browser consume Ctrl+wheel before the PDF can handle it.
export function attachDocumentZoom(viewport: HTMLElement, onZoom: (percent: number) => void) {
  const win = viewport.ownerDocument.defaultView!;
  let anchor: ZoomAnchor | null = null;
  let queuedAnchor: ZoomAnchor | null = null;
  let pendingPercent: number | null = null;
  let frame = 0;
  const wheel = (event: WheelEvent) => {
    if (!event.ctrlKey && !event.metaKey) return;
    const pages = Array.from(viewport.querySelectorAll<HTMLElement>('[data-reader-page]'));
    let nearest: {page: HTMLElement; rect: DOMRect; distance: number} | undefined;
    // Continuous view can contain hundreds of page placeholders. Find the
    // nearest vertical page with logarithmic layout reads; spreads have <= 4.
    let candidates = pages;
    if (pages.length > 4) {
      let low = 0, high = pages.length - 1;
      while (low < high) {
        const mid = Math.floor((low + high) / 2);
        if (pages[mid].getBoundingClientRect().bottom < event.clientY) low = mid + 1;
        else high = mid;
      }
      candidates = pages.slice(Math.max(0, low - 1), low + 1);
    }
    for (const page of candidates) {
      const rect = page.getBoundingClientRect();
      if (!rect.width || !rect.height) continue;
      const dx = Math.max(rect.left - event.clientX, 0, event.clientX - rect.right);
      const dy = Math.max(rect.top - event.clientY, 0, event.clientY - rect.bottom);
      const distance = dx * dx + dy * dy;
      if (!nearest || distance < nearest.distance) nearest = {page, rect, distance};
    }
    if (!nearest) return;
    // Keep preventing browser zoom at both PDF zoom limits as well.
    event.preventDefault();
    const {page, rect} = nearest;
    const current = pendingPercent ?? rect.width / Number(page.dataset.readerWidth) * 100;
    const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? viewport.clientHeight : 1);
    const next = Math.max(25, Math.min(500, Math.round(current * Math.exp(-delta * .002))));
    if (!Number.isFinite(next) || next === current || !delta) return;
    // In a page margin, hold the closest edge steady instead of scaling the gap.
    const clientX = Math.max(rect.left, Math.min(rect.right, event.clientX));
    const clientY = Math.max(rect.top, Math.min(rect.bottom, event.clientY));
    queuedAnchor = {page, x: (clientX - rect.left) / rect.width, y: (clientY - rect.top) / rect.height, clientX, clientY};
    pendingPercent = next;
    // Trackpad/wheel bursts update layout at most once per animation frame.
    if (!frame) frame = win.requestAnimationFrame(() => {
      frame = 0;
      anchor = queuedAnchor;
      queuedAnchor = null;
      if (pendingPercent !== null) onZoom(pendingPercent);
    });
  };
  viewport.addEventListener('wheel', wheel, {passive: false});
  return {
    restore() {
      if (anchor) {
        const rect = anchor.page.getBoundingClientRect();
        viewport.scrollLeft += rect.left + anchor.x * rect.width - anchor.clientX;
        viewport.scrollTop += rect.top + anchor.y * rect.height - anchor.clientY;
      }
      anchor = null;
      if (!frame) pendingPercent = null;
    },
    dispose() {win.cancelAnimationFrame(frame); viewport.removeEventListener('wheel', wheel);},
  };
}
