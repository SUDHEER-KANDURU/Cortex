// =============================================================================
// NavigatePanel — Full-depth code exploration panel
// Shows: definition, callers, callees, dependencies, dependents, related modules,
//        tests, insights, source, explain. Supports navigation modes, breadcrumb,
//        back/forward history.
// =============================================================================

'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft, ArrowRight, Search, Code2, GitBranch, Layers,
  ArrowUpRight, ArrowDownRight, AlertTriangle, Zap,
  Activity, Hash, ChevronRight, TestTube2,
  Target, Compass, Eye, Sparkles, X,
  MessageSquare,
} from 'lucide-react';
import type { GraphNode } from '@/types';
import { useIsMobile } from '@/lib/utils/useBreakpoint';
import { useNavigate } from '../hooks/useNavigate';
import type { ConnectedNode, NavigationMode, CallPath, NavigateResponse, NavigateExplainResponse } from '@/lib/api/navigate.api';

// ─── Props ───────────────────────────────────────────────────────────────────

interface NavigatePanelProps {
  jobId: string;
  nodes: GraphNode[];
  /** Optional: pre-select a node on mount */
  initialNodeId?: string;
}

// ─── Navigation Mode Config ──────────────────────────────────────────────────

const MODE_CONFIG: Record<NavigationMode, { label: string; icon: React.ReactNode; description: string }> = {
  overview:     { label: 'Overview',     icon: <Eye style={{ width: 12, height: 12 }} />,           description: 'Everything known about this — all relations at once.' },
  upstream:     { label: 'Upstream',     icon: <ArrowDownRight style={{ width: 12, height: 12 }} />, description: 'What leads to this?' },
  downstream:   { label: 'Downstream',   icon: <ArrowUpRight style={{ width: 12, height: 12 }} />,  description: 'What does this affect?' },
  call_path:    { label: 'Call Path',    icon: <GitBranch style={{ width: 12, height: 12 }} />,     description: 'How does execution reach this?' },
  dependencies: { label: 'Dependencies', icon: <Layers style={{ width: 12, height: 12 }} />,        description: 'What does this rely on?' },
  impact:       { label: 'Impact',       icon: <Target style={{ width: 12, height: 12 }} />,        description: 'What might break if this changes?' },
  source:       { label: 'Source',       icon: <Code2 style={{ width: 12, height: 12 }} />,         description: 'Show the actual code.' },
  chat:         { label: 'Chat',         icon: <MessageSquare style={{ width: 12, height: 12 }} />, description: 'Ask questions and dig deep into this entity.' },
};

// ─── Node Type Icons ─────────────────────────────────────────────────────────

const NODE_ICONS: Record<string, string> = {
  Repository: '📦', Module: '📁', File: '📄', Function: 'ƒ',
  Class: '🔷', Method: '⚡', Interface: '🔶', Enum: '📋',
  Endpoint: '🌐', Test: '🧪', Constant: '🔒', Pattern: '🧩',
};

function nodeIcon(nodeType: string) {
  return NODE_ICONS[nodeType] || '•';
}

// ─── Severity Colors ─────────────────────────────────────────────────────────

function severityColor(severity: string): string {
  switch (severity) {
    case 'critical': return '#ef4444';
    case 'high':     return '#f97316';
    case 'medium':   return '#eab308';
    case 'low':      return '#22c55e';
    default:         return 'var(--text-muted)';
  }
}

function statusBadge(status: string): { label: string; color: string } {
  switch (status) {
    case 'detected':    return { label: 'Detected', color: '#22c55e' };
    case 'inferred':    return { label: 'Inferred', color: '#eab308' };
    case 'unavailable': return { label: 'Unavailable', color: 'var(--text-muted)' };
    default:            return { label: status, color: 'var(--text-muted)' };
  }
}

// =============================================================================
// COMPONENT
// =============================================================================

export default function NavigatePanel({ jobId, nodes, initialNodeId }: NavigatePanelProps) {
  const nav = useNavigate(jobId);
  const isMobile = useIsMobile();
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(!initialNodeId);

  // Auto-navigate on mount if initialNodeId provided
  useEffect(() => {
    if (initialNodeId && !nav.current) {
      nav.navigateTo(initialNodeId);
      setShowSearch(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialNodeId]);

  // Filtered node list for the search panel
  const filteredNodes = useMemo(() => {
    const selectable = nodes.filter(n => n.node_type !== 'Repository');
    if (!searchQuery) return selectable.slice(0, 30);
    const q = searchQuery.toLowerCase();
    return selectable.filter(n =>
      n.label.toLowerCase().includes(q) ||
      ((n.properties.file as string) || '').toLowerCase().includes(q) ||
      n.node_type.toLowerCase().includes(q)
    ).slice(0, 30);
  }, [nodes, searchQuery]);

  const handleSelectNode = useCallback((node: GraphNode) => {
    nav.navigateTo(node.id);
    setShowSearch(false);
  }, [nav]);

  const handleNavigateConnected = useCallback((id: string) => {
    nav.navigateTo(id);
    setShowSearch(false);
  }, [nav]);

  // Load impact when switching to impact mode
  useEffect(() => {
    if (nav.mode === 'impact' && nav.current && !nav.impact && !nav.isLoadingImpact) {
      nav.loadImpact();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nav.mode, nav.current?.id]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 0 }}>
      {/* ── Toolbar ──────────────────────────────────────────────────────── */}
      <NavigateToolbar
        nav={nav}
        showSearch={showSearch}
        onToggleSearch={() => setShowSearch(s => !s)}
      />

      {/* ── Main Content ─────────────────────────────────────────────────── */}
      {/* On mobile the search panel and content stack as full-width views (only
          one shown at a time). On desktop they sit side-by-side as before. */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        {/* Search panel (left column on desktop, full-width overlay on mobile) */}
        {showSearch && (
          <SearchPanel
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            filteredNodes={filteredNodes}
            onSelect={handleSelectNode}
            selectedId={nav.current?.id}
            fullWidth={isMobile}
          />
        )}

        {/* Navigation content — hidden on mobile while the search panel is open */}
        {nav.current && !nav.isLoading && !(isMobile && showSearch) && (
          <div className="dash-scroll" style={{ flex: 1, overflow: 'auto', padding: '16px 20px' }}>
            {/* Breadcrumb */}
            <Breadcrumb
              items={nav.current.breadcrumb}
              onNavigate={handleNavigateConnected}
            />

            {/* Entity Header */}
            <EntityHeader data={nav.current} />

            {/* Mode Tabs */}
            <ModeTabs mode={nav.mode} onSetMode={nav.setMode} />

            {/* Mode Content */}
            <ModeContent
              nav={nav}
              onNavigate={handleNavigateConnected}
            />
          </div>
        )}

        {/* Loading state */}
        {nav.isLoading && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div className="cortex-pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)' }} />
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Loading navigation context...</span>
            </div>
          </div>
        )}

        {/* Error state */}
        {nav.error && !nav.isLoading && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
            <p style={{ fontSize: 13, color: '#ef4444' }}>{nav.error}</p>
          </div>
        )}

        {/* Empty state */}
        {!nav.current && !nav.isLoading && !nav.error && !showSearch && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
            <Compass style={{ width: 28, height: 28, color: 'var(--text-muted)' }} />
            <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center' }}>
              Select an entity to explore how it fits into the system
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

// ── Toolbar ──────────────────────────────────────────────────────────────────

function NavigateToolbar({
  nav,
  showSearch,
  onToggleSearch,
}: {
  nav: ReturnType<typeof useNavigate>;
  showSearch: boolean;
  onToggleSearch: () => void;
}) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px',
      borderBottom: '0.5px solid rgba(255,255,255,0.3)',
      background: 'rgba(255,255,255,0.15)',
    }}>
      {/* Back/Forward */}
      <button
        type="button"
        onClick={nav.goBack}
        disabled={!nav.canGoBack}
        title="Go back"
        style={{
          ...iconBtnStyle,
          opacity: nav.canGoBack ? 1 : 0.3,
          cursor: nav.canGoBack ? 'pointer' : 'default',
        }}
      >
        <ArrowLeft style={{ width: 14, height: 14 }} />
      </button>
      <button
        type="button"
        onClick={nav.goForward}
        disabled={!nav.canGoForward}
        title="Go forward"
        style={{
          ...iconBtnStyle,
          opacity: nav.canGoForward ? 1 : 0.3,
          cursor: nav.canGoForward ? 'pointer' : 'default',
        }}
      >
        <ArrowRight style={{ width: 14, height: 14 }} />
      </button>

      {/* Search toggle */}
      <button
        type="button"
        onClick={onToggleSearch}
        title={showSearch ? 'Hide search' : 'Search entities'}
        style={{
          ...iconBtnStyle,
          background: showSearch ? 'var(--primary-dim)' : 'transparent',
        }}
      >
        <Search style={{ width: 13, height: 13 }} />
      </button>

      {/* Current entity label */}
      {nav.current && (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 6, marginLeft: 8, overflow: 'hidden' }}>
          <span style={{ fontSize: 11, opacity: 0.7 }}>{nodeIcon(nav.current.node_type)}</span>
          <span style={{
            fontSize: 12, fontWeight: 600, color: 'var(--text)',
            fontFamily: 'var(--font-mono)', overflow: 'hidden',
            textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {nav.current.label}
          </span>
        </div>
      )}

      {/* Explain button */}
      {nav.current && (
        <button
          type="button"
          onClick={() => nav.loadExplanation()}
          disabled={nav.isLoadingExplain}
          title="Explain this entity (AI)"
          style={{ ...iconBtnStyle, gap: 4, padding: '4px 8px' }}
        >
          <Sparkles style={{ width: 12, height: 12, color: 'var(--primary)' }} />
          <span style={{ fontSize: 10, fontWeight: 600 }}>Explain</span>
        </button>
      )}
    </div>
  );
}

// ── Search Panel ─────────────────────────────────────────────────────────────

function SearchPanel({
  searchQuery,
  onSearchChange,
  filteredNodes,
  onSelect,
  selectedId,
  fullWidth,
}: {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  filteredNodes: GraphNode[];
  onSelect: (n: GraphNode) => void;
  selectedId?: string;
  fullWidth?: boolean;
}) {
  return (
    <div style={{
      width: fullWidth ? '100%' : 240,
      minWidth: fullWidth ? 0 : 240,
      flex: fullWidth ? 1 : undefined,
      borderRight: fullWidth ? 'none' : '0.5px solid rgba(255,255,255,0.3)',
      display: 'flex', flexDirection: 'column', background: 'rgba(255,255,255,0.08)',
    }}>
      {/* Search input */}
      <div style={{ padding: '8px 10px' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '5px 8px',
          borderRadius: 6, background: 'rgba(255,255,255,0.25)',
          border: '0.5px solid rgba(255,255,255,0.35)',
        }}>
          <Search style={{ width: 11, height: 11, color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={e => onSearchChange(e.target.value)}
            placeholder="Search entities..."
            style={{
              flex: 1, border: 'none', outline: 'none', background: 'transparent',
              fontSize: 11, color: 'var(--text)', fontFamily: 'var(--font-mono)',
            }}
          />
          {searchQuery && (
            <button type="button" onClick={() => onSearchChange('')} style={{ ...iconBtnStyle, padding: 2 }}>
              <X style={{ width: 10, height: 10 }} />
            </button>
          )}
        </div>
      </div>

      {/* Node list */}
      <div className="dash-scroll" style={{ flex: 1, overflow: 'auto', padding: '0 6px 8px' }}>
        {filteredNodes.map(node => (
          <button
            key={node.id}
            type="button"
            onClick={() => onSelect(node)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, width: '100%',
              padding: '5px 8px', borderRadius: 6, border: 'none', cursor: 'pointer',
              textAlign: 'left', transition: 'background 0.1s',
              background: selectedId === node.id ? 'var(--primary-dim)' : 'transparent',
            }}
            onMouseEnter={e => { if (selectedId !== node.id) e.currentTarget.style.background = 'rgba(255,255,255,0.2)'; }}
            onMouseLeave={e => { if (selectedId !== node.id) e.currentTarget.style.background = 'transparent'; }}
          >
            <span style={{ fontSize: 11, width: 16, textAlign: 'center' }}>{nodeIcon(node.node_type)}</span>
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{
                fontSize: 10.5, color: 'var(--text)', fontFamily: 'var(--font-mono)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {node.label}
              </div>
              {typeof node.properties.file === 'string' && node.properties.file && (
                <div style={{ fontSize: 9, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {node.properties.file.split('/').slice(-2).join('/')}
                </div>
              )}
            </div>
          </button>
        ))}
        {filteredNodes.length === 0 && (
          <p style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', padding: '20px 0' }}>
            No matching entities
          </p>
        )}
      </div>
    </div>
  );
}

// ── Breadcrumb ───────────────────────────────────────────────────────────────

function Breadcrumb({
  items,
  onNavigate,
}: {
  items: ConnectedNode[];
  onNavigate: (id: string) => void;
}) {
  if (!items.length) return null;

  return (
    <nav aria-label="Navigation breadcrumb" style={{
      display: 'flex', alignItems: 'center', gap: 2, marginBottom: 12,
      flexWrap: 'wrap',
    }}>
      {items.map((item, i) => (
        <React.Fragment key={item.id}>
          {i > 0 && <ChevronRight style={{ width: 10, height: 10, color: 'var(--text-muted)', flexShrink: 0 }} />}
          <button
            type="button"
            onClick={() => { if (i < items.length - 1) onNavigate(item.id); }}
            disabled={i === items.length - 1}
            style={{
              fontSize: 10, padding: '2px 5px', borderRadius: 4, border: 'none',
              background: i === items.length - 1 ? 'var(--primary-dim)' : 'transparent',
              color: i === items.length - 1 ? 'var(--text)' : 'var(--text-muted)',
              cursor: i === items.length - 1 ? 'default' : 'pointer',
              fontFamily: 'var(--font-mono)', fontWeight: i === items.length - 1 ? 600 : 400,
              transition: 'background 0.1s',
            }}
            onMouseEnter={e => { if (i < items.length - 1) e.currentTarget.style.background = 'rgba(255,255,255,0.2)'; }}
            onMouseLeave={e => { if (i < items.length - 1) e.currentTarget.style.background = 'transparent'; }}
          >
            <span style={{ marginRight: 3 }}>{nodeIcon(item.node_type)}</span>
            {item.label}
          </button>
        </React.Fragment>
      ))}
    </nav>
  );
}

// ── Entity Header ────────────────────────────────────────────────────────────

function EntityHeader({ data }: { data: NavigateResponse }) {
  const ins = data.insights;

  return (
    <div style={{
      padding: '14px 16px', borderRadius: 10, marginBottom: 12,
      background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.45)',
    }}>
      {/* Type badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 16 }}>{nodeIcon(data.node_type)}</span>
        <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
          {data.node_type}
        </span>
        {ins.is_async && <Badge text="async" color="#8b5cf6" />}
        {ins.has_docstring && <Badge text="documented" color="#22c55e" />}
      </div>

      {/* Label */}
      <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)', margin: '0 0 4px', fontFamily: 'var(--font-mono)' }}>
        {data.label}
      </h2>

      {/* Source location */}
      {data.source.file_path && (
        <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '2px 0', fontFamily: 'var(--font-mono)' }}>
          {data.source.file_path}
          {data.source.line_start > 0 && `:${data.source.line_start}`}
          {data.source.line_end > 0 && data.source.line_end !== data.source.line_start && `–${data.source.line_end}`}
        </p>
      )}

      {/* Metrics row — show every metric that has a real (non-null) value.
          `!= null` keeps 0 visible (e.g. "Coupling In: 0") but still hides
          genuinely missing data. */}
      {(ins.complexity != null || ins.lines != null || ins.methods != null ||
        ins.parameters != null || ins.coupling_in != null || ins.coupling_out != null) && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
          {ins.complexity != null && <MetricChip icon={<Activity style={{ width: 10, height: 10 }} />} label="Complexity" value={ins.complexity} warn={ins.complexity >= 10} />}
          {ins.lines != null && <MetricChip icon={<Hash style={{ width: 10, height: 10 }} />} label="Lines" value={ins.lines} warn={ins.lines > 100} />}
          {ins.methods != null && <MetricChip icon={<Code2 style={{ width: 10, height: 10 }} />} label="Methods" value={ins.methods} warn={ins.methods > 12} />}
          {ins.parameters != null && <MetricChip icon={<Zap style={{ width: 10, height: 10 }} />} label="Params" value={ins.parameters} warn={ins.parameters > 5} />}
          {ins.coupling_in != null && <MetricChip icon={<ArrowDownRight style={{ width: 10, height: 10 }} />} label="Coupling In" value={ins.coupling_in} warn={ins.coupling_in >= 10} />}
          {ins.coupling_out != null && <MetricChip icon={<ArrowUpRight style={{ width: 10, height: 10 }} />} label="Coupling Out" value={ins.coupling_out} warn={ins.coupling_out >= 8} />}
        </div>
      )}

      {/* Risk factors */}
      {ins.risk_factors.length > 0 && (
        <div style={{ marginTop: 8, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {ins.risk_factors.map((risk, i) => (
            <span key={i} style={{
              fontSize: 9, padding: '2px 6px', borderRadius: 4,
              background: 'rgba(239,68,68,0.12)', color: '#ef4444',
              border: '0.5px solid rgba(239,68,68,0.25)',
            }}>
              ⚠️ {risk}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Mode Tabs ────────────────────────────────────────────────────────────────

function ModeTabs({ mode, onSetMode }: { mode: NavigationMode; onSetMode: (m: NavigationMode) => void }) {
  const modes = Object.entries(MODE_CONFIG) as [NavigationMode, typeof MODE_CONFIG[NavigationMode]][];

  return (
    <div style={{
      display: 'flex', gap: 2, marginBottom: 14, padding: '3px',
      borderRadius: 8, background: 'rgba(255,255,255,0.15)',
      border: '0.5px solid rgba(255,255,255,0.25)',
      overflowX: 'auto',
    }}>
      {modes.map(([key, cfg]) => {
        const isActive = mode === key;
        return (
          <button
            key={key}
            type="button"
            onClick={() => onSetMode(key)}
            title={cfg.description}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '5px 8px', borderRadius: 6, border: 'none',
              fontSize: 10, fontWeight: isActive ? 600 : 400,
              background: isActive ? 'rgba(255,255,255,0.4)' : 'transparent',
              color: isActive ? 'var(--text)' : 'var(--text-muted)',
              cursor: 'pointer', transition: 'all 0.15s', whiteSpace: 'nowrap',
            }}
          >
            {cfg.icon}
            {cfg.label}
          </button>
        );
      })}
    </div>
  );
}

// ── Mode Content ─────────────────────────────────────────────────────────────

function ModeContent({
  nav,
  onNavigate,
}: {
  nav: ReturnType<typeof useNavigate>;
  onNavigate: (id: string) => void;
}) {
  const data = nav.current;
  if (!data) return null;

  switch (nav.mode) {
    case 'overview': {
      // Show EVERYTHING known about this entity. Every section renders only
      // when it actually has data — nothing is hidden behind a sub-mode, and
      // empty/null sections are skipped so the view stays clean.
      const hasCallPaths =
        data.call_paths_upstream.length > 0 || data.call_paths_downstream.length > 0;
      const hasAnything =
        data.callers.length > 0 || data.callees.length > 0 ||
        data.dependencies.length > 0 || data.dependents.length > 0 ||
        data.contains.length > 0 || data.related_modules.length > 0 ||
        data.tests.length > 0 || hasCallPaths ||
        data.insights.issues.length > 0 || Boolean(data.source_snippet);

      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {data.callers.length > 0 && (
            <ConnectionSection
              title="Callers"
              subtitle="Who calls this"
              icon={<ArrowDownRight style={{ width: 13, height: 13, color: '#22c55e' }} />}
              nodes={data.callers}
              onNavigate={onNavigate}
              emptyText="No callers detected"
            />
          )}
          {data.callees.length > 0 && (
            <ConnectionSection
              title="Callees"
              subtitle="What this calls"
              icon={<ArrowUpRight style={{ width: 13, height: 13, color: '#f97316' }} />}
              nodes={data.callees}
              onNavigate={onNavigate}
              emptyText="No callees detected"
            />
          )}
          {data.dependencies.length > 0 && (
            <ConnectionSection
              title="Dependencies"
              subtitle="What this relies on (imports, inherits, implements)"
              icon={<Layers style={{ width: 13, height: 13, color: '#3b82f6' }} />}
              nodes={data.dependencies}
              onNavigate={onNavigate}
              emptyText="No dependencies detected"
            />
          )}
          {data.dependents.length > 0 && (
            <ConnectionSection
              title="Dependents"
              subtitle="Who depends on this"
              icon={<Layers style={{ width: 13, height: 13, color: '#8b5cf6' }} />}
              nodes={data.dependents}
              onNavigate={onNavigate}
              emptyText="No dependents detected"
            />
          )}
          {data.contains.length > 0 && (
            <ConnectionSection
              title="Contains"
              subtitle="Child entities"
              icon={<Layers style={{ width: 13, height: 13, color: 'var(--primary)' }} />}
              nodes={data.contains}
              onNavigate={onNavigate}
              emptyText="No children"
            />
          )}
          {data.related_modules.length > 0 && (
            <ConnectionSection
              title="Related Modules"
              subtitle="Nearby architectural components"
              icon={<GitBranch style={{ width: 13, height: 13, color: '#8b5cf6' }} />}
              nodes={data.related_modules}
              onNavigate={onNavigate}
              emptyText="No related modules"
            />
          )}
          {data.tests.length > 0 && (
            <ConnectionSection
              title="Tests"
              subtitle="Related test coverage"
              icon={<TestTube2 style={{ width: 13, height: 13, color: '#22c55e' }} />}
              nodes={data.tests}
              onNavigate={onNavigate}
              emptyText="No related tests detected"
            />
          )}
          {data.call_paths_upstream.length > 0 && (
            <CallPathSection
              title="Upstream Call Paths"
              paths={data.call_paths_upstream}
              onNavigate={onNavigate}
            />
          )}
          {data.call_paths_downstream.length > 0 && (
            <CallPathSection
              title="Downstream Call Paths"
              paths={data.call_paths_downstream}
              onNavigate={onNavigate}
            />
          )}
          {data.insights.issues.length > 0 && (
            <IssuesSection issues={data.insights.issues} />
          )}
          {data.source_snippet && (
            <SourceSection source={data.source} snippet={data.source_snippet} />
          )}
          {!hasAnything && (
            <EmptyState text="No connections, issues, or source detected for this entity yet." />
          )}
        </div>
      );
    }

    case 'upstream':
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <ConnectionSection
            title="Callers"
            subtitle="Who calls this"
            icon={<ArrowDownRight style={{ width: 13, height: 13, color: '#22c55e' }} />}
            nodes={data.callers}
            onNavigate={onNavigate}
            emptyText="No callers detected"
          />
          <ConnectionSection
            title="Dependents"
            subtitle="Who depends on this"
            icon={<Layers style={{ width: 13, height: 13, color: '#8b5cf6' }} />}
            nodes={data.dependents}
            onNavigate={onNavigate}
            emptyText="No dependents detected"
          />
          {data.call_paths_upstream.length > 0 && (
            <CallPathSection
              title="Upstream Call Paths"
              paths={data.call_paths_upstream}
              onNavigate={onNavigate}
            />
          )}
        </div>
      );

    case 'downstream':
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <ConnectionSection
            title="Callees"
            subtitle="What this calls"
            icon={<ArrowUpRight style={{ width: 13, height: 13, color: '#f97316' }} />}
            nodes={data.callees}
            onNavigate={onNavigate}
            emptyText="No callees detected"
          />
          <ConnectionSection
            title="Contains"
            subtitle="Child entities"
            icon={<Layers style={{ width: 13, height: 13, color: 'var(--primary)' }} />}
            nodes={data.contains}
            onNavigate={onNavigate}
            emptyText="No children"
          />
          {data.call_paths_downstream.length > 0 && (
            <CallPathSection
              title="Downstream Call Paths"
              paths={data.call_paths_downstream}
              onNavigate={onNavigate}
            />
          )}
        </div>
      );

    case 'call_path':
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {data.call_paths_upstream.length > 0 && (
            <CallPathSection
              title="How execution reaches this (upstream)"
              paths={data.call_paths_upstream}
              onNavigate={onNavigate}
            />
          )}
          {data.call_paths_downstream.length > 0 && (
            <CallPathSection
              title="What this triggers (downstream)"
              paths={data.call_paths_downstream}
              onNavigate={onNavigate}
            />
          )}
          {data.call_paths_upstream.length === 0 && data.call_paths_downstream.length === 0 && (
            <EmptyState text="No call paths detected for this entity" />
          )}
        </div>
      );

    case 'dependencies':
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <ConnectionSection
            title="Dependencies"
            subtitle="What this relies on (imports, inherits, implements)"
            icon={<Layers style={{ width: 13, height: 13, color: '#3b82f6' }} />}
            nodes={data.dependencies}
            onNavigate={onNavigate}
            emptyText="No dependencies detected"
          />
          <ConnectionSection
            title="Related Modules"
            subtitle="Nearby architectural components"
            icon={<GitBranch style={{ width: 13, height: 13, color: '#8b5cf6' }} />}
            nodes={data.related_modules}
            onNavigate={onNavigate}
            emptyText="No related modules"
          />
          <ConnectionSection
            title="Tests"
            subtitle="Related test coverage"
            icon={<TestTube2 style={{ width: 13, height: 13, color: '#22c55e' }} />}
            nodes={data.tests}
            onNavigate={onNavigate}
            emptyText="No related tests detected"
          />
        </div>
      );

    case 'impact':
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {nav.isLoadingImpact && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 16 }}>
              <div className="cortex-pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)' }} />
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Computing impact analysis...</span>
            </div>
          )}
          {nav.impact && (
            <ConnectionSection
              title={`Impact Analysis (${nav.impact.length} affected)`}
              subtitle="What might break if this changes"
              icon={<Target style={{ width: 13, height: 13, color: '#ef4444' }} />}
              nodes={nav.impact}
              onNavigate={onNavigate}
              emptyText="No downstream impact detected"
            />
          )}
          {/* Issues */}
          {data.insights.issues.length > 0 && (
            <IssuesSection issues={data.insights.issues} />
          )}
        </div>
      );

    case 'source':
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <SourceSection source={data.source} snippet={data.source_snippet} />
          {/* Also show insights here */}
          {data.insights.issues.length > 0 && (
            <IssuesSection issues={data.insights.issues} />
          )}
        </div>
      );

    default:
      return null;
  }
}

// ── Connection Section ───────────────────────────────────────────────────────

function ConnectionSection({
  title,
  subtitle,
  icon,
  nodes,
  onNavigate,
  emptyText,
}: {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  nodes: ConnectedNode[];
  onNavigate: (id: string) => void;
  emptyText: string;
}) {
  return (
    <div style={{
      padding: '10px 14px', borderRadius: 10,
      background: 'rgba(255,255,255,0.25)', border: '0.5px solid rgba(255,255,255,0.4)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        {icon}
        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text)' }}>{title}</span>
        <span style={{ fontSize: 9, color: 'var(--text-muted)', marginLeft: 4 }}>{subtitle}</span>
      </div>

      {nodes.length === 0 ? (
        <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '8px 0 0', fontStyle: 'italic' }}>{emptyText}</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 4 }}>
          {nodes.map(node => (
            <button
              key={node.id}
              type="button"
              onClick={() => onNavigate(node.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px',
                borderRadius: 6, border: 'none', background: 'transparent',
                cursor: 'pointer', textAlign: 'left', width: '100%',
                transition: 'background 0.1s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.25)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            >
              <span style={{ fontSize: 11, width: 16, textAlign: 'center', flexShrink: 0 }}>
                {nodeIcon(node.node_type)}
              </span>
              <span style={{
                fontSize: 11, color: 'var(--text)', fontFamily: 'var(--font-mono)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
              }}>
                {node.label}
              </span>
              {/* Relationship badge */}
              <span style={{
                fontSize: 8, padding: '1px 4px', borderRadius: 3,
                background: 'rgba(255,255,255,0.3)',
                color: 'var(--text-muted)', fontWeight: 500, flexShrink: 0,
              }}>
                {node.relationship}
              </span>
              {/* Status indicator */}
              {node.relationship_status !== 'detected' && (
                <span style={{
                  fontSize: 7, padding: '1px 3px', borderRadius: 3,
                  background: node.relationship_status === 'inferred' ? 'rgba(234,179,8,0.15)' : 'rgba(0,0,0,0.05)',
                  color: statusBadge(node.relationship_status).color,
                }}>
                  {statusBadge(node.relationship_status).label}
                </span>
              )}
              <ChevronRight style={{ width: 10, height: 10, color: 'var(--text-muted)', flexShrink: 0 }} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Call Path Section ─────────────────────────────────────────────────────────

function CallPathSection({
  title,
  paths,
  onNavigate,
}: {
  title: string;
  paths: CallPath[];
  onNavigate: (id: string) => void;
}) {
  return (
    <div style={{
      padding: '10px 14px', borderRadius: 10,
      background: 'rgba(255,255,255,0.25)', border: '0.5px solid rgba(255,255,255,0.4)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
        <GitBranch style={{ width: 13, height: 13, color: 'var(--primary)' }} />
        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text)' }}>{title}</span>
        <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>({paths.length} paths)</span>
      </div>

      {paths.slice(0, 5).map((path, pi) => (
        <div key={pi} style={{
          display: 'flex', alignItems: 'center', gap: 4, padding: '4px 0',
          flexWrap: 'wrap',
        }}>
          {path.nodes.map((node, ni) => (
            <React.Fragment key={node.id}>
              {ni > 0 && <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>→</span>}
              <button
                type="button"
                onClick={() => onNavigate(node.id)}
                style={{
                  fontSize: 10, padding: '2px 6px', borderRadius: 4, border: 'none',
                  background: ni === 0 ? 'var(--primary-dim)' : 'rgba(255,255,255,0.25)',
                  color: 'var(--text)', cursor: 'pointer', fontFamily: 'var(--font-mono)',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.4)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = ni === 0 ? 'var(--primary-dim)' : 'rgba(255,255,255,0.25)'; }}
              >
                {nodeIcon(node.node_type)} {node.label}
              </button>
            </React.Fragment>
          ))}
        </div>
      ))}
    </div>
  );
}

// ── Source Section ────────────────────────────────────────────────────────────

function SourceSection({ source, snippet }: { source: NavigateResponse['source']; snippet: string }) {
  return (
    <div style={{
      padding: '10px 14px', borderRadius: 10,
      background: 'rgba(255,255,255,0.25)', border: '0.5px solid rgba(255,255,255,0.4)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
        <Code2 style={{ width: 13, height: 13, color: 'var(--primary)' }} />
        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text)' }}>Source Location</span>
      </div>

      <div style={{
        padding: '8px 10px', borderRadius: 6,
        background: 'rgba(0,0,0,0.04)', fontFamily: 'var(--font-mono)', fontSize: 11,
      }}>
        {source.repository && <div style={{ color: 'var(--text-muted)', marginBottom: 2 }}>{source.repository}</div>}
        <div style={{ color: 'var(--text)' }}>
          {source.file_path || 'Unknown location'}
          {source.line_start > 0 && (
            <span style={{ color: 'var(--primary)' }}>
              :{source.line_start}
              {source.line_end > 0 && source.line_end !== source.line_start && `–${source.line_end}`}
            </span>
          )}
        </div>
        <div style={{ color: 'var(--text-muted)', marginTop: 2 }}>Symbol: {source.symbol_name}</div>
      </div>

      {snippet && (
        <pre style={{
          marginTop: 8, padding: '8px 10px', borderRadius: 6,
          background: 'rgba(0,0,0,0.06)', fontSize: 10,
          fontFamily: 'var(--font-mono)', color: 'var(--text)',
          overflow: 'auto', maxHeight: 200, whiteSpace: 'pre-wrap',
          border: '0.5px solid rgba(0,0,0,0.08)',
        }}>
          {snippet}
        </pre>
      )}

      {!snippet && source.file_path && (
        <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 6, fontStyle: 'italic' }}>
          Source snippet not available — open the file at the location above.
        </p>
      )}
    </div>
  );
}

// ── Issues Section ───────────────────────────────────────────────────────────

function IssuesSection({ issues }: { issues: NavigateResponse['insights']['issues'] }) {
  return (
    <div style={{
      padding: '10px 14px', borderRadius: 10,
      background: 'rgba(255,255,255,0.25)', border: '0.5px solid rgba(255,255,255,0.4)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
        <AlertTriangle style={{ width: 13, height: 13, color: '#f97316' }} />
        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text)' }}>Issues ({issues.length})</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {issues.map((issue, i) => (
          <div key={i} style={{
            padding: '6px 8px', borderRadius: 6,
            background: 'rgba(255,255,255,0.2)', border: '0.5px solid rgba(255,255,255,0.3)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
              <span style={{
                fontSize: 8, padding: '1px 4px', borderRadius: 3, fontWeight: 700,
                background: `${severityColor(issue.severity)}20`,
                color: severityColor(issue.severity),
                textTransform: 'uppercase',
              }}>
                {issue.severity}
              </span>
              <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text)' }}>{issue.title}</span>
            </div>
            <p style={{ fontSize: 10, color: 'var(--text-muted)', margin: '2px 0' }}>{issue.description}</p>
            {issue.recommendation && (
              <p style={{ fontSize: 9, color: '#22c55e', margin: '2px 0' }}>💡 {issue.recommendation}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Explain Panel (renders as overlay when explanation is loaded) ─────────────

// This is displayed inline when nav.explanation exists — integrated into ModeContent
// Actually, let's export it as part of the panel (shown below the mode content)
export function ExplainOverlay({
  explanation,
  isLoading,
  onClose,
}: {
  explanation: NavigateExplainResponse | null;
  isLoading: boolean;
  onClose: () => void;
}) {
  if (!explanation && !isLoading) return null;

  return (
    <div style={{
      margin: '12px 0', padding: '12px 14px', borderRadius: 10,
      background: 'rgba(139,92,246,0.06)', border: '0.5px solid rgba(139,92,246,0.2)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
        <Sparkles style={{ width: 13, height: 13, color: '#8b5cf6' }} />
        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text)' }}>AI Explanation</span>
        {explanation && (
          <span style={{ fontSize: 9, color: 'var(--text-muted)', marginLeft: 'auto' }}>
            Confidence: {Math.round(explanation.confidence * 100)}%
          </span>
        )}
        <button type="button" onClick={onClose} style={{ ...iconBtnStyle, marginLeft: 4 }}>
          <X style={{ width: 10, height: 10 }} />
        </button>
      </div>

      {isLoading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div className="cortex-pulse" style={{ width: 5, height: 5, borderRadius: '50%', background: '#8b5cf6' }} />
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Generating explanation...</span>
        </div>
      )}

      {explanation && (
        <div style={{ fontSize: 11, lineHeight: 1.6, color: 'var(--text)', whiteSpace: 'pre-wrap' }}>
          {explanation.explanation}
        </div>
      )}
    </div>
  );
}

// ── Small UI Components ──────────────────────────────────────────────────────

function Badge({ text, color }: { text: string; color: string }) {
  return (
    <span style={{
      fontSize: 8, padding: '1px 5px', borderRadius: 4, fontWeight: 600,
      background: `${color}15`, color, border: `0.5px solid ${color}30`,
    }}>
      {text}
    </span>
  );
}

function MetricChip({ icon, label, value, warn }: { icon: React.ReactNode; label: string; value: number; warn: boolean }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 4, padding: '3px 7px',
      borderRadius: 5, fontSize: 10,
      background: warn ? 'rgba(239,68,68,0.08)' : 'rgba(255,255,255,0.25)',
      border: `0.5px solid ${warn ? 'rgba(239,68,68,0.2)' : 'rgba(255,255,255,0.4)'}`,
      color: warn ? '#ef4444' : 'var(--text-muted)',
    }}>
      {icon}
      <span>{label}: <strong style={{ color: warn ? '#ef4444' : 'var(--text)' }}>{value}</strong></span>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '30px 20px',
    }}>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>{text}</p>
    </div>
  );
}

// ─── Shared Styles ────────────────────────────────────────────────────────────

const iconBtnStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  padding: 4, borderRadius: 4, border: 'none', background: 'transparent',
  color: 'var(--text-muted)', cursor: 'pointer', transition: 'background 0.1s',
};
