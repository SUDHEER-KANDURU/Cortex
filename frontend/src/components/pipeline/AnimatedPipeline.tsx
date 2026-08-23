// =============================================================================
// AnimatedPipeline — Full Framer Motion pipeline with living animations
// Apple Vision Pro / Stripe Radar / Linear / GitHub Actions inspired
// =============================================================================

'use client';

import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence, useAnimationControls } from 'framer-motion';
import { GitBranch, Cpu, Database, FileCode } from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────
export type PipelineStatus = 'idle' | 'running' | 'completed' | 'failed';
export type StageKey = 'clone' | 'parse' | 'graph' | 'generate';
export type StageStatus = 'pending' | 'active' | 'done' | 'failed';

export interface PipelineStage {
  key: StageKey;
  label: string;
  sublabel: string;
  Icon: React.ComponentType<{ style?: React.CSSProperties }>;
  logLine: string;
}

export interface AnimatedPipelineProps {
  jobId: string;
  isDark: boolean;
  /** Optional: real stage index from backend (0-3). Falls back to timed cycling. */
  activeStageIndex?: number;
  /** If set, pipeline shows failure on this stage index */
  failedStageIndex?: number;
  /** Called when completion sequence ends — parent swaps in artifact viewer */
  onCompletionEnd?: () => void;
  pipelineStatus?: PipelineStatus;
}

// ── Constants ─────────────────────────────────────────────────────────────────
export const PIPELINE_STAGES: PipelineStage[] = [
  { key: 'clone',    label: 'Clone Repository', sublabel: 'Fetching source',      Icon: GitBranch, logLine: 'Cloning repository into /tmp/cortex-work…'    },
  { key: 'parse',    label: 'Parse AST',         sublabel: 'Analysing structure',  Icon: Cpu,       logLine: 'Parsing AST nodes and resolving imports…'      },
  { key: 'graph',    label: 'Build Knowledge Graph', sublabel: 'Mapping relations', Icon: Database,  logLine: 'Writing graph nodes and relationships…'        },
  { key: 'generate', label: 'Generate Artifact', sublabel: 'Producing output',    Icon: FileCode,  logLine: 'Generating artifact from graph traversal…'     },
];

// Easing curves
const SPRING = { type: 'spring', stiffness: 320, damping: 28 } as const;
const EASE_OUT = [0.16, 1, 0.3, 1] as const;

// Colors — all token-driven, no hardcoded teal
const C_PRIMARY   = 'var(--primary)';
const C_SUCCESS   = 'var(--success)';
const C_DANGER    = 'var(--danger)';
const C_MUTED     = 'var(--text-muted)';
const C_TEXT      = 'var(--text)';
const C_TEXT_SEC  = 'var(--text-secondary)';

// Theme helpers — token-driven, no hardcoded rgba
function tint(d: boolean, s: 'xs' | 'sm' | 'md' = 'sm') {
  const dk = { xs: 'rgba(255,255,255,0.02)', sm: 'rgba(255,255,255,0.04)', md: 'rgba(255,255,255,0.07)' };
  const lt = { xs: 'rgba(0,0,0,0.02)',       sm: 'rgba(0,0,0,0.035)',      md: 'rgba(0,0,0,0.06)'      };
  return d ? dk[s] : lt[s];
}
function tintBorder(d: boolean) { return d ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)'; }
function logBg(d: boolean)      { return d ? 'rgba(0,0,0,0.30)'       : 'rgba(0,0,0,0.03)'; }

// ── SVG Checkmark (drawn with stroke animation) ───────────────────────────────
function AnimatedCheckmark() {
  return (
    <motion.svg
      width="20" height="20" viewBox="0 0 20 20" fill="none"
      aria-hidden="true"
      initial="hidden"
      animate="visible"
    >
      <motion.circle
        cx="10" cy="10" r="9"
        stroke={C_SUCCESS} strokeWidth="1.5"
        fill="none"
        variants={{
          hidden: { pathLength: 0, opacity: 0 },
          visible: { pathLength: 1, opacity: 1, transition: { duration: 0.4, ease: EASE_OUT } },
        }}
      />
      <motion.path
        d="M6 10.5 L9 13.5 L14 8"
        stroke={C_SUCCESS} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
        fill="none"
        variants={{
          hidden: { pathLength: 0, opacity: 0 },
          visible: { pathLength: 1, opacity: 1, transition: { duration: 0.35, delay: 0.25, ease: EASE_OUT } },
        }}
      />
    </motion.svg>
  );
}

// ── SVG Error X ───────────────────────────────────────────────────────────────
function AnimatedErrorX() {
  return (
    <motion.svg
      width="20" height="20" viewBox="0 0 20 20" fill="none"
      aria-hidden="true"
      initial="hidden" animate="visible"
    >
      <motion.circle
        cx="10" cy="10" r="9" stroke={C_DANGER} strokeWidth="1.5" fill="none"
        variants={{
          hidden: { pathLength: 0, opacity: 0 },
          visible: { pathLength: 1, opacity: 1, transition: { duration: 0.35, ease: EASE_OUT } },
        }}
      />
      <motion.path
        d="M7 7 L13 13 M13 7 L7 13"
        stroke={C_DANGER} strokeWidth="1.8" strokeLinecap="round"
        fill="none"
        variants={{
          hidden: { pathLength: 0, opacity: 0 },
          visible: { pathLength: 1, opacity: 1, transition: { duration: 0.3, delay: 0.2, ease: EASE_OUT } },
        }}
      />
    </motion.svg>
  );
}

// ── Connector line with liquid pulse ─────────────────────────────────────────
interface ConnectorProps {
  state: 'pending' | 'flowing' | 'done';
  isDark: boolean;
}

function Connector({ state, isDark }: ConnectorProps) {
  const bdr = tintBorder(isDark);
  return (
    <div style={{ position: 'relative', width: 52, height: 2, margin: '0 2px', marginBottom: 28, flexShrink: 0 }} aria-hidden="true">
      {/* Base track */}
      <div style={{ position: 'absolute', inset: 0, borderRadius: 2, background: bdr }} />

      {/* Filled state (done) */}
      <AnimatePresence>
        {(state === 'done' || state === 'flowing') && (
          <motion.div
            key="fill"
            style={{
              position: 'absolute', top: 0, bottom: 0, left: 0,
              borderRadius: 2,
              background: 'var(--success)',
              transformOrigin: 'left center',
            }}
            initial={{ scaleX: 0, opacity: 0 }}
            animate={{ scaleX: 1, opacity: 0.8 }}
            transition={{ duration: 0.55, ease: EASE_OUT }}
          />
        )}
      </AnimatePresence>

      {/* Liquid pulse — soft, not neon */}
      <AnimatePresence>
        {state === 'flowing' && (
          <motion.div
            key="pulse"
            style={{
              position: 'absolute', top: -2, width: 12, height: 6,
              borderRadius: 3,
              background: 'var(--primary)',
              opacity: 0.7,
            }}
            initial={{ left: 0, opacity: 0 }}
            animate={{ left: '100%', opacity: [0, 0.7, 0.7, 0] }}
            transition={{ duration: 0.5, ease: 'easeInOut', repeat: Infinity, repeatDelay: 0.3 }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Pipeline node ─────────────────────────────────────────────────────────────
interface PipelineNodeProps {
  stage: PipelineStage;
  status: StageStatus;
  index: number;
  isDark: boolean;
}

function PipelineNode({ stage, status, index, isDark }: PipelineNodeProps) {
  const { Icon } = stage;
  const isActive  = status === 'active';
  const isDone    = status === 'done';
  const isFailed  = status === 'failed';
  const isPending = status === 'pending';

  const ringControls = useAnimationControls();

  // Rotating outer ring while active
  useEffect(() => {
    if (isActive) {
      ringControls.start({ rotate: 360, transition: { duration: 2.8, ease: 'linear', repeat: Infinity } });
    } else {
      ringControls.stop();
      ringControls.set({ rotate: 0 });
    }
  }, [isActive, ringControls]);

  // Circle border color
  const borderColor = isFailed ? C_DANGER
    : isDone                   ? C_SUCCESS
    : isActive                 ? C_PRIMARY
    : tintBorder(isDark);

  // Circle bg
  const circleBg = isFailed ? (isDark ? 'rgba(239,83,80,0.12)' : 'rgba(239,83,80,0.08)')
    : (isDone || isActive)   ? 'var(--primary-dim)'
    : tint(isDark, 'xs');

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.07, ease: EASE_OUT }}
      style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, position: 'relative' }}
    >
      {/* Node circle wrapper — handles entry scale */}
      <motion.div
        animate={isActive ? { scale: [0.96, 1.0, 0.96] } : isDone ? { scale: 1 } : { scale: 0.97 }}
        transition={isActive
          ? { duration: 2.2, ease: 'easeInOut', repeat: Infinity }
          : { ...SPRING }}
        style={{ position: 'relative', width: 52, height: 52 }}
      >
        {/* Rotating dashed ring (active only) */}
        <AnimatePresence>
          {isActive && (
            <motion.div
              key="ring"
              initial={{ opacity: 0, scale: 0.7 }}
              animate={ringControls}
              exit={{ opacity: 0, scale: 0.7, transition: { duration: 0.3 } }}
              style={{
                position: 'absolute', inset: -6, borderRadius: '50%',
                border: `1.5px dashed var(--border-hover)`,
                pointerEvents: 'none',
              }}
            />
          )}
        </AnimatePresence>

        {/* Glow halo — very soft */}
        <AnimatePresence>
          {(isActive || isDone) && (
            <motion.div
              key="glow"
              initial={{ opacity: 0 }}
              animate={{ opacity: isActive ? [0.25, 0.5, 0.25] : 0.3 }}
              exit={{ opacity: 0 }}
              transition={isActive
                ? { duration: 2.2, ease: 'easeInOut', repeat: Infinity }
                : { duration: 0.5 }}
              style={{
                position: 'absolute', inset: -8, borderRadius: '50%',
                background: isFailed
                  ? 'radial-gradient(circle, var(--danger-dim) 0%, transparent 70%)'
                  : 'radial-gradient(circle, var(--primary-dim) 0%, transparent 70%)',
                pointerEvents: 'none',
              }}
            />
          )}
        </AnimatePresence>

        {/* Inner circle */}
        <motion.div
          animate={isFailed ? { x: [0, -4, 4, -3, 3, 0] } : {}}
          transition={isFailed ? { duration: 0.5, ease: 'easeInOut' } : {}}
          style={{
            width: 52, height: 52, borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: circleBg,
            border: `1.5px solid ${borderColor}`,
            boxShadow: isActive
              ? `0 0 0 1px ${borderColor}, var(--shadow-sm)`
              : isDone
              ? 'var(--shadow-sm)'
              : isFailed
              ? `0 0 8px var(--danger-dim)`
              : 'none',
            transition: 'background 0.4s ease, border-color 0.4s ease, box-shadow 0.4s ease',
            position: 'relative', zIndex: 1, overflow: 'hidden',
          }}
        >
          {/* Icon / checkmark / error */}
          <AnimatePresence mode="wait">
            {isDone ? (
              <motion.div key="check" initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0, opacity: 0 }} transition={SPRING}>
                <AnimatedCheckmark />
              </motion.div>
            ) : isFailed ? (
              <motion.div key="error" initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0, opacity: 0 }} transition={SPRING}>
                <AnimatedErrorX />
              </motion.div>
            ) : (
              <motion.div
                key="icon"
                initial={{ opacity: 0, scale: 0.6 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.6 }}
                transition={{ duration: 0.35, ease: EASE_OUT }}
              >
                <Icon style={{
                  width: 18, height: 18,
                  color: isActive ? C_PRIMARY : isPending ? C_MUTED : C_TEXT_SEC,
                  transition: 'color 0.3s ease',
                }} />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </motion.div>

      {/* Label */}
      <motion.div
        style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}
        animate={{ opacity: isPending ? 0.45 : 1 }}
        transition={{ duration: 0.4 }}
      >
        <span style={{
          fontSize: 10, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase',
          whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)',
          color: isFailed ? C_DANGER : (isDone || isActive) ? C_TEXT : C_MUTED,
          transition: 'color 0.35s ease',
        }}>
          {stage.label}
        </span>
        <span style={{
          fontSize: 9, letterSpacing: '0.04em', whiteSpace: 'nowrap',
          fontFamily: 'var(--font-mono)',
          color: isFailed ? 'rgba(239,83,80,0.7)' : (isDone || isActive) ? C_MUTED : 'transparent',
          transition: 'color 0.35s ease',
        }}>
          {stage.sublabel}
        </span>
      </motion.div>
    </motion.div>
  );
}

// ── Status pill ───────────────────────────────────────────────────────────────
interface StatusPillProps {
  elapsed: number;
  activeLabel: string;
  failed?: boolean;
}

function StatusPill({ elapsed, activeLabel, failed }: StatusPillProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.45, ease: EASE_OUT }}
      style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '9px 20px', borderRadius: 100,
        background: failed ? 'var(--danger-dim)' : 'var(--primary-dim)',
        border: `1px solid ${failed ? 'var(--danger)' : 'var(--border-hover)'}`,
        opacity: failed ? 1 : 0.9,
      }}
    >
      {/* Morphing spinner */}
      {!failed && (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1.2, ease: 'linear', repeat: Infinity }}
          style={{ position: 'relative', width: 14, height: 14, flexShrink: 0 }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <motion.circle
              cx="7" cy="7" r="5.5"
              stroke={failed ? C_DANGER : C_PRIMARY}
              strokeWidth="1.8"
              strokeLinecap="round"
              fill="none"
              strokeDasharray="22 12"
              animate={{ strokeDashoffset: [0, -34] }}
              transition={{ duration: 1.2, ease: 'linear', repeat: Infinity }}
            />
          </svg>
        </motion.div>
      )}

      {failed && (
        <motion.div
          initial={{ scale: 0 }} animate={{ scale: 1 }} transition={SPRING}
          style={{ width: 8, height: 8, borderRadius: '50%', background: C_DANGER, boxShadow: '0 0 8px rgba(239,83,80,0.6)' }}
        />
      )}

      {/* Label */}
      <AnimatePresence mode="wait">
        <motion.span
          key={activeLabel}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.3, ease: EASE_OUT }}
          style={{
            fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 600,
            color: failed ? C_DANGER : C_PRIMARY,
            whiteSpace: 'nowrap',
          }}
        >
          {failed ? 'Analysis failed' : activeLabel}
        </motion.span>
      </AnimatePresence>

      {/* Elapsed timer */}
      {!failed && (
        <span style={{
          fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)',
          fontWeight: 500, minWidth: '3ch', textAlign: 'right',
        }}>
          {elapsed}s
        </span>
      )}
    </motion.div>
  );
}

// ── Log terminal ──────────────────────────────────────────────────────────────
interface LogPanelProps {
  lines: string[];
  isDark: boolean;
}

function LogPanel({ lines, isDark }: LogPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Smooth-follow new entries
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [lines.length]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2, ease: EASE_OUT }}
      style={{
        width: '100%', maxWidth: 500,
        background: logBg(isDark), border: `1px solid ${tintBorder(isDark)}`,
        borderRadius: 'var(--radius-md)',
        fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.9,
        overflow: 'hidden',
        transition: 'background 0.3s ease, border-color 0.3s ease',
      }}
    >
      {/* Terminal header bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '8px 14px', borderBottom: `1px solid ${tintBorder(isDark)}`,
        background: isDark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)',
      }}>
        {/* macOS traffic lights — softer palette */}
        {['rgba(185,64,64,0.65)', 'rgba(172,122,42,0.65)', 'rgba(78,155,111,0.65)'].map((c, i) => (
          <div key={i} style={{ width: 7, height: 7, borderRadius: '50%', background: c }} aria-hidden="true" />
        ))}
        <span style={{ fontSize: 10, color: C_MUTED, marginLeft: 6, letterSpacing: '0.06em' }}>
          cortex · analysis log
        </span>
      </div>

      {/* Log lines */}
      <div
        ref={scrollRef}
        style={{ padding: '12px 16px', maxHeight: 140, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 0 }}
      >
        <AnimatePresence initial={false}>
          {lines.map((line, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.32, ease: EASE_OUT }}
              style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}
            >
              <span style={{
                color: i < lines.length - 1 ? C_SUCCESS : C_PRIMARY,
                fontSize: 10, lineHeight: 1.9, flexShrink: 0,
              }}>
                {i < lines.length - 1 ? '✓' : '›'}
              </span>
              <span style={{ color: i < lines.length - 1 ? C_MUTED : C_TEXT_SEC }}>
                {line}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Blinking cursor — soft primary */}
        <motion.span
          animate={{ opacity: [1, 0, 1] }}
          transition={{ duration: 1, repeat: Infinity, ease: [0, 0, 1, 1] }}
          style={{ display: 'inline-block', width: 7, height: 13, background: 'var(--primary)', opacity: 0.7, verticalAlign: 'middle', marginLeft: 20, borderRadius: 1 }}
          aria-hidden="true"
        />
      </div>
    </motion.div>
  );
}

// ── Completion flash overlay ───────────────────────────────────────────────────
function CompletionFlash() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: [0, 0.10, 0] }}
      transition={{ duration: 0.7, ease: 'easeInOut' }}
      style={{
        position: 'absolute', inset: 0, pointerEvents: 'none', borderRadius: 'inherit',
        background: 'radial-gradient(ellipse 80% 60% at 50% 50%, var(--primary-dim) 0%, transparent 70%)',
        zIndex: 10,
      }}
      aria-hidden="true"
    />
  );
}

// ── Main AnimatedPipeline component ──────────────────────────────────────────
export default function AnimatedPipeline({
  jobId,
  isDark,
  activeStageIndex,
  failedStageIndex,
  onCompletionEnd,
  pipelineStatus = 'running',
}: AnimatedPipelineProps) {

  // Internal cycling when no real stage index is provided
  const [internalStep, setInternalStep] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [logLines, setLogLines] = useState<string[]>([PIPELINE_STAGES[0].logLine]);
  const [showFlash, setShowFlash] = useState(false);
  const startRef = useRef(Date.now());
  const lastStepRef = useRef(-1);
  const isFailed = pipelineStatus === 'failed' || failedStageIndex != null;

  // Determine which step index is active
  const activeIdx = activeStageIndex ?? internalStep;

  // Timer — elapsed
  useEffect(() => {
    startRef.current = Date.now();
    const et = setInterval(() => {
      if (document.visibilityState !== 'hidden') {
        setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
      }
    }, 1000);
    return () => clearInterval(et);
  }, [jobId]);

  // Internal step advancement (only when no external index)
  useEffect(() => {
    if (activeStageIndex != null) return; // driven externally
    if (isFailed) return;
    const st = setInterval(() => {
      if (document.visibilityState !== 'hidden') {
        setInternalStep(s => (s + 1) % PIPELINE_STAGES.length);
      }
    }, 3200);
    return () => clearInterval(st);
  }, [jobId, activeStageIndex, isFailed]);

  // Append log line when step changes
  useEffect(() => {
    if (activeIdx === lastStepRef.current) return;
    lastStepRef.current = activeIdx;
    const line = PIPELINE_STAGES[activeIdx]?.logLine;
    if (line && !logLines.includes(line)) {
      // Stagger the log append slightly so it feels like it types in
      const t = setTimeout(() => setLogLines(prev => [...prev, line]), 120);
      return () => clearTimeout(t);
    }
  }, [activeIdx, logLines]);

  // Completion flash
  useEffect(() => {
    if (pipelineStatus === 'completed') {
      setShowFlash(true);
      const t = setTimeout(() => {
        setShowFlash(false);
        onCompletionEnd?.();
      }, 900);
      return () => clearTimeout(t);
    }
  }, [pipelineStatus, onCompletionEnd]);

  // Build stage statuses
  const stageStatuses: StageStatus[] = PIPELINE_STAGES.map((_, i) => {
    if (isFailed && i === (failedStageIndex ?? activeIdx)) return 'failed';
    if (pipelineStatus === 'completed' || i < activeIdx) return 'done';
    if (i === activeIdx && !isFailed) return 'active';
    return 'pending';
  });

  // Connector states
  const connectorState = (i: number): 'pending' | 'flowing' | 'done' => {
    if (stageStatuses[i] === 'done' && stageStatuses[i + 1] === 'active') return 'flowing';
    if (stageStatuses[i] === 'done') return 'done';
    return 'pending';
  };

  const activeStage = PIPELINE_STAGES[activeIdx];

  return (
    <motion.div
      layout
      style={{ display: 'flex', flexDirection: 'column', gap: 28, padding: '36px 24px', alignItems: 'center', position: 'relative' }}
    >
      {/* Completion flash */}
      <AnimatePresence>{showFlash && <CompletionFlash key="flash" />}</AnimatePresence>

      {/* Status pill */}
      <StatusPill
        elapsed={elapsed}
        activeLabel={`${activeStage?.label ?? 'Processing'}…`}
        failed={isFailed}
      />

      {/* Pipeline nodes + connectors */}
      <motion.div
        layout
        style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', justifyContent: 'center', gap: 0 }}
      >
        {PIPELINE_STAGES.map((stage, i) => (
          <React.Fragment key={stage.key}>
            <PipelineNode stage={stage} status={stageStatuses[i]} index={i} isDark={isDark} />
            {i < PIPELINE_STAGES.length - 1 && (
              <Connector state={connectorState(i)} isDark={isDark} />
            )}
          </React.Fragment>
        ))}
      </motion.div>

      {/* Log terminal */}
      <LogPanel lines={logLines} isDark={isDark} />

      {/* Hint */}
      {!isFailed && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.5 }}
          style={{ fontSize: 11, color: C_MUTED, fontFamily: 'var(--font-mono)', margin: 0 }}
        >
          This usually takes 30–60 seconds
        </motion.p>
      )}
    </motion.div>
  );
}
