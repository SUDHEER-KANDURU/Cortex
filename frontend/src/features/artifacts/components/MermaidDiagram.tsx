'use client';
// =============================================================================
// MermaidDiagram — Zoomable, pannable, downloadable architecture diagram
//
// Fixes applied:
//   - Dynamic canvas height: min 480px, grows to fill available space
//     (was fixed 580px which compressed graph TB diagrams into thin bands)
//   - fit() now scales to fill width first, then centres vertically
//     (was Math.min(wW/sW, wH/sH) which collapsed wide LR diagrams)
//   - SVG_LINE_CSS is now theme-aware (separate dark / light palettes)
//   - Mermaid config includes flowchart nodeSpacing + rankSpacing
//   - Fullscreen toggle added so users can escape the panel height limit
//   - Download label corrected to SVG (was labelled PNG)
// =============================================================================

import React, { useCallback, useEffect, useRef, useState } from 'react';
import Mermaid from 'react-mermaid2';

export interface MermaidDiagramProps { definition: string }

// ── Clamp ─────────────────────────────────────────────────────────────────────
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

// ── Mermaid config — dark, warm-toned ─────────────────────────────────────────
function mermaidConfig() {
  return {
    theme: 'dark',
    themeVariables: {
      background:            'transparent',
      primaryColor:          '#33230f',
      primaryBorderColor:    '#a87a3e',
      primaryTextColor:      '#F5EFE7',
      secondaryColor:        '#2a1c0e',
      tertiaryColor:         '#241708',
      mainBkg:               '#33230f',
      nodeBorder:            '#a87a3e',
      lineColor:             '#b09268',
      textColor:             '#F5EFE7',
      edgeLabelBackground:   '#241708',
      clusterBkg:            'rgba(255,255,255,0.04)',
      clusterBorder:         'rgba(255,255,255,0.14)',
      fontFamily:            "var(--font-mono, 'JetBrains Mono', monospace)",
    },
    flowchart: { nodeSpacing: 60, rankSpacing: 80, htmlLabels: true, curve: 'basis' },
    securityLevel: 'loose',
  };
}

function svgLineCss(): string {
  return `
  .edgePath path, .edgePath .path { stroke: #b09268 !important; stroke-width: 1.8px !important; }
  .edgeLabel { background: #241708 !important; color: #F5EFE7 !important; }
  .edgeLabel rect { fill: #241708 !important; }
  marker path { fill: #b09268 !important; }
  .node rect, .node polygon, .node circle, .node ellipse { stroke-width: 1.5px !important; }
  .label { color: #F5EFE7 !important; fill: #F5EFE7 !important; }
  .cluster rect { fill: rgba(255,255,255,0.04) !important; stroke: rgba(255,255,255,0.14) !important; }
`;
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

// ── Tiny icon buttons — fully token-driven ───────────────────────────────────
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
        border: '1px solid var(--border)',
        background: h
          ? (accent ? 'var(--primary-dim)' : 'var(--surface)')
          : (accent ? 'var(--primary-dim)' : 'transparent'),
        color: accent ? 'var(--primary)' : 'var(--text-muted)',
        fontSize: 11, fontWeight: 600, transition: 'all 0.15s', whiteSpace: 'nowrap',
      }}>
      {children}
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function MermaidDiagram({ definition }: MermaidDiagramProps) {
  const wrap       = useRef<HTMLDivElement>(null);
  const inner      = useRef<HTMLDivElement>(null);
  const drag       = useRef<{ sx: number; sy: number; tx: number; ty: number } | null>(null);
  const isDragging = useRef(false);

  const [tr,         setTr]         = useState({ x: 0, y: 0, s: 1 });
  const [ready,      setReady]      = useState(false);
  const [err,        setErr]        = useState<string | null>(null);
  const [dl,         setDl]         = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

  // Light-only — no dark theme

  // ── Patch SVG lines once it renders ──────────────────────────────────────
  const patchSvg = useCallback(() => {
    const svg = inner.current?.querySelector('svg');
    if (!svg) return;
    svg.querySelectorAll('style[data-cortex]').forEach(el => el.remove());
    const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
    style.setAttribute('data-cortex', '1');
    style.textContent = svgLineCss();
    svg.insertBefore(style, svg.firstChild);
    svg.querySelectorAll('.edgePath path, .edgePath .path').forEach(p => {
      (p as SVGElement).style.stroke = '#A1A1AA';
      (p as SVGElement).style.strokeWidth = '1.8px';
    });
    svg.querySelectorAll('marker path').forEach(p => {
      (p as SVGElement).style.fill = '#A1A1AA';
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Auto-fit: scale SVG to fill container width, centre vertically ────────
  // Previous implementation used Math.min(wW/sW, wH/sH) which caused a
  // graph TB diagram (taller than wide) to scale down to a thin horizontal
  // band when the height ratio was the limiting factor. The corrected version
  // scales to fill the available width and centres the result vertically,
  // giving the diagram the space it needs while staying within the canvas.
  const fit = useCallback(() => {
    const w = wrap.current;
    const i = inner.current;
    if (!w || !i) return;
    const svg = i.querySelector('svg');
    if (!svg) return;

    const pad = 32;
    const wW = w.clientWidth  - pad;
    const wH = w.clientHeight - pad;
    const sW = svg.scrollWidth  || svg.viewBox?.baseVal?.width  || 800;
    const sH = svg.scrollHeight || svg.viewBox?.baseVal?.height || 600;
    if (sW <= 0 || sH <= 0) return;

    // Scale to fill width. If the result is taller than the canvas, also
    // constrain by height so nothing overflows — but prefer width-first.
    const sByW = wW / sW;
    const sByH = wH / sH;
    const s = clamp(
      sH * sByW > wH ? sByH : sByW,   // use height-scale only if width-scale overflows height
      0.05,
      2.5,
    );

    const x = (wW - sW * s) / 2 + pad / 2;
    const y = (wH - sH * s) / 2 + pad / 2;
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

  // ── Refit when fullscreen changes ─────────────────────────────────────────
  useEffect(() => {
    if (ready) {
      const t = setTimeout(fit, 60);
      return () => clearTimeout(t);
    }
  }, [fullscreen, ready, fit]);

  // ── Wheel zoom (Ctrl + scroll only — normal scroll passes through) ──────
  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return; // let normal scroll through
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
    setTr(current => {
      drag.current = { sx: e.clientX, sy: e.clientY, tx: current.x, ty: current.y };
      return current;
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

  // ── Touch pan & pinch-zoom ──────────────────────────────────────────────
  // Single finger drags to pan; two fingers pinch to zoom around the midpoint.
  // Registered as a non-passive listener so we can preventDefault and stop the
  // page from scrolling while the user manipulates the diagram.
  const pinch = useRef<{ dist: number; cx: number; cy: number } | null>(null);
  useEffect(() => {
    const el = wrap.current;
    if (!el) return;

    const dist = (a: Touch, b: Touch) =>
      Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);

    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        isDragging.current = true;
        setTr(cur => {
          drag.current = { sx: e.touches[0].clientX, sy: e.touches[0].clientY, tx: cur.x, ty: cur.y };
          return cur;
        });
      } else if (e.touches.length === 2) {
        drag.current = null;
        pinch.current = {
          dist: dist(e.touches[0], e.touches[1]),
          cx: (e.touches[0].clientX + e.touches[1].clientX) / 2,
          cy: (e.touches[0].clientY + e.touches[1].clientY) / 2,
        };
      }
    };

    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2 && pinch.current) {
        e.preventDefault();
        const r = el.getBoundingClientRect();
        const newDist = dist(e.touches[0], e.touches[1]);
        const cx = (e.touches[0].clientX + e.touches[1].clientX) / 2 - r.left;
        const cy = (e.touches[0].clientY + e.touches[1].clientY) / 2 - r.top;
        const factor = newDist / (pinch.current.dist || newDist);
        pinch.current.dist = newDist;
        setTr(p => {
          const ns = clamp(p.s * factor, 0.05, 8);
          const ratio = ns / p.s;
          return { s: ns, x: cx - (cx - p.x) * ratio, y: cy - (cy - p.y) * ratio };
        });
      } else if (e.touches.length === 1 && drag.current) {
        e.preventDefault();
        const d = drag.current;
        setTr(p => ({ ...p, x: d.tx + e.touches[0].clientX - d.sx, y: d.ty + e.touches[0].clientY - d.sy }));
      }
    };

    const onTouchEnd = (e: TouchEvent) => {
      if (e.touches.length === 0) {
        drag.current = null;
        isDragging.current = false;
      }
      if (e.touches.length < 2) pinch.current = null;
    };

    el.addEventListener('touchstart', onTouchStart, { passive: true });
    el.addEventListener('touchmove', onTouchMove, { passive: false });
    el.addEventListener('touchend', onTouchEnd, { passive: true });
    el.addEventListener('touchcancel', onTouchEnd, { passive: true });
    return () => {
      el.removeEventListener('touchstart', onTouchStart);
      el.removeEventListener('touchmove', onTouchMove);
      el.removeEventListener('touchend', onTouchEnd);
      el.removeEventListener('touchcancel', onTouchEnd);
    };
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

  // ── Download SVG ──────────────────────────────────────────────────────────
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

      const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      bg.setAttribute('width', '100%');
      bg.setAttribute('height', '100%');
      bg.setAttribute('fill', '#1A1208');
      clone.insertBefore(bg, clone.firstChild);

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
  }, [patchSvg]);

  // ── Canvas height ─────────────────────────────────────────────────────────
  // Dynamic: minimum 480px in normal mode, fills the viewport in fullscreen.
  // Previously fixed at 580px, which compressed graph TB diagrams into a
  // thin horizontal band when the SVG was taller than wide.
  const canvasHeight = fullscreen ? 'calc(100vh - 90px)' : 'clamp(480px, 55vh, 800px)';

  const outerStyle: React.CSSProperties = fullscreen
    ? {
        position: 'fixed', inset: 0, zIndex: 9999,
        display: 'flex', flexDirection: 'column',
        borderRadius: 0, border: 'none',
        background: 'var(--bg)',
      }
    : {
        display: 'flex', flexDirection: 'column',
        width: '100%', borderRadius: 16,
        border: '1px solid rgba(255,255,255,0.13)',
        background: 'rgba(255,255,255,0.05)',
        backdropFilter: 'blur(30px) saturate(155%)',
        WebkitBackdropFilter: 'blur(30px) saturate(155%)',
        boxShadow:
          '0 14px 34px rgba(0,0,0,0.36),' +
          'inset 0 1.5px 1px rgba(255,255,255,0.32),' +
          'inset 0 -1.5px 1px rgba(255,255,255,0.12)',
      };

  return (
    <div style={outerStyle}>

      {/* ── Toolbar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px',
        background: 'var(--surface)', borderBottom: '1px solid var(--border)',
        flexWrap: 'wrap', flexShrink: 0,
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
        <Btn onClick={() => setFullscreen(f => !f)} title={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
          {fullscreen
            ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="10" y1="14" x2="3" y2="21"/><line x1="21" y1="3" x2="14" y2="10"/></svg>
            : <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
          }
          {fullscreen ? 'Exit' : 'Fullscreen'}
        </Btn>
        <Btn onClick={download} title="Download as SVG" accent>
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
          position: 'relative', width: '100%',
          height: canvasHeight,
          overflow: 'hidden',
          background: 'rgba(255,255,255,0.05)',
          cursor: isDragging.current ? 'grabbing' : 'grab',
          userSelect: 'none',
          // Let our touch handlers own the gestures (pan + pinch) instead of
          // the browser scrolling/zooming the page.
          touchAction: 'none',
          flex: fullscreen ? 1 : undefined,
        }}
      >
        {/* Loading state */}
        {!ready && !err && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12, color: 'var(--text-muted)', fontSize: 13 }}>
            <div style={{ width: 24, height: 24, border: '2px solid var(--border)', borderTopColor: 'var(--primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            Rendering diagram…
          </div>
        )}

        {/* Error state */}
        {err && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 10, padding: 32 }}>
            <span style={{ fontSize: 24 }}>⚠️</span>
            <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--danger)', margin: 0 }}>Diagram syntax error</p>
            <pre style={{ fontSize: 11, color: 'var(--text-muted)', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', maxWidth: 480, overflowX: 'auto', margin: 0 }}>{err}</pre>
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
            <Mermaid chart={definition} config={mermaidConfig()} key={definition} />
          </ErrBound>
        </div>

        {ready && (
          <>
            <div className="mermaid-hint-desktop" style={{ position: 'absolute', bottom: 10, right: 14, fontSize: 10, color: '#94a3b8', pointerEvents: 'none' }}>
              Ctrl + Scroll to zoom · Drag to pan
            </div>
            <div className="mermaid-hint-touch" style={{ position: 'absolute', bottom: 10, right: 14, fontSize: 10, color: '#94a3b8', pointerEvents: 'none' }}>
              Pinch to zoom · Drag to pan
            </div>
          </>
        )}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
