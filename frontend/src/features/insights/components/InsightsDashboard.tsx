// =============================================================================
// InsightsDashboard — Industry-grade engineering health report
// Accurate metrics, grouped issues, category filtering, file-level drill-down
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

// ── Severity helpers ──────────────────────────────────────────────────────────

function sevColor(s: IssueSeverity): string {
  switch (s) {
    case 'critical': return '#dc2626';
    case 'high':     return 'var(--danger)';
    case 'medium':   return 'var(--warning)';
    case 'low':      return 'var(--success)';
    default:         return 'var(--text-muted)';
  }
}
function sevIcon(s: IssueSeverity): string {
  switch (s) {
    case 'critical': return '🚨';
    case 'high':     return '🔴';
    case 'medium':   return '🟡';
    case 'low':      return '🟢';
    default:         return '⚪';
  }
}
function sevLabel(s: IssueSeverity): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// ── Grade helpers ─────────────────────────────────────────────────────────────

function gradeColor(g: string): string {
  switch (g) {
    case 'A': return '#22c55e';
    case 'B': return '#84cc16';
    case 'C': return '#f59e0b';
    case 'D': return '#f97316';
    case 'F': return '#ef4444';
    default:  return 'var(--text-muted)';
  }
}

function gradeDesc(g: string): string {
  switch (g) {
    case 'A': return 'Excellent';
    case 'B': return 'Good';
    case 'C': return 'Fair';
    case 'D': return 'Poor';
    case 'F': return 'Critical';
    default:  return '';
  }
}

// ── Category helpers ──────────────────────────────────────────────────────────

const CATEGORY_ICONS: Record<string, string> = {
  complexity:    '⚙️',
  coupling:      '🔗',
  size:          '📏',
  architecture:  '🏛️',
  documentation: '📝',
  naming:        '🏷️',
  duplication:   '📋',
  error_handling:'🛡️',
  'error handling': '🛡️',
};

function catIcon(c: string): string { return CATEGORY_ICONS[c] ?? '🔍'; }
function catLabel(c: string): string {
  return c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// ── Score bar ─────────────────────────────────────────────────────────────────

function ScoreBar({
  score, color, height = 6,
}: { score: number; color: string; height?: number }) {
  return (
    <div style={{
      width: '100%', height, borderRadius: height / 2,
      background: 'rgba(255,255,255,0.07)', overflow: 'hidden',
    }}>
      <div style={{
        width: `${Math.max(0, Math.min(100, score))}%`,
        height: '100%', background: color, borderRadius: height / 2,
        transition: 'width 0.7s cubic-bezier(0.16,1,0.3,1)',
      }} />
    </div>
  );
}

// ── Score Ring ────────────────────────────────────────────────────────────────

function ScoreRing({ score, grade }: { score: number; grade: string }) {
  const r     = 46;
  const circ  = 2 * Math.PI * r;
  const fill  = (score / 100) * circ;
  const color = gradeColor(grade);
  return (
    <div style={{ position: 'relative', width: 128, height: 128, flexShrink: 0 }}>
      <svg width={128} height={128} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={64} cy={64} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={10} />
        <circle
          cx={64} cy={64} r={r} fill="none"
          stroke={color} strokeWidth={10}
          strokeDasharray={`${fill} ${circ - fill}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.9s cubic-bezier(0.16,1,0.3,1)' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: 1,
      }}>
        <span style={{ fontSize: 28, fontWeight: 800, color, lineHeight: 1, fontFamily: 'var(--font-mono)' }}>
          {score}
        </span>
        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>/ 100</span>
        <span style={{
          fontSize: 11, fontWeight: 700,
          color, marginTop: 1,
          padding: '1px 7px', borderRadius: 8,
          background: `${color}18`,
          border: `1px solid ${color}30`,
        }}>
          {grade} · {gradeDesc(grade)}
        </span>
      </div>
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────

function StatCard({
  label, value, accent, sub,
}: { label: string; value: number | string; accent?: string; sub?: string }) {
  return (
    <div style={{
      background: 'var(--glass-card)',
      border: `1px solid ${accent ? `${accent}30` : 'var(--border)'}`,
      borderRadius: 'var(--radius-md)',
      padding: '12px 14px',
      textAlign: 'center',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {accent && (
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: 2,
          background: accent,
        }} />
      )}
      <div style={{
        fontSize: 22, fontWeight: 800, color: accent ?? 'var(--text)',
        fontFamily: 'var(--font-mono)', lineHeight: 1.1,
      }}>
        {value}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{label}</div>
      {sub && <div style={{ fontSize: 10, color: 'var(--text-faint)', marginTop: 1, opacity: 0.7 }}>{sub}</div>}
    </div>
  );
}

// ── Dimension Card ────────────────────────────────────────────────────────────

function DimensionCard({ dim }: { dim: HealthDimension }) {
  const [open, setOpen] = useState(false);
  const color = gradeColor(dim.grade);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-expanded={open}
      onClick={() => setOpen(o => !o)}
      onKeyDown={e => e.key === 'Enter' && setOpen(o => !o)}
      style={{
        background: 'var(--glass-card)',
        border: `1px solid var(--border)`,
        borderLeft: `3px solid ${color}`,
        borderRadius: 'var(--radius-md)',
        padding: '14px 16px',
        cursor: 'pointer',
        transition: 'border-color 0.2s, background 0.2s',
        outline: 'none',
      }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = `${color}60`)}
      onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10, flexShrink: 0,
          background: `${color}18`, border: `1px solid ${color}35`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <span style={{ fontSize: 18, fontWeight: 800, color, fontFamily: 'var(--font-mono)' }}>
            {dim.grade}
          </span>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, alignItems: 'baseline' }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>{dim.name}</span>
            <span style={{ fontSize: 12, color, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
              {dim.score}/100
            </span>
          </div>
          <ScoreBar score={dim.score} color={color} height={5} />
        </div>
        <span style={{
          fontSize: 9, color: 'var(--text-muted)',
          transform: open ? 'rotate(180deg)' : 'none',
          transition: 'transform 0.2s', flexShrink: 0,
        }}>▼</span>
      </div>

      <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
        {dim.summary}
      </p>
      {(dim.confidence < 1 || dim.issue_count > 0) && (
        <div style={{ display: 'flex', gap: 10, marginTop: 6 }}>
          {dim.issue_count > 0 && (
            <span style={{ fontSize: 10, color: color, fontWeight: 600 }}>
              {dim.issue_count} issue{dim.issue_count !== 1 ? 's' : ''}
            </span>
          )}
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
            {Math.round((dim.confidence ?? 1) * 100)}% confidence
          </span>
        </div>
      )}

      {/* Expanded metrics */}
      {open && dim.metrics.length > 0 && (
        <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {dim.metrics.map(m => {
            const mColor = m.score >= 80 ? '#22c55e' : m.score >= 65 ? '#84cc16' : m.score >= 50 ? '#f59e0b' : '#ef4444';
            return (
              <div key={m.label}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between',
                  marginBottom: 4, alignItems: 'baseline',
                }}>
                  <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>
                    {m.label}
                  </span>
                  <span style={{
                    fontSize: 11, fontFamily: 'var(--font-mono)',
                    color: mColor, fontWeight: 700,
                  }}>
                    {m.raw_value} {m.unit}
                  </span>
                </div>
                <ScoreBar score={m.score} color={mColor} height={4} />
                <p style={{ fontSize: 10, color: 'var(--text-muted)', margin: '3px 0 0', lineHeight: 1.4 }}>
                  {m.description}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Issue Row ─────────────────────────────────────────────────────────────────

function IssueRow({ issue }: { issue: CodeIssue }) {
  const [open, setOpen] = useState(false);
  const color = sevColor(issue.severity);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-expanded={open}
      onClick={() => setOpen(o => !o)}
      onKeyDown={e => e.key === 'Enter' && setOpen(o => !o)}
      style={{
        background: 'rgba(255,255,255,0.022)',
        border: '1px solid var(--border)',
        borderLeft: `3px solid ${color}`,
        borderRadius: 'var(--radius-sm)',
        padding: '10px 14px',
        cursor: 'pointer',
        transition: 'background 0.15s',
        outline: 'none',
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.045)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.022)')}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
        <span style={{ fontSize: 13, lineHeight: 1.5, flexShrink: 0 }}>{sevIcon(issue.severity)}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Title + category badge */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 3 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{issue.title}</span>
            <span style={{
              fontSize: 10, padding: '2px 7px', borderRadius: 4,
              background: 'rgba(255,255,255,0.07)', color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
              letterSpacing: '0.06em', flexShrink: 0,
            }}>
              {catIcon(issue.category)} {catLabel(issue.category)}
            </span>
          </div>

          {/* Description */}
          <p style={{
            fontSize: 12, color: 'var(--text-secondary)',
            margin: 0, lineHeight: 1.55,
          }}>
            {issue.description}
          </p>

          {/* File + line */}
          {issue.file_path && (
            <p style={{
              fontSize: 11, fontFamily: 'var(--font-mono)',
              color: 'var(--text-muted)', margin: '4px 0 0',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              📁 {issue.file_path}{issue.line > 0 ? `:${issue.line}` : ''}
              {issue.affected_symbol && (
                <span style={{ color: 'var(--primary)', marginLeft: 6 }}>
                  · {issue.affected_symbol}
                </span>
              )}
            </p>
          )}
        </div>
        <span style={{
          fontSize: 9, color: 'var(--text-muted)',
          transform: open ? 'rotate(180deg)' : 'none',
          transition: 'transform 0.2s', flexShrink: 0, marginTop: 2,
        }}>▼</span>
      </div>

      {/* Suggestion panel */}
      {open && (
        <div style={{
          marginTop: 10, padding: '10px 13px',
          background: 'rgba(0,229,168,0.05)',
          border: '1px solid rgba(0,229,168,0.18)',
          borderRadius: 8,
        }}>
          <span style={{
            fontSize: 11, fontWeight: 700, color: 'var(--primary)',
            display: 'block', marginBottom: 5,
          }}>
            💡 How to fix
          </span>
          <p style={{
            fontSize: 12, color: 'var(--text-secondary)',
            margin: 0, lineHeight: 1.65,
          }}>
            {issue.recommendation || issue.suggestion}
          </p>
          {issue.evidence && Object.keys(issue.evidence).length > 0 && (
            <div style={{ marginTop: 8 }}>
              <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', display: 'block', marginBottom: 3 }}>
                📊 Evidence
              </span>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {Object.entries(issue.evidence).map(([k, v]) => (
                  <span key={k} style={{
                    fontSize: 10, padding: '1px 7px', borderRadius: 4,
                    background: 'rgba(255,255,255,0.07)', color: 'var(--text-muted)',
                    fontFamily: 'var(--font-mono)',
                  }}>
                    {k}: {String(v)}
                  </span>
                ))}
              </div>
            </div>
          )}
          {issue.confidence < 1 && (
            <p style={{ fontSize: 10, color: 'var(--text-muted)', margin: '6px 0 0' }}>
              Confidence: {Math.round((issue.confidence ?? 1) * 100)}%
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Issues grouped by file ────────────────────────────────────────────────────

function FileGroup({ filePath, issues }: { filePath: string; issues: CodeIssue[] }) {
  const [open, setOpen] = useState(true);
  const highCount   = issues.filter(i => i.severity === 'high').length;
  const medCount    = issues.filter(i => i.severity === 'medium').length;

  const shortPath = filePath.split('/').slice(-2).join('/') || filePath;

  return (
    <div style={{
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)',
      overflow: 'hidden',
      marginBottom: 8,
    }}>
      {/* File header */}
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', textAlign: 'left', cursor: 'pointer',
          background: 'rgba(255,255,255,0.03)',
          border: 'none', padding: '10px 14px',
          display: 'flex', alignItems: 'center', gap: 10,
        }}
      >
        <span style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          📄 {shortPath}
        </span>
        <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
          {highCount > 0 && (
            <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: 'rgba(239,68,68,0.15)', color: '#ef4444', fontWeight: 700 }}>
              {highCount} high
            </span>
          )}
          {medCount > 0 && (
            <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: 'rgba(245,158,11,0.15)', color: '#f59e0b', fontWeight: 700 }}>
              {medCount} med
            </span>
          )}
          <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: 'rgba(255,255,255,0.07)', color: 'var(--text-muted)', fontWeight: 600 }}>
            {issues.length} total
          </span>
        </div>
        <span style={{ fontSize: 9, color: 'var(--text-muted)', transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>▼</span>
      </button>

      {open && (
        <div style={{ padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 5 }}>
          {issues.map((issue, i) => (
            <IssueRow key={`${issue.title}-${i}`} issue={issue} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Issues Panel ──────────────────────────────────────────────────────────────

type SevFilter = 'all' | IssueSeverity;
type CatFilter = 'all' | IssueCategory;
type ViewMode  = 'flat' | 'byFile';

function IssuesPanel({ issues }: { issues: CodeIssue[] }) {
  const prefersReduced = useReducedMotion();
  const [sevFilter, setSevFilter] = useState<SevFilter>('all');
  const [catFilter, setCatFilter] = useState<CatFilter>('all');
  const [viewMode,  setViewMode]  = useState<ViewMode>('byFile');
  const [showAll,   setShowAll]   = useState(false);

  // Derive unique categories from the actual data
  const categories = useMemo(
    () => Array.from(new Set(issues.map(i => i.category))).sort(),
    [issues],
  );

  const filtered = useMemo(() => {
    let list = issues;
    if (sevFilter !== 'all') list = list.filter(i => i.severity === sevFilter);
    if (catFilter !== 'all') list = list.filter(i => i.category === catFilter);
    return list;
  }, [issues, sevFilter, catFilter]);

  const LIMIT = 40;
  const visible = showAll ? filtered : filtered.slice(0, LIMIT);

  // Group by file for file view
  const byFile = useMemo(() => {
    const map = new Map<string, CodeIssue[]>();
    for (const issue of filtered) {
      const key = issue.file_path || '(no file)';
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(issue);
    }
    // Sort: files with most high-severity issues first
    return Array.from(map.entries()).sort(([, a], [, b]) => {
      const highA = a.filter(i => i.severity === 'high').length;
      const highB = b.filter(i => i.severity === 'high').length;
      return highB - highA || b.length - a.length;
    });
  }, [filtered]);

  const sevCounts = useMemo<Record<IssueSeverity, number>>(() => ({
    critical: issues.filter(i => i.severity === 'critical').length,
    high:     issues.filter(i => i.severity === 'high').length,
    medium:   issues.filter(i => i.severity === 'medium').length,
    low:      issues.filter(i => i.severity === 'low').length,
    info:     issues.filter(i => i.severity === 'info').length,
  }), [issues]);

  return (
    <div>
      {/* ── Toolbar ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 14 }}>
        {/* Row 1: title + view toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <h3 style={{
            fontSize: 12, fontWeight: 700, color: 'var(--text-muted)',
            margin: 0, textTransform: 'uppercase', letterSpacing: '0.1em',
          }}>
            Issues ({filtered.length})
          </h3>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
            {(['byFile', 'flat'] as ViewMode[]).map(m => (
              <button
                key={m}
                onClick={() => setViewMode(m)}
                style={{
                  padding: '3px 10px', borderRadius: 8, fontSize: 11, fontWeight: 600,
                  cursor: 'pointer', border: `1px solid ${viewMode === m ? 'var(--primary)' : 'var(--border)'}`,
                  background: viewMode === m ? 'var(--primary-dim)' : 'transparent',
                  color: viewMode === m ? 'var(--primary)' : 'var(--text-muted)',
                  transition: 'all 0.15s',
                }}
              >
                {m === 'byFile' ? '📁 By File' : '☰ Flat'}
              </button>
            ))}
          </div>
        </div>

        {/* Row 2: severity filters */}
        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
          <button
            onClick={() => setSevFilter('all')}
            style={{
              padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600,
              cursor: 'pointer', transition: 'all 0.15s',
              background: sevFilter === 'all' ? 'rgba(255,255,255,0.1)' : 'transparent',
              color: sevFilter === 'all' ? 'var(--text)' : 'var(--text-muted)',
              border: `1px solid ${sevFilter === 'all' ? 'var(--border-hover)' : 'var(--border)'}`,
            }}
          >
            All ({issues.length})
          </button>
          {(['critical', 'high', 'medium', 'low'] as IssueSeverity[]).map(s => (
            <button
              key={s}
              onClick={() => setSevFilter(s === sevFilter ? 'all' : s)}
              style={{
                padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600,
                cursor: 'pointer', transition: 'all 0.15s',
                background: sevFilter === s ? `${sevColor(s)}20` : 'transparent',
                color: sevFilter === s ? sevColor(s) : 'var(--text-muted)',
                border: `1px solid ${sevFilter === s ? sevColor(s) : 'var(--border)'}`,
              }}
            >
              {sevIcon(s)} {sevLabel(s)} ({sevCounts[s]})
            </button>
          ))}
        </div>

        {/* Row 3: category filters (only categories present in data) */}
        {categories.length > 1 && (
          <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
            <button
              onClick={() => setCatFilter('all')}
              style={{
                padding: '2px 8px', borderRadius: 8, fontSize: 10, fontWeight: 600,
                cursor: 'pointer', transition: 'all 0.15s',
                background: catFilter === 'all' ? 'rgba(255,255,255,0.07)' : 'transparent',
                color: catFilter === 'all' ? 'var(--text)' : 'var(--text-muted)',
                border: `1px solid ${catFilter === 'all' ? 'var(--border-hover)' : 'var(--border)'}`,
              }}
            >
              All categories
            </button>
            {categories.map(c => (
              <button
                key={c}
                onClick={() => setCatFilter(c === catFilter ? 'all' : c as CatFilter)}
                style={{
                  padding: '2px 8px', borderRadius: 8, fontSize: 10, fontWeight: 600,
                  cursor: 'pointer', transition: 'all 0.15s',
                  background: catFilter === c ? 'rgba(255,255,255,0.09)' : 'transparent',
                  color: catFilter === c ? 'var(--text)' : 'var(--text-muted)',
                  border: `1px solid ${catFilter === c ? 'var(--border-hover)' : 'var(--border)'}`,
                }}
              >
                {catIcon(c)} {catLabel(c)}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── Issue list ── */}
      {filtered.length === 0 ? (
        <div style={{
          padding: '32px 24px', textAlign: 'center',
          background: 'var(--glass-card)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)',
        }}>
          <p style={{ fontSize: 14, color: 'var(--text-muted)', margin: 0 }}>
            ✅ No issues for this filter.
          </p>
        </div>
      ) : viewMode === 'byFile' ? (
        <div>
          {byFile.slice(0, showAll ? undefined : 15).map(([fp, iss]) => (
            <FileGroup key={fp} filePath={fp} issues={iss} />
          ))}
          {byFile.length > 15 && !showAll && (
            <button
              onClick={() => setShowAll(true)}
              style={{
                width: '100%', marginTop: 4, padding: '8px',
                background: 'transparent', border: '1px dashed var(--border)',
                borderRadius: 8, color: 'var(--text-muted)', fontSize: 12,
                cursor: 'pointer', transition: 'color 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--text)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              Show {byFile.length - 15} more files…
            </button>
          )}
        </div>
      ) : (
        <motion.div
          style={{ display: 'flex', flexDirection: 'column', gap: 5 }}
          variants={prefersReduced ? undefined : staggerFastContainer}
          initial={prefersReduced ? false : 'hidden'}
          animate="visible"
        >
          {visible.map((issue, i) => (
            <motion.div
              key={`${issue.title}-${issue.file_path}-${i}`}
              variants={prefersReduced ? undefined : staggerFastChild}
            >
              <IssueRow issue={issue} />
            </motion.div>
          ))}
          {filtered.length > LIMIT && !showAll && (
            <button
              onClick={() => setShowAll(true)}
              style={{
                marginTop: 4, padding: '8px',
                background: 'transparent', border: '1px dashed var(--border)',
                borderRadius: 8, color: 'var(--text-muted)', fontSize: 12,
                cursor: 'pointer', width: '100%',
              }}
            >
              Show {filtered.length - LIMIT} more issues…
            </button>
          )}
        </motion.div>
      )}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

interface Props {
  report: InsightsReport;
  isDark: boolean;
}

export default function InsightsDashboard({ report, isDark }: Props) {
  const [exporting, setExporting] = useState(false);
  const prefersReduced = useReducedMotion();

  const cardBg = isDark
    ? 'rgba(13,17,27,0.82)'
    : 'rgba(255,255,255,0.92)';

  const handleExport = useCallback(async () => {
    setExporting(true);
    try {
      const md  = await exportInsightsMarkdown(report.job_id);
      const blob = new Blob([md], { type: 'text/markdown' });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `${report.repo_name}-engineering-report.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // export is non-critical
    } finally {
      setExporting(false);
    }
  }, [report.job_id, report.repo_name]);

  // Derive doc coverage % for display
  const docCovPct = report.stats.functions > 0
    ? Math.round((report.stats.documented_fns / report.stats.functions) * 100)
    : 100;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, padding: '4px 0' }}>

      {/* ── Header card ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 20,
        background: cardBg,
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '20px 24px',
        flexWrap: 'wrap',
      }}>
        <ScoreRing score={report.overall_score} grade={report.overall_grade} />
        <div style={{ flex: 1, minWidth: 180 }}>
          <h2 style={{ fontSize: 20, fontWeight: 800, color: 'var(--text)', margin: '0 0 3px' }}>
            {report.repo_name}
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '0 0 10px' }}>
            Engineering Health Report · {report.stats.files} source files
            · {report.coverage?.test_files ?? 0} test files
            · {report.stats.dominant_language}
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{
              padding: '3px 12px', borderRadius: 20, fontSize: 12, fontWeight: 700,
              background: `${gradeColor(report.overall_grade)}20`,
              color: gradeColor(report.overall_grade),
              border: `1px solid ${gradeColor(report.overall_grade)}40`,
            }}>
              Grade {report.overall_grade} — {gradeDesc(report.overall_grade)}
            </span>
            <span style={{
              padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
              background: 'rgba(255,255,255,0.07)', color: 'var(--text-muted)',
              border: '1px solid var(--border)',
            }}>
              {Math.round((report.overall_confidence ?? 1) * 100)}% confidence
            </span>
            {report.stats.critical_issues > 0 && (
              <span style={{
                padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                background: 'rgba(220,38,38,0.12)', color: '#dc2626',
                border: '1px solid rgba(220,38,38,0.3)',
              }}>
                🚨 {report.stats.critical_issues} critical
              </span>
            )}
            {report.stats.high_issues > 0 && (
              <span style={{
                padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                background: 'rgba(239,68,68,0.12)', color: '#ef4444',
                border: '1px solid rgba(239,68,68,0.3)',
              }}>
                🔴 {report.stats.high_issues} high
              </span>
            )}
          </div>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting}
          style={{
            padding: '8px 16px', borderRadius: 10, fontSize: 12, fontWeight: 600,
            background: 'var(--primary-dim)', color: 'var(--primary)',
            border: '1px solid rgba(0,229,168,0.25)', cursor: exporting ? 'wait' : 'pointer',
            transition: 'background 0.2s', flexShrink: 0,
          }}
        >
          {exporting ? 'Exporting…' : '↓ Export .md'}
        </button>
      </div>

      {/* ── Stats strip ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(95px,1fr))', gap: 8 }}>
        <StatCard label="Source Files"   value={report.stats.files} />
        <StatCard label="Test Files"     value={report.stats.test_files ?? 0} />
        <StatCard label="Classes"        value={report.stats.classes} />
        <StatCard label="Functions"      value={report.stats.functions} />
        <StatCard label="Language"       value={report.stats.dominant_language ?? '—'} />
        <StatCard label="Doc Coverage"   value={`${docCovPct}%`} accent={docCovPct >= 70 ? '#22c55e' : docCovPct >= 50 ? '#f59e0b' : '#ef4444'} />
        <StatCard label="Confidence"     value={`${Math.round((report.overall_confidence ?? 1)*100)}%`} />
        <StatCard label="🚨 Critical"    value={report.stats.critical_issues ?? 0} accent={(report.stats.critical_issues ?? 0) > 0 ? '#dc2626' : undefined} />
        <StatCard label="🔴 High"        value={report.stats.high_issues}   accent={report.stats.high_issues > 0 ? '#ef4444' : undefined} />
        <StatCard label="🟡 Warnings"   value={report.stats.medium_issues} accent={report.stats.medium_issues > 0 ? '#f59e0b' : undefined} />
      </div>

      {/* ── Coverage bar ── */}
      {report.coverage && (
        <div style={{
          background: 'var(--glass-card)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)', padding: '12px 16px',
          display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center',
        }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Analysis Coverage
          </span>
          <span style={{ fontSize: 12, color: 'var(--text)' }}>
            {report.coverage.analyzed_files} / {Math.max(report.coverage.analyzed_files, report.coverage.source_files)} source files
          </span>
          {report.coverage.test_files > 0 && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              · {report.coverage.test_files} test files excluded from metrics
            </span>
          )}
          {report.coverage.generated_files > 0 && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              · {report.coverage.generated_files} generated files excluded
            </span>
          )}
          {report.coverage.languages_detected?.length > 0 && (
            <span style={{ fontSize: 11, color: 'var(--primary)', marginLeft: 'auto' }}>
              Languages: {report.coverage.languages_detected.join(', ')}
            </span>
          )}
        </div>
      )}

      {/* ── Dimensions grid ── */}
      <div>
        <h3 style={{
          fontSize: 11, fontWeight: 700, color: 'var(--text-muted)',
          margin: '0 0 10px', textTransform: 'uppercase', letterSpacing: '0.1em',
        }}>
          Health Dimensions
        </h3>
        <motion.div
          style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(260px,1fr))', gap: 10 }}
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

      {/* ── Dimension score overview bar ── */}
      <div style={{
        background: 'var(--glass-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        padding: '16px 18px',
      }}>
        <h3 style={{
          fontSize: 11, fontWeight: 700, color: 'var(--text-muted)',
          margin: '0 0 12px', textTransform: 'uppercase', letterSpacing: '0.1em',
        }}>
          Score Overview
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {report.dimensions.map(dim => {
            const color = gradeColor(dim.grade);
            return (
              <div key={dim.name} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 11, color: 'var(--text-secondary)', minWidth: 100, fontWeight: 500 }}>
                  {dim.name}
                </span>
                <div style={{ flex: 1 }}>
                  <ScoreBar score={dim.score} color={color} height={7} />
                </div>
                <span style={{
                  fontSize: 11, fontFamily: 'var(--font-mono)',
                  color, fontWeight: 700, minWidth: 40, textAlign: 'right',
                }}>
                  {dim.score}
                </span>
                <span style={{
                  fontSize: 10, fontWeight: 700, color,
                  background: `${color}18`, border: `1px solid ${color}30`,
                  padding: '1px 6px', borderRadius: 5, minWidth: 20, textAlign: 'center',
                }}>
                  {dim.grade}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Issues ── */}
      <IssuesPanel issues={report.issues} />

    </div>
  );
}
