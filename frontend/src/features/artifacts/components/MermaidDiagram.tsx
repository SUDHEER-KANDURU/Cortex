'use client';
// =============================================================================
// MermaidDiagram — Zoomable, pannable, downloadable architecture diagram
// Fixes: SVG connection lines visible, auto-fit, PNG download, ready detection
// =============================================================================

import React, { useCallback, useEffect, useRef, useState } from 'react';
import Mermaid from 'react-mermaid2';

export interface MermaidDiagramProps { definition: string }

// ── Clamp ─────────────────────────────────────────────────────────────────────
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

// ── Mermaid config ────────────────────────────────────────────────────────────
function mermaidConfig(dark: boolean) {
  return {
    theme: dark ? 'dark' : 'neutral',
    themeVariables: {
      background:       dark ? '#0d111b' : '#ffffff',
      primaryColor:     dark ? '#1e3a5f' : '#dbeafe',
      primaryTextColor: dark ? '#e2e8f0' : '#1e293b',
      lineColor:        dark ? '#94a3b8' : '#475569',
      edgeLabelBackground: dark ? '#1e293b' : '#f1f5f9',
    },
    securityLevel: 'loose',
  };
}

// ── Error boundary ────────────────────────────────────────────────────────────
class ErrBound extends React.Component<
  { children: React.ReactNode; onErr: (m: string) => void },
  { err: boolean }
> {
  state = { err: false };
  static getDerivedStateFromError() { return { err: true }; }
  componentDidCatch(e: Error) { this.props.onErr(e.message); }
  render() { return this.state.err ? null : this.props.children; }
}

// ── Tiny icon buttons ─────────────────────────────────────────────────────────
function Btn({ onClick, title, accent, children }: {
  onClick: () => void; title: string; accent?: boolean; children: React.ReactNode;
}) {
  const [h, setH] = useState(false);
  return (
    <button onClick={onClick} title={title} aria-label={title}
      onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{
        display: 'flex', alignItems: 'center', gap: 5,
        padding: '5px 10px', borderRadius: 7, cursor: 'pointer',
        border: `1px solid ${accent ? 'rgba(0,229,168,0.35)' : 'rgba(255,255,255,0.14)'}`,
        background: h
          ? (accent ? 'rgba(0,229,168,0.2)' : 'rgba(255,255,255,0.12)')
          : (accent ? 'rgba(0,229,168,0.09)' : 'rgba(255,255,255,0.05)'),
        color: accent ? '#00e5a8' : '#94a3b8',
        fontSize: 11, fontWeight: 600, transition: 'all 0.15s', whiteSpace: 'nowrap',
      }}>
      {children}
    </button>
  );
}

// ── CSS injected into SVG to ensure lines are visible ────────────────────────
const SVG_LINE_CSS = `
  .edgePath path, .edgePath .path { stroke: #94a3b8 !important; stroke-width: 1.8px !important; }
  .edgeLabel { background: #1e293b !important; }
  marker path { fill: #94a3b8 !important; }
  .node rect, .node polygon, .node circle, .node ellipse {
    stroke-width: 1.5px !important;
  }
  .label { color: #e2e8f0 !important; fill: #e2e8f0 !important; }
`;

// ── Main component ────────────────────────────────────────────────────────────
export default function MermaidDiagram({ definition }: MermaidDiagramProps) {
  const wrap   = useRef<HTMLDivElement>(null);
  const inner  = useRef<HTMLDivElement>(null);
  const drag   = useRef<{ sx: number; sy: number; tx: number; ty: number } | null>(null);
  const isDragging = useRef(false);
  const [tr,   setTr]   = useState({ x: 0, y: 0, s: 1 });
  const [ready,setReady]= useState(false);
  const [err,  setErr]  = useState<string | null>(null);
  const [dl,   setDl]   = useState(false);
  const dark = typeof document !== 'undefined'
    ? document.documentElement.getAttribute('data-theme') !== 'light'
    : true;

  // ── Patch SVG lines once it renders ──────────────────────────────────────
  const patchSvg = useCallback(() => {
    const svg = inner.current?.querySelector('svg');
    if (!svg) return;
    // Remove any existing patch style
    svg.querySelectorAll('style[data-cortex]').forEach(el => el.remove());
    const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
    style.setAttribute('data-cortex', '1');
    style.textContent = SVG_LINE_CSS;
    svg.insertBefore(style, svg.firstChild);
    // Also set explicit stroke on all existing paths
    svg.querySelectorAll('.edgePath path, .edgePath .path').forEach(p => {
      (p as SVGElement).style.stroke = '#94a3b8';
      (p as SVGElement).style.strokeWidth = '1.8px';
    });
    svg.querySelectorAll('marker path').forEach(p => {
      (p as SVGElement).style.fill = '#94a3b8';
    });
  }, []);

  // ── Auto-fit: scale SVG to fill container ────────────────────────────────
  const fit = useCallback(() => {
    const w = wrap.current;
    const i = inner.current;
    if (!w || !i) return;
    const svg = i.querySelector('svg');
    if (!svg) return;
    const wW = w.clientWidth  - 40;
    const wH = w.clientHeight - 40;
    const sW = svg.scrollWidth  || (svg.viewBox?.baseVal?.width)  || 800;
    const sH = svg.scrollHeight || (svg.viewBox?.baseVal?.height) || 600;
    if (sW <= 0 || sH <= 0) return;
    const s = clamp(Math.min(wW / sW, wH / sH), 0.05, 2.0);
    const x = (wW - sW * s) / 2 + 20;
    const y = (wH - sH * s) / 2 + 20;
    setTr({ x, y, s });
  }, []);

  // ── MutationObserver: detect when SVG appears ─────────────────────────────
  useEffect(() => {
    setReady(false);
    setErr(null);
    setTr({ x: 0, y: 0, s: 1 });
    if (!inner.current) return;

    const obs = new MutationObserver(() => {
      const svg = inner.current?.querySelector('svg');
      if (svg && svg.querySelector('.node')) {
        patchSvg();
        setReady(true);
        obs.disconnect();
      }
    });
    obs.observe(inner.current, { childList: true, subtree: true, attributes: false });

    // Fallback: if SVG already there
    const existing = inner.current.querySelector('svg');
    if (existing) { patchSvg(); setReady(true); obs.disconnect(); }

    return () => obs.disconnect();
  }, [definition, patchSvg]);

  // ── Fit after ready ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!ready) return;
    const t = setTimeout(fit, 80);
    return () => clearTimeout(t);
  }, [ready, fit]);

  // ── Refit on resize ───────────────────────────────────────────────────────
  useEffect(() => {
    window.addEventListener('resize', fit);
    return () => window.removeEventListener('resize', fit);
  }, [fit]);

  // ── Wheel zoom ────────────────────────────────────────────────────────────
  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const r  = el.getBoundingClientRect();
      const mx = e.clientX - r.left;
      const my = e.clientY - r.top;
      const d  = e.deltaY > 0 ? 0.88 : 1.14;
      setTr(p => {
        const ns = clamp(p.s * d, 0.05, 8);
        const r2 = ns / p.s;
        return { s: ns, x: mx - (mx - p.x) * r2, y: my - (my - p.y) * r2 };
      });
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  // ── Drag pan ──────────────────────────────────────────────────────────────
  const onMD = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    // Capture current transform values directly from the ref-stable setter
    setTr(current => {
      drag.current = { sx: e.clientX, sy: e.clientY, tx: current.x, ty: current.y };
      return current; // no change, just reading
    });
    isDragging.current = true;
  }, []);
  const onMM = useCallback((e: React.MouseEvent) => {
    if (!drag.current) return;
    const d = drag.current;
    setTr(p => ({ ...p, x: d.tx + e.clientX - d.sx, y: d.ty + e.clientY - d.sy }));
  }, []);
  const onMU = useCallback(() => {
    drag.current = null;
    isDragging.current = false;
  }, []);

  // ── Zoom buttons ──────────────────────────────────────────────────────────
  const zoom = useCallback((f: number) => {
    const w = wrap.current;
    if (!w) return;
    const cx = w.clientWidth / 2, cy = w.clientHeight / 2;
    setTr(p => {
      const ns = clamp(p.s * f, 0.05, 8);
      const r  = ns / p.s;
      return { s: ns, x: cx - (cx - p.x) * r, y: cy - (cy - p.y) * r };
    });
  }, []);

  // ── Download PNG ──────────────────────────────────────────────────────────
  const download = useCallback(async () => {
    setDl(true);
    try {
      const svg = inner.current?.querySelector('svg') as SVGSVGElement | null;
      if (!svg) { setDl(false); return; }
      patchSvg();

      const sw = svg.scrollWidth || 1400;
      const sh = svg.scrollHeight || 900;

      const clone = svg.cloneNode(true) as SVGSVGElement;
      clone.setAttribute('width',  String(sw));
      clone.setAttribute('height', String(sh));
      clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');

      // Add background rect
      const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      bg.setAttribute('width', '100%');
      bg.setAttribute('height', '100%');
      bg.setAttribute('fill', dark ? '#0d111b' : '#ffffff');
      clone.insertBefore(bg, clone.firstChild);

      // Download as SVG (avoids tainted canvas SecurityError from cross-origin image data)
      const svgStr = new XMLSerializer().serializeToString(clone);
      const blob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'architecture-diagram.svg';
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      console.error('Download failed:', e);
    } finally {
      setDl(false);
    }
  }, [dark, patchSvg]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', borderRadius: 12, overflow: 'hidden', border: '1px solid var(--border)' }}>

      {/* ── Toolbar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px',
        background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border)',
        flexWrap: 'wrap',
      }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginRight: 6, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          Architecture Diagram
        </span>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', minWidth: 36, textAlign: 'right' }}>
          {Math.round(tr.s * 100)}%
        </span>
        <Btn onClick={() => zoom(1.3)} title="Zoom in">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
          Zoom In
        </Btn>
        <Btn onClick={() => zoom(0.77)} title="Zoom out">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
          Zoom Out
        </Btn>
        <Btn onClick={fit} title="Fit diagram to screen">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
          Fit
        </Btn>
        <Btn onClick={download} title="Download as PNG image" accent>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          {dl ? 'Exporting…' : '↓ SVG'}
        </Btn>
      </div>

      {/* ── Canvas ── */}
      <div
        ref={wrap}
        onMouseDown={onMD} onMouseMove={onMM}
        onMouseUp={onMU}   onMouseLeave={onMU}
        style={{
          position: 'relative', width: '100%', height: 580,
          overflow: 'hidden',
          background: dark ? '#080b14' : '#f8faff',
          cursor: isDragging.current ? 'grabbing' : 'grab',
          userSelect: 'none',
        }}
      >
        {/* Loading state */}
        {!ready && !err && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12, color: '#64748b', fontSize: 13 }}>
            <div style={{ width: 24, height: 24, border: '2px solid #334155', borderTopColor: '#00e5a8', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            Rendering diagram…
          </div>
        )}

        {/* Error state */}
        {err && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 10, padding: 32 }}>
            <span style={{ fontSize: 24 }}>⚠️</span>
            <p style={{ fontSize: 13, fontWeight: 600, color: '#f87171', margin: 0 }}>Diagram syntax error</p>
            <pre style={{ fontSize: 11, color: '#94a3b8', background: 'rgba(255,255,255,0.04)', border: '1px solid #334155', borderRadius: 8, padding: '10px 14px', maxWidth: 480, overflowX: 'auto', margin: 0 }}>{err}</pre>
          </div>
        )}

        {/* Transformed inner */}
        <div
          ref={inner}
          style={{
            position: 'absolute', top: 0, left: 0,
            transform: `translate(${tr.x}px,${tr.y}px) scale(${tr.s})`,
            transformOrigin: '0 0',
            transition: isDragging.current ? 'none' : 'transform 0.08s ease-out',
          }}
        >
          <ErrBound onErr={m => { setErr(m); setReady(false); }}>
            <Mermaid chart={definition} config={mermaidConfig(dark)} key={definition} />
          </ErrBound>
        </div>

        {/* Usage hint */}
        {ready && (
          <div style={{ position: 'absolute', bottom: 10, right: 14, fontSize: 10, color: '#475569', pointerEvents: 'none' }}>
            Scroll to zoom · Drag to pan
          </div>
        )}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
