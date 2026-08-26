"use client"

import type React from "react"
import { ArrowUpRight } from "lucide-react"
import { SectionTitle } from "@/components/ui/section-title"
import { DashboardLink } from "@/components/shared/DashboardLink"
import { useEffect, useRef, useState } from "react"
import { motion, useReducedMotion } from "framer-motion"
import { SPRING, DURATION, EASE } from "@/lib/utils/motion"

// ── Visuals — ink palette only, zero blue/purple ──────────────────────────────

function ArchitectureDemoVisual({ onStart }: { onStart?: (startFn: () => void) => void }) {
  const [nodeStep, setNodeStep] = useState(0)
  const [edgeStep, setEdgeStep] = useState(0)
  const [activeEdge, setActiveEdge] = useState(-1)

  useEffect(() => {
    if (!onStart) return
    onStart(() => {
      let n = 0
      // Animate root first, then children one by one
      const nodeTimer = setInterval(() => {
        if (document.visibilityState === 'hidden') return
        n += 1
        setNodeStep(n)
        if (n >= 5) {
          clearInterval(nodeTimer)
          // Then draw edges one by one
          let e = 0
          const edgeTimer = setInterval(() => {
            if (document.visibilityState === 'hidden') return
            e += 1
            setEdgeStep(e)
            if (e >= 4) {
              clearInterval(edgeTimer)
              // Pulse active edge
              let p = 0
              const pulseTimer = setInterval(() => {
                if (document.visibilityState === 'hidden') return
                p = (p + 1) % 4
                setActiveEdge(p)
              }, 700)
              return () => clearInterval(pulseTimer)
            }
          }, 180)
        }
      }, 200)
      return () => clearInterval(nodeTimer)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Layout: 1 root at top-center, 4 children in a row below
  // SVG viewBox: 0 0 280 130
  const root     = { label: "cortex/", x: 140, y: 20,  w: 72, h: 24, fill: "#e4e4e7", textFill: "#111827" }
  const children = [
    { label: "api/",    x: 28,  y: 88, w: 58, h: 22, fill: "#3f3f46", textFill: "#e4e4e7" },
    { label: "domain/", x: 96,  y: 88, w: 66, h: 22, fill: "#3f3f46", textFill: "#e4e4e7" },
    { label: "infra/",  x: 172, y: 88, w: 58, h: 22, fill: "#3f3f46", textFill: "#e4e4e7" },
    { label: "shared/", x: 240, y: 88, w: 64, h: 22, fill: "#3f3f46", textFill: "#e4e4e7" },
  ]

  // Edge: root bottom-center → child top-center
  const rootBX = root.x
  const rootBY = root.y + root.h
  const edges = children.map(c => ({
    x1: rootBX, y1: rootBY,
    x2: c.x + c.w / 2, y2: c.y,
  }))

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: "16px", background: "rgba(15,20,28,0.88)", backdropFilter: "blur(8px) saturate(180%)", WebkitBackdropFilter: "blur(8px) saturate(180%)" }}>
      <svg viewBox="0 0 280 130" style={{ width: "100%", maxWidth: 310, overflow: "visible" }}>
        {/* Edges — drawn after nodes appear */}
        {edges.map((edge, i) => {
          const visible = edgeStep > i
          const isActive = activeEdge === i
          // Elbow path: vertical down from root, then diagonal to child
          const midY = (rootBY + edge.y2) / 2
          const d = `M ${edge.x1} ${edge.y1} L ${edge.x1} ${midY} L ${edge.x2} ${midY} L ${edge.x2} ${edge.y2}`
          return (
            <path key={i} d={d} fill="none"
              stroke={visible ? (isActive ? "#e4e4e7" : "rgba(255,255,255,0.30)") : "rgba(255,255,255,0.04)"}
              strokeWidth={isActive ? 1.8 : 1.2}
              style={{ transition: "stroke 0.3s ease, stroke-width 0.3s ease" }} />
          )
        })}

        {/* Root node */}
        <g style={{
          opacity: nodeStep >= 1 ? 1 : 0,
          transform: nodeStep >= 1 ? "none" : "translateY(-8px)",
          transition: "opacity 0.35s ease, transform 0.35s ease",
        }}>
          <rect x={root.x - root.w / 2} y={root.y} width={root.w} height={root.h} rx={6} fill={root.fill} />
          <text x={root.x} y={root.y + 15} textAnchor="middle"
            fontSize="9" fontWeight="700" fill={root.textFill}
            style={{ fontFamily: "var(--font-mono,'JetBrains Mono',monospace)" }}>
            {root.label}
          </text>
        </g>

        {/* Child nodes */}
        {children.map((c, i) => (
          <g key={i} style={{
            opacity: nodeStep >= i + 2 ? 1 : 0,
            transform: nodeStep >= i + 2 ? "none" : "translateY(8px)",
            transition: `opacity 0.35s ease ${i * 40}ms, transform 0.35s ease ${i * 40}ms`,
          }}>
            <rect x={c.x} y={c.y} width={c.w} height={c.h} rx={5} fill={c.fill} />
            <text x={c.x + c.w / 2} y={c.y + 14} textAnchor="middle"
              fontSize="8" fontWeight="600" fill={c.textFill}
              style={{ fontFamily: "var(--font-mono,'JetBrains Mono',monospace)" }}>
              {c.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}

function LearningPathVisual() {
  const nodes = [
    { label: "Python Basics", x: 50,  done: true  },
    { label: "FastAPI",       x: 150, done: true  },
    { label: "SQLAlchemy",    x: 250, done: true  },
    { label: "Domain Models", x: 100, done: false },
    { label: "Use Cases",     x: 200, done: false },
    { label: "Graph Queries", x: 150, done: false },
  ]
  const yPos = [30, 70, 70, 110, 110, 145]
  const fills = ["rgba(255,255,255,0.90)","rgba(255,255,255,0.70)","rgba(255,255,255,0.50)","rgba(255,255,255,0.14)","rgba(255,255,255,0.14)","rgba(255,255,255,0.14)"]

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: "20px", background: "rgba(15,20,28,0.88)", backdropFilter: "blur(8px) saturate(180%)", WebkitBackdropFilter: "blur(8px) saturate(180%)" }}>
      <svg viewBox="0 0 300 175" style={{ width: "100%", maxWidth: 300, overflow: "visible" }}>
        {[[0,1],[0,2],[1,3],[2,4],[3,5],[4,5]].map(([a, b], i) => (
          <line key={i}
            x1={nodes[a].x} y1={yPos[a] + 10}
            x2={nodes[b].x} y2={yPos[b]}
            stroke={nodes[a].done ? "rgba(255,255,255,0.35)" : "rgba(255,255,255,0.08)"}
            strokeWidth="1.5" strokeDasharray={nodes[a].done ? "none" : "4 3"} />
        ))}
        {nodes.map((n, i) => (
          <g key={i}>
            <rect x={n.x - 38} y={yPos[i]} width={76} height={20} rx={10} fill={fills[i]} />
            <text x={n.x} y={yPos[i] + 13} textAnchor="middle"
              fontSize="7" fontWeight="600"
              fill={n.done ? "#111827" : "#9ca3af"}
              style={{ fontFamily: "var(--font-mono,'JetBrains Mono',monospace)" }}>
              {n.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}

function InterviewPrepVisual({ onStart }: { onStart?: (startFn: () => void) => void }) {
  const [idx, setIdx] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const questions = [
    "What design pattern does JobRepository use?",
    "How does Celery handle task retries here?",
    "Explain the dependency between api/ and domain/",
  ]
  useEffect(() => {
    if (!onStart) return
    onStart(() => {
      setRevealed(true)
      // Cycle through questions with a delay
      let i = 0
      const t = setInterval(() => {
        if (document.visibilityState === 'hidden') return
        i = (i + 1) % questions.length
        setIdx(i)
      }, 1800)
      return () => clearInterval(t)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: "20px", background: "rgba(15,20,28,0.88)", backdropFilter: "blur(8px) saturate(180%)", WebkitBackdropFilter: "blur(8px) saturate(180%)" }}>
      <div style={{ width: "100%", maxWidth: 300 }}>
        {questions.map((q, i) => (
          <div key={i} style={{
            padding: "8px 12px", marginBottom: "6px", borderRadius: "10px",
            fontSize: "10px", fontWeight: 500,
            fontFamily: "var(--font-mono,'JetBrains Mono',monospace)",
            border: `1px solid ${i === idx ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.08)"}`,
            background: i === idx ? "rgba(255,255,255,0.10)" : "rgba(255,255,255,0.03)",
            color: i === idx ? "#e4e4e7" : "#71717a",
            opacity: revealed ? 1 : 0,
            transition: "all 0.4s cubic-bezier(0.16,1,0.3,1)",
            transform: i === idx ? "translateX(4px)" : "none",
            display: "flex", alignItems: "center", gap: "8px",
          }}>
            <span style={{ fontSize: "8px", opacity: 0.55, color: "#71717a" }}>Q{i + 1}</span>
            {q}
          </div>
        ))}
        <div style={{
          marginTop: "8px", padding: "8px 12px", borderRadius: "10px",
          fontSize: "9px", fontFamily: "var(--font-mono,'JetBrains Mono',monospace)",
          background: "rgba(52,211,153,0.12)", border: "1px solid rgba(52,211,153,0.30)",
          color: "#34d399",
          opacity: revealed ? 1 : 0,
          transition: "opacity 0.5s ease 0.3s",
        }}>
          ✓ Model answer generated from your code
        </div>
      </div>
    </div>
  )
}

function VibeCodeVisual({ onStart }: { onStart?: (startFn: () => void) => void }) {
  const [revealed, setRevealed] = useState(false)
  const [highlight, setHighlight] = useState(-1)
  useEffect(() => {
    if (!onStart) return
    onStart(() => {
      setRevealed(true)
      // Pulse through each issue in sequence
      let i = 0
      const t = setInterval(() => {
        if (document.visibilityState === 'hidden') return
        setHighlight(i % 3)
        i++
      }, 1200)
      return () => clearInterval(t)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const issues = [
    { line: "14", text: "Missing error handling", severity: "high", color: "#ef4444" },
    { line: "27", text: "Duplicate logic block",  severity: "med",  color: "#f59e0b" },
    { line: "41", text: "Inconsistent naming",    severity: "low",  color: "#555"    },
  ]

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: "20px", background: "rgba(15,20,28,0.88)", backdropFilter: "blur(8px) saturate(180%)", WebkitBackdropFilter: "blur(8px) saturate(180%)" }}>
      <div style={{ width: "100%", maxWidth: 300, fontFamily: "var(--font-mono,'JetBrains Mono',monospace)" }}>
        <div style={{ marginBottom: "8px", fontSize: "9px", color: "#71717a", letterSpacing: "0.1em", textTransform: "uppercase",
          opacity: revealed ? 1 : 0, transition: "opacity 0.4s ease" }}>
          repository.py — 3 issues found
        </div>
        {issues.map((issue, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: "8px",
            padding: "7px 10px", marginBottom: "5px", borderRadius: "8px",
            border: `1px solid ${issue.color}40`,
            background: highlight === i ? `${issue.color}14` : `${issue.color}07`,
            opacity: revealed ? 1 : 0,
            transform: revealed ? "none" : "translateX(-8px)",
            transition: `opacity 0.4s ease ${i * 80}ms, transform 0.4s ease ${i * 80}ms, background 0.35s ease`,
            boxShadow: highlight === i ? `0 0 0 1px ${issue.color}40` : "none",
          }}>
            <span style={{ fontSize: "8px", color: issue.color, fontWeight: 700, minWidth: 24 }}>L{issue.line}</span>
            <span style={{ fontSize: "9px", color: "#a1a1aa", flex: 1 }}>{issue.text}</span>
            <span style={{ fontSize: "7px", fontWeight: 700, textTransform: "uppercase", color: issue.color, letterSpacing: "0.06em" }}>{issue.severity}</span>
          </div>
        ))}
        <div style={{ marginTop: "8px", display: "flex", alignItems: "center", gap: "6px", fontSize: "9px", color: "#71717a",
          opacity: revealed ? 1 : 0, transition: "opacity 0.5s ease 0.4s" }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#34d399", display: "inline-block" }} />
          LLM-free — static analysis only
        </div>
      </div>
    </div>
  )
}

interface Work {
  id: number; title: string; category: string; description: string
  Visual: React.FC<{ onStart?: (startFn: (() => (() => void) | void)) => void; active?: boolean }>
  tags: string[]; accent: string
}

function WorkCard({ work, index }: { work: Work; index: number }) {
  const cardRef = useRef<HTMLDivElement>(null)
  const hasPlayed = useRef(false)
  const startAnimationRef = useRef<(() => (() => void) | void) | null>(null)
  const cleanupRef = useRef<(() => void) | null>(null)
  const [inView, setInView] = useState(false)
  const prefersReduced = useReducedMotion()

  const handleRegisterStart = (startFn: (() => (() => void) | void)) => {
    startAnimationRef.current = startFn
  }

  useEffect(() => {
    const cardEl = cardRef.current
    if (!cardEl) return
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !hasPlayed.current) {
        hasPlayed.current = true
        setInView(true)
        if (startAnimationRef.current) {
          const cleanup = startAnimationRef.current()
          if (typeof cleanup === 'function') cleanupRef.current = cleanup
        }
        obs.disconnect()
      }
    }, { threshold: 0.15 })
    obs.observe(cardEl)
    return () => {
      obs.disconnect()
      if (cleanupRef.current) { cleanupRef.current(); cleanupRef.current = null }
    }
  }, [])

  return (
    <div ref={cardRef} className="sticky" style={{ top: `${80 + index * 16}px`, zIndex: index + 1 }}>
      <motion.div
        className="pt-6"
        initial={prefersReduced ? false : { opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.12 }}
        transition={{ duration: DURATION.reveal, delay: index * 0.06, ease: EASE.out }}
      >
        <DashboardLink className="group block">
          <motion.article
            data-spotlight
            className="overflow-hidden rounded-2xl md:rounded-3xl"
            style={{
              background: "rgba(240, 238, 235, 0.82)",
              backdropFilter: "blur(32px) saturate(200%)",
              WebkitBackdropFilter: "blur(32px) saturate(200%)",
              border: "0.5px solid rgba(255,255,255,0.50)",
              boxShadow: "0 4px 24px rgba(80,60,20,0.08), inset 0 1px 0 rgba(255,255,255,0.70)",
            }}
            whileHover={prefersReduced ? {} : {
              y: -6,
              boxShadow: "0 24px 64px rgba(0,0,0,0.22), 0 4px 16px rgba(0,0,0,0.12)",
              transition: SPRING.snappy,
            }}
          >
            <div className="relative overflow-hidden"
              style={{
                height: "200px",
                borderBottom: "1px solid rgba(255,255,255,0.40)",
                background: "rgba(240, 238, 235, 0.60)",
                backdropFilter: "blur(8px)",
              }}>
              <work.Visual onStart={handleRegisterStart} active={inView} />
              <div className="cx-pill" style={{
                position: "absolute", top: "12px", left: "12px",
                padding: "3px 10px", borderRadius: "100px",
                fontSize: "9px", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase",
                backdropFilter: "blur(12px) saturate(180%)",
                WebkitBackdropFilter: "blur(12px) saturate(180%)",
                fontFamily: "var(--font-mono,'JetBrains Mono',monospace)",
              }}>
                {work.category}
              </div>
            </div>

            <div className="p-5 md:p-6" style={{ background: "rgba(240, 238, 235, 0.88)" }}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="cx-text text-lg md:text-xl font-semibold">{work.title}</h3>
                  <p className="cx-text-muted text-sm mt-1.5 leading-relaxed">{work.description}</p>
                </div>
                {/* Arrow — rotates & shifts on group hover via CSS */}
                <motion.div
                  className="cx-arrow-circle flex-shrink-0 mt-0.5 w-8 h-8 rounded-full flex items-center justify-center"
                  whileHover={prefersReduced ? {} : { scale: 1.15, backgroundColor: "#000", transition: SPRING.snappy }}
                >
                  <ArrowUpRight className="cx-arrow-color w-4 h-4 transition-all duration-300 group-hover:!text-white group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </motion.div>
              </div>
              <div className="flex flex-wrap gap-2 mt-4">
                {work.tags.map(tag => (
                  <span key={tag} className="cx-tag px-3 py-1 text-xs font-medium rounded-full">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </motion.article>
        </DashboardLink>
      </motion.div>
    </div>
  )
}

const works: Work[] = [
  { id: 1, title: "Architecture Diagram Generator", category: "Code Intelligence",
    description: "Auto-generates Mermaid flowcharts showing every module, dependency, and service boundary in your codebase.",
    Visual: ArchitectureDemoVisual, tags: ["AST Parsing", "Neo4j", "Mermaid"], accent: "#111" },
  { id: 2, title: "Learning Path Builder", category: "Developer Education",
    description: "Identifies every concept and pattern in your repository and creates a personalised curriculum ordered from fundamentals to advanced.",
    Visual: LearningPathVisual, tags: ["Knowledge Graph", "NLP", "FastAPI"], accent: "#444" },
  { id: 3, title: "Interview Prep Engine", category: "Career Tools",
    description: "Generates technical questions grounded in your actual project code with model answers. Walk into any interview prepared.",
    Visual: InterviewPrepVisual, tags: ["Graph Queries", "Python", "Celery"], accent: "#d97706" },
  { id: 4, title: "Vibe Code Detector", category: "Code Quality",
    description: "Flags AI-generated anti-patterns — missing error handling, duplicate logic, inconsistent naming — and explains exactly how to fix each one.",
    Visual: VibeCodeVisual, tags: ["Static Analysis", "LLM-free", "Neo4j"], accent: "#ef4444" },
]

export function PortfolioSelectedWorks() {
  return (
    <section id="works" className="py-20 md:py-10 md:pt-32 pb-4"
      style={{
        borderTop: "1px solid var(--cx-card-border)",
        background: "var(--cx-section-bg)",
        backdropFilter: "saturate(200%) blur(24px)",
        WebkitBackdropFilter: "saturate(200%) blur(24px)",
      }}>
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">
        <div className="flex items-center justify-between mb-12 md:mb-16">
          <div>
            <p className="cx-eyebrow" style={{
              fontSize: "10px", fontWeight: 700, letterSpacing: "0.16em",
              textTransform: "uppercase",
              fontFamily: "var(--font-mono,'JetBrains Mono',monospace)", marginBottom: "8px",
            }}>
              Outputs
            </p>
            <SectionTitle className="text-3xl md:text-4xl lg:text-[52px] font-semibold tracking-tight">
              Capabilities
            </SectionTitle>
          </div>
          <DashboardLink
            className="cx-link hidden md:inline-flex items-center gap-2 text-sm font-medium transition-all duration-200 hover:gap-3">
            Launch App
            <ArrowUpRight className="w-4 h-4" />
          </DashboardLink>
        </div>
        <div className="relative">
          {works.map((work, index) => <WorkCard key={work.id} work={work} index={index} />)}
        </div>
        <div className="md:hidden mt-8 text-center">
          <DashboardLink
            className="cx-link cx-row inline-flex items-center gap-2 px-6 py-3 text-sm font-medium rounded-full transition-colors">
            Launch App <ArrowUpRight className="w-4 h-4" />
          </DashboardLink>
        </div>
      </div>
    </section>
  )
}


