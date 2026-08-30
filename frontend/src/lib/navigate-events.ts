// =============================================================================
// Navigate Events — Custom event bus for triggering Navigate from any surface
// Any component can emit a navigate request; the dashboard listens and switches
// to the Navigate tab with the target node pre-selected.
// =============================================================================

export interface NavigateEvent {
  nodeId: string;
  label: string;
  nodeType: string;
  /**
   * Optional source location carried by evidence links (Req 7.5). When present,
   * the Code Navigator opens this file and highlights the referenced line so
   * evidence chips land the user on the exact code.
   */
  filePath?: string | null;
  /** 1-indexed start of the referenced line range. */
  lineStart?: number | null;
  /** 1-indexed end of the referenced line range. */
  lineEnd?: number | null;
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
