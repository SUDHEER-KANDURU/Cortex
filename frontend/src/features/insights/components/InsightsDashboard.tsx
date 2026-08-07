// =============================================================================
// InsightsDashboard — Engineering health report for a completed job
// Uses CSS variables only — fully theme-aware.
// =============================================================================

'use client';

import React, { useState, useCallback } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import type { InsightsReport, HealthDimension, CodeIssue, IssueSeverity } from '@/types';
import { exportInsightsMarkdown } from '@/lib/api/insights.api';
import { staggerFastContainer, staggerFastChild, SPRING } from '@/lib/utils/motion';

// ── Helpers ───────────────────────────────────────────────────────────────────

function gradeColor(grade: string): string {
  switch (grade) {
    case 'A': return 'var(--success)';
    case 'B': return '#60C060';
    case 'C': return 'var(--warning)';
    case 'D': return '#E8772A';
    case 'F': return 'var(--danger)';
    default:  return 'var(--text-muted)';
  }
}

function severityColor(sev: IssueSeverity): string {
  switch (sev) {
    case 'high':   return 'var(--danger)';
    case 'medium': return 'var(--warning)';
    case 'low':    return 'var(--success)';
    default:       return 'var(--text-muted)';
  }
}

function severityIcon(sev: IssueSeverity): string {
  switch (sev) {
    case 'high':   return '🔴';
    case 'medium': return '🟡';
    case 'low':    return '🟢';
    default:       return '⚪';
  }
}

function scoreBar(score: number, color: string) {
  return (
    <div style={{
      width: '100%', height: 6, borderRadius: 3,
      background: 'rgba(255,255,255,0.07)',
      overflow: 'hidden',
    }}>
      <div style={{
        width: `${score}%`, height: '100%',
        background: color,
        borderRadius: 3,
        transition: 'width 0.6s cubic-bezier(0.16,1,0.3,1)',
      }} />
    </div>
  );
}

// ── Score Ring ────────────────────────────────────────────────────────────────

function ScoreRing({ score, grade }: { score: number; grade: string }) {
  const r = 44;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color = gradeColor(grade);

  return (
    <div style={{ position: 'relative', width: 120, height: 120, flexShrink: 0 }}>
      <svg width={120} height={120} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={60} cy={60} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={10} />
        <circle
          cx={60} cy={60} r={r} fill="none"
          stroke={color} strokeWidth={10}
          strokeDasharray={`${fill} ${circ - fill}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.8s cubic-bezier(0.16,1,0.3,1)' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ fontSize: 26, fontWeight: 700, color, lineHeight: 1 }}>{score}</span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>/ 100</span>
      </div>
    </div>
  );
}

// ── Dimension Card ────────────────────────────────────────────────────────────

function DimensionCard({ dim }: { dim: HealthDimension }) {
  const [expanded, setExpanded] = useState(false);
  const color = gradeColor(dim.grade);

  return (
    <div
      style={{
        background: 'var(--glass-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        padding: '16px 18px',
        cursor: 'pointer',
        transition: 'border-color 0.2s',
      }}
      onClick={() => setExpanded(e => !e)}
      onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border-hover)')}
      onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
        <span style={{
          fontSize: 20, fontWeight: 800, color,
          fontFamily: 'var(--font-mono)', minWidth: 28,
        }}>
          {dim.grade}
        </span>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{dim.name}</span>
            <span style={{ fontSize: 12, color, fontWeight: 600 }}>{dim.score}/100</span>
          </div>
          {scoreBar(dim.score, color)}
        </div>
        <span style={{
          fontSize: 10, color: 'var(--text-muted)', transform: expanded ? 'rotate(180deg)' : 'none',
          transition: 'transform 0.2s', marginLeft: 4,
        }}>▼</span>
      </div>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>{dim.summary}</p>

      {expanded && dim.metrics.length > 0 && (
        <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {dim.metrics.map(m => (
            <div key={m.label}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{m.label}</span>
                <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: gradeColor(m.score >= 80 ? 'A' : m.score >= 65 ? 'B' : m.score >= 50 ? 'C' : 'D') }}>
                  {m.raw_value} {m.unit}
                </span>
              </div>
              {scoreBar(m.score, 'var(--accent)')}
              <p style={{ fontSize: 10, color: 'var(--text-muted)', margin: '3px 0 0' }}>{m.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Issue Row ─────────────────────────────────────────────────────────────────

function IssueRow({ issue }: { issue: CodeIssue }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.025)',
        border: '1px solid var(--border)',
        borderLeft: `3px solid ${severityColor(issue.severity)}`,
        borderRadius: 'var(--radius-sm)',
        padding: '10px 14px',
        cursor: 'pointer',
        transition: 'background 0.15s',
      }}
      onClick={() => setExpanded(e => !e)}
      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.025)')}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
        <span style={{ fontSize: 13, lineHeight: 1.4, flexShrink: 0 }}>{severityIcon(issue.severity)}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{issue.title}</span>
            <span style={{
              fontSize: 10, padding: '2px 6px', borderRadius: 4,
              background: 'rgba(255,255,255,0.07)', color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.05em',
            }}>
              {issue.category}
            </span>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '4px 0 0', lineHeight: 1.5 }}>
            {issue.description}
          </p>
          {issue.file_path && (
            <p style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', margin: '3px 0 0' }}>
              {issue.file_path}{issue.line > 0 ? `:${issue.line}` : ''}
            </p>
          )}
        </div>
      </div>
      {expanded && (
        <div style={{
          marginTop: 10, padding: '10px 12px',
          background: 'rgba(0,229,168,0.05)',
          border: '1px solid rgba(0,229,168,0.15)',
          borderRadius: 6,
        }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--primary)', display: 'block', marginBottom: 4 }}>
            💡 Suggestion
          </span>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.6 }}>
            {issue.suggestion}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Stats Row ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  return (
    <div style={{
      background: 'var(--glass-card)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)',
      padding: '14px 16px',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)', fontFamily: 'var(--font-mono)' }}>
        {value}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{label}</div>
      {sub && <div style={{ fontSize: 10, color: 'var(--text-faint)', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

interface Props {
  report: InsightsReport;
  isDark: boolean;
}

type SeverityFilter = 'all' | IssueSeverity;

export default function InsightsDashboard({ report, isDark }: Props) {
  const [issueFilter, setIssueFilter] = useState<SeverityFilter>('all');
  const [exporting, setExporting] = useState(false);
  const prefersReduced = useReducedMotion();

  const filteredIssues = issueFilter === 'all'
    ? report.issues
    : report.issues.filter(i => i.severity === issueFilter);

  const handleExport = useCallback(async () => {
    setExporting(true);
    try {
      const md = await exportInsightsMarkdown(report.job_id);
      const blob = new Blob([md], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.repo_name}-engineering-report.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silent — export is non-critical
    } finally {
      setExporting(false);
    }
  }, [report.job_id, report.repo_name]);

  const cardBg = isDark
    ? 'rgba(13,17,27,0.82)'
    : 'rgba(255,255,255,0.92)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, padding: '4px 0' }}>

      {/* ── Header ── */}
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
          <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text)', margin: '0 0 4px' }}>
            {report.repo_name}
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '0 0 10px' }}>
            Engineering Health Report
          </p>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{
              padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600,
              background: `${gradeColor(report.overall_grade)}20`,
              color: gradeColor(report.overall_grade),
              border: `1px solid ${gradeColor(report.overall_grade)}40`,
            }}>
              Grade {report.overall_grade}
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {report.stats.total_issues} issues · {report.stats.files} files · {report.stats.classes} classes
            </span>
          </div>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting}
          style={{
            padding: '8px 16px', borderRadius: 8, fontSize: 12, fontWeight: 600,
            background: 'var(--primary-dim)', color: 'var(--primary)',
            border: '1px solid rgba(0,229,168,0.25)', cursor: exporting ? 'wait' : 'pointer',
            transition: 'background 0.2s', flexShrink: 0,
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--primary-glow)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'var(--primary-dim)')}
        >
          {exporting ? 'Exporting…' : '↓ Export .md'}
        </button>
      </div>

      {/* ── Stats strip ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(100px,1fr))', gap: 10 }}>
        <StatCard label="Nodes" value={report.stats.total_nodes} />
        <StatCard label="Files" value={report.stats.files} />
        <StatCard label="Classes" value={report.stats.classes} />
        <StatCard label="Functions" value={report.stats.functions} />
        <StatCard label="Modules" value={report.stats.modules} />
        <StatCard label="Edges" value={report.stats.total_edges} />
        <StatCard label="High Issues" value={report.stats.high_issues} sub="critical" />
        <StatCard label="Med Issues" value={report.stats.medium_issues} sub="warning" />
      </div>

      {/* ── Dimensions ── */}
      <div>
        <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', margin: '0 0 10px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
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

      {/* ── Issues ── */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Issues ({filteredIssues.length})
          </h3>
          <div style={{ display: 'flex', gap: 6 }}>
            {(['all', 'high', 'medium', 'low'] as const).map(sev => (
              <button
                key={sev}
                onClick={() => setIssueFilter(sev)}
                style={{
                  padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600,
                  cursor: 'pointer', transition: 'all 0.15s',
                  background: issueFilter === sev
                    ? (sev === 'all' ? 'var(--accent-dim)' : `${severityColor(sev as IssueSeverity)}20`)
                    : 'transparent',
                  color: issueFilter === sev
                    ? (sev === 'all' ? 'var(--accent)' : severityColor(sev as IssueSeverity))
                    : 'var(--text-muted)',
                  border: `1px solid ${issueFilter === sev
                    ? (sev === 'all' ? 'var(--accent)' : severityColor(sev as IssueSeverity))
                    : 'var(--border)'}`,
                }}
              >
                {sev === 'all' ? 'All' : sev.charAt(0).toUpperCase() + sev.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {filteredIssues.length === 0 ? (
          <div style={{
            padding: '32px 24px', textAlign: 'center',
            background: 'var(--glass-card)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
          }}>
            <p style={{ fontSize: 14, color: 'var(--text-muted)', margin: 0 }}>
              ✅ No {issueFilter === 'all' ? '' : issueFilter + ' '}issues detected.
            </p>
          </div>
        ) : (
          <motion.div
            style={{ display: 'flex', flexDirection: 'column', gap: 6 }}
            variants={prefersReduced ? undefined : staggerFastContainer}
            initial={prefersReduced ? false : 'hidden'}
            animate="visible"
          >
            {filteredIssues.slice(0, 30).map((issue, i) => (
              <motion.div key={`${issue.title}-${i}`} variants={prefersReduced ? undefined : staggerFastChild}>
                <IssueRow issue={issue} />
              </motion.div>
            ))}
            {filteredIssues.length > 30 && (
              <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', margin: '8px 0 0' }}>
                + {filteredIssues.length - 30} more issues — export the report to see all.
              </p>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}
