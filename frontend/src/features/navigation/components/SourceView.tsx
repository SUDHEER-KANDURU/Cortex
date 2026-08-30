// =============================================================================
// SourceView — Center region of the Code Navigator
// Renders the source of the open file. Deliberately kept thin: it exposes the
// seams later tasks build on without implementing their behavior here.
//   - Task 13 (annotations + selection-driven chat): `onSelectRange` fires with
//     the clicked line(s); `annotations` may decorate lines later.
//   - Task 14 (evidence-link navigation): `highlightLine` scrolls/marks a line.
// =============================================================================

'use client';

import React from 'react';
import { FileCode2, Activity, ArrowDownRight, Globe } from 'lucide-react';
import type { GraphNode } from '@/types';
import type { LineAnnotation } from './annotations';

export interface SourceSelection {
  lineStart: number;
  lineEnd: number;
}

interface SourceViewProps {
  /** The open FILE node, or null when nothing is selected. */
  file: GraphNode | null;
  /** Raw source of the open file. Empty string while loading / unavailable. */
  source?: string;
  /** True while the source is being fetched. */
  isLoading?: boolean;
  /** Line to visually mark (Task 14 seam). 1-indexed. */
  highlightLine?: number | null;
  /** Fired when the user selects a line/range (Task 13 seam). */
  onSelectRange?: (selection: SourceSelection) => void;
  /**
   * Symbol annotations keyed by 1-based line number (Req 7.2). Each entry
   * decorates its line with complexity / fan-in / endpoint badges derived from
   * graph evidence.
   */
  annotations?: Map<number, LineAnnotation>;
}

// ── Line annotation badges (Req 7.2) ─────────────────────────────────────────
function LineBadges({ annotation }: { annotation: LineAnnotation }) {
  const { complexity, complexityWarn, fanIn, isEndpoint, route } = annotation;
  return (
    <span
      data-testid={`source-annotation-${annotation.line}`}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 5, marginLeft: 8,
        flexShrink: 0, verticalAlign: 'middle',
      }}
    >
      {isEndpoint && (
        <span
          data-testid={`annotation-endpoint-${annotation.line}`}
          title={route ? `API endpoint — ${route}` : 'API endpoint'}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 9, fontWeight: 700,
            padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--font-mono)',
            color: 'var(--primary)', background: 'var(--primary-dim)',
            border: '0.5px solid rgba(255,255,255,0.4)',
          }}
        >
          <Globe style={{ width: 9, height: 9 }} aria-hidden="true" />
          {route || 'endpoint'}
        </span>
      )}
      {complexity != null && (
        <span
          data-testid={`annotation-complexity-${annotation.line}`}
          title={`Cyclomatic complexity: ${complexity}${complexityWarn ? ' (high)' : ''}`}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 9, fontWeight: 700,
            padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--font-mono)',
            color: complexityWarn ? '#f97316' : 'var(--text-muted)',
            background: complexityWarn ? 'rgba(249,115,22,0.10)' : 'rgba(255,255,255,0.30)',
            border: `0.5px solid ${complexityWarn ? 'rgba(249,115,22,0.30)' : 'rgba(255,255,255,0.45)'}`,
          }}
        >
          <Activity style={{ width: 9, height: 9 }} aria-hidden="true" />
          cx {complexity}
        </span>
      )}
      {fanIn > 0 && (
        <span
          data-testid={`annotation-fanin-${annotation.line}`}
          title={`Fan-in: ${fanIn} caller(s) / dependent(s)`}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 9, fontWeight: 700,
            padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)', background: 'rgba(255,255,255,0.30)',
            border: '0.5px solid rgba(255,255,255,0.45)',
          }}
        >
          <ArrowDownRight style={{ width: 9, height: 9 }} aria-hidden="true" />
          {fanIn}
        </span>
      )}
    </span>
  );
}

function filePath(node: GraphNode): string {
  return ((node.properties.path as string) || (node.properties.file as string) || node.label);
}

export default function SourceView({
  file, source = '', isLoading = false, highlightLine = null, onSelectRange, annotations,
}: SourceViewProps) {
  const lines = source ? source.split('\n') : [];
  const highlightRef = React.useRef<HTMLDivElement | null>(null);

  // Scroll the highlighted line into view when arriving via an evidence link
  // (Task 14). Runs after the source for the target line is available.
  React.useEffect(() => {
    if (highlightLine != null && highlightRef.current) {
      highlightRef.current.scrollIntoView({ block: 'center' });
    }
  }, [highlightLine, source]);

  return (
    <div
      data-testid="source-view"
      style={{
        display: 'flex', flexDirection: 'column', height: '100%', minHeight: 240,
        borderRadius: 12, overflow: 'hidden',
        background: 'rgba(255,255,255,0.35)', border: '0.5px solid rgba(255,255,255,0.55)',
      }}
    >
      {/* Header — open file path */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px',
        borderBottom: '0.5px solid rgba(255,255,255,0.5)', background: 'rgba(255,255,255,0.3)',
      }}>
        <FileCode2 style={{ width: 13, height: 13, color: 'var(--primary)' }} />
        <span
          data-testid="source-view-path"
          style={{ fontSize: 11, color: 'var(--text)', fontFamily: 'var(--font-mono)' }}
        >
          {file ? filePath(file) : 'No file open'}
        </span>
      </div>

      {/* Body */}
      <div className="dash-scroll" style={{ flex: 1, overflow: 'auto', padding: '4px 0' }}>
        {!file && (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', height: '100%', minHeight: 200, gap: 10, padding: '40px 20px',
          }}>
            <FileCode2 style={{ width: 22, height: 22, color: 'var(--text-muted)' }} />
            <p style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', margin: 0 }}>
              Select a file to view its source
            </p>
          </div>
        )}

        {file && isLoading && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '32px 0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div className="cortex-pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)' }} />
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Loading source...</span>
            </div>
          </div>
        )}

        {file && !isLoading && lines.length === 0 && (
          <p style={{ fontSize: 11, color: 'var(--text-muted)', padding: '16px', margin: 0 }}>
            No source available for this file.
          </p>
        )}

        {file && !isLoading && lines.length > 0 && (
          <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: 11.5, lineHeight: 1.6 }}>
            {lines.map((text, i) => {
              const lineNo = i + 1;
              const marked = highlightLine === lineNo;
              const annotation = annotations?.get(lineNo) ?? null;
              return (
                <div
                  key={lineNo}
                  ref={marked ? highlightRef : undefined}
                  data-testid={`source-line-${lineNo}`}
                  data-annotated={annotation ? 'true' : undefined}
                  data-highlighted={marked ? 'true' : undefined}
                  onClick={() => onSelectRange?.({ lineStart: lineNo, lineEnd: lineNo })}
                  style={{
                    display: 'flex', gap: 12, padding: '0 14px', cursor: onSelectRange ? 'pointer' : 'default',
                    background: marked ? 'var(--primary-dim)' : 'transparent',
                  }}
                >
                  <span style={{
                    color: 'var(--text-muted)', userSelect: 'none', textAlign: 'right',
                    minWidth: 32, opacity: 0.6,
                  }}>
                    {lineNo}
                  </span>
                  <span style={{ color: 'var(--text)', whiteSpace: 'pre-wrap' }}>{text || ' '}</span>
                  {annotation && <LineBadges annotation={annotation} />}
                </div>
              );
            })}
          </pre>
        )}
      </div>
    </div>
  );
}
