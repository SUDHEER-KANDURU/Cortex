// =============================================================================
// RepositoryOverview — "Understand this repository" experience
// Shows purpose, languages, health, structure, risks, and starting point
// =============================================================================

'use client';

import React from 'react';
import {
  Code2, FileText, Layers, Shield, Activity,
  BookOpen, AlertTriangle, CheckCircle2, Zap,
  Globe,
} from 'lucide-react';
import { useOverview } from '../hooks/useOverview';
import type { HealthDimension } from '@/lib/api/overview.api';
import { DeltaIntelligence } from '@/features/delta';

interface RepositoryOverviewProps {
  jobId: string;
}

// ── Score Ring ────────────────────────────────────────────────────────────────
function ScoreRing({ score, grade, size = 80 }: { score: number; grade: string; size?: number }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);
  const color = score >= 80 ? '#22c55e' : score >= 60 ? '#eab308' : score >= 40 ? '#f97316' : '#ef4444';

  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth={4}
        />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={color} strokeWidth={4}
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ fontSize: size * 0.25, fontWeight: 800, color: 'var(--text)', lineHeight: 1 }}>
          {grade}
        </span>
        <span style={{ fontSize: size * 0.14, color: 'var(--text-muted)', marginTop: 2 }}>
          {score}/100
        </span>
      </div>
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────
function StatCard({ icon, label, value, subtitle }: {
  icon: React.ReactNode; label: string; value: string | number; subtitle?: string;
}) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px',
      borderRadius: 12, background: 'rgba(255,255,255,0.3)',
      border: '0.5px solid rgba(255,255,255,0.5)',
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: 8, flexShrink: 0,
        background: 'rgba(255,255,255,0.35)', border: '0.5px solid rgba(255,255,255,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--primary)',
      }}>
        {icon}
      </div>
      <div>
        <p style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', margin: 0, lineHeight: 1.2 }}>
          {typeof value === 'number' ? value.toLocaleString() : value}
        </p>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>{label}</p>
        {subtitle && <p style={{ fontSize: 10, color: 'var(--text-muted)', margin: '2px 0 0', opacity: 0.7 }}>{subtitle}</p>}
      </div>
    </div>
  );
}

// ── Dimension Bar ─────────────────────────────────────────────────────────────
function DimensionBar({ dim }: { dim: HealthDimension }) {
  const color = dim.score >= 80 ? '#22c55e' : dim.score >= 60 ? '#eab308' : dim.score >= 40 ? '#f97316' : '#ef4444';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text)', minWidth: 90 }}>
        {dim.name}
      </span>
      <div style={{
        flex: 1, height: 6, borderRadius: 3,
        background: 'rgba(255,255,255,0.2)', overflow: 'hidden',
      }}>
        <div style={{
          width: `${dim.score}%`, height: '100%', borderRadius: 3,
          background: color, transition: 'width 0.6s ease',
        }} />
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, color, minWidth: 24, textAlign: 'right' }}>
        {dim.grade}
      </span>
      {dim.issue_count > 0 && (
        <span style={{
          fontSize: 9, padding: '2px 6px', borderRadius: 6,
          background: 'rgba(255,100,50,0.08)', color: '#f97316',
          fontWeight: 600,
        }}>
          {dim.issue_count}
        </span>
      )}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function RepositoryOverview({ jobId }: RepositoryOverviewProps) {
  const { overview, health, isLoading, error } = useOverview(jobId);

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="cortex-pulse" style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--primary)' }} />
          <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading overview...</span>
        </div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div style={{ padding: '40px 20px', textAlign: 'center' }}>
        <AlertTriangle style={{ width: 20, height: 20, color: 'var(--text-muted)', margin: '0 auto 10px' }} />
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{error || 'Overview not available'}</p>
      </div>
    );
  }

  const o = overview;
  const h = health;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* ── Header Section ────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 20, padding: '20px 24px',
        borderRadius: 14, background: 'rgba(255,255,255,0.35)',
        border: '0.5px solid rgba(255,255,255,0.55)',
      }}>
        {h && <ScoreRing score={h.overall_score} grade={h.overall_grade} />}
        <div style={{ flex: 1 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)', margin: '0 0 4px' }}>
            {o.repo_name}
          </h2>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 8px', fontFamily: 'var(--font-mono)' }}>
            {o.repo_url}
          </p>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {o.languages.map((lang) => (
              <span key={lang} style={{
                fontSize: 10, padding: '3px 8px', borderRadius: 6,
                background: 'var(--primary-dim)', color: 'var(--primary)',
                fontWeight: 600, fontFamily: 'var(--font-mono)',
              }}>
                {lang}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ── Delta Intelligence (since last analysis) ─────────────────────── */}
      <DeltaIntelligence jobId={jobId} />

      {/* ── Structure Stats ───────────────────────────────────────────────── */}
      <div>
        <h3 style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 10px', fontFamily: 'var(--font-mono)' }}>
          Repository Structure
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 8 }}>
          <StatCard icon={<Layers style={{ width: 14, height: 14 }} />} label="Modules" value={o.total_modules} subtitle="Separate concerns" />
          <StatCard icon={<FileText style={{ width: 14, height: 14 }} />} label="Source Files" value={o.total_files} subtitle={`${o.total_lines.toLocaleString()} lines`} />
          <StatCard icon={<Code2 style={{ width: 14, height: 14 }} />} label="Classes" value={o.total_classes} />
          <StatCard icon={<Zap style={{ width: 14, height: 14 }} />} label="Functions" value={o.total_functions} />
          <StatCard icon={<Globe style={{ width: 14, height: 14 }} />} label="API Endpoints" value={o.total_endpoints} />
          <StatCard icon={<Shield style={{ width: 14, height: 14 }} />} label="Test Functions" value={o.total_tests} subtitle={`ratio: ${o.test_ratio}`} />
        </div>
      </div>

      {/* ── Health Dimensions ─────────────────────────────────────────────── */}
      {h && (
        <div>
          <h3 style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 10px', fontFamily: 'var(--font-mono)' }}>
            Engineering Health
          </h3>
          <div style={{
            display: 'flex', flexDirection: 'column', gap: 8, padding: '14px 16px',
            borderRadius: 12, background: 'rgba(255,255,255,0.3)',
            border: '0.5px solid rgba(255,255,255,0.5)',
          }}>
            {h.dimensions.map((dim) => (
              <DimensionBar key={dim.name} dim={dim} />
            ))}
          </div>
        </div>
      )}

      {/* ── Quality Metrics ───────────────────────────────────────────────── */}
      <div>
        <h3 style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 10px', fontFamily: 'var(--font-mono)' }}>
          Quality Indicators
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 8 }}>
          <QualityIndicator
            label="Avg Complexity"
            value={o.avg_complexity.toFixed(1)}
            status={o.avg_complexity < 5 ? 'good' : o.avg_complexity < 10 ? 'warning' : 'danger'}
            description={o.avg_complexity < 5 ? 'Clean and simple' : o.avg_complexity < 10 ? 'Some complex areas' : 'High complexity risk'}
          />
          <QualityIndicator
            label="Documentation"
            value={`${Math.round(o.documentation_ratio * 100)}%`}
            status={o.documentation_ratio >= 0.6 ? 'good' : o.documentation_ratio >= 0.3 ? 'warning' : 'danger'}
            description={o.documentation_ratio >= 0.6 ? 'Well documented' : o.documentation_ratio >= 0.3 ? 'Needs more docs' : 'Mostly undocumented'}
          />
          <QualityIndicator
            label="Test Coverage"
            value={`${Math.round(o.test_ratio * 100)}%`}
            status={o.test_ratio >= 0.4 ? 'good' : o.test_ratio >= 0.2 ? 'warning' : 'danger'}
            description={o.test_ratio >= 0.4 ? 'Good coverage' : o.test_ratio >= 0.2 ? 'Partial coverage' : 'Needs more tests'}
          />
        </div>
      </div>

      {/* ── Top Issues ────────────────────────────────────────────────────── */}
      {h && h.top_issues.length > 0 && (
        <div>
          <h3 style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 10px', fontFamily: 'var(--font-mono)' }}>
            Top Risks
          </h3>
          <div style={{
            display: 'flex', flexDirection: 'column', gap: 6, padding: '12px 14px',
            borderRadius: 12, background: 'rgba(255,255,255,0.3)',
            border: '0.5px solid rgba(255,255,255,0.5)',
          }}>
            {h.top_issues.slice(0, 5).map((issue, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                <span style={{
                  fontSize: 9, padding: '2px 6px', borderRadius: 4, marginTop: 2,
                  background: issue.severity === 'critical' || issue.severity === 'high' ? 'rgba(239,68,68,0.08)' : 'rgba(245,158,11,0.08)',
                  color: issue.severity === 'critical' || issue.severity === 'high' ? '#ef4444' : '#f59e0b',
                  fontWeight: 700, textTransform: 'uppercase', flexShrink: 0,
                }}>
                  {issue.severity}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', margin: 0, lineHeight: 1.3 }}>
                    {issue.title}
                  </p>
                  {issue.symbol && (
                    <p style={{ fontSize: 10, color: 'var(--text-muted)', margin: '2px 0 0', fontFamily: 'var(--font-mono)' }}>
                      {issue.symbol} {issue.file_path && `in ${issue.file_path.split('/').pop()}`}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Starting Point ────────────────────────────────────────────────── */}
      <div style={{
        padding: '16px 18px', borderRadius: 12,
        background: 'var(--primary-dim)', border: '0.5px solid rgba(255,255,255,0.4)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <BookOpen style={{ width: 14, height: 14, color: 'var(--primary)' }} />
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--primary)' }}>Where to Start</span>
        </div>
        <p style={{ fontSize: 12, color: 'var(--text)', margin: 0, lineHeight: 1.6 }}>
          This is a <strong>{o.languages[0] || 'multi-language'}</strong> project with{' '}
          <strong>{o.total_modules} modules</strong> and{' '}
          <strong>{o.total_endpoints} API endpoints</strong>.{' '}
          {o.overall_score >= 70
            ? 'The codebase is well-structured. Start with the API endpoints to understand the public interface, then trace into the service layer.'
            : o.overall_score >= 50
            ? 'The codebase has some areas needing attention. Start with entry points, then review the health dimensions above to prioritize learning.'
            : 'This codebase needs significant improvement. Focus on understanding the coupling hotspots and complexity risks before making changes.'
          }
        </p>
      </div>
    </div>
  );
}

// ── Quality Indicator ─────────────────────────────────────────────────────────
function QualityIndicator({ label, value, status, description }: {
  label: string; value: string; status: 'good' | 'warning' | 'danger'; description: string;
}) {
  const colors = {
    good: { bg: 'rgba(34,197,94,0.06)', border: 'rgba(34,197,94,0.2)', text: '#22c55e' },
    warning: { bg: 'rgba(234,179,8,0.06)', border: 'rgba(234,179,8,0.2)', text: '#eab308' },
    danger: { bg: 'rgba(239,68,68,0.06)', border: 'rgba(239,68,68,0.2)', text: '#ef4444' },
  };
  const c = colors[status];
  const Icon = status === 'good' ? CheckCircle2 : status === 'warning' ? Activity : AlertTriangle;

  return (
    <div style={{
      padding: '12px 14px', borderRadius: 10,
      background: c.bg, border: `0.5px solid ${c.border}`,
      display: 'flex', flexDirection: 'column', gap: 4,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <Icon style={{ width: 12, height: 12, color: c.text }} />
        <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)' }}>{label}</span>
      </div>
      <span style={{ fontSize: 18, fontWeight: 800, color: c.text }}>{value}</span>
      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{description}</span>
    </div>
  );
}
