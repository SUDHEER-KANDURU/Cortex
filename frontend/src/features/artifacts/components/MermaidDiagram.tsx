// =============================================================================
// MermaidDiagram — Renders a Mermaid diagram definition using react-mermaid2
// Handles loading state and invalid definition errors gracefully.
// =============================================================================

'use client';

import React from 'react';
import Mermaid from 'react-mermaid2';
import { Skeleton } from '@/components/ui/skeleton';
import ErrorAlert from '@/components/shared/ErrorAlert';

export interface MermaidDiagramProps {
  /** Raw Mermaid diagram definition string */
  definition: string;
}

// Dark theme configuration passed to Mermaid
const MERMAID_CONFIG = {
  theme: 'dark',
  themeVariables: {
    background: 'transparent',
  },
};

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
        <ErrorAlert
          title="Unable to render diagram"
          message={this.state.errorMessage}
        />
      );
    }
    return this.props.children;
  }
}

export default function MermaidDiagram({ definition }: MermaidDiagramProps) {
  const [isLoading, setIsLoading] = React.useState(true);

  // react-mermaid2 v0.1.x renders synchronously after mount
  React.useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 300);
    return () => clearTimeout(timer);
  }, [definition]);

  return (
    <div className="relative w-full overflow-auto rounded-lg border border-gray-700 bg-gray-900 p-4">
      {isLoading && (
        <div className="space-y-2 py-4">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}
      <div className={isLoading ? 'invisible h-0 overflow-hidden' : 'block'}>
        <MermaidErrorBoundary>
          <Mermaid chart={definition} config={MERMAID_CONFIG} />
        </MermaidErrorBoundary>
      </div>
    </div>
  );
}
