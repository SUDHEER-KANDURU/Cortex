"use client"

import { useState, useEffect, useRef } from "react"
import { SectionTitle } from "@/components/ui/section-title"

// =============================================================================
// CortexOutputs — replaces the old "What developers say" testimonials section.
// Shows real product artifacts Cortex can generate, with live animated previews.
// =============================================================================

// ── Architecture Diagram Output Preview ──────────────────────────────────────
function ArchitectureOutput({ active }: { active: boolean }) {
  const [step, setStep] = useState(0)

  useEffect(() => {
    if (!active) { setStep(0); return }
    let s = 0
    const t = setInterval(() => {
      s += 1
      setStep(s)
      if (s >= 8) clearInterval(t)
    }, 280)
    return () => clearInterval(t)
  }, [active])

  const boxes = [
    { label: "api/",       x: 20,  y: 16,  fill: "#111" },
    { label: "domain/",    x: 145, y: 16,  fill: "#333" },
    { label: "infra/",     x: 20,  y: 86,  fill: "#555" },
    { label: "shared/",    x: 145, y: 86,  fill: "#777" },
    { label: "workers/",   x: 82,  y: 155, fill: "#999" },
  ]
  const edges = [
    [0, 1], [0, 2], [1, 3], [2, 3], [2, 4], [3, 4], [0, 4],
  ]
  const cx = (i: number) => boxes[i].x + 42
  const cy = (i: number) => boxes[i].y + 13

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
      <svg viewBox="0 0 268 192" style={{ width: "100%", maxWidth: 268, overflow: "visible" }}>
        {edges.map(([a, b], i) => (
          <line key={i}
            x1={cx(a)} y1={cy(a)} x2={cx(b)} y2={cy(b)}
            stroke={step > i + boxes.length ? "#333" : "rgba(0,0,0,0.06)"}
            strokeWidth="1.5"
            strokeDasharray={i > 3 ? "4 3" : "none"}
            style={{ transition: "stroke 0.3s ease" }} />
        ))}
        {boxes.map((box, i) => (
          <g key={i} style={{ opacity: step > i ? 1 : 0, transition: "opacity 0.25s ease" }}>
            <rect x={box.x} y={box.y} width={84} height={26} rx={6}
              fill={step > i ? box.fill : "#f0f0f0"}
              style={{ transition: "fill 0.3s ease" }} />
            <text x={box.x + 42} y={box.y + 17} textAnchor="middle"
              fontSize="8.5" fontWeight="600" fill={step > i ? "#fff" : "#ccc"}
              style={{ fontFamily: "var(--font-mono,'Fira Code',monospace)" }}>
              {box.label}
            </text>
          </g>
        ))}
      </svg>
      <p style={{ fontSize: "9px", color: "rgba(0,0,0,0.35)", fontFamily: "var(--font-mono)", letterSpacing: "0.08em", textAlign: "center" }}>
        5 modules · 7 relationships · auto-generated
      </p>
    </div>
  )
}

// ── Learning Path Output Preview ─────────────────────────────────────────────
function LearningPathOutput({ active }: { active: boolean }) {
  const [revealed, setRevealed] = useState(0)

  useEffect(() => {
    if (!active) { setRevealed(0); return }
    let r = 0
    const t = setInterval(() => {
      r += 1
      setRevealed(r)
      if (r >= 6) clearInterval(t)
    }, 300)
    return () => clearInterval(t)
  }, [active])

  const nodes = [
    { label: "Python Fundamentals", done: true,  week: "Week 1" },
    { label: "FastAPI Routing",      done: true,  week: "Week 2" },
    { label: "Domain Modeling",      done: false, week: "Week 3" },
    { label: "Neo4j Graph Queries",  done: false, week: "Week 4" },
    { label: "Celery & Workers",     done: false, week: "Week 5" },
    { label: "Architecture Patterns",done: false, week: "Week 6" },
  ]

  return (
    <div style={{ padding: "14px 18px", display: "flex", flexDirection: "column", gap: "5px" }}>
      {nodes.map((node, i) => (
        <div key={node.label} style={{
          display: "flex", alignItems: "center", gap: "10px",
          padding: "7px 10px", borderRadius: "8px",
          opacity: i < revealed ? 1 : 0,
          transform: i < revealed ? "none" : "translateX(-8px)",
          transition: `opacity 0.3s ease ${i * 30}ms, transform 0.3s ease ${i * 30}ms`,
          background: node.done ? "rgba(0,0,0,0.04)" : "transparent",
          border: `1px solid ${node.done ? "rgba(0,0,0,0.1)" : "rgba(0,0,0,0.05)"}`,
        }}>
          <span style={{
            width: 18, height: 18, borderRadius: "50%", flexShrink: 0,
            background: node.done ? "#111" : "rgba(0,0,0,0.08)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "8px", color: node.done ? "#fff" : "rgba(0,0,0,0.25)",
            fontFamily: "var(--font-mono)",
          }}>
            {node.done ? "✓" : (i + 1)}
          </span>
          <span style={{ fontSize: "10px", color: node.done ? "#111" : "rgba(0,0,0,0.45)", fontWeight: node.done ? 600 : 400, flex: 1, fontFamily: "var(--font-mono)" }}>
            {node.label}
          </span>
          <span style={{ fontSize: "8px", color: "rgba(0,0,0,0.25)", fontFamily: "var(--font-mono)" }}>
            {node.week}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Interview Questions Output Preview ───────────────────────────────────────
function InterviewOutput({ active }: { active: boolean }) {
  const [current, setCurrent] = useState(0)

  const questions = [
    { q: "What design pattern does JobRepository implement?", a: "Repository pattern — abstracts Neo4j queries behind a domain interface." },
    { q: "How does Cortex avoid circular imports in domain/?", a: "domain/ has zero external dependencies — it only defines pure Python entities." },
    { q: "Why use Celery workers for AST parsing?", a: "Parsing is CPU-bound; Celery distributes work across processes without blocking the API." },
  ]

  useEffect(() => {
    if (!active) { setCurrent(0); return }
    const t = setInterval(() => setCurrent(c => (c + 1) % questions.length), 2800)
    return () => clearInterval(t)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active])

  const q = questions[current]

  return (
    <div style={{ padding: "16px 18px", display: "flex", flexDirection: "column", gap: "10px" }}>
      <div style={{
        padding: "10px 12px", borderRadius: "10px",
        border: "1px solid rgba(0,0,0,0.12)",
        background: "rgba(0,0,0,0.03)",
        transition: "all 0.4s ease",
      }}>
        <p style={{ fontSize: "10px", fontWeight: 600, color: "#111", lineHeight: 1.5, fontFamily: "var(--font-mono)" }}>
          Q{current + 1}: {q.q}
        </p>
      </div>
      <div style={{
        padding: "10px 12px", borderRadius: "10px",
        border: "1px solid rgba(40,200,64,0.2)",
        background: "rgba(40,200,64,0.04)",
        transition: "all 0.4s ease 0.15s",
      }}>
        <p style={{ fontSize: "9.5px", color: "rgba(0,0,0,0.55)", lineHeight: 1.6, fontFamily: "var(--font-mono)" }}>
          → {q.a}
        </p>
      </div>
      <div style={{ display: "flex", gap: "4px", justifyContent: "center", marginTop: "4px" }}>
        {questions.map((_, i) => (
          <span key={i} style={{
            width: i === current ? 16 : 5, height: 5, borderRadius: "3px",
            background: i === current ? "#111" : "rgba(0,0,0,0.12)",
            transition: "all 0.35s ease",
          }} />
        ))}
      </div>
    </div>
  )
}

// ── Self-Analysis Metrics Preview ────────────────────────────────────────────
function SelfAnalysisOutput({ active }: { active: boolean }) {
  const [count, setCount] = useState(0)

  const metrics = [
    { label: "Files Parsed",        value: 241,  unit: "files",    bar: 0.85 },
    { label: "Functions Extracted", value: 1842, unit: "symbols",  bar: 0.72 },
    { label: "Import Edges",        value: 389,  unit: "edges",    bar: 0.60 },
    { label: "Graph Density",       value: 1.61, unit: "edges/node", bar: 0.55 },
  ]

  useEffect(() => {
    if (!active) { setCount(0); return }
    let c = 0
    const t = setInterval(() => {
      c += 1
      setCount(c)
      if (c >= metrics.length) clearInterval(t)
    }, 320)
    return () => clearInterval(t)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active])

  return (
    <div style={{ padding: "14px 18px", display: "flex", flexDirection: "column", gap: "8px" }}>
      {metrics.map((m, i) => (
        <div key={m.label} style={{
          opacity: i < count ? 1 : 0,
          transform: i < count ? "none" : "translateY(6px)",
          transition: `opacity 0.3s ease ${i * 60}ms, transform 0.3s ease ${i * 60}ms`,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
            <span style={{ fontSize: "9.5px", color: "rgba(0,0,0,0.5)", fontFamily: "var(--font-mono)" }}>{m.label}</span>
            <span style={{ fontSize: "10px", fontWeight: 700, color: "#111", fontFamily: "var(--font-mono)" }}>
              {m.value} <span style={{ fontWeight: 400, color: "rgba(0,0,0,0.3)" }}>{m.unit}</span>
            </span>
          </div>
          <div style={{ height: "3px", borderRadius: "2px", background: "rgba(0,0,0,0.07)", overflow: "hidden" }}>
            <div style={{
              height: "100%", borderRadius: "2px",
              background: "#111",
              width: i < count ? `${m.bar * 100}%` : "0%",
              transition: `width 0.7s cubic-bezier(0.16,1,0.3,1) ${i * 80}ms`,
            }} />
          </div>
        </div>
      ))}
    </div>
  )
}

// ── API Spec Preview ─────────────────────────────────────────────────────────
function APISpecOutput({ active }: { active: boolean }) {
  const [lines, setLines] = useState(0)

  const spec = [
    { t: "key",   v: "openapi: 3.0.0" },
    { t: "key",   v: "info:" },
    { t: "val",   v: "  title: Cortex API" },
    { t: "val",   v: "  version: '1.0.0'" },
    { t: "key",   v: "paths:" },
    { t: "route", v: "  /jobs:" },
    { t: "method",v: "    post: submit analysis job" },
    { t: "route", v: "  /jobs/{id}/artifacts:" },
    { t: "method",v: "    get:  list generated outputs" },
  ]

  useEffect(() => {
    if (!active) { setLines(0); return }
    let l = 0
    const t = setInterval(() => {
      l += 1
      setLines(l)
      if (l >= spec.length) clearInterval(t)
    }, 180)
    return () => clearInterval(t)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active])

  const lineColor = (type: string) => {
    switch (type) {
      case "key":    return "#333"
      case "val":    return "rgba(0,0,0,0.45)"
      case "route":  return "#111"
      case "method": return "rgba(0,0,0,0.4)"
      default:       return "rgba(0,0,0,0.3)"
    }
  }

  return (
    <div style={{ padding: "14px 18px", fontFamily: "var(--font-mono,'Fira Code',monospace)", fontSize: "10.5px", lineHeight: "1.9" }}>
      {spec.map((line, i) => (
        <div key={i} style={{
          color: lineColor(line.t),
          opacity: i < lines ? 1 : 0,
          transition: "opacity 0.2s ease",
          fontWeight: line.t === "route" ? 600 : 400,
        }}>
          {line.v}
        </div>
      ))}
      {lines >= spec.length && (
        <span style={{
          display: "inline-block", width: 7, height: 13,
          background: "rgba(0,0,0,0.3)", verticalAlign: "middle",
          animation: "caret-blink 0.9s step-end infinite",
        }} />
      )}
    </div>
  )
}

// ── Output Card ───────────────────────────────────────────────────────────────
interface OutputDef {
  id: string
  label: string
  headline: string
  description: string
  Visual: React.FC<{ active: boolean }>
}

const OUTPUTS: OutputDef[] = [
  {
    id: "arch",
    label: "Architecture Diagram",
    headline: "See every module and dependency at a glance",
    description: "Auto-generated Mermaid flowchart showing how your codebase is actually wired together.",
    Visual: ArchitectureOutput,
  },
  {
    id: "path",
    label: "Learning Path",
    headline: "Structured curriculum from your own codebase",
    description: "Ordered by concepts actually present in your repo — not generic tutorials.",
    Visual: LearningPathOutput,
  },
  {
    id: "interview",
    label: "Interview Questions",
    headline: "Questions grounded in your actual code",
    description: "Harder and more relevant than anything online. Generated from your repository's real patterns.",
    Visual: InterviewOutput,
  },
  {
    id: "metrics",
    label: "Self-Analysis Report",
    headline: "Quantified structural complexity",
    description: "Graph density, symbol counts, cyclomatic complexity — all derived from the knowledge graph.",
    Visual: SelfAnalysisOutput,
  },
  {
    id: "api",
    label: "API Specification",
    headline: "OpenAPI 3.0 spec from your endpoints",
    description: "Inferred from FastAPI route definitions, Pydantic models, and docstrings.",
    Visual: APISpecOutput,
  },
]

import type React from "react"

function OutputCard({ output, index }: { output: OutputDef; index: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const [active, setActive] = useState(false)
  const played = useRef(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !played.current) {
        played.current = true
        setTimeout(() => setActive(true), index * 80)
        obs.disconnect()
      }
    }, { threshold: 0.2 })
    obs.observe(el)
    return () => obs.disconnect()
  }, [index])

  return (
    <div
      ref={ref}
      data-spotlight
      style={{
        borderRadius: "20px",
        overflow: "hidden",
        background: "rgba(255,255,255,0.68)",
        backdropFilter: "blur(12px) saturate(180%)",
        WebkitBackdropFilter: "blur(12px) saturate(180%)",
        border: "1px solid rgba(255,255,255,0.9)",
        boxShadow: "0 4px 24px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,1)",
        transition: "box-shadow 0.4s ease, transform 0.4s cubic-bezier(0.16,1,0.3,1)",
        opacity: active ? 1 : 0,
        transform: active ? "none" : "translateY(20px)",
      }}
    >
      {/* Visual preview area */}
      <div style={{
        borderBottom: "1px solid rgba(0,0,0,0.06)",
        minHeight: "160px",
        display: "flex",
        alignItems: "center",
        background: "rgba(255,255,255,0.4)",
      }}>
        <div style={{ width: "100%" }}>
          <output.Visual active={active} />
        </div>
      </div>

      {/* Label + description */}
      <div style={{ padding: "16px 18px" }}>
        <div style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          padding: "2px 10px",
          borderRadius: "100px",
          background: "rgba(0,0,0,0.06)",
          marginBottom: "8px",
        }}>
          <span style={{
            fontSize: "8px", fontWeight: 700, letterSpacing: "0.12em",
            textTransform: "uppercase", color: "rgba(0,0,0,0.45)",
            fontFamily: "var(--font-mono,'Fira Code',monospace)",
          }}>
            {output.label}
          </span>
        </div>
        <h3 style={{
          fontFamily: "var(--font-display,'Syne',sans-serif)",
          fontSize: "14px", fontWeight: 600, color: "#111",
          lineHeight: 1.3, margin: "0 0 5px",
        }}>
          {output.headline}
        </h3>
        <p style={{ fontSize: "11px", color: "rgba(0,0,0,0.45)", lineHeight: 1.6, margin: 0 }}>
          {output.description}
        </p>
      </div>
    </div>
  )
}

// ── Section ───────────────────────────────────────────────────────────────────
export function PortfolioTestimonials() {
  return (
    <section
      id="testimonials"
      className="py-20 md:py-32"
      style={{
        borderTop: "1px solid rgba(255,255,255,0.65)",
        background: "rgba(255,255,255,0.52)",
        backdropFilter: "blur(8px) saturate(160%)",
        WebkitBackdropFilter: "blur(8px) saturate(160%)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.9)",
      }}
    >
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">
        {/* Section header */}
        <div className="mb-12 md:mb-16" data-reveal="up">
          <p style={{
            fontSize: "10px", fontWeight: 700, letterSpacing: "0.15em",
            textTransform: "uppercase", color: "rgba(0,0,0,0.35)",
            fontFamily: "var(--font-mono,'Fira Code',monospace)",
            marginBottom: "10px",
          }}>
            Artifacts
          </p>
          <SectionTitle className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight">
            What Cortex generates
          </SectionTitle>
          <p className="mt-4 text-base max-w-xl" style={{ color: "rgba(0,0,0,0.45)", lineHeight: 1.7 }}>
            Every artifact is derived from your repository's knowledge graph — not templates, not guesswork.
          </p>
        </div>

        {/* Grid — 3 cols on lg, 2 on md, 1 on mobile */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6">
          {OUTPUTS.map((output, i) => (
            <OutputCard key={output.id} output={output} index={i} />
          ))}
        </div>
      </div>
    </section>
  )
}
