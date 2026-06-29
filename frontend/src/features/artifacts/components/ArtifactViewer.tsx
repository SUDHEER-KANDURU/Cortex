// =============================================================================
// ArtifactViewer — Renders a Cortex artifact based on its content_type
// Supports: mermaid, text/markdown, application/json, text/plain
// =============================================================================

import React from 'react';
import { FileText, Calendar } from 'lucide-react';
import type { Artifact } from '@/types';
import { formatDate } from '@/lib/utils/formatDate';
import MermaidDiagram from './MermaidDiagram';

export interface ArtifactViewerProps {
  /** The artifact to render */
  artifact: Artifact;
}

/** Format JSON string with indentation, returning null on parse failure */
function tryFormatJson(raw: string): string | null {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return null;
  }
}

export default function ArtifactViewer({ artifact }: ArtifactViewerProps) {
  const content = artifact.content_inline ?? '';
  const contentType = artifact.content_type;

  const renderContent = (): React.ReactNode => {
    if (!content) {
      return (
        <p className="py-4 text-center text-sm text-gray-500">
          No inline content available.{' '}
          {artifact.storage_path && (
            <span className="font-mono text-xs">{artifact.storage_path}</span>
          )}
        </p>
      );
    }

    // Mermaid diagram
    if (contentType === 'mermaid') {
      return <MermaidDiagram definition={content} />;
    }

    // Markdown — render in a styled pre block (no external markdown library required)
    if (contentType === 'text/markdown') {
      return (
        <pre className="whitespace-pre-wrap rounded-lg border border-gray-700 bg-gray-900 p-4 text-sm text-gray-200 font-sans leading-relaxed overflow-auto">
          {content}
        </pre>
      );
    }

    // JSON — formatted with syntax highlighting via Tailwind classes
    if (contentType === 'application/json') {
      const formatted = tryFormatJson(content);
      return (
        <pre className="overflow-auto rounded-lg border border-gray-700 bg-gray-900 p-4 text-xs text-green-300 font-mono leading-relaxed">
          {formatted ?? content}
        </pre>
      );
    }

    // Plain text / fallback
    return (
      <pre className="overflow-auto whitespace-pre-wrap rounded-lg border border-gray-700 bg-gray-900 p-4 text-sm text-gray-300 font-mono leading-relaxed">
        {content}
      </pre>
    );
  };

  return (
    <article className="flex flex-col gap-3" aria-label={`Artifact ${artifact.id}`}>
      {/* Artifact header */}
      <header className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-gray-700/50 bg-gray-800/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-gray-500" aria-hidden="true" />
          <span className="text-xs font-mono text-gray-400">{artifact.id}</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
          {formatDate(artifact.created_at)}
        </div>
        <span className="rounded-full border border-gray-600 bg-gray-700 px-2 py-0.5 text-xs text-gray-300">
          {contentType}
        </span>
      </header>

      {/* Content */}
      {renderContent()}
    </article>
  );
}
