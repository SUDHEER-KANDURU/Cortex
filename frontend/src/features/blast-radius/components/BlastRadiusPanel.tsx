// =============================================================================
// BlastRadiusPanel — "What happens if I change this?"
// Shows impact graph, risk assessment, affected modules and tests
// =============================================================================

'use client';

import React, { useCallback, useState } from 'react';
import {
  Zap, AlertTriangle,
  Search, FileText, Code2, GitBranch,
} from 'lucide-react';
import { getBlastRadius, type BlastRadiusData, type BlastRadiusNode } from '@/lib/api/blast-radius.api';
import type { GraphNode } from '@/types';

interface BlastRadiusPanelProps {
  jobId: string;
  nodes: GraphNode[];
}

export default function BlastRadiusPanel({ jobId, nodes }: BlastRadiusPanelProps) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [result, setResult] = useState<BlastRadiusData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Filter nodes for selection (only files, classes, functions)
  const selectableNodes = nodes.filter(n =>
    n.node_type !== 'Repository' &&
    n.node_type !== 'Module' &&
    n.label !== '__init__'
  );

  const filteredNodes = searchQuery
    ? selectableNodes.filter(n =>
        n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (n.properties.file as string || '').toLowerCase().includes(searchQuery.toLowerCase())
      )
    : selectableNodes.slice(0, 20);

  const handleNodeSelect = useCallback(async (node: GraphNode) => {
    setSelectedNode(node);
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await getBlastRadius(jobId, node.id);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compute blast radius');
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  const riskColors = {
    low: { bg: 'rgba(34,197,94,0.06)', border: 'rgba(34,197,94,0.2)', text: '#22c55e' },
    medium: { bg: 'rgba(234,179,8,0.06)', border: 'rgba(234,179,8,0.2)', text: '#eab308' },
    high: { bg: 'rgba(249,115,22,0.06)', border: 'rgba(249,115,22,0.2)', text: '#f97316' },
    critical: { bg: 'rgba(239,68,68,0.06)', border: 'rgba(239,68,68,0.2)', text: '#ef4444' },
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '14px 16px',
        borderRadius: 12, background: 'rgba(255,255,255,0.35)',
        border: '0.5px solid rgba(255,255,255,0.55)',
      }}>
        <Zap style={{ width: 16, height: 16, color: 'var(--primary)' }} />
        <div>
          <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', margin: 0 }}>
            Blast Radius
          </p>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>
            Select a node to see what would be affected by a change
          </p>
        </div>
      </div>

      {/* Node Selector */}
      <div style={{
        padding: '12px 14px', borderRadius: 12,
        background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.5)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '6px 10px', borderRadius: 8,
          background: 'rgba(255,255,255,0.4)', border: '0.5px solid rgba(255,255,255,0.5)',
          marginBottom: 10,
        }}>
          <Search style={{ width: 12, height: 12, color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search files, classes, functions..."
            style={{
              flex: 1, border: 'none', outline: 'none', background: 'transparent',
              fontSize: 12, color: 'var(--text)', fontFamily: 'var(--font-sans)',
            }}
          />
        </div>

        <div style={{ maxHeight: 160, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 3 }}>
          {filteredNodes.map((node) => (
            <button
              key={node.id}
              type="button"
              onClick={() => handleNodeSelect(node)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 10px', borderRadius: 8, cursor: 'pointer',
                background: selectedNode?.id === node.id ? 'var(--primary-dim)' : 'transparent',
                border: selectedNode?.id === node.id ? '0.5px solid rgba(255,255,255,0.5)' : '0.5px solid transparent',
                textAlign: 'left', width: '100%', transition: 'all 0.1s ease',
              }}
              onMouseEnter={(e) => { if (selectedNode?.id !== node.id) e.currentTarget.style.background = 'rgba(255,255,255,0.2)'; }}
              onMouseLeave={(e) => { if (selectedNode?.id !== node.id) e.currentTarget.style.background = 'transparent'; }}
            >
              <NodeTypeIcon type={node.node_type} />
              <span style={{ fontSize: 11, color: 'var(--text)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {node.label}
              </span>
              <span style={{ fontSize: 9, color: 'var(--text-muted)', marginLeft: 'auto', flexShrink: 0 }}>
                {node.node_type}
              </span>
            </button>
          ))}
          {filteredNodes.length === 0 && (
            <p style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', padding: '12px 0' }}>
              No matching nodes
            </p>
          )}
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '30px 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className="cortex-pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)' }} />
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Computing blast radius...</span>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ padding: '12px 14px', borderRadius: 10, background: 'rgba(239,68,68,0.06)', border: '0.5px solid rgba(239,68,68,0.2)' }}>
          <p style={{ fontSize: 12, color: '#ef4444', margin: 0 }}>{error}</p>
        </div>
      )}

      {/* Results */}
      {result && !isLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Risk Assessment */}
          <div style={{
            padding: '14px 16px', borderRadius: 12,
            background: riskColors[result.risk_level as keyof typeof riskColors]?.bg || riskColors.low.bg,
            border: `0.5px solid ${riskColors[result.risk_level as keyof typeof riskColors]?.border || riskColors.low.border}`,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <AlertTriangle style={{
                width: 14, height: 14,
                color: riskColors[result.risk_level as keyof typeof riskColors]?.text || riskColors.low.text,
              }} />
              <span style={{
                fontSize: 12, fontWeight: 700, textTransform: 'uppercase',
                color: riskColors[result.risk_level as keyof typeof riskColors]?.text || riskColors.low.text,
              }}>
                {result.risk_level} Risk — Score {result.risk_score}/100
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {result.risk_factors.map((factor, i) => (
                <p key={i} style={{ fontSize: 11, color: 'var(--text)', margin: 0, paddingLeft: 22 }}>
                  • {factor}
                </p>
              ))}
            </div>
          </div>

          {/* Impact Summary */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(88px, 1fr))', gap: 8 }}>
            <ImpactStat label="Direct" value={result.direct_dependents.length} />
            <ImpactStat label="Transitive" value={result.transitive_dependents.length} />
            <ImpactStat label="Modules" value={result.affected_modules.length} />
            <ImpactStat label="Tests" value={result.affected_tests.length} />
          </div>

          {/* Impact Paths */}
          {result.impact_paths.length > 0 && (
            <div style={{
              padding: '12px 14px', borderRadius: 10,
              background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.5)',
            }}>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 8px' }}>
                Impact Paths
              </p>
              {result.impact_paths.map((path, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap',
                  padding: '4px 0',
                }}>
                  {path.map((segment, j) => (
                    <span key={j} style={{
                      fontSize: 10,
                      fontFamily: segment.startsWith('—') ? 'var(--font-sans)' : 'var(--font-mono)',
                      color: segment.startsWith('—') ? 'var(--text-muted)' : 'var(--text)',
                      fontWeight: j === 0 ? 700 : 400,
                    }}>
                      {segment}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          )}

          {/* Direct Dependents */}
          {result.direct_dependents.length > 0 && (
            <DependentList title="Direct Dependents" nodes={result.direct_dependents} />
          )}

          {/* Transitive */}
          {result.transitive_dependents.length > 0 && (
            <DependentList title="Transitive Dependents" nodes={result.transitive_dependents.slice(0, 15)} />
          )}

          {/* Affected Modules */}
          {result.affected_modules.length > 0 && (
            <div style={{
              padding: '10px 14px', borderRadius: 10,
              background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.5)',
            }}>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 6px' }}>
                Affected Modules
              </p>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {result.affected_modules.map((mod) => (
                  <span key={mod} style={{
                    fontSize: 10, padding: '3px 8px', borderRadius: 6,
                    background: 'rgba(249,115,22,0.06)', border: '0.5px solid rgba(249,115,22,0.2)',
                    color: '#f97316', fontFamily: 'var(--font-mono)', fontWeight: 600,
                  }}>
                    {mod}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Affected Tests */}
          {result.affected_tests.length > 0 && (
            <DependentList title="Tests to Verify" nodes={result.affected_tests} />
          )}
        </div>
      )}
    </div>
  );
}

// ── Helper components ─────────────────────────────────────────────────────────

function NodeTypeIcon({ type }: { type: string }) {
  const iconStyle = { width: 10, height: 10, color: 'var(--text-muted)' };
  switch (type) {
    case 'File': return <FileText style={iconStyle} />;
    case 'Class': return <Code2 style={iconStyle} />;
    case 'Function': return <Zap style={iconStyle} />;
    default: return <GitBranch style={iconStyle} />;
  }
}

function ImpactStat({ label, value }: { label: string; value: number }) {
  return (
    <div style={{
      padding: '10px 12px', borderRadius: 8, textAlign: 'center',
      background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.5)',
    }}>
      <p style={{ fontSize: 18, fontWeight: 800, color: 'var(--text)', margin: 0 }}>{value}</p>
      <p style={{ fontSize: 9, color: 'var(--text-muted)', margin: 0, fontWeight: 600 }}>{label}</p>
    </div>
  );
}

function DependentList({ title, nodes }: { title: string; nodes: BlastRadiusNode[] }) {
  return (
    <div style={{
      padding: '10px 14px', borderRadius: 10,
      background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.5)',
    }}>
      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 6px' }}>
        {title} ({nodes.length})
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {nodes.map((node) => (
          <div key={node.id} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              fontSize: 8, padding: '1px 4px', borderRadius: 3,
              background: 'rgba(255,255,255,0.3)', color: 'var(--text-muted)',
              fontWeight: 600, fontFamily: 'var(--font-mono)',
            }}>
              {node.node_type}
            </span>
            <span style={{ fontSize: 11, color: 'var(--text)', fontFamily: 'var(--font-mono)' }}>
              {node.label}
            </span>
            {node.file_path && (
              <span style={{ fontSize: 9, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                {node.file_path.split('/').pop()}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
