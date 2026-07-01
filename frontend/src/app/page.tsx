'use client';

// =============================================================================
// Cortex Landing Page — Cinematic product story
// Apple × Linear × Vercel quality. Cube is the hero.
// =============================================================================

import dynamic from 'next/dynamic';
import { useRef, useEffect, useState } from 'react';
import { motion, useScroll, useTransform, useSpring } from 'framer-motion';

// Lazy-load WebGL components — SSR-safe
const CortexCube = dynamic(() => import('./_landing/CortexCube'), { ssr: false });
const SplitCube  = dynamic(() => import('./_landing/SplitCube'),  { ssr: false });

// ── Design tokens ──────────────────────────────────────────────────────────────

const C = {
  bg:      '#000000',
  bg1:     '#060609',
  bg2:     '#0A0A10',
  violet:  '#6B57E8',
  violet2: '#8B7BFF',
  cyan:    '#3BBBF0',
  text:    '#FFFFFF',
  text2:   '#8A8A9A',
  text3:   '#3A3A4A',
  border:  'rgba(255,255,255,0.07)',
};

const EASE = [0.16, 1, 0.3, 1] as const;

// ── Fade-up motion variant ──────────────────────────────────────────────────

const fadeUp = {
  hidden:  { opacity: 0, y: 32 },
  visible: (i = 0) => ({
    opacity: 1, y: 0,
    transition: { duration: 0.8, ease: EASE, delay: i * 0.1 },
  }),
};

// ── Navbar ──────────────────────────────────────────────────────────────────

function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);

  return (
    <motion.nav
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: EASE }}
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 200,
        height: 52,
        background: scrolled ? 'rgba(0,0,0,0.85)' : 'transparent',
        backdropFilter: scrolled ? 'blur(20px)' : 'none',
        borderBottom: scrolled ? `1px solid ${C.border}` : '1px solid transparent',
        transition: 'background 0.4s, border-color 0.4s, backdrop-filter 0.4s',
      }}
    >
      <div style={{
        maxWidth: 1120, margin: '0 auto', height: '100%',
        padding: '0 28px', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Solid cube logo mark */}
          <div style={{
            width: 22, height: 22, borderRadius: 5,
            background: `linear-gradient(135deg, ${C.violet}, ${C.violet2})`,
            boxShadow: `0 0 12px ${C.violet}66`,
          }} />
          <span style={{ color: C.text, fontWeight: 500, fontSize: 15, letterSpacing: '-0.01em' }}>
            Cortex
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
          <a href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
            style={{ color: C.text2, fontSize: 13, textDecoration: 'none', transition: 'color 0.2s' }}
            onMouseEnter={e => (e.currentTarget.style.color = C.text)}
            onMouseLeave={e => (e.currentTarget.style.color = C.text2)}>
            GitHub
          </a>
          <a href="/dashboard" style={{
            background: C.violet, color: C.text, fontSize: 13, fontWeight: 500,
            padding: '7px 18px', borderRadius: 8, textDecoration: 'none',
            transition: 'all 0.2s', boxShadow: `0 0 0 0 ${C.violet}`,
          }}
            onMouseEnter={e => { e.currentTarget.style.background = C.violet2; e.currentTarget.style.boxShadow = `0 0 20px ${C.violet}66`; }}
            onMouseLeave={e => { e.currentTarget.style.background = C.violet; e.currentTarget.style.boxShadow = 'none'; }}>
            Launch App
          </a>
        </div>
      </div>
    </motion.nav>
  );
}

// ── Hero ─────────────────────────────────────────────────────────────────────

function Hero() {
  return (
    <section style={{
      position: 'relative', height: '100vh', background: C.bg,
      display: 'flex', alignItems: 'center', overflow: 'hidden',
    }}>
      {/* Subtle radial glow behind cube */}
      <div style={{
        position: 'absolute', right: '5%', top: '50%', transform: 'translateY(-50%)',
        width: 560, height: 560, borderRadius: '50%',
        background: `radial-gradient(circle, ${C.violet}18 0%, transparent 70%)`,
        filter: 'blur(40px)', pointerEvents: 'none',
      }} />

      {/* Subtle grid */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        backgroundImage: `linear-gradient(${C.violet}08 1px, transparent 1px), linear-gradient(90deg, ${C.violet}08 1px, transparent 1px)`,
        backgroundSize: '88px 88px',
        maskImage: 'radial-gradient(ellipse 80% 80% at 60% 50%, black 30%, transparent 80%)',
        WebkitMaskImage: 'radial-gradient(ellipse 80% 80% at 60% 50%, black 30%, transparent 80%)',
      }} />

      <div style={{
        maxWidth: 1120, margin: '0 auto', padding: '0 28px',
        display: 'grid', gridTemplateColumns: '1fr 480px',
        gap: 48, alignItems: 'center', width: '100%',
      }}>
        {/* Left — copy */}
        <div>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.1 }}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              marginBottom: 32, padding: '5px 14px',
              border: `1px solid ${C.violet}44`, borderRadius: 100,
              background: `${C.violet}0A`,
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: C.violet2, boxShadow: `0 0 8px ${C.violet2}` }} />
            <span style={{ fontSize: 11, fontWeight: 500, letterSpacing: '0.13em', textTransform: 'uppercase', color: C.violet2 }}>
              Engineering Reasoning Engine
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, ease: EASE, delay: 0.2 }}
            style={{
              fontSize: 'clamp(52px, 6.5vw, 88px)', fontWeight: 200,
              letterSpacing: '-0.04em', lineHeight: 0.95,
              color: C.text, marginBottom: 24,
            }}
          >
            Understand<br />
            <span style={{ color: `${C.text}50` }}>any</span>{' '}
            <span style={{ color: C.violet2 }}>codebase.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE, delay: 0.35 }}
            style={{
              fontSize: 17, lineHeight: 1.75, color: C.text2,
              maxWidth: 440, marginBottom: 40,
            }}
          >
            Paste a GitHub URL. Cortex scans, parses, and maps your
            repository into architecture diagrams, learning paths,
            and interview prep — in seconds.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE, delay: 0.48 }}
            style={{ display: 'flex', gap: 12, alignItems: 'center' }}
          >
            <a href="/dashboard" style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              background: C.violet, color: C.text, fontWeight: 500,
              fontSize: 15, padding: '13px 26px', borderRadius: 10,
              textDecoration: 'none', transition: 'all 0.2s',
            }}
              onMouseEnter={e => { e.currentTarget.style.background = C.violet2; e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = `0 12px 32px ${C.violet}44`; }}
              onMouseLeave={e => { e.currentTarget.style.background = C.violet; e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = 'none'; }}>
              Analyze a Repository
              <span style={{ fontSize: 17 }}>→</span>
            </a>
            <a href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 8,
                color: C.text2, fontSize: 15, textDecoration: 'none',
                padding: '13px 24px', border: `1px solid ${C.border}`,
                borderRadius: 10, transition: 'all 0.2s',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = C.text; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.18)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = C.text2; e.currentTarget.style.borderColor = C.border; }}>
              View Source
            </a>
          </motion.div>

          {/* Stats row */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.7 }}
            style={{
              display: 'flex', gap: 40, marginTop: 56,
              paddingTop: 28, borderTop: `1px solid ${C.border}`,
            }}
          >
            {[['6', 'Artifact types'], ['0', 'API keys needed'], ['∞', 'Repositories']].map(([n, l]) => (
              <div key={l}>
                <div style={{ fontSize: 28, fontWeight: 200, color: C.text, letterSpacing: '-0.02em' }}>{n}</div>
                <div style={{ fontSize: 12, color: C.text3, marginTop: 3 }}>{l}</div>
              </div>
            ))}
          </motion.div>
        </div>

        {/* Right — 3D Cube */}
        <motion.div
          initial={{ opacity: 0, scale: 0.88 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.1, ease: EASE, delay: 0.3 }}
          style={{ height: 480, position: 'relative' }}
        >
          <CortexCube />
          {/* Floor shadow */}
          <div style={{
            position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)',
            width: 200, height: 24, borderRadius: '50%',
            background: `radial-gradient(ellipse, ${C.violet}30 0%, transparent 70%)`,
            filter: 'blur(8px)',
          }} />
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.4 }}
        style={{
          position: 'absolute', bottom: 32, left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
          color: C.text3, fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase',
        }}
      >
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
          style={{ width: 1, height: 32, background: `linear-gradient(to bottom, transparent, ${C.text3})` }}
        />
        scroll
      </motion.div>
    </section>
  );
}

// ── How It Works ─────────────────────────────────────────────────────────────

const PIPELINE_STEPS = [
  { n: '01', title: 'GitHub URL',       sub: 'Paste any public repository URL', color: C.violet2 },
  { n: '02', title: 'Repository Scan',  sub: 'File tree, languages, structure',  color: C.cyan },
  { n: '03', title: 'AST Parsing',      sub: 'Reads every file with deep analysis', color: C.violet2 },
  { n: '04', title: 'Knowledge Graph',  sub: 'Neo4j graph of nodes and edges',   color: C.cyan },
  { n: '05', title: 'Artifacts',        sub: 'Diagrams, paths, specs generated', color: C.violet2 },
];

function HowItWorks() {
  return (
    <section style={{
      background: `linear-gradient(180deg, ${C.bg} 0%, ${C.bg1} 100%)`,
      padding: '140px 0',
    }}>
      <div style={{ maxWidth: 1120, margin: '0 auto', padding: '0 28px' }}>
        <motion.div
          initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }}
          style={{ marginBottom: 80 }}
        >
          <motion.p variants={fadeUp} custom={0}
            style={{ fontSize: 11, fontWeight: 500, letterSpacing: '0.16em', textTransform: 'uppercase', color: C.text3, marginBottom: 16 }}>
            01 — How it works
          </motion.p>
          <motion.h2 variants={fadeUp} custom={1}
            style={{ fontSize: 'clamp(36px, 4.5vw, 64px)', fontWeight: 200, letterSpacing: '-0.03em', color: C.text, lineHeight: 1.05 }}>
            Five steps.<br />
            <span style={{ color: `${C.text}30` }}>One pipeline.</span>
          </motion.h2>
        </motion.div>

        {/* Pipeline steps */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          {PIPELINE_STEPS.map((step, i) => (
            <motion.div
              key={step.n}
              initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-60px' }}
              variants={fadeUp} custom={i * 0.5}
              style={{
                display: 'flex', alignItems: 'center', gap: 28,
                padding: '22px 28px',
                borderBottom: `1px solid ${C.border}`,
                borderTop: i === 0 ? `1px solid ${C.border}` : 'none',
              }}
              whileHover={{ background: `${C.violet}05` }}
              transition={{ duration: 0.15 }}
            >
              <span style={{
                fontFamily: 'monospace', fontSize: 12, color: step.color,
                minWidth: 32, fontWeight: 500,
              }}>{step.n}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 16, fontWeight: 400, color: C.text, marginBottom: 3 }}>{step.title}</div>
                <div style={{ fontSize: 13, color: C.text2 }}>{step.sub}</div>
              </div>
              {i < PIPELINE_STEPS.length - 1 && (
                <div style={{ width: 1, height: 32, background: `linear-gradient(to bottom, ${step.color}60, transparent)`, marginLeft: 'auto' }} />
              )}
              {i === PIPELINE_STEPS.length - 1 && (
                <span style={{ fontSize: 13, color: C.violet2, fontWeight: 500 }}>Artifacts ready →</span>
              )}
            </motion.div>
          ))}
        </div>

        {/* Terminal preview */}
        <motion.div
          initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }} transition={{ duration: 0.9, ease: EASE, delay: 0.2 }}
          style={{
            marginTop: 64, background: '#08080E',
            border: `1px solid ${C.border}`, borderRadius: 16,
            overflow: 'hidden', boxShadow: '0 48px 96px rgba(0,0,0,0.7)',
          }}
        >
          <div style={{
            padding: '12px 18px', borderBottom: `1px solid ${C.border}`,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            {['#FF5F57','#FFBD2E','#28C840'].map(c => (
              <div key={c} style={{ width: 10, height: 10, borderRadius: '50%', background: c, opacity: 0.9 }} />
            ))}
            <span style={{ marginLeft: 10, fontSize: 12, color: C.text3, fontFamily: 'monospace' }}>
              cortex — terminal
            </span>
          </div>
          <div style={{ padding: '28px 28px', fontFamily: 'monospace', fontSize: 13, lineHeight: 2.1 }}>
            {[
              { c: C.text3,   t: '$ cortex analyze github.com/myorg/api-service' },
              { c: C.violet2, t: '◆  Scanning repository structure...' },
              { c: C.text2,   t: '   → 84 files · 9 modules · Python 3.12' },
              { c: C.violet2, t: '◆  Building knowledge graph...' },
              { c: C.text2,   t: '   → 241 nodes · 387 relationships' },
              { c: C.violet2, t: '◆  Generating artifacts...' },
              { c: '#4ADE80', t: '   ✓  architecture_diagram.mermaid' },
              { c: '#4ADE80', t: '   ✓  module_breakdown.md' },
              { c: '#4ADE80', t: '   ✓  interview_questions.md' },
              { c: C.cyan,    t: '   ━━━ Done in 4.1s ━━━' },
            ].map(({ c, t }, i) => (
              <div key={i} style={{ color: c }}>{t}</div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ── Cube Split + Feature Breakdown ────────────────────────────────────────────

const FEATURES = [
  {
    q: 'top-left', color: '#5B4AE8',
    tag: 'Repository Scanner',
    title: 'Full structural analysis\nof any repository.',
    body: 'Cortex walks every file and directory, identifies languages, maps module boundaries, and extracts the skeleton of your codebase before any parsing begins.',
    detail: ['File tree mapping', 'Language detection', 'Module boundaries', 'Dependency graph'],
  },
  {
    q: 'top-right', color: '#6A59F0',
    tag: 'Analysis Engine',
    title: 'AST-level parsing,\nnot just grep.',
    body: 'Every file is read with a proper abstract syntax tree. Functions, classes, imports, and patterns are all extracted with full context and relationships preserved.',
    detail: ['Abstract syntax trees', 'Symbol resolution', 'Call graph extraction', 'Pattern recognition'],
  },
  {
    q: 'bottom-left', color: '#4438C0',
    tag: 'Knowledge Graph',
    title: 'Your codebase\nas a graph database.',
    body: 'All extracted symbols and relationships are stored in Neo4j as a queryable knowledge graph. Architecture diagrams are generated directly from this graph.',
    detail: ['Neo4j graph storage', 'Node + edge relationships', 'Mermaid diagram export', 'Live graph queries'],
  },
  {
    q: 'bottom-right', color: '#3D2FC7',
    tag: 'Learning Engine',
    title: 'Study your code.\nAce your interviews.',
    body: 'The knowledge graph powers personalized learning paths and technical interview questions — all grounded in your actual project, not generic examples.',
    detail: ['Learning path generation', 'Concept identification', 'Interview questions', 'Model answers'],
  },
];

function FeatureCard({ f, i }: { f: typeof FEATURES[0]; i: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.8, ease: EASE, delay: i * 0.08 }}
      style={{
        padding: '40px 40px', borderRadius: 20,
        border: `1px solid ${f.color}20`,
        background: `linear-gradient(135deg, ${f.color}0A 0%, ${C.bg2} 100%)`,
        position: 'relative', overflow: 'hidden',
      }}
    >
      {/* Corner glow */}
      <div style={{
        position: 'absolute', top: -60, right: -60,
        width: 200, height: 200, borderRadius: '50%',
        background: `radial-gradient(circle, ${f.color}18, transparent)`,
        pointerEvents: 'none',
      }} />

      {/* Quadrant indicator */}
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 8,
        marginBottom: 24,
      }}>
        <div style={{ width: 10, height: 10, borderRadius: 2, background: f.color }} />
        <span style={{ fontSize: 11, fontWeight: 500, letterSpacing: '0.13em', textTransform: 'uppercase', color: f.color }}>
          {f.tag}
        </span>
      </div>

      <h3 style={{
        fontSize: 'clamp(22px, 2vw, 28px)', fontWeight: 300,
        letterSpacing: '-0.025em', color: C.text, lineHeight: 1.25,
        marginBottom: 16, whiteSpace: 'pre-line',
      }}>{f.title}</h3>

      <p style={{ fontSize: 14, lineHeight: 1.75, color: C.text2, marginBottom: 28 }}>{f.body}</p>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {f.detail.map(d => (
          <span key={d} style={{
            fontSize: 12, color: C.text3,
            padding: '4px 12px',
            border: `1px solid ${C.border}`,
            borderRadius: 100, background: `${C.bg2}`,
          }}>{d}</span>
        ))}
      </div>
    </motion.div>
  );
}

function CubeSplitSection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ['start end', 'center center'] });
  const rawProgress = useTransform(scrollYProgress, [0, 1], [0, 1]);
  const springProgress = useSpring(rawProgress, { stiffness: 60, damping: 20 });
  const progressRef = useRef(0);

  useEffect(() => {
    const unsub = springProgress.on('change', (v) => { progressRef.current = v; });
    return unsub;
  }, [springProgress]);

  return (
    <section style={{ background: C.bg1, padding: '140px 0' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto', padding: '0 28px' }}>

        {/* Section header */}
        <motion.div
          initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-80px' }}
          style={{ marginBottom: 80, textAlign: 'center' }}
        >
          <motion.p variants={fadeUp} custom={0}
            style={{ fontSize: 11, fontWeight: 500, letterSpacing: '0.16em', textTransform: 'uppercase', color: C.text3, marginBottom: 16 }}>
            02 — Four capabilities
          </motion.p>
          <motion.h2 variants={fadeUp} custom={1}
            style={{ fontSize: 'clamp(36px, 4.5vw, 64px)', fontWeight: 200, letterSpacing: '-0.03em', color: C.text, lineHeight: 1.05 }}>
            One system.<br />
            <span style={{ color: `${C.text}30` }}>Four engines.</span>
          </motion.h2>
        </motion.div>

        {/* Scroll-driven split cube */}
        <div ref={sectionRef} style={{ height: 500, marginBottom: 80, position: 'relative' }}>
          <SplitCube progress={progressRef} />
          {/* Ambient glow */}
          <div style={{
            position: 'absolute', inset: 0, pointerEvents: 'none',
            background: `radial-gradient(ellipse 60% 40% at 50% 50%, ${C.violet}0C, transparent)`,
          }} />
        </div>

        {/* 2×2 feature grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {FEATURES.map((f, i) => <FeatureCard key={f.tag} f={f} i={i} />)}
        </div>
      </div>
    </section>
  );
}

// ── Tech strip ────────────────────────────────────────────────────────────────

const TECHS_A = ['Next.js 14', 'TypeScript', 'FastAPI', 'Python 3.12', 'Neo4j', 'PostgreSQL', 'Celery', 'Redis', 'React Flow', 'Docker', 'SQLAlchemy', 'Pydantic'];
const TECHS_B = [...TECHS_A]; // duplicate for seamless loop

function TechStrip() {
  return (
    <section style={{
      padding: '72px 0', background: C.bg,
      borderTop: `1px solid ${C.border}`, borderBottom: `1px solid ${C.border}`,
      overflow: 'hidden',
    }}>
      <motion.p
        initial={{ opacity: 0 }} whileInView={{ opacity: 1 }}
        viewport={{ once: true }} transition={{ duration: 0.6 }}
        style={{ fontSize: 11, fontWeight: 500, letterSpacing: '0.16em', textTransform: 'uppercase', color: C.text3, textAlign: 'center', marginBottom: 32 }}
      >
        Built on
      </motion.p>
      <div style={{
        overflow: 'hidden',
        maskImage: 'linear-gradient(to right, transparent, black 12%, black 88%, transparent)',
        WebkitMaskImage: 'linear-gradient(to right, transparent, black 12%, black 88%, transparent)',
      }}>
        <motion.div
          animate={{ x: ['0%', '-50%'] }}
          transition={{ duration: 28, ease: 'linear', repeat: Infinity }}
          style={{ display: 'flex', gap: 10, width: 'max-content' }}
        >
          {[...TECHS_A, ...TECHS_B].map((t, i) => (
            <span key={i} style={{
              display: 'inline-flex', padding: '7px 20px',
              border: `1px solid ${C.border}`, borderRadius: 100,
              fontSize: 13, color: C.text2, whiteSpace: 'nowrap',
              background: `${C.bg2}80`, flexShrink: 0,
            }}>{t}</span>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

// ── Final CTA ─────────────────────────────────────────────────────────────────

function FinalCTA() {
  return (
    <section style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: `linear-gradient(180deg, ${C.bg1} 0%, ${C.bg} 100%)`,
      textAlign: 'center', padding: '120px 24px',
      position: 'relative', overflow: 'hidden',
    }}>
      {/* Cube glow */}
      <div style={{
        position: 'absolute', width: 700, height: 700, borderRadius: '50%',
        background: `radial-gradient(circle, ${C.violet}0D 0%, transparent 70%)`,
        filter: 'blur(80px)', pointerEvents: 'none',
      }} />

      {/* Reassembled cube mark */}
      <motion.div
        initial={{ opacity: 0, scale: 0.7 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1, ease: EASE }}
        style={{
          position: 'absolute', top: '18%', left: '50%', transform: 'translateX(-50%)',
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4,
        }}
      >
        {[C.violet, C.violet2, '#4438C0', '#3D2FC7'].map((c, i) => (
          <div key={i} style={{ width: 28, height: 28, borderRadius: 4, background: c, opacity: 0.7 }} />
        ))}
      </motion.div>

      <motion.div
        initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-80px' }}
        style={{ position: 'relative', zIndex: 1, maxWidth: 680 }}
      >
        <motion.p variants={fadeUp} custom={0}
          style={{ fontSize: 11, fontWeight: 500, letterSpacing: '0.16em', textTransform: 'uppercase', color: C.text3, marginBottom: 32 }}>
          Start now — it&apos;s free
        </motion.p>

        <motion.h2 variants={fadeUp} custom={1}
          style={{ fontSize: 'clamp(48px, 6vw, 88px)', fontWeight: 200, letterSpacing: '-0.04em', lineHeight: 0.95, color: C.text, marginBottom: 48 }}>
          Your code,<br />
          <span style={{
            background: `linear-gradient(135deg, ${C.violet2}, ${C.cyan})`,
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
          }}>fully understood.</span>
        </motion.h2>

        <motion.a
          variants={fadeUp} custom={2}
          href="/dashboard"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 10,
            background: C.violet, color: C.text, fontWeight: 500, fontSize: 16,
            padding: '15px 34px', borderRadius: 12, textDecoration: 'none',
            transition: 'all 0.2s',
          }}
          whileHover={{ scale: 1.03, boxShadow: `0 16px 48px ${C.violet}55` }}
          whileTap={{ scale: 0.98 }}
        >
          Analyze a Repository
          <span style={{ fontSize: 20 }}>→</span>
        </motion.a>

        <motion.p variants={fadeUp} custom={3}
          style={{ marginTop: 56, fontSize: 13, color: C.text3 }}>
          Cortex · Built by Sudheer Kanduru · SRMIST, Chennai · 2025
        </motion.p>
      </motion.div>
    </section>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <div style={{ background: C.bg, minHeight: '100vh' }}>
      <Navbar />
      <Hero />
      <HowItWorks />
      <CubeSplitSection />
      <TechStrip />
      <FinalCTA />
    </div>
  );
}
