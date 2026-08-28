// =============================================================================
// Navigate Events — Custom event bus for triggering Navigate from any surface
// Any component can emit a navigate request; the dashboard listens and switches
// to the Navigate tab with the target node pre-selected.
// =============================================================================

export interface NavigateEvent {
  nodeId: string;
  label: string;
  nodeType: string;
}

const NAVIGATE_EVENT = 'cortex:navigate';

/** Emit a navigate request — the dashboard will switch to Navigate tab */
export function emitNavigate(event: NavigateEvent): void {
  window.dispatchEvent(new CustomEvent(NAVIGATE_EVENT, { detail: event }));
}

/** Subscribe to navigate events */
export function onNavigateEvent(handler: (event: NavigateEvent) => void): () => void {
  const listener = (e: Event) => {
    const detail = (e as CustomEvent<NavigateEvent>).detail;
    handler(detail);
  };
  window.addEventListener(NAVIGATE_EVENT, listener);
  return () => window.removeEventListener(NAVIGATE_EVENT, listener);
}
