// =============================================================================
// ArtifactViewer — Renders a Cortex artifact based on its content_type
// Fully theme-aware — uses CSS variables only, no hardcoded dark values.
// =============================================================================

import React from 'react';
import type { Artifact } from '@/types';
import MermaidDiagram from './MermaidDiagram';
import MarkdownViewer from './MarkdownViewer';

export interface ArtifactViewerProps {
  artifact: Artifact;
}

function tryFormatJson(raw: string): string | null {
  try { return JSON.stringify(JSON.parse(raw), null, 2); }
  catch { return null; }
}

// Base styles for pre/code blocks — background adapts via CSS variable
const preBase: React.CSSProperties = {
  overflow: 'auto',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  borderRadius: 'var(--radius-md)',
  border: '1px solid var(--border)',
  // Use a CSS-variable-driven background so both themes work correctly.
  // Dark:  surface (~#151922) + a little extra depth
  // Light: white with a very subtle tint
  background: 'var(--surface)',
  padding: '16px 18px',
  fontSize: 13,
  lineHeight: 1.75,
  margin: 0,
  fontFamily: 'var(--font-mono)',
};

export default React.memo(function ArtifactViewer({ artifact }: ArtifactViewerProps) {
  const content     = artifact.content_inline ?? '';
  const contentType = artifact.content_type;

  const renderContent = (): React.ReactNode => {
    if (!content) {
      return (
        <p style={{ padding: '16px 0', textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
          No inline content available.{' '}
          {artifact.storage_path && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>
              {artifact.storage_path}
            </span>
          )}
        </p>
      );
    }

    if (contentType === 'mermaid') {
      return <MermaidDiagram definition={content} />;
    }

    if (contentType === 'text/markdown') {
      return <MarkdownViewer content={content} />;
    }

    if (contentType === 'application/json') {
      const formatted = tryFormatJson(content);
      return (
        <pre style={{ ...preBase, color: 'var(--success)' }}>
          {formatted ?? content}
        </pre>
      );
    }

    return (
      <pre style={{ ...preBase, color: 'var(--text-secondary)' }}>
        {content}
      </pre>
    );
  };

  return (
    <article className="flex flex-col gap-3" aria-label={`Artifact ${artifact.id}`}>
      {renderContent()}
    </article>
  );
});
