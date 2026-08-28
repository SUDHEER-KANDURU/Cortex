// =============================================================================
// DeltaIntelligence — "Since your last analysis" section
// Shows score changes, improvements, degradations, structural changes
// =============================================================================

'use client';

import React, { useEffect, useState } from 'react';
import {
  TrendingUp, TrendingDown, Minus, AlertTriangle,
  CheckCircle2, GitBranch, Activity, Clock,
} from 'lucide-react';
import { getDelta, type DeltaData, type ScoreChange } from '@/lib/api/delta.api';

interface DeltaIntelligenceProps {
  jobId: string;
}

export default function DeltaIntelligence({ jobId }: DeltaIntelligenceProps) {
  const [delta, setDelta] = useState<DeltaData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);

    getDelta(jobId)
      .then((data) => {
        if (!cancelled) setDelta(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load delta');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => { cancelled = true; };
  }, [jobId]);

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '16px 0' }}>
        <div className="cortex-pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)' }} />
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Loading delta...</span>
      </div>
    );
  }

  if (error || !delta) return null;

  // First analysis — show baseline info
  if (delta.is_first_analysis) {
    return (
      <div style={{
        padding: '14px 16px', borderRadius: 12,
        background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.5)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <Clock style={{ width: 14, height: 14, color: 'var(--text-muted)' }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>
            First Analysis
          </span>
        </div>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0, lineHeight: 1.5 }}>
          This is the first time this repository has been analyzed. Re-analyze it later to see
          how the codebase health changes over time — score improvements, new issues, structural growth.
        </p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Activity style={{ width: 14, height: 14, color: 'var(--primary)' }} />
        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text)' }}>
          Since Your Last Analysis
        </span>
        <span style={{
          fontSize: 9, padding: '2px 8px', borderRadius: 10,
          background: 'rgba(255,255,255,0.3)', color: 'var(--text-muted)',
          fontWeight: 600, marginLeft: 'auto',
        }}>
          Analysis #{delta.analysis_count}
        </span>
      </div>

      {/* Overall Score Change */}
      {delta.overall_change && (
        <ScoreChangeCard change={delta.overall_change} isOverall />
      )}

      {/* Improvements */}
      {delta.improvements.length > 0 && (
        <div style={{
          padding: '10px 14px', borderRadius: 10,
          background: 'rgba(34,197,94,0.04)', border: '0.5px solid rgba(34,197,94,0.15)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <CheckCircle2 style={{ width: 12, height: 12, color: '#22c55e' }} />
            <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#22c55e' }}>
              Improvements
            </span>
          </div>
          {delta.improvements.map((imp, i) => (
            <p key={i} style={{ fontSize: 11, color: 'var(--text)', margin: '3px 0', paddingLeft: 18, lineHeight: 1.5 }}>
              • {imp}
            </p>
          ))}
        </div>
      )}

      {/* Degradations */}
      {delta.degradations.length > 0 && (
        <div style={{
          padding: '10px 14px', borderRadius: 10,
          background: 'rgba(249,115,22,0.04)', border: '0.5px solid rgba(249,115,22,0.15)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <AlertTriangle style={{ width: 12, height: 12, color: '#f97316' }} />
            <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#f97316' }}>
              Needs Attention
            </span>
          </div>
          {delta.degradations.map((deg, i) => (
            <p key={i} style={{ fontSize: 11, color: 'var(--text)', margin: '3px 0', paddingLeft: 18, lineHeight: 1.5 }}>
              • {deg}
            </p>
          ))}
        </div>
      )}

      {/* Structural Changes */}
      {delta.structural_changes.length > 0 && (
        <div style={{
          padding: '10px 14px', borderRadius: 10,
          background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.5)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <GitBranch style={{ width: 12, height: 12, color: 'var(--text-muted)' }} />
            <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              Structural Changes
            </span>
          </div>
          {delta.structural_changes.map((change, i) => (
            <p key={i} style={{ fontSize: 11, color: 'var(--text)', margin: '3px 0', paddingLeft: 18, lineHeight: 1.5 }}>
              • {change}
            </p>
          ))}
        </div>
      )}

      {/* Dimension Changes */}
      {delta.dimension_changes.length > 0 && (
        <div style={{
          padding: '10px 14px', borderRadius: 10,
          background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.5)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <Activity style={{ width: 12, height: 12, color: 'var(--text-muted)' }} />
            <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              Dimension Scores
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {delta.dimension_changes.map((dc) => (
              <DimensionChangeRow key={dc.metric} change={dc} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Score Change Card ─────────────────────────────────────────────────────────
function ScoreChangeCard({ change, isOverall }: { change: ScoreChange; isOverall?: boolean }) {
  const colors = {
    improved: { bg: 'rgba(34,197,94,0.05)', border: 'rgba(34,197,94,0.2)', text: '#22c55e', icon: TrendingUp },
    degraded: { bg: 'rgba(239,68,68,0.05)', border: 'rgba(239,68,68,0.2)', text: '#ef4444', icon: TrendingDown },
    stable: { bg: 'rgba(255,255,255,0.3)', border: 'rgba(255,255,255,0.5)', text: 'var(--text-muted)', icon: Minus },
  };
  const c = colors[change.direction];
  const Icon = c.icon;

  return (
    <div style={{
      padding: isOverall ? '16px 18px' : '10px 14px', borderRadius: 12,
      background: c.bg, border: `0.5px solid ${c.border}`,
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <div style={{
        width: isOverall ? 40 : 32, height: isOverall ? 40 : 32,
        borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: `${c.text}15`,
      }}>
        <Icon style={{ width: isOverall ? 18 : 14, height: isOverall ? 18 : 14, color: c.text }} />
      </div>
      <div style={{ flex: 1 }}>
        <p style={{ fontSize: isOverall ? 13 : 11, fontWeight: 700, color: 'var(--text)', margin: 0 }}>
          {change.metric}
        </p>
        <p style={{ fontSize: isOverall ? 11 : 10, color: 'var(--text-muted)', margin: '2px 0 0' }}>
          {change.previous.toFixed(0)} → {change.current.toFixed(0)}
        </p>
      </div>
      <div style={{ textAlign: 'right' }}>
        <span style={{
          fontSize: isOverall ? 18 : 14, fontWeight: 800, color: c.text,
        }}>
          {change.delta > 0 ? '+' : ''}{change.delta.toFixed(0)}
        </span>
      </div>
    </div>
  );
}

// ── Dimension Change Row ──────────────────────────────────────────────────────
function DimensionChangeRow({ change }: { change: ScoreChange }) {
  const Icon = change.direction === 'improved' ? TrendingUp
    : change.direction === 'degraded' ? TrendingDown : Minus;
  const color = change.direction === 'improved' ? '#22c55e'
    : change.direction === 'degraded' ? '#ef4444' : 'var(--text-muted)';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <Icon style={{ width: 10, height: 10, color, flexShrink: 0 }} />
      <span style={{ fontSize: 11, color: 'var(--text)', flex: 1, fontWeight: 500 }}>
        {change.metric}
      </span>
      <span style={{ fontSize: 11, fontWeight: 700, color, minWidth: 40, textAlign: 'right' }}>
        {change.current.toFixed(0)}/100
      </span>
      <span style={{
        fontSize: 9, color, fontWeight: 600, minWidth: 30, textAlign: 'right',
      }}>
        {change.delta > 0 ? '+' : ''}{change.delta.toFixed(0)}
      </span>
    </div>
  );
}
