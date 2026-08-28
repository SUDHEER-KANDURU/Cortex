"use client"

// =============================================================================
// HowItWorks — Scroll-pinned cinematic pipeline
//
// Behaviour:
//  • Section pins to viewport while you scroll through all 6 steps
//  • Each step advances with scroll (1/6 of scroll runway per step)
//  • When idle (no scroll) the steps auto-cycle every 3.2 s
//  • Releasing the scroll lets the page continue past the section
//  • Zero blue, zero purple — monochrome + ink palette only
// =============================================================================

import React, { useEffect, useRef, useState, useCallback } from "react"
import gsap from "gsap"

// ── Palette — NO blue, NO purple ─────────────────────────────────────────────

const STEP_COLORS = {
  active:   "var(--primary)",
  inactive: "var(--text-muted)",
  line:     "var(--border)",
  dot:      "var(--primary)",
  dotText:  "#FFFFFF",
  border:   "var(--border)",
  panelBg:  "var(--cx-section-bg, rgba(15,17,23,0.60))",
  scanCurrent: "var(--text)",
  scanDone:    "var(--success)",
  astNode:     "var(--text)",
  graphRoot:   "var(--primary)",
  graphMod:    "var(--text-secondary)",
  graphFile:   "var(--text-muted)",
  graphEdge:   "var(--border)",
  graphEdgeActive: "var(--primary)",
  artifactBg:  "var(--cx-pill-bg)",
  artifactBorder: "var(--cx-pill-border)",
}

// ── Visuals ───────────────────────────────────────────────────────────────────

function ScanVisual({ active }: { active: boolean }) {
  const [tick, setTick] = useState(0)
  useEffect(() => {
    if (!active) { setTick(0); return }
    const t = setInterval(() => {
      if (document.visibilityState === 'hidden') return
      setTick(v => v + 1)
    }, 180)
    return () => clearInterval(t)
  }, [active])

  const files = [
    "src/cortex/main.py",
    "src/cortex/config.py",
    "src/cortex/graph/domain/entities.py",
    "src/cortex/artifacts/application/use_cases.py",
    "src/cortex/jobs/infrastructure/repository.py",
    "src/cortex/graph/presentation/router.py",
  ]
  const cur = Math.floor(tick / 2) % (files.length + 1)

  return (
    <div style={{ padding: "20px 24px", fontFamily: "var(--font-mono)", fontSize: "11px" }}>
      {files.map((f, i) => {
        const shown = cur > i
        const current = cur === i
        return (
          <div key={f} style={{
            display: "flex", alignItems: "center", gap: "10px",
            padding: "5px 8px", borderRadius: "6px", marginBottom: "3px",
            background: current ? "var(--primary-dim)" : "transparent",
            opacity: shown || current ? 1 : 0.25,
            transition: "all 0.25s ease",
          }}>
            <span style={{
              color: shown ? STEP_COLORS.scanDone : (current ? STEP_COLORS.scanCurrent : "var(--text-muted)"),
              fontSize: "10px", minWidth: "12px",
            }}>
              {shown ? "✓" : (current ? "›" : "·")}
            </span>
            <span style={{ color: current ? STEP_COLORS.scanCurrent : "var(--text-muted)" }}>{f}</span>
          </div>
        )
      })}
      <div style={{
        marginTop: "12px", display: "flex", alignItems: "center", gap: "7px",
        fontSize: "10px", color: STEP_COLORS.scanCurrent, fontWeight: 600,
        letterSpacing: "0.04em",
      }}>
        <span style={{
          display: "inline-block", width: 7, height: 12,
          background: STEP_COLORS.scanCurrent, verticalAlign: "middle",
          animation: active ? "caret-blink 0.9s step-end infinite" : "none",
        }} />
        {active ? "Scanning repository…" : "Repository scanned"}
      </div>
    </div>
  )
}

function ASTVisual({ active }: { active: boolean }) {
  const nodes = [
    { label: "Module",   x: 120, y: 8   },
    { label: "ClassDef", x: 50,  y: 58  },
    { label: "FuncDef",  x: 190, y: 58  },
    { label: "Assign",   x: 20,  y: 108 },
    { label: "Return",   x: 88,  y: 108 },
    { label: "Call",     x: 162, y: 108 },
    { label: "Name",     x: 218, y: 108 },
  ]
  const edges = [[0,1],[0,2],[1,3],[1,4],[2,5],[2,6]]
  const [rev, setRev] = useState(0)

  useEffect(() => {
    if (!active) { setRev(0); return }
    const t = setInterval(() => {
      if (document.visibilityState === 'hidden') return
      setRev(v => Math.min(v + 1, nodes.length + edges.length))
    }, 220)
    return () => clearInterval(t)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active])

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
      <svg viewBox="0 0 280 145" style={{ width: "100%", maxWidth: 300, overflow: "visible" }}>
        {edges.map(([a, b], i) => {
          const from = nodes[a], to = nodes[b]
          const show = rev > nodes.length + i
          return (
            <line key={i}
              x1={from.x + 28} y1={from.y + 12}
              x2={to.x + 28}   y2={to.y}
              stroke={show ? STEP_COLORS.astNode : "transparent"}
              strokeWidth="1.5" opacity="0.3"
              style={{ transition: "stroke 0.3s ease" }} />
          )
        })}
        {nodes.map((n, i) => {
          const isRoot = i === 0
          const isMid  = i <= 2
          const show   = rev > i
          const fill   = show ? (isRoot ? "var(--primary)" : isMid ? "var(--text-secondary)" : "var(--text-muted)") : "var(--border)"
          return (
            <g key={i} style={{ opacity: show ? 1 : 0, transition: "opacity 0.25s ease" }}>
              <rect x={n.x} y={n.y} width={56} height={22} rx={5} fill={fill} />
              <text x={n.x + 28} y={n.y + 14} textAnchor="middle"
                fontSize="7.5" fontWeight="700" fill={show ? "#FFFFFF" : "var(--text-muted)"}
                style={{ fontFamily: "var(--font-mono)" }}>
                {n.label}
              </text>
            </g>
          )
        })}
      </svg>
      <p style={{ fontSize: "10px", color: "var(--text-muted)", fontFamily: "var(--font-mono)", letterSpacing: "0.06em" }}>
        abstract syntax tree extracted
      </p>
    </div>
  )
}

function GraphVisual({ active }: { active: boolean }) {
  const [pulse, setPulse] = useState(0)
  useEffect(() => {
    if (!active) return
    const t = setInterval(() => {
      if (document.visibilityState === 'hidden') return
      setPulse(p => (p + 1) % 6)
    }, 480)
    return () => clearInterval(t)
  }, [active])

  const gNodes = [
    { id: "cortex/",    x: 130, y: 65,  r: 15, fill: STEP_COLORS.graphRoot   },
    { id: "api/",       x: 45,  y: 22,  r: 10, fill: STEP_COLORS.graphMod    },
    { id: "domain/",    x: 215, y: 22,  r: 10, fill: STEP_COLORS.graphMod    },
    { id: "infra/",     x: 45,  y: 108, r: 10, fill: STEP_COLORS.graphMod    },
    { id: "shared/",    x: 215, y: 108, r: 10, fill: STEP_COLORS.graphMod    },
    { id: "router.py",  x: 5,   y: 60,  r:  6, fill: STEP_COLORS.graphFile   },
    { id: "entities.py",x: 245, y: 60,  r:  6, fill: STEP_COLORS.graphFile   },
  ]
  const gEdges = [[0,1],[0,2],[0,3],[0,4],[1,5],[2,6]]

  return (
    <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
      <svg viewBox="0 0 260 135" style={{ width: "100%", maxWidth: 280, overflow: "visible" }}>
        {gEdges.map(([a, b], i) => {
          const from = gNodes[a], to = gNodes[b]
          const isHot = active && pulse === i
          return (
            <line key={i}
              x1={from.x} y1={from.y}
              x2={to.x}   y2={to.y}
              stroke={isHot ? STEP_COLORS.graphEdgeActive : STEP_COLORS.graphEdge}
              strokeWidth={isHot ? 1.8 : 1}
              style={{ transition: "all 0.35s ease" }} />
          )
        })}
        {gNodes.map((n, i) => (
          <g key={i}>
            <circle cx={n.x} cy={n.y} r={n.r} fill={n.fill}
              style={{
                filter: active && pulse % gNodes.length === i
                  ? `drop-shadow(0 0 5px ${n.fill}aa)` : "none",
                transition: "filter 0.35s ease",
              }} />
            <text x={n.x} y={n.y + n.r + 9} textAnchor="middle"
              fontSize="6" fill="var(--text-muted)"
              style={{ fontFamily: "var(--font-mono)" }}>
              {n.id}
            </text>
          </g>
        ))}
      </svg>
      <p style={{ fontSize: "10px", color: "var(--text-muted)", fontFamily: "var(--font-mono)", letterSpacing: "0.06em" }}>
        241 nodes · 387 relationships
      </p>
    </div>
  )
}

function ArtifactsVisual({ active }: { active: boolean }) {
  const artifacts = [
    { name: "Architecture Diagram", icon: "⬡", delay: 0    },
    { name: "Learning Path",        icon: "◈", delay: 120  },
    { name: "API Spec",             icon: "◎", delay: 240  },
    { name: "Interview Prep",       icon: "◆", delay: 360  },
    { name: "Vibe Code Report",     icon: "◉", delay: 480  },
    { name: "Onboarding Guide",     icon: "◐", delay: 600  },
  ]

  return (
    <div style={{ padding: "16px 20px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
      {artifacts.map((a) => (
        <div key={a.name} style={{
          display: "flex", alignItems: "center", gap: "9px",
          padding: "9px 12px", borderRadius: "10px",
          border: "1px solid var(--cx-pill-border)",
          background: active ? "var(--cx-pill-bg)" : "var(--surface)",
          backdropFilter: "blur(12px) saturate(160%)",
          WebkitBackdropFilter: "blur(12px) saturate(160%)",
          boxShadow: active ? "var(--shadow-sm)" : "none",
          transition: `all 0.45s ease ${active ? a.delay : 0}ms`,
          transform: active ? "none" : "translateY(8px)",
          opacity: active ? 1 : 0,
        }}>
          <span style={{ fontSize: "13px", color: "var(--primary)" }}>{a.icon}</span>
          <span style={{
            fontSize: "9px", fontWeight: 600, color: "var(--text-secondary)",
            fontFamily: "var(--font-mono)", lineHeight: 1.3,
          }}>
            {a.name}
          </span>
        </div>
      ))}
    </div>
  )
}

function RepositoryVisual({ active }: { active: boolean }) {
  const [pulse, setPulse] = useState(0)
  useEffect(() => {
    if (!active) { setPulse(0); return }
    const t = setInterval(() => {
      if (document.visibilityState === 'hidden') return
      setPulse(v => v + 1)
    }, 600)
    return () => clearInterval(t)
  }, [active])

  const items = [
    { label: "main",       icon: "⌥", depth: 0 },
    { label: "src/",       icon: "◈", depth: 1 },
    { label: "tests/",     icon: "◈", depth: 1 },
    { label: "README.md",  icon: "◎", depth: 1 },
    { label: "pyproject.toml", icon: "◎", depth: 1 },
  ]

  return (
    <div style={{ padding: "20px 24px", fontFamily: "var(--font-mono)", fontSize: "11px" }}>
      <div style={{
        display: "flex", alignItems: "center", gap: "8px",
        marginBottom: "14px", fontSize: "10px",
        color: "var(--text-muted)", letterSpacing: "0.08em",
      }}>
        <span style={{
          display: "inline-block", width: 8, height: 8, borderRadius: "50%",
          background: active ? "var(--success)" : "var(--border)",
          transition: "background 0.4s ease",
        }} />
        {active ? "Connected — cloning…" : "Awaiting URL"}
      </div>
      {items.map((item, i) => {
        const isHighlighted = active && pulse % (items.length + 1) === i
        return (
          <div key={item.label} style={{
            display: "flex", alignItems: "center", gap: "8px",
            paddingLeft: `${item.depth * 16 + 8}px`,
            padding: `5px 8px 5px ${item.depth * 16 + 8}px`,
            borderRadius: "6px", marginBottom: "3px",
            background: isHighlighted ? "var(--primary-dim)" : "transparent",
            opacity: active ? (isHighlighted ? 1 : 0.65) : 0.25,
            transition: "all 0.3s ease",
          }}>
            <span style={{ fontSize: "9px", color: "var(--text-muted)", minWidth: "12px" }}>{item.icon}</span>
            <span style={{ color: isHighlighted ? "var(--text)" : "var(--text-muted)" }}>{item.label}</span>
          </div>
        )
      })}
      <div style={{
        marginTop: "12px", padding: "8px 10px", borderRadius: "8px",
        background: "var(--surface)", border: "1px solid var(--border)",
        fontSize: "10px", color: "var(--text-muted)", letterSpacing: "0.05em",
      }}>
        <span style={{ color: "var(--text-muted)", marginRight: "6px" }}>$</span>
        git clone {active ? <span style={{ opacity: 0.6 }}>github.com/…</span> : "—"}
      </div>
    </div>
  )
}

function ReasoningEngineVisual({ active }: { active: boolean }) {
  const [step, setStep] = useState(0)
  useEffect(() => {
    if (!active) { setStep(0); return }
    const t = setInterval(() => {
      if (document.visibilityState === 'hidden') return
      setStep(v => (v + 1) % 5)
    }, 700)
    return () => clearInterval(t)
  }, [active])

  const thoughts = [
    "Traversing dependency subgraph…",
    "Resolving cross-module refs…",
    "Ranking symbol relevance…",
    "Composing context window…",
    "Generating reasoning chain…",
  ]

  return (
    <div style={{ padding: "20px 24px", fontFamily: "var(--font-mono)", fontSize: "11px" }}>
      <div style={{
        display: "flex", alignItems: "center", gap: "8px",
        marginBottom: "14px", fontSize: "10px", color: "var(--text-muted)", letterSpacing: "0.06em",
      }}>
        <span style={{
          display: "inline-block", width: 7, height: 12,
          background: active ? "var(--primary)" : "var(--border)",
          verticalAlign: "middle",
          animation: active ? "caret-blink 0.9s step-end infinite" : "none",
        }} />
        {active ? "Reasoning engine active" : "Idle"}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {thoughts.map((thought, i) => {
          const isDone    = active && i < step
          const isCurrent = active && i === step
          return (
            <div key={thought} style={{
              display: "flex", alignItems: "center", gap: "10px",
              padding: "6px 10px", borderRadius: "8px",
              background: isCurrent ? "var(--primary-dim)" : "transparent",
              opacity: isDone ? 0.45 : (isCurrent ? 1 : 0.2),
              transition: "all 0.35s ease",
            }}>
              <span style={{
                fontSize: "9px",
                color: isDone ? "var(--success)" : (isCurrent ? "var(--primary)" : "var(--text-muted)"),
                minWidth: "12px",
              }}>
                {isDone ? "✓" : (isCurrent ? "›" : "·")}
              </span>
              <span style={{ color: isCurrent ? "var(--text)" : "var(--text-muted)", lineHeight: 1.4 }}>
                {thought}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── ConnectorLine — SVG draw-on connector between adjacent stage bubbles ─────
const LINE_LENGTH = 20 // SVG line height in px (matches previous 20px div)

interface ConnectorLineProps {
  active: boolean  // when true, triggers draw-on animation
  isDone: boolean  // when true, show line fully without animation
}

function ConnectorLine({ active, isDone }: ConnectorLineProps) {
  const lineRef = useRef<SVGLineElement>(null)
  const glowRef = useRef<SVGLineElement>(null)
  const hasAnimated = useRef(false)

  useEffect(() => {
    const line = lineRef.current
    const glow = glowRef.current
    if (!line || !glow) return

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReducedMotion) {
      if (lineRef.current) lineRef.current.style.strokeDashoffset = '0'
      if (glowRef.current) glowRef.current.style.strokeDashoffset = '0'
      return
    }

    if (isDone) {
      line.style.strokeDashoffset = "0"
      glow.style.strokeDashoffset = "0"
      hasAnimated.current = true
      return
    }

    if (active && !hasAnimated.current) {
      hasAnimated.current = true
      gsap.fromTo(
        [line, glow],
        { strokeDashoffset: LINE_LENGTH },
        { strokeDashoffset: 0, duration: 0.4, ease: "power2.out" }
      )
    }

    if (!active && !isDone) {
      hasAnimated.current = false
      line.style.strokeDashoffset = String(LINE_LENGTH)
      glow.style.strokeDashoffset = String(LINE_LENGTH)
    }
  }, [active, isDone])

  // Particle animation runs entirely in CSS — no GSAP tween, no JS loop.
  // The SVG element uses a CSS animation when isDone is true.
  const particleStyle: React.CSSProperties = isDone
    ? { animation: 'connector-flow 2s linear infinite', opacity: 0.6 }
    : { opacity: 0 }

  return (
    <>
      {/* Keyframe defined once per ConnectorLine instance — tiny overhead */}
      <style>{`
        @keyframes connector-flow {
          from { stroke-dashoffset: ${LINE_LENGTH}; }
          to   { stroke-dashoffset: ${-LINE_LENGTH}; }
        }
      `}</style>
      <svg
        width="2"
        height={LINE_LENGTH}
        viewBox={`0 0 2 ${LINE_LENGTH}`}
        overflow="visible"
        style={{ display: "block", margin: "0 auto" }}
        aria-hidden="true"
      >
        {/* Glow line */}
        <line
          ref={glowRef}
          x1="1" y1="0" x2="1" y2={LINE_LENGTH}
          stroke="var(--border-hover)"
          strokeWidth="2"
          strokeDasharray={LINE_LENGTH}
          strokeDashoffset={isDone ? 0 : LINE_LENGTH}
          opacity={(isDone || active) ? 0.4 : 0}
          style={{ transition: "opacity 0.3s ease" }}
        />
        {/* Main connector line */}
        <line
          ref={lineRef}
          x1="1" y1="0" x2="1" y2={LINE_LENGTH}
          stroke={isDone ? "var(--text-muted)" : "var(--border)"}
          strokeWidth="1"
          strokeDasharray={LINE_LENGTH}
          strokeDashoffset={isDone ? 0 : LINE_LENGTH}
        />
        {/* Data-flow particle — CSS animation, zero JS overhead */}
        <line
          x1="1" y1="0" x2="1" y2={LINE_LENGTH}
          stroke="var(--primary)"
          strokeWidth="2"
          strokeDasharray={`3 ${LINE_LENGTH}`}
          strokeDashoffset={LINE_LENGTH}
          style={particleStyle}
        />
      </svg>
    </>
  )
}

// ── Pipeline stages — 6 entries per spec requirement 2.1 ──────────────────────
const STEPS = [
  {
    number: "01",
    title: "Repository",
    description: "Paste any GitHub URL. Cortex clones and recursively indexes every file — Python, JS, TypeScript, and more.",
    Visual: RepositoryVisual,
  },
  {
    number: "02",
    title: "Scanning",
    description: "Every file is discovered, read, and queued for parsing. Cortex records file types, sizes, and entry points.",
    Visual: ScanVisual,
  },
  {
    number: "03",
    title: "AST Parsing",
    description: "Every file is parsed at the syntax-tree level. Functions, classes, imports, and relationships are extracted — not just text.",
    Visual: ASTVisual,
  },
  {
    number: "04",
    title: "Knowledge Graph",
    description: "All symbols and dependencies are written as nodes and edges into Neo4j. The structure of your codebase becomes queryable.",
    Visual: GraphVisual,
  },
  {
    number: "05",
    title: "Reasoning Engine",
    description: "Cortex traverses the knowledge graph, resolves cross-module references, and composes a rich context for generation.",
    Visual: ReasoningEngineVisual,
  },
  {
    number: "06",
    title: "Artifacts",
    description: "Cortex queries the graph and generates architecture diagrams, learning paths, interview questions, and more.",
    Visual: ArtifactsVisual,
  },
]

// ── EngineeringTerminal — the large prominent terminal visual ────────────────
// This replaces the small panel and becomes the primary visual of the section.

interface LogLine {
  text: string
  type: "cmd" | "info" | "ok" | "node" | "edge" | "artifact" | "think" | "step"
}

const TERMINAL_LOGS: Record<number, LogLine[]> = {
  0: [
    { type: "cmd",  text: "$ cortex connect github.com/cortex-hq/cortex" },
    { type: "info", text: "  Authenticating via SSH keypair…" },
    { type: "ok",   text: "  ✓ Authentication successful" },
    { type: "info", text: "  Cloning repository… [████████░░] 83%" },
    { type: "ok",   text: "  ✓ Clone complete — 2,847 files discovered" },
    { type: "info", text: "  Indexing directory tree…" },
    { type: "node", text: "  src/   infra/   api/   domain/   tests/" },
    { type: "ok",   text: "  ✓ Repository connected and indexed" },
  ],
  1: [
    { type: "cmd",  text: "$ cortex scan --recursive --workers=8" },
    { type: "info", text: "  [01/8] Dispatching file workers…" },
    { type: "step", text: "  ├─ src/cortex/main.py                    .py" },
    { type: "step", text: "  ├─ src/cortex/config.py                  .py" },
    { type: "step", text: "  ├─ src/cortex/graph/domain/entities.py   .py" },
    { type: "step", text: "  ├─ src/cortex/artifacts/use_cases.py     .py" },
    { type: "step", text: "  ├─ src/cortex/jobs/infrastructure/repo.py .py" },
    { type: "ok",   text: "  ✓ 241 files scanned · 12 entry points found" },
  ],
  2: [
    { type: "cmd",  text: "$ cortex parse --lang=python --extract-all" },
    { type: "info", text: "  Building abstract syntax trees…" },
    { type: "node", text: "  Module       → 1 root node" },
    { type: "node", text: "  ClassDef     → 47 class definitions" },
    { type: "node", text: "  FuncDef      → 213 function definitions" },
    { type: "edge", text: "  Import       → 389 import relationships" },
    { type: "edge", text: "  Inheritance  → 23 class hierarchies" },
    { type: "ok",   text: "  ✓ AST complete — 672 nodes · 412 edges extracted" },
  ],
  3: [
    { type: "cmd",  text: "$ cortex graph --backend=neo4j --merge" },
    { type: "info", text: "  Connecting to Neo4j bolt://localhost:7687…" },
    { type: "ok",   text: "  ✓ Connected — schema validation passed" },
    { type: "node", text: "  CREATE (n:Module {name:'cortex.main'})   +1" },
    { type: "node", text: "  CREATE (n:Class {name:'JobRepository'})  +1" },
    { type: "edge", text: "  CREATE (a)-[:IMPORTS]->(b)               +389" },
    { type: "edge", text: "  CREATE (a)-[:DEPENDS_ON]->(b)            +241" },
    { type: "ok",   text: "  ✓ Graph written — 241 nodes · 387 relationships" },
  ],
  4: [
    { type: "cmd",  text: "$ cortex reason --depth=5 --strategy=bfs" },
    { type: "info", text: "  Traversing dependency subgraph…" },
    { type: "think",text: "  → Resolving cross-module references…" },
    { type: "think",text: "  → Ranking symbol relevance [BFS depth=3]" },
    { type: "think",text: "  → Composing context window [4,096 tokens]" },
    { type: "info", text: "  Building reasoning chain…" },
    { type: "ok",   text: "  ✓ Context assembled — 6 inference passes complete" },
  ],
  5: [
    { type: "cmd",  text: "$ cortex generate --all --format=markdown" },
    { type: "info", text: "  Generating artifacts from knowledge graph…" },
    { type: "artifact", text: "  ✓ architecture_diagram.md        [4.2 KB]" },
    { type: "artifact", text: "  ✓ learning_path.md               [8.7 KB]" },
    { type: "artifact", text: "  ✓ interview_questions.md         [11.1 KB]" },
    { type: "artifact", text: "  ✓ api_spec.yaml                  [2.9 KB]" },
    { type: "artifact", text: "  ✓ onboarding_guide.md            [6.3 KB]" },
    { type: "ok",   text: "  ✓ All 6 artifacts generated successfully" },
  ],
}

function EngineeringTerminal({ activeStep }: { activeStep: number }) {
  const [visibleLines, setVisibleLines] = useState<number>(0)
  const prevStep = useRef<number>(-1)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const logs = TERMINAL_LOGS[activeStep] ?? []

  useEffect(() => {
    if (prevStep.current === activeStep) return
    prevStep.current = activeStep

    setVisibleLines(0)
    if (timerRef.current) clearInterval(timerRef.current)

    let count = 0
    timerRef.current = setInterval(() => {
      if (document.visibilityState === 'hidden') return
      count += 1
      setVisibleLines(count)
      if (count >= logs.length) {
        if (timerRef.current) clearInterval(timerRef.current)
      }
    }, 250)

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [activeStep, logs.length])

  const lineColor = (type: LogLine["type"]): string => {
    switch (type) {
      case "cmd":      return "#e4e4e7"
      case "ok":       return "#34d399"
      case "node":     return "#a1a1aa"
      case "edge":     return "#71717a"
      case "artifact": return "#d4d4d8"
      case "think":    return "#737373"
      case "step":     return "#52525b"
      case "info":
      default:         return "#71717a"
    }
  }

  const stepLabel = STEPS[activeStep]?.title ?? ""
  const stepNum   = STEPS[activeStep]?.number ?? "01"

  return (
    <div style={{
      background: "rgba(18, 20, 24, 0.88)",
      borderRadius: "16px",
      border: "1px solid rgba(255,255,255,0.10)",
      boxShadow: "0 16px 48px rgba(0,0,0,0.28), 0 4px 12px rgba(0,0,0,0.18)",
      overflow: "hidden",
      height: "100%",
      display: "flex",
      flexDirection: "column",
    }}>
      {/* Terminal chrome bar */}
      <div style={{
        background: "rgba(30, 32, 36, 0.92)",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        padding: "11px 16px",
        display: "flex",
        alignItems: "center",
        gap: "8px",
        flexShrink: 0,
      }}>
        <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#E07070", display: "block" }} />
        <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#D4A055", display: "block" }} />
        <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#6AAF7C", display: "block" }} />
        <div style={{ flex: 1, display: "flex", justifyContent: "center", alignItems: "center", gap: "8px" }}>
          <span style={{
            fontSize: "10px", fontWeight: 700, letterSpacing: "0.12em",
            textTransform: "uppercase", color: "rgba(160,160,170,0.85)",
            fontFamily: "var(--font-mono)",
          }}>
            cortex — step {stepNum} / {STEPS.length} — {stepLabel}
          </span>
        </div>
        <span style={{
          width: "6px", height: "6px", borderRadius: "50%",
          background: "#34d399", display: "inline-block",
        }} />
      </div>

      {/* Log output area */}
      <div style={{
        flex: 1,
        padding: "20px 22px",
        fontFamily: "var(--font-mono)",
        fontSize: "12.5px",
        lineHeight: "2",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        justifyContent: "flex-start",
        gap: "0",
      }}>
        {logs.map((line, i) => (
          <div key={`${activeStep}-${i}`} style={{
            color: lineColor(line.type),
            opacity: i < visibleLines ? 1 : 0,
            transform: i < visibleLines ? "translateY(0)" : "translateY(6px)",
            transition: "opacity 0.2s ease, transform 0.2s ease",
            whiteSpace: "pre",
            fontWeight: line.type === "cmd" ? 600 : (line.type === "ok" || line.type === "artifact") ? 500 : 400,
          }}>
            {line.text}
          </div>
        ))}
        {/* Blinking cursor at end */}
        {visibleLines >= logs.length && (
          <div style={{ color: "#52525b", display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{
              display: "inline-block", width: "8px", height: "14px",
              background: "#52525b", verticalAlign: "middle",
              animation: "caret-blink 0.9s step-end infinite",
            }} />
          </div>
        )}
      </div>

      {/* Status bar */}
      <div style={{
        borderTop: "1px solid rgba(255,255,255,0.08)",
        padding: "6px 16px",
        background: "rgba(30, 32, 36, 0.92)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#34d399", display: "inline-block" }} />
          <span style={{ fontSize: "10px", color: "rgba(160,160,170,0.75)", fontFamily: "var(--font-mono)", letterSpacing: "0.06em" }}>
            cortex-engine · python 3.12 · neo4j connected
          </span>
        </div>
        <span style={{ fontSize: "10px", color: "rgba(160,160,170,0.75)", fontFamily: "var(--font-mono)", letterSpacing: "0.06em" }}>
          UTF-8
        </span>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export function PortfolioHowItWorks() {
  const [activeStep, setActiveStep] = useState(0)
  const wrapperRef    = useRef<HTMLDivElement>(null)   // the tall scroll runway
  const autoTimerRef  = useRef<ReturnType<typeof setInterval> | null>(null)
  const isScrolling   = useRef(false)
  const scrollTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ── Start / restart the auto-cycle timer ──────────────────────────────────
  const startAuto = useCallback(() => {
    if (autoTimerRef.current) clearInterval(autoTimerRef.current)
    autoTimerRef.current = setInterval(() => {
      if (document.visibilityState === 'hidden') return
      setActiveStep(s => (s + 1) % STEPS.length)
    }, 3200)
  }, [])

  const stopAuto = useCallback(() => {
    if (autoTimerRef.current) {
      clearInterval(autoTimerRef.current)
      autoTimerRef.current = null
    }
  }, [])

  // ── Scroll-driven step advancement ────────────────────────────────────────
  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReducedMotion) {
      setActiveStep(STEPS.length - 1) // show all stages
      return
    }

    const wrapper = wrapperRef.current
    if (!wrapper) return

    // Only attach scroll listener and auto-timer while section is on-screen.
    // This prevents the setInterval and scroll handler from firing across the
    // entire landing page scroll, which caused ~60 calls/s of useless work.
    let removeScroll: (() => void) | null = null

    const startListening = () => {
      if (removeScroll) return  // already listening

      startAuto()

      const onScroll = () => {
        const w = wrapperRef.current
        if (!w) return

        const rect     = w.getBoundingClientRect()
        const total    = w.offsetHeight - window.innerHeight
        const scrolled = -(rect.top - 56)
        const progress = Math.max(0, Math.min(1, scrolled / total))
        const step     = Math.min(Math.floor(progress * STEPS.length), STEPS.length - 1)

        setActiveStep(step)

        if (!isScrolling.current) {
          isScrolling.current = true
          stopAuto()
        }
        if (scrollTimeout.current) clearTimeout(scrollTimeout.current)
        scrollTimeout.current = setTimeout(() => {
          isScrolling.current = false
          startAuto()
        }, 2000)
      }

      window.addEventListener("scroll", onScroll, { passive: true })
      removeScroll = () => {
        window.removeEventListener("scroll", onScroll)
        stopAuto()
        if (scrollTimeout.current) clearTimeout(scrollTimeout.current)
      }
    }

    const stopListening = () => {
      removeScroll?.()
      removeScroll = null
    }

    // IntersectionObserver: start/stop when section enters/leaves viewport
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) startListening()
        else stopListening()
      },
      { threshold: 0 },
    )
    io.observe(wrapper)

    return () => {
      io.disconnect()
      stopListening()
    }
  }, [startAuto, stopAuto])

  return (
    // Tall wrapper — 300vh gives the scroll runway for all 6 steps
    <div
      ref={wrapperRef}
      id="how-it-works"
      style={{ height: "300vh", position: "relative" }}
    >
      {/* ── Sticky inner — glass panel, dark/light aware ── */}
      <div style={{
        position: "sticky",
        top: 56,
        height: "calc(100vh - 56px)",
        borderTop: "1px solid var(--cx-card-border)",
        borderBottom: "1px solid var(--cx-card-border)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        // This panel is sticky and full-height, so any backdrop-filter here is
        // re-sampled on every frame of the pinned scroll animation. Use an
        // opaque-ish tint instead of a live blur to keep the pin smooth.
        background: "rgba(244,242,239,0.82)",
        paddingTop: "8px",
        paddingBottom: "8px",
      }}>
        <div className="max-w-[1280px] mx-auto px-6 md:px-12 w-full">

          {/* Mobile-only header */}
          <div className="flex flex-col gap-3 mb-5 md:hidden">
            <div>
              <p style={{
                fontSize: "10px", fontWeight: 700, letterSpacing: "0.15em",
                textTransform: "uppercase", color: "var(--cx-eyebrow)",
                fontFamily: "var(--font-mono)",
                marginBottom: "8px",
              }}>
                Pipeline
              </p>
              <h2 className="text-3xl font-semibold tracking-tight cx-text"
                style={{ fontFamily: "var(--font-sans)", letterSpacing: "-0.04em", lineHeight: 1.1 }}>
                How Cortex works
              </h2>
            </div>
            <p className="text-sm leading-relaxed cx-text-muted">
              Six steps from raw repository to structured understanding.
            </p>
          </div>

          {/* ── Desktop layout ── */}
          <div className="hidden md:grid gap-8 lg:gap-14" style={{ gridTemplateColumns: "5fr 7fr", alignItems: "center" }}>

            {/* Left: header + step list */}
            <div className="flex flex-col gap-0">

              {/* Header — title + subtitle stacked in the left column */}
              <div className="mb-5 md:mb-8">
                <div>
                  <p style={{
                    fontSize: "10px", fontWeight: 700, letterSpacing: "0.15em",
                    textTransform: "uppercase", color: "var(--cx-eyebrow)",
                    fontFamily: "var(--font-mono)",
                    marginBottom: "8px",
                  }}>
                    Pipeline
                  </p>
                  <h2 className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight cx-text"
                    style={{ fontFamily: "var(--font-sans)", letterSpacing: "-0.04em", lineHeight: 1.1 }}>
                    How Cortex works
                  </h2>
                  <p className="text-sm leading-relaxed cx-text-muted mt-2">
                    Six steps from raw repository to structured understanding.
                  </p>
                </div>
              </div>
              {STEPS.map((step, i) => {
                const isActive = i === activeStep
                const isDone   = i < activeStep
                return (
                  <button
                    key={step.number}
                    onClick={() => { stopAuto(); setActiveStep(i); setTimeout(startAuto, 4000) }}
                    style={{ outline: "none", border: "none", background: "none", textAlign: "left", cursor: "pointer" }}>
                    <div style={{
                      display: "flex", alignItems: "flex-start", gap: "12px",
                      padding: isActive ? "10px 12px" : "6px 12px",
                      borderRadius: "12px",
                      background: isActive ? "var(--cx-pill-bg)" : "transparent",
                      backdropFilter: isActive ? "blur(8px) saturate(180%)" : "none",
                      WebkitBackdropFilter: isActive ? "blur(8px) saturate(180%)" : "none",
                      border: isActive ? "1px solid var(--cx-pill-border)" : "1px solid transparent",
                      boxShadow: isActive ? "var(--shadow-sm)" : "none",
                      transition: "all 0.4s cubic-bezier(0.16,1,0.3,1)",
                    }}>
                      {/* Number bubble + connector line */}
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
                        <div style={{
                          width: "28px", height: "28px", borderRadius: "50%",
                          background: isActive ? "var(--primary)" : (isDone ? "var(--success)" : "var(--cx-stat-bg)"),
                          border: `1px solid ${isActive ? "transparent" : isDone ? "transparent" : "var(--cx-stat-border)"}`,
                          display: "flex", alignItems: "center", justifyContent: "center",
                          transition: "background 0.35s ease",
                          boxShadow: isActive ? "0 0 10px var(--primary-glow)" : "none",
                        }}>
                          <span style={{
                            fontSize: "10px", fontWeight: 700,
                            color: (isActive || isDone) ? (isActive ? "#FFFFFF" : "var(--text-secondary)") : "var(--text-muted)",
                            fontFamily: "var(--font-mono)",
                            transition: "color 0.3s ease",
                          }}>
                            {isDone ? "✓" : step.number}
                          </span>
                        </div>
                        {i < STEPS.length - 1 && (
                          <ConnectorLine active={isActive} isDone={isDone} />
                        )}
                      </div>

                      {/* Text */}
                      <div style={{ paddingTop: "5px", flex: 1, minWidth: 0 }}>
                        <h3 style={{
                          fontFamily: "var(--font-sans)",
                          fontSize: "13px", fontWeight: 600,
                          color: isActive ? "var(--text)" : "var(--text-muted)",
                          transition: "color 0.35s ease",
                          margin: 0,
                        }}>
                          {step.title}
                        </h3>
                        <div style={{
                          overflow: "hidden",
                          transform: isActive ? "scaleY(1)" : "scaleY(0)",
                          transformOrigin: "top",
                          opacity: isActive ? 1 : 0,
                          transition: "transform 0.4s cubic-bezier(0.16,1,0.3,1), opacity 0.3s ease",
                          pointerEvents: isActive ? "auto" : "none",
                        }}>
                          <p style={{
                            fontSize: "11px", lineHeight: 1.5,
                            color: "var(--text-muted)",
                            marginTop: "2px",
                          }}>
                            {step.description}
                          </p>
                        </div>
                      </div>
                    </div>
                  </button>
                )
              })}

              {/* Scroll progress indicator */}
              <div style={{ marginTop: "10px", paddingLeft: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
                {STEPS.map((_, i) => (
                  <div key={i} style={{
                    height: "2px",
                    flex: i === activeStep ? 3 : 1,
                    borderRadius: "2px",
                    background: i <= activeStep ? "var(--primary)" : "var(--border)",
                    transition: "all 0.4s cubic-bezier(0.16,1,0.3,1)",
                  }} />
                ))}
                <span style={{ fontSize: "9px", color: "var(--text-muted)", fontFamily: "var(--font-mono)", letterSpacing: "0.08em", marginLeft: "4px" }}>
                  {activeStep + 1} / {STEPS.length}
                </span>
              </div>
            </div>

            {/* Right: engineering terminal — vertically centered */}
            <div style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "calc(100vh - 56px - 80px)",
              minHeight: "360px",
            }}>
              <div style={{ width: "100%", maxHeight: "480px", height: "100%" }}>
                <EngineeringTerminal activeStep={activeStep} />
              </div>
            </div>
          </div>

          {/* ── Mobile: stacked static cards ── */}
          <div className="flex flex-col gap-4 md:hidden">
            {STEPS.map((step, i) => (
              <div key={step.number} style={{
                borderRadius: "16px",
                overflow: "hidden",
                background: i === activeStep ? "var(--cx-pill-bg)" : "var(--cx-row-bg)",
                backdropFilter: "blur(8px) saturate(180%)",
                WebkitBackdropFilter: "blur(8px) saturate(180%)",
                border: i === activeStep
                  ? "1px solid var(--cx-pill-border)"
                  : "1px solid var(--cx-card-border)",
                boxShadow: i === activeStep ? "var(--shadow-md)" : "none",
                transition: "all 0.4s cubic-bezier(0.16,1,0.3,1)",
              }}>
                <div style={{
                  padding: "14px 16px",
                  borderBottom: "1px solid var(--cx-card-border)",
                  background: "var(--surface)",
                  display: "flex", alignItems: "center", gap: "12px",
                }}>
                  <div style={{
                    width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
                    background: i === activeStep ? "var(--primary)" : "var(--cx-stat-bg)",
                    border: `1px solid ${i === activeStep ? "transparent" : "var(--cx-stat-border)"}`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    transition: "background 0.3s ease",
                    boxShadow: i === activeStep ? "var(--shadow-sm)" : "none",
                  }}>
                    <span style={{
                      fontSize: "10px", fontWeight: 700,
                      color: i === activeStep ? "#FFFFFF" : "var(--text-muted)",
                      fontFamily: "var(--font-mono)",
                    }}>{step.number}</span>
                  </div>
                  <div>
                    <h3 style={{
                      fontFamily: "var(--font-sans)",
                      fontSize: "14px", fontWeight: 600, margin: 0,
                      color: "var(--text)",
                    }}>{step.title}</h3>
                    <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>{step.description}</p>
                  </div>
                </div>
                <step.Visual active={i === activeStep} />
              </div>
            ))}
          </div>

        </div>
      </div>
    </div>
  )
}

