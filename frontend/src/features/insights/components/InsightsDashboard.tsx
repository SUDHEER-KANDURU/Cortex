// =============================================================================
// InsightsDashboard — Engineering health report
//
// Design system:
//   - One neutral base palette: everything is text-muted / border / glass-card
//   - Severity color used in EXACTLY ONE place per card (left border only)
//   - Grade shown as a letter only — no color on scores, no colored bars
//   - Score bars are all the same single accent (--primary) — progress, not alarm
//   - No emoji in UI chrome; emoji only in category labels where it aids scanning
//   - Sections are separated by whitespace, not color blocks
// =============================================================================

'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import type {
  InsightsReport,
  HealthDimension,
  CodeIssue,
  IssueSeverity,
  IssueCategory,
} from '@/types';
import { exportInsightsMarkdown } from '@/lib/api/insights.api';
import { staggerFastContainer, staggerFastChild } from '@/lib/utils/motion';
import NavigateButton from '@/components/shared/NavigateButton';
import { emitNavigate } from '@/lib/navigate-events';

// Severity — solid pill colors for the badge, muted for border
const SEV: Record<IssueSeverity | 'default', string> = {
  critical: '#dc2626',
  high:     '#ea580c',
  medium:   '#d97706',
  low:      '#16a34a',
  info:     '#6b7280',
  default:  '#6b7280',
};

// Solid background for the badge pill
const SEV_BG: Record<string, string> = {
  critical: 'rgba(220,38,38,0.12)',
  high:     'rgba(234,88,12,0.12)',
  medium:   'rgba(217,119,6,0.12)',
  low:      'rgba(22,163,74,0.10)',
  info:     'rgba(107,114,128,0.10)',
  default:  'rgba(107,114,128,0.10)',
};

function sevColor(s: IssueSeverity): string {
  return SEV[s] ?? SEV.default;
}

function sevBg(s: IssueSeverity): string {
  return SEV_BG[s] ?? SEV_BG.default;
}

function sevLabel(s: IssueSeverity): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// Grade — muted, single accent for A, subtle steps for the rest
function gradeColor(g: string): string {
  switch (g) {
    case 'A': return 'var(--primary)';
    case 'B': return 'var(--primary)';
    case 'C': return 'var(--warning)';
    case 'D': return '#A06828';
    case 'F': return 'var(--danger)';
    default:  return 'var(--text-muted)';
  }
}

function gradeLabel(g: string): string {
  switch (g) {
    case 'A': return 'Excellent';
    case 'B': return 'Good';
    case 'C': return 'Fair';
    case 'D': return 'Poor';
    case 'F': return 'Critical';
    default:  return '';
  }
}

// ── Category labels ───────────────────────────────────────────────────────────

const CAT_LABEL: Record<string, string> = {
  complexity:    'Complexity',
  coupling:      'Coupling',
  size:          'Size',
  architecture:  'Architecture',
  documentation: 'Documentation',
  naming:        'Naming',
  duplication:   'Duplication',
  error_handling:'Error Handling',
};

function catLabel(c: string): string {
  return CAT_LABEL[c] ?? c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// ── Shared primitives ─────────────────────────────────────────────────────────

// A single neutral progress bar. Color is always --primary (teal/green).
// Score bars should communicate progress, not alarm levels.
function ScoreBar({ score, height = 5 }: { score: number; height?: number }) {
  return (
    <div style={{
      width: '100%', height, borderRadius: height,
      background: 'var(--border)', overflow: 'hidden',
    }}>
      <div style={{
        width: `${Math.max(0, Math.min(100, score))}%`,
        height: '100%',
        background: 'var(--primary)',
        borderRadius: height,
        opacity: 0.75,
        transition: 'width 0.6s cubic-bezier(0.16,1,0.3,1)',
      }} />
    </div>
  );
}

// Section label — reused throughout
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p style={{
      fontSize: 11, fontWeight: 600, color: 'var(--text-muted)',
      margin: '0 0 12px', textTransform: 'uppercase', letterSpacing: '0.1em',
    }}>
      {children}
    </p>
  );
}

// Inline pill — higher contrast
function Pill({ children, active }: { children: React.ReactNode; active?: boolean }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      fontSize: 11, padding: '3px 9px', borderRadius: 6,
      background: active ? 'rgba(0,0,0,0.06)' : 'rgba(0,0,0,0.04)',
      border: `1px solid ${active ? 'rgba(0,0,0,0.14)' : 'rgba(0,0,0,0.09)'}`,
      color: active ? 'var(--text)' : 'var(--text-secondary)',
      fontFamily: 'var(--font-mono)',
      whiteSpace: 'nowrap',
    }}>
      {children}
    </span>
  );
}

// ── Score ring ────────────────────────────────────────────────────────────────
// Grade letter in center; ring color is grade color but kept subtle.

function ScoreRing({ score, grade }: { score: number; grade: string }) {
  const r    = 44;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color = gradeColor(grade);

  return (
    <div style={{ position: 'relative', width: 112, height: 112, flexShrink: 0 }}>
      <svg width={112} height={112} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={56} cy={56} r={r} fill="none"
          stroke="var(--border)" strokeWidth={8} />
        <circle cx={56} cy={56} r={r} fill="none"
          stroke={color} strokeWidth={8}
          strokeDasharray={`${fill} ${circ - fill}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.8s cubic-bezier(0.16,1,0.3,1)', opacity: 0.85 }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{
          fontSize: 26, fontWeight: 800, color: 'var(--text)',
          fontFamily: 'var(--font-mono)', lineHeight: 1,
        }}>
          {score}
        </span>
        <span style={{ fontSize: 11, color: color, fontWeight: 700, marginTop: 2 }}>
          {grade}
        </span>
      </div>
    </div>
  );
}

// ── Dimension card ────────────────────────────────────────────────────────────
// Left border uses grade color. Everything else is neutral.

const DimensionCard = React.memo(function DimensionCard({ dim }: { dim: HealthDimension }) {
  const [open, setOpen] = useState(false);
  const borderColor = gradeColor(dim.grade);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-expanded={open}
      onClick={() => setOpen(o => !o)}
      onKeyDown={e => e.key === 'Enter' && setOpen(o => !o)}
      style={{
        background: 'var(--glass-card)',
        border: '1px solid rgba(0,0,0,0.10)',
        borderLeft: `3px solid ${borderColor}`,
        borderRadius: 8,
        padding: '14px 16px',
        cursor: 'pointer',
        outline: 'none',
        transition: 'background 0.15s',
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'var(--glass-card)')}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'baseline', marginBottom: 6,
          }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
              {dim.name}
            </span>
            <span style={{
              fontSize: 12, fontFamily: 'var(--font-mono)',
              color: 'var(--text-secondary)', fontWeight: 600,
            }}>
              {dim.score}
              <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 2 }}>/100</span>
            </span>
          </div>
          <ScoreBar score={dim.score} height={4} />
        </div>
        <span style={{
          fontSize: 14, fontWeight: 800, color: borderColor,
          fontFamily: 'var(--font-mono)', flexShrink: 0, minWidth: 18, textAlign: 'center',
        }}>
          {dim.grade}
        </span>
        <span style={{
          fontSize: 8, color: 'var(--text-muted)',
          transform: open ? 'rotate(180deg)' : 'none',
          transition: 'transform 0.2s', flexShrink: 0,
        }}>▼</span>
      </div>

      <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.6 }}>
        {dim.summary}
      </p>

      {dim.issue_count > 0 && (
        <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '6px 0 0', fontWeight: 500 }}>
          {dim.issue_count} issue{dim.issue_count !== 1 ? 's' : ''} ·{' '}
          {Math.round((dim.confidence ?? 1) * 100)}% confidence
        </p>
      )}

      {/* Expanded metrics */}
      {open && dim.metrics.length > 0 && (
        <div style={{
          marginTop: 14, paddingTop: 14,
          borderTop: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column', gap: 12,
        }}>
          {dim.metrics.map(m => (
            <div key={m.label}>
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                marginBottom: 5, alignItems: 'baseline',
              }}>
                <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>
                  {m.label}
                </span>
                <span style={{
                  fontSize: 11, fontFamily: 'var(--font-mono)',
                  color: 'var(--text-secondary)', fontWeight: 600,
                }}>
                  {m.raw_value} <span style={{ color: 'var(--text-muted)' }}>{m.unit}</span>
                </span>
              </div>
              <ScoreBar score={m.score} height={3} />
              <p style={{ fontSize: 10, color: 'var(--text-muted)', margin: '4px 0 0', lineHeight: 1.5 }}>
                {m.description}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
});

// ── Issue card ────────────────────────────────────────────────────────────────
// Left border = only place severity color appears.
// Everything else: neutral text, neutral pills, neutral background.

const IssueCard = React.memo(function IssueCard({ issue }: { issue: CodeIssue }) {
  const [open, setOpen] = useState(false);
  const color = sevColor(issue.severity);

  const location = issue.file_path
    ? (() => {
        const parts = issue.file_path.replace(/\\/g, '/').split('/');
        const short = parts.length > 3 ? parts.slice(-3).join('/') : issue.file_path;
        const line  = issue.line_start > 0 ? issue.line_start : issue.line > 0 ? issue.line : 0;
        return line > 0 ? `${short}:${line}` : short;
      })()
    : null;

  const topEvidence = Object.entries(issue.evidence ?? {})
    .filter(([k]) => !['threshold', 'recommendation', 'suggestion'].includes(k))
    .slice(0, 5);

  return (
    <div style={{
      background: 'var(--glass-card)',
      border: '1px solid rgba(0,0,0,0.10)',
      borderLeft: `4px solid ${color}`,
      borderRadius: 8,
      overflow: 'hidden',
    }}>
      <div style={{ padding: '12px 14px' }}>

        {/* Row 1: severity PILL + category + confidence */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          marginBottom: 8, flexWrap: 'wrap',
        }}>
          {/* Solid severity badge */}
          <span style={{
            fontSize: 10, fontWeight: 700, color,
            background: sevBg(issue.severity),
            border: `1px solid ${color}40`,
            borderRadius: 5,
            padding: '2px 8px',
            textTransform: 'uppercase', letterSpacing: '0.07em',
          }}>
            {sevLabel(issue.severity)}
          </span>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.03em', fontWeight: 500 }}>
            {catLabel(issue.category)}
          </span>
          {issue.confidence < 1 && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto', fontWeight: 500 }}>
              {Math.round(issue.confidence * 100)}% confidence
            </span>
          )}
        </div>

        {/* Row 2: symbol + title */}
        <div style={{ marginBottom: 8 }}>
          {issue.affected_symbol && (
            <code style={{
              fontSize: 13, fontWeight: 700,
              color: 'var(--text)', marginRight: 8,
              fontFamily: 'var(--font-mono)',
            }}>
              {issue.affected_symbol}
            </code>
          )}
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>
            {issue.title}
          </span>
        </div>

        {/* Row 3: file location */}
        {location && (
          <div style={{ marginBottom: 10 }}>
            <code style={{
              fontSize: 11, fontFamily: 'var(--font-mono)',
              color: 'var(--text-secondary)',
              background: 'rgba(0,0,0,0.05)',
              border: '1px solid rgba(0,0,0,0.10)',
              borderRadius: 4, padding: '2px 8px',
            }}>
              {location}
            </code>
          </div>
        )}

        {/* Row 4: description */}
        {issue.description && (
          <p style={{
            fontSize: 13, color: 'var(--text-secondary)',
            margin: '0 0 10px', lineHeight: 1.65,
          }}>
            {issue.description.replace(/`/g, '').replace(/\(threshold:\s*\d+\)/g, '').trim()}
          </p>
        )}

        {/* Row 5: evidence strip */}
        {topEvidence.length > 0 && (
          <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 10 }}>
            {topEvidence.map(([k, v]) => (
              <Pill key={k}>
                <span style={{ color: 'var(--text-muted)', marginRight: 4 }}>{k}</span>
                <span style={{ color: 'var(--text)', fontWeight: 700 }}>{String(v)}</span>
              </Pill>
            ))}
          </div>
        )}

        {/* Row 6: how to fix toggle + navigate */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {(issue.recommendation || issue.suggestion) && (
            <button
              type="button"
              onClick={e => { e.stopPropagation(); setOpen(o => !o); }}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                fontSize: 11, fontWeight: 600,
                color: 'var(--text-muted)',
                background: 'transparent', border: 'none', cursor: 'pointer',
                padding: 0, transition: 'color 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--text)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              <span style={{
                display: 'inline-block', fontSize: 8,
                transform: open ? 'rotate(90deg)' : 'none',
                transition: 'transform 0.2s',
              }}>▶</span>
              {open ? 'Hide' : 'How to fix'}
            </button>
          )}
          {issue.affected_symbol && (
            <NavigateButton
              onClick={() => emitNavigate({
                nodeId: '',  // will be resolved by symbol lookup
                label: issue.affected_symbol,
                nodeType: 'Function',
              })}
              size="sm"
              label="Navigate"
            />
          )}
        </div>
      </div>

      {/* Expanded: fix text */}
      {open && (issue.recommendation || issue.suggestion) && (
        <div style={{
          borderTop: '1px solid var(--border)',
          padding: '12px 14px',
          background: 'var(--surface)',
        }}>
          <p style={{
            fontSize: 12, color: 'var(--text-secondary)',
            margin: 0, lineHeight: 1.7,
          }}>
            {issue.recommendation || issue.suggestion}
          </p>
        </div>
      )}
    </div>
  );
});

// ── File group ────────────────────────────────────────────────────────────────

function FileGroup({ filePath, issues }: { filePath: string; issues: CodeIssue[] }) {
  const [open, setOpen] = useState(true);

  const counts = useMemo(() => ({
    critical: issues.filter(i => i.severity === 'critical').length,
    high:     issues.filter(i => i.severity === 'high').length,
    medium:   issues.filter(i => i.severity === 'medium').length,
    low:      issues.filter(i => i.severity === 'low').length,
  }), [issues]);

  const displayPath = (() => {
    const parts = (filePath ?? '(no file)').replace(/\\/g, '/').split('/');
    return parts.length > 3 ? `…/${parts.slice(-3).join('/')}` : filePath;
  })();

  const sevOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
  const sorted = [...issues].sort(
    (a, b) => (sevOrder[a.severity] ?? 9) - (sevOrder[b.severity] ?? 9),
  );

  // Worst severity in this file — used for the single left border
  const worstSev = (sorted[0]?.severity ?? 'low') as IssueSeverity;

  return (
    <div style={{
      border: '1px solid var(--border)',
      borderLeft: `3px solid ${sevColor(worstSev)}`,
      borderRadius: 8, overflow: 'hidden', marginBottom: 6,
    }}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', textAlign: 'left', cursor: 'pointer',
          background: 'var(--surface)',
          border: 'none', padding: '9px 14px',
          display: 'flex', alignItems: 'center', gap: 10,
        }}
      >
        <span style={{
          fontSize: 8, color: 'var(--text-muted)',
          transform: open ? 'rotate(90deg)' : 'none',
          transition: 'transform 0.2s', flexShrink: 0,
        }}>▶</span>

        <code style={{
          fontSize: 12, color: 'var(--text)',
          fontFamily: 'var(--font-mono)', flex: 1,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          fontWeight: 500,
        }}>
          {displayPath}
        </code>

        {/* Compact issue counts — text only, no emoji */}
        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          {counts.critical > 0 && (
            <span style={{ fontSize: 11, color: SEV.critical, fontWeight: 700, fontFamily: 'var(--font-mono)', background: 'rgba(220,38,38,0.10)', borderRadius: 4, padding: '1px 6px' }}>
              {counts.critical}C
            </span>
          )}
          {counts.high > 0 && (
            <span style={{ fontSize: 11, color: SEV.high, fontWeight: 700, fontFamily: 'var(--font-mono)', background: 'rgba(234,88,12,0.10)', borderRadius: 4, padding: '1px 6px' }}>
              {counts.high}H
            </span>
          )}
          {counts.medium > 0 && (
            <span style={{ fontSize: 11, color: SEV.medium, fontWeight: 600, fontFamily: 'var(--font-mono)', background: 'rgba(217,119,6,0.10)', borderRadius: 4, padding: '1px 6px' }}>
              {counts.medium}M
            </span>
          )}
          {counts.low > 0 && (
            <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
              {counts.low}L
            </span>
          )}
          <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            {issues.length} total
          </span>
        </div>
      </button>

      {open && (
        <div style={{ padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {sorted.map((issue, i) => (
            <IssueCard key={`${issue.title}-${issue.line_start ?? 0}-${i}`} issue={issue} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Issues panel ──────────────────────────────────────────────────────────────

type SevFilter = 'all' | IssueSeverity;
type CatFilter = 'all' | IssueCategory;
type ViewMode  = 'byFile' | 'flat';

function IssuesPanel({ issues }: { issues: CodeIssue[] }) {
  const prefersReduced = useReducedMotion();
  const [sevFilter, setSevFilter] = useState<SevFilter>('all');
  const [catFilter, setCatFilter] = useState<CatFilter>('all');
  const [viewMode,  setViewMode]  = useState<ViewMode>('byFile');
  const [showAll,   setShowAll]   = useState(false);

  const categories = useMemo(
    () => Array.from(new Set(issues.map(i => i.category))).sort(),
    [issues],
  );

  const sevCounts = useMemo(() => ({
    critical: issues.filter(i => i.severity === 'critical').length,
    high:     issues.filter(i => i.severity === 'high').length,
    medium:   issues.filter(i => i.severity === 'medium').length,
    low:      issues.filter(i => i.severity === 'low').length,
    info:     issues.filter(i => i.severity === 'info').length,
  }), [issues]);

  const filtered = useMemo(() => {
    let list = issues;
    if (sevFilter !== 'all') list = list.filter(i => i.severity === sevFilter);
    if (catFilter !== 'all') list = list.filter(i => i.category === catFilter);
    return list;
  }, [issues, sevFilter, catFilter]);

  const byFile = useMemo(() => {
    const map = new Map<string, CodeIssue[]>();
    for (const issue of filtered) {
      const key = issue.file_path || '(no file)';
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(issue);
    }
    const sevOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
    return Array.from(map.entries()).sort(([, a], [, b]) => {
      const wa = Math.min(...a.map(i => sevOrder[i.severity] ?? 9));
      const wb = Math.min(...b.map(i => sevOrder[i.severity] ?? 9));
      return wa - wb || b.length - a.length;
    });
  }, [filtered]);

  const LIMIT = 40;
  const visible = showAll ? filtered : filtered.slice(0, LIMIT);

  // Shared button style factory
  const filterBtn = (active: boolean, activeColor?: string) => ({
    padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
    cursor: 'pointer' as const,
    background: active ? 'var(--surface)' : 'transparent',
    color: active ? (activeColor ?? 'var(--text)') : 'var(--text-muted)',
    border: `1px solid ${active ? 'var(--border-hover)' : 'var(--border)'}`,
    transition: 'all 0.15s',
  } as const);

  return (
    <div>
      {/* Toolbar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>

        {/* Row 1: title + view toggle */}
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <SectionLabel>Issues ({filtered.length})</SectionLabel>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
            {(['byFile', 'flat'] as ViewMode[]).map(m => (
              <button key={m} onClick={() => { setViewMode(m); setShowAll(false); }}
                style={filterBtn(viewMode === m)}>
                {m === 'byFile' ? 'By file' : 'Flat'}
              </button>
            ))}
          </div>
        </div>

        {/* Row 2: severity filters */}
        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
          <button onClick={() => setSevFilter('all')}
            style={filterBtn(sevFilter === 'all')}>
            All {issues.length}
          </button>
          {(['critical', 'high', 'medium', 'low'] as IssueSeverity[]).map(s => (
            sevCounts[s] > 0 && (
              <button key={s}
                onClick={() => setSevFilter(s === sevFilter ? 'all' : s)}
                style={filterBtn(sevFilter === s, sevColor(s))}>
                {sevLabel(s)} {sevCounts[s]}
              </button>
            )
          ))}
        </div>

        {/* Row 3: category filters */}
        {categories.length > 1 && (
          <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
            <button onClick={() => setCatFilter('all')}
              style={filterBtn(catFilter === 'all')}>
              All categories
            </button>
            {categories.map(c => (
              <button key={c}
                onClick={() => setCatFilter(c === catFilter ? 'all' : c as CatFilter)}
                style={filterBtn(catFilter === c)}>
                {catLabel(c)}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Issue list */}
      {filtered.length === 0 ? (
        <div style={{
          padding: '32px', textAlign: 'center',
          background: 'var(--glass-card)', border: '1px solid var(--border)',
          borderRadius: 8,
        }}>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
            No issues match this filter.
          </p>
        </div>
      ) : viewMode === 'byFile' ? (
        <div>
          {byFile.slice(0, showAll ? undefined : 15).map(([fp, iss]) => (
            <FileGroup key={fp} filePath={fp} issues={iss} />
          ))}
          {byFile.length > 15 && !showAll && (
            <button onClick={() => setShowAll(true)} style={{
              width: '100%', marginTop: 4, padding: '9px',
              background: 'transparent',
              border: '1px dashed var(--border-hover)',
              borderRadius: 8, color: 'var(--text-muted)', fontSize: 12,
              cursor: 'pointer',
            }}>
              Show {byFile.length - 15} more files
            </button>
          )}
        </div>
      ) : (
        <motion.div
          style={{ display: 'flex', flexDirection: 'column', gap: 6 }}
          variants={prefersReduced ? undefined : staggerFastContainer}
          initial={prefersReduced ? false : 'hidden'}
          animate="visible"
        >
          {visible.map((issue, i) => (
            <motion.div
              key={`${issue.title}-${issue.file_path}-${i}`}
              variants={prefersReduced ? undefined : staggerFastChild}
            >
              <IssueCard issue={issue} />
            </motion.div>
          ))}
          {filtered.length > LIMIT && !showAll && (
            <button onClick={() => setShowAll(true)} style={{
              marginTop: 4, padding: '9px',
              background: 'transparent',
              border: '1px dashed var(--border-hover)',
              borderRadius: 8, color: 'var(--text-muted)', fontSize: 12,
              cursor: 'pointer', width: '100%',
            }}>
              Show {filtered.length - LIMIT} more issues
            </button>
          )}
        </motion.div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  report: InsightsReport;
  isDark?: boolean;   // accepted for compat, ignored — always light
}

export default function InsightsDashboard({ report }: Props) {
  const [exporting, setExporting] = useState(false);
  const prefersReduced = useReducedMotion();

  const handleExport = useCallback(async () => {
    setExporting(true);
    try {
      const md   = await exportInsightsMarkdown(report.job_id);
      const blob = new Blob([md], { type: 'text/markdown' });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url;
      a.download = `${report.repo_name}-health-report.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { /* non-critical */ }
    finally { setExporting(false); }
  }, [report.job_id, report.repo_name]);

  const docCovPct = report.stats.functions > 0
    ? Math.round((report.stats.documented_fns / report.stats.functions) * 100)
    : 100;

  const totalIssues   = report.issues.length;
  const criticalCount = report.stats.critical_issues ?? 0;
  const highCount     = report.stats.high_issues ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, padding: '4px 0' }}>

      {/* ── Header ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 20,
        background: 'var(--glass-card)',
        border: '1px solid var(--border)',
        borderRadius: 10, padding: '20px 24px',
        flexWrap: 'wrap',
      }}>
        <ScoreRing score={report.overall_score} grade={report.overall_grade} />

        <div style={{ flex: 1, minWidth: 200 }}>
          <h2 style={{
            fontSize: 18, fontWeight: 700,
            color: 'var(--text)', margin: '0 0 4px',
          }}>
            {report.repo_name}
          </h2>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 12px' }}>
            {report.stats.files} source files · {report.coverage?.test_files ?? 0} test files
            · {report.stats.dominant_language}
            · {Math.round((report.overall_confidence ?? 1) * 100)}% confidence
          </p>

          {/* Grade badge + issue summary — single neutral row */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{
              fontSize: 12, fontWeight: 700,
              color: gradeColor(report.overall_grade),
              fontFamily: 'var(--font-mono)',
            }}>
              Grade {report.overall_grade} — {gradeLabel(report.overall_grade)}
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>·</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {totalIssues} issue{totalIssues !== 1 ? 's' : ''}
              {criticalCount > 0 && (
                <span style={{ color: SEV.critical, fontWeight: 700 }}>
                  {' '}({criticalCount} critical)
                </span>
              )}
              {!criticalCount && highCount > 0 && (
                <span style={{ color: SEV.high, fontWeight: 700 }}>
                  {' '}({highCount} high)
                </span>
              )}
            </span>
          </div>
        </div>

        <button
          onClick={handleExport}
          disabled={exporting}
          style={{
            padding: '8px 16px', borderRadius: 8, fontSize: 12, fontWeight: 600,
            background: 'var(--surface)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border)',
            cursor: exporting ? 'wait' : 'pointer',
            transition: 'background 0.2s', flexShrink: 0,
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--card)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'var(--surface)')}
        >
          {exporting ? 'Exporting…' : 'Export .md'}
        </button>
      </div>

      {/* ── Stats strip — neutral, no accent colors ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))',
        gap: 8,
      }}>
        {[
          { label: 'Source Files',   value: report.stats.files },
          { label: 'Test Files',     value: report.stats.test_files ?? 0 },
          { label: 'Classes',        value: report.stats.classes },
          { label: 'Functions',      value: report.stats.functions },
          { label: 'Doc Coverage',   value: `${docCovPct}%` },
          { label: 'Critical',       value: criticalCount },
          { label: 'High',           value: highCount },
          { label: 'Medium',         value: report.stats.medium_issues },
          { label: 'Low',            value: report.stats.low_issues ?? 0 },
        ].map(({ label, value }) => (
          <div key={label} style={{
            background: 'var(--glass-card)',
            border: '1px solid var(--border)',
            borderRadius: 8, padding: '12px 14px',
            textAlign: 'center',
          }}>
            <div style={{
              fontSize: 20, fontWeight: 700,
              color: 'var(--text)',
              fontFamily: 'var(--font-mono)', lineHeight: 1.1,
            }}>
              {value}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
              {label}
            </div>
          </div>
        ))}
      </div>

      {/* ── Coverage line ── */}
      {report.coverage && (
        <div style={{
          background: 'var(--glass-card)', border: '1px solid var(--border)',
          borderRadius: 8, padding: '10px 16px',
          display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center',
        }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Coverage
          </span>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            {report.coverage.analyzed_files} of {Math.max(report.coverage.analyzed_files, report.coverage.source_files)} source files analysed
          </span>
          {report.coverage.test_files > 0 && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              · {report.coverage.test_files} test files excluded
            </span>
          )}
          {report.coverage.generated_files > 0 && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              · {report.coverage.generated_files} generated excluded
            </span>
          )}
          {(report.coverage.languages_detected?.length ?? 0) > 0 && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
              {report.coverage.languages_detected.join(', ')}
            </span>
          )}
        </div>
      )}

      {/* ── Dimension scores — compact table ── */}
      <div style={{
        background: 'var(--glass-card)',
        border: '1px solid var(--border)',
        borderRadius: 10, padding: '16px 18px',
      }}>
        <SectionLabel>Dimensions</SectionLabel>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {report.dimensions.map(dim => (
            <div key={dim.name} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{
                fontSize: 12, color: 'var(--text-secondary)',
                fontWeight: 500, minWidth: 108, flexShrink: 0,
              }}>
                {dim.name}
              </span>
              <div style={{ flex: 1 }}>
                <ScoreBar score={dim.score} height={5} />
              </div>
              <span style={{
                fontSize: 12, fontFamily: 'var(--font-mono)',
                color: 'var(--text-secondary)', fontWeight: 600,
                minWidth: 32, textAlign: 'right', flexShrink: 0,
              }}>
                {dim.score}
              </span>
              <span style={{
                fontSize: 11, fontWeight: 700,
                color: gradeColor(dim.grade),
                minWidth: 14, textAlign: 'center', flexShrink: 0,
                fontFamily: 'var(--font-mono)',
              }}>
                {dim.grade}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Dimension detail cards ── */}
      <div>
        <SectionLabel>Health Dimensions</SectionLabel>
        <motion.div
          style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(270px, 1fr))', gap: 10 }}
          variants={prefersReduced ? undefined : staggerFastContainer}
          initial={prefersReduced ? false : 'hidden'}
          animate="visible"
        >
          {report.dimensions.map(dim => (
            <motion.div key={dim.name} variants={prefersReduced ? undefined : staggerFastChild}>
              <DimensionCard dim={dim} />
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* ── Issues ── */}
      <IssuesPanel issues={report.issues} />

    </div>
  );
}
