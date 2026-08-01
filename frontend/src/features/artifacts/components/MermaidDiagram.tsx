// =============================================================================
// MermaidDiagram — Renders a Mermaid diagram, fully theme-aware
// Reads data-theme from <html> to pick dark or neutral mermaid theme.
// =============================================================================

'use client';

import React from 'react';
import Mermaid from 'react-mermaid2';
import { InlineLoader } from '@/components/shared/BrandedLoader';
import ErrorAlert from '@/components/shared/ErrorAlert';

export interface MermaidDiagramProps {
  definition: string;
}

function getMermaidConfig() {
  const isDark =
    typeof document !== 'undefined'
      ? document.documentElement.getAttribute('data-theme') !== 'light'
      : true;
  return {
    theme: isDark ? 'dark' : 'neutral',
    themeVariables: { background: 'transparent' },
  };
}

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
      return <ErrorAlert title="Unable to render diagram" message={this.state.errorMessage} />;
    }
    return this.props.children;
  }
}

export default function MermaidDiagram({ definition }: MermaidDiagramProps) {
  const [isLoading, setIsLoading] = React.useState(true);
  const config = getMermaidConfig();

  React.useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 300);
    return () => clearTimeout(timer);
  }, [definition]);

  return (
    <div style={{
      position: 'relative', width: '100%', overflow: 'auto',
      borderRadius: 12,
      border: '1px solid var(--border)',
      background: 'var(--surface)',
      padding: '16px',
      transition: 'background 0.3s ease, border-color 0.3s ease',
    }}>
      {isLoading && (
        <InlineLoader stage="rendering_diagram" message="Rendering Diagram…" size={28} />
      )}
      <div className={isLoading ? 'invisible h-0 overflow-hidden' : 'block'}>
        <MermaidErrorBoundary>
          <Mermaid chart={definition} config={config} />
        </MermaidErrorBoundary>
      </div>
    </div>
  );
}
