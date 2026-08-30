// =============================================================================
// RepositoryOverview — "Understand this repository" experience
// Shows purpose, languages, health, structure, risks, and starting point
// =============================================================================

'use client';

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useOverview } from '../hooks/useOverview';
import { DeltaIntelligence } from '@/features/delta';
import { AnswerView, overviewToAnswer } from '@/features/answer';
import { CoverageConfidence } from '@/components/answer';

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

// ── Main Component ────────────────────────────────────────────────────────────
export default function RepositoryOverview({ jobId }: RepositoryOverviewProps) {
  const { overview, health, coverage, isLoading, error } = useOverview(jobId);

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
        flexWrap: 'wrap',
      }}>
        {h && <ScoreRing score={h.overall_score} grade={h.overall_grade} />}
        <div style={{ flex: 1, minWidth: 200 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)', margin: '0 0 4px' }}>
            {o.repo_name}
          </h2>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 8px', fontFamily: 'var(--font-mono)', overflowWrap: 'anywhere', wordBreak: 'break-word' }}>
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

      {/* ── Coverage + Confidence (per analysis) ─────────────────────────── */}
      {/* Req 6.4: the analysis surfaces both Coverage and Confidence through   */}
      {/* the same shared component the per-answer banner uses. Confidence is   */}
      {/* the overall health score; Coverage is analyzed vs. total files from   */}
      {/* the real analysis coverage when available.                            */}
      <CoverageConfidence
        confidence={(h?.overall_score ?? o.overall_score) / 100}
        coverage={
          coverage
            ? {
                totalFiles: Math.max(coverage.source_files, coverage.analyzed_files),
                analyzedFiles: coverage.analyzed_files,
              }
            : null
        }
        coverageNote={
          coverage
            ? null
            : 'Detailed file coverage is not available for this analysis yet.'
        }
      />

      {/* ── Delta Intelligence (since last analysis) ─────────────────────── */}
      <DeltaIntelligence jobId={jobId} />

      {/* ── Structured overview ───────────────────────────────────────────── */}
      {/* Structure, health, quality, and risks are rendered through the shared */}
      {/* AnswerRenderer so this view matches every other CortexAnswer output   */}
      {/* (Req 4.4, Req 8.2). The header + score ring above stay as chrome       */}
      {/* around the same underlying facts.                                     */}
      <AnswerView answer={overviewToAnswer(o, h ?? null)} />
    </div>
  );
}
