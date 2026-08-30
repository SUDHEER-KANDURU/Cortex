// =============================================================================
// CodeNavigator — Engineering investigation for a selected node
// Shows: purpose, source, dependencies, dependents, callers, callees,
//        complexity, issues, architectural role, related files
// =============================================================================

'use client';

import React, { useCallback, useState } from 'react';
import {
  Search, FileText, Code2, Zap, Layers, GitBranch,
  ArrowUpRight, ArrowDownRight, FolderTree, Activity,
  ChevronRight, Shield, BookOpen, Hash,
} from 'lucide-react';
import { getNodeDetail, type NodeDetailData } from '@/lib/api/navigation.api';
import { useIsCompact } from '@/lib/utils/useBreakpoint';
import type { GraphNode } from '@/types';

interface CodeNavigatorProps {
  jobId: string;
  nodes: GraphNode[];
}

export default function CodeNavigator({ jobId, nodes }: CodeNavigatorProps) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [detail, setDetail] = useState<NodeDetailData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const isCompact = useIsCompact();

  const selectableNodes = nodes.filter(n =>
    n.node_type !== 'Repository'
  );

  const filteredNodes = searchQuery
    ? selectableNodes.filter(n =>
        n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (n.properties.file as string || '').toLowerCase().includes(searchQuery.toLowerCase())
      ).slice(0, 25)
    : selectableNodes.slice(0, 25);

  const handleSelect = useCallback(async (node: GraphNode) => {
    setSelectedNode(node);
    setIsLoading(true);
    try {
      const data = await getNodeDetail(jobId, node.id);
      setDetail(data);
    } catch {
      setDetail(null);
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  // Navigate to a connected node
  const handleNavigateTo = useCallback((nodeId: string) => {
    const target = nodes.find(n => n.id === nodeId);
    if (target) handleSelect(target);
  }, [nodes, handleSelect]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: isCompact ? 'column' : 'row',
      gap: 16,
      minHeight: isCompact ? 0 : 400,
    }}>
      {/* Left panel — Node browser. Stacks on top (full width, capped height)
          on compact widths; fixed 260px column on desktop. */}
      <div style={{
        width: isCompact ? '100%' : 260,
        minWidth: isCompact ? 0 : 260,
        maxHeight: isCompact ? 260 : undefined,
        display: 'flex', flexDirection: 'column',
        padding: '12px', borderRadius: 12,
        background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.5)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px',
          borderRadius: 8, background: 'rgba(255,255,255,0.4)',
          border: '0.5px solid rgba(255,255,255,0.5)', marginBottom: 10,
        }}>
          <Search style={{ width: 11, height: 11, color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search symbols..."
            style={{
              flex: 1, border: 'none', outline: 'none', background: 'transparent',
              fontSize: 11, color: 'var(--text)', fontFamily: 'var(--font-mono)',
            }}
          />
        </div>

        <div className="dash-scroll" style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {filteredNodes.map((node) => (
            <button
              key={node.id}
              type="button"
              onClick={() => handleSelect(node)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '5px 8px', borderRadius: 6, cursor: 'pointer', width: '100%',
                background: selectedNode?.id === node.id ? 'var(--primary-dim)' : 'transparent',
                border: 'none', textAlign: 'left', transition: 'background 0.1s',
              }}
              onMouseEnter={(e) => { if (selectedNode?.id !== node.id) e.currentTarget.style.background = 'rgba(255,255,255,0.25)'; }}
              onMouseLeave={(e) => { if (selectedNode?.id !== node.id) e.currentTarget.style.background = 'transparent'; }}
            >
              <NodeIcon type={node.node_type} />
              <span style={{
                fontSize: 10.5, color: 'var(--text)', fontFamily: 'var(--font-mono)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
              }}>
                {node.label}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Right panel — Node detail */}
      <div style={{ flex: 1, minWidth: 0, minHeight: isCompact ? 200 : undefined }}>
        {!selectedNode && (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', height: '100%', minHeight: isCompact ? 200 : undefined,
            gap: 12, padding: '40px 20px',
          }}>
            <FolderTree style={{ width: 24, height: 24, color: 'var(--text-muted)' }} />
            <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center' }}>
              Select a node to investigate its engineering context
            </p>
          </div>
        )}

        {isLoading && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '40px 0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div className="cortex-pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)' }} />
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Loading node detail...</span>
            </div>
          </div>
        )}

        {detail && !isLoading && (
          <NodeDetailView detail={detail} onNavigate={handleNavigateTo} />
        )}
      </div>
    </div>
  );
}

// ── Node Detail View ──────────────────────────────────────────────────────────
function NodeDetailView({ detail, onNavigate }: { detail: NodeDetailData; onNavigate: (id: string) => void }) {
  const props = detail.properties;
  const filePath = (props.file as string) || (props.path as string) || '';
  const complexity = Number(props.cyclomatic || 0);
  const lines = Number(props.lines || 0);
  const methods = Number(props.methods || 0);
  const params = Number(props.parameters || 0);
  const isAsync = Boolean(props.is_async);
  const hasDocstring = Boolean(props.has_docstring);
  const route = props.route_info as string || '';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Header */}
      <div style={{
        padding: '14px 16px', borderRadius: 12,
        background: 'rgba(255,255,255,0.35)', border: '0.5px solid rgba(255,255,255,0.55)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <NodeIcon type={detail.node_type} size={16} />
          <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            {detail.node_type}
          </span>
          {isAsync && <Badge text="async" color="#8b5cf6" />}
          {hasDocstring && <Badge text="documented" color="#22c55e" />}
          {route && <Badge text={route} color="var(--primary)" />}
        </div>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)', margin: '0 0 4px', fontFamily: 'var(--font-mono)' }}>
          {detail.label}
        </h2>
        {filePath && (
          <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0, fontFamily: 'var(--font-mono)' }}>
            {filePath}
          </p>
        )}
        {detail.contained_by && (
          <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '4px 0 0' }}>
            Contained by: <strong>{detail.contained_by}</strong>
          </p>
        )}
      </div>

      {/* Metrics row */}
      {(complexity > 0 || lines > 0 || methods > 0 || params > 0) && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {complexity > 0 && <MetricChip icon={<Activity style={{ width: 10, height: 10 }} />} label="Complexity" value={complexity} warn={complexity >= 10} />}
          {lines > 0 && <MetricChip icon={<Hash style={{ width: 10, height: 10 }} />} label="Lines" value={lines} warn={lines > 100} />}
          {methods > 0 && <MetricChip icon={<Code2 style={{ width: 10, height: 10 }} />} label="Methods" value={methods} warn={methods > 12} />}
          {params > 0 && <MetricChip icon={<Zap style={{ width: 10, height: 10 }} />} label="Params" value={params} warn={params > 5} />}
        </div>
      )}

      {/* Callers (who calls/imports this) */}
      {detail.callers.length > 0 && (
        <ConnectionSection
          title="Dependencies (incoming)"
          subtitle="Who depends on this"
          icon={<ArrowDownRight style={{ width: 12, height: 12, color: '#22c55e' }} />}
          connections={detail.callers}
          onNavigate={onNavigate}
        />
      )}

      {/* Callees (what this calls/imports) */}
      {detail.callees.length > 0 && (
        <ConnectionSection
          title="Dependencies (outgoing)"
          subtitle="What this depends on"
          icon={<ArrowUpRight style={{ width: 12, height: 12, color: '#f97316' }} />}
          connections={detail.callees}
          onNavigate={onNavigate}
        />
      )}

      {/* Contains (children) */}
      {detail.contains.length > 0 && (
        <div style={{
          padding: '10px 14px', borderRadius: 10,
          background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.5)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <FolderTree style={{ width: 12, height: 12, color: 'var(--primary)' }} />
            <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              Contains ({detail.contains.length})
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {detail.contains.slice(0, 15).map((child) => (
              <button
                key={child.id}
                type="button"
                onClick={() => onNavigate(child.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px',
                  borderRadius: 6, background: 'transparent', border: 'none',
                  cursor: 'pointer', textAlign: 'left', transition: 'background 0.1s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.3)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                <NodeIcon type={child.type} />
                <span style={{ fontSize: 11, color: 'var(--text)', fontFamily: 'var(--font-mono)' }}>
                  {child.label}
                </span>
                <ChevronRight style={{ width: 10, height: 10, color: 'var(--text-muted)', marginLeft: 'auto' }} />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Architectural role inference */}
      <ArchitecturalRole detail={detail} />
    </div>
  );
}

// ── Connection Section ────────────────────────────────────────────────────────
function ConnectionSection({ title, subtitle, icon, connections, onNavigate }: {
  title: string; subtitle: string; icon: React.ReactNode;
  connections: { id: string; label: string; type: string; relationship: string }[];
  onNavigate: (id: string) => void;
}) {
  return (
    <div style={{
      padding: '10px 14px', borderRadius: 10,
      background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.5)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
        {icon}
        <div>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            {title} ({connections.length})
          </span>
          <span style={{ fontSize: 9, color: 'var(--text-muted)', marginLeft: 6 }}>{subtitle}</span>
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {connections.slice(0, 12).map((conn) => (
          <button
            key={conn.id}
            type="button"
            onClick={() => onNavigate(conn.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px',
              borderRadius: 6, background: 'transparent', border: 'none',
              cursor: 'pointer', textAlign: 'left', width: '100%', transition: 'background 0.1s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.3)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
          >
            <NodeIcon type={conn.type} />
            <span style={{ fontSize: 11, color: 'var(--text)', fontFamily: 'var(--font-mono)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {conn.label}
            </span>
            <span style={{ fontSize: 9, color: 'var(--text-muted)', padding: '1px 5px', borderRadius: 4, background: 'rgba(255,255,255,0.3)' }}>
              {conn.relationship}
            </span>
            <ChevronRight style={{ width: 10, height: 10, color: 'var(--text-muted)' }} />
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Architectural Role ────────────────────────────────────────────────────────
function ArchitecturalRole({ detail }: { detail: NodeDetailData }) {
  const props = detail.properties;
  const filePath = ((props.file as string) || (props.path as string) || '').toLowerCase();
  const label = detail.label.toLowerCase();

  // Infer role from naming and location
  const roles: string[] = [];

  if (filePath.includes('domain') || filePath.includes('entities') || filePath.includes('model')) {
    roles.push('Domain Layer — defines core business concepts');
  }
  if (filePath.includes('application') || filePath.includes('service') || filePath.includes('use_case')) {
    roles.push('Application Layer — orchestrates business operations');
  }
  if (filePath.includes('infrastructure') || filePath.includes('repository') || filePath.includes('persistence')) {
    roles.push('Infrastructure Layer — connects to external systems');
  }
  if (filePath.includes('presentation') || filePath.includes('router') || filePath.includes('controller')) {
    roles.push('Presentation Layer — handles HTTP/API concerns');
  }
  if (label.includes('test') || filePath.includes('test')) {
    roles.push('Test — verifies behavior of production code');
  }
  if (detail.node_type === 'Endpoint') {
    roles.push('API Endpoint — public interface of the system');
  }
  if (detail.callers.length >= 5) {
    roles.push(`Critical Hub — ${detail.callers.length} other nodes depend on this`);
  }
  if (detail.callees.length >= 5) {
    roles.push(`High Coupling — depends on ${detail.callees.length} other nodes`);
  }

  if (roles.length === 0) return null;

  return (
    <div style={{
      padding: '10px 14px', borderRadius: 10,
      background: 'var(--primary-dim)', border: '0.5px solid rgba(255,255,255,0.4)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        <BookOpen style={{ width: 12, height: 12, color: 'var(--primary)' }} />
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--primary)' }}>
          Architectural Role
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {roles.map((role, i) => (
          <p key={i} style={{ fontSize: 11, color: 'var(--text)', margin: 0, lineHeight: 1.5 }}>
            • {role}
          </p>
        ))}
      </div>
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function NodeIcon({ type, size = 10 }: { type: string; size?: number }) {
  const style = { width: size, height: size, color: 'var(--text-muted)', flexShrink: 0 };
  switch (type) {
    case 'File': return <FileText style={style} />;
    case 'Class': return <Code2 style={style} />;
    case 'Interface': return <Shield style={style} />;
    case 'Function': case 'Method': return <Zap style={style} />;
    case 'Endpoint': return <GitBranch style={style} />;
    case 'Module': return <Layers style={style} />;
    default: return <FolderTree style={style} />;
  }
}

function Badge({ text, color }: { text: string; color: string }) {
  return (
    <span style={{
      fontSize: 9, padding: '2px 6px', borderRadius: 4,
      background: `${color}12`, border: `0.5px solid ${color}30`,
      color, fontWeight: 600, fontFamily: 'var(--font-mono)',
    }}>
      {text}
    </span>
  );
}

function MetricChip({ icon, label, value, warn }: {
  icon: React.ReactNode; label: string; value: number; warn?: boolean;
}) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px',
      borderRadius: 8,
      background: warn ? 'rgba(249,115,22,0.05)' : 'rgba(255,255,255,0.3)',
      border: `0.5px solid ${warn ? 'rgba(249,115,22,0.2)' : 'rgba(255,255,255,0.5)'}`,
    }}>
      <span style={{ color: warn ? '#f97316' : 'var(--text-muted)' }}>{icon}</span>
      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{label}:</span>
      <span style={{ fontSize: 11, fontWeight: 700, color: warn ? '#f97316' : 'var(--text)' }}>{value}</span>
    </div>
  );
}
