'use client';
// =============================================================================
// ArchitectureDiagramPanel — Self-contained panel that fetches + renders
// the layered architecture diagram for a given job.
//
// Drop-in replacement for the Mermaid diagram on the job detail page
// when artifact_type === 'architecture_diagram'.
// =============================================================================

import React from 'react';
import { useDiagram } from '../hooks/useDiagram';
import ArchitectureDiagram from './ArchitectureDiagram';

interface ArchitectureDiagramPanelProps {
  jobId: string;
}

export default function ArchitectureDiagramPanel({ jobId }: ArchitectureDiagramPanelProps) {
  const {
    data,
    isLoading,
    error,
    drillToModule,
    drillToClass,
    goToSystem,
    goToModule,
  } = useDiagram(jobId);

  if (isLoading && !data) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: 400,
        color: '#6B7280',
        fontSize: 14,
        fontFamily: 'Inter, system-ui, sans-serif',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: 32,
            height: 32,
            border: '3px solid #E5E7EB',
            borderTopColor: '#3B82F6',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
            margin: '0 auto 12px',
          }} />
          Loading architecture diagram...
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        padding: 24,
        color: '#991B1B',
        background: '#FEF2F2',
        borderRadius: 8,
        fontSize: 13,
        fontFamily: 'Inter, system-ui, sans-serif',
      }}>
        <strong>Failed to load diagram:</strong> {error}
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div style={{
        padding: 24,
        color: '#6B7280',
        fontSize: 13,
        fontFamily: 'Inter, system-ui, sans-serif',
        textAlign: 'center',
      }}>
        No architecture data available for this job yet.
      </div>
    );
  }

  return (
    <div style={{
      width: '100%',
      height: 600,
      border: '1px solid #E5E7EB',
      borderRadius: 12,
      overflow: 'hidden',
      background: '#FFFFFF',
    }}>
      <ArchitectureDiagram
        data={data}
        onDrillModule={drillToModule}
        onDrillClass={drillToClass}
        onGoSystem={goToSystem}
        onGoModule={goToModule}
      />
    </div>
  );
}
