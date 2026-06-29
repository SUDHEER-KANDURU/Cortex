// =============================================================================
// MermaidDiagram — Renders a Mermaid diagram definition using react-mermaid2
// Handles loading state and invalid definition errors gracefully.
// =============================================================================

'use client';

import React, { useState } from 'react';
import Mermaid from 'react-mermaid2';
import { AlertTriangle } from 'lucide-react';
import LoadingSpinner from '@/components/shared/LoadingSpinner';

export interface MermaidDiagramProps {
  /** Raw Mermaid diagram definition string */
  definition: string;
}

// Dark theme configuration passed to Mermaid
const MERMAID_CONFIG = {
  theme: 'dark',
  themeVariables: {
    background: '#0f172a',
    primaryColor: '#1e293b',
    primaryTextColor: '#e2e8f0',
    primaryBorderColor: '#475569',
    lineColor: '#64748b',
    secondaryColor: '#1e293b',
    tertiaryColor: '#0f172a',
  },
  securityLevel: 'loose',
  fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
} as const;

/** Minimal error boundary to catch react-mermaid2 rendering errors */
class MermaidErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; errorMessage: string }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, errorMessage: error.message };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-start gap-2 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4 text-sm text-yellow-400">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">Invalid diagram definition</p>
            <p className="mt-1 text-yellow-400/80 text-xs font-mono break-all">
              {this.state.errorMessage}
            </p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function MermaidDiagram({ definition }: MermaidDiagramProps) {
  const [isRendered, setIsRendered] = useState(false);

  return (
    <div className="relative w-full overflow-auto rounded-lg border border-gray-700 bg-gray-900 p-4">
      {!isRendered && (
        <div className="flex justify-center py-6">
          <LoadingSpinner label="Rendering diagram…" />
        </div>
      )}

      <div
        // Hide until rendered to avoid flash of unstyled content
        className={isRendered ? 'block' : 'invisible h-0 overflow-hidden'}
        onLoad={() => setIsRendered(true)}
      >
        <MermaidErrorBoundary>
          <Mermaid
            chart={definition}
            config={MERMAID_CONFIG}
            // react-mermaid2 calls this when rendering completes
            onRenderComplete={() => setIsRendered(true)}
          />
        </MermaidErrorBoundary>
      </div>
    </div>
  );
}
